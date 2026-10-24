"""Minimal client for the (unofficial) Eight Sleep app API - read-only.

Eight Sleep publishes no developer API. This uses the endpoints and the app client id the
Home Assistant integration uses: a password-grant token, the user profile (device, side,
time zone) and the per-night trends. The token is kept in memory and renewed when it expires.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

from . import config

AUTH_URL = "https://auth-api.8slp.net/v1/tokens"
API_URL = "https://client-api.8slp.net/v1"
# The Android app's OAuth client, as used by the Home Assistant integration.
CLIENT_ID = "0894c7f33bb94800a03f1f4df13a4f38"
CLIENT_SECRET = "f0954a3ed5763ba3d06834c73731a32f15f168f47d4f164751275def86db0c76"
HEADERS = {"content-type": "application/json", "accept": "application/json",
           "user-agent": "okhttp/4.9.3"}
TIMEOUT = 20
RENEW_BEFORE_SECONDS = 120


class EightSleepError(Exception):
    """Login or API failure, with a message fit for the user."""


class Client:
    """One Eight Sleep account."""

    def __init__(self) -> None:
        self._token = ""
        self._expires = 0.0
        self._user_id = ""
        self._profile: dict | None = None

    def _request(self, method: str, url: str, body: dict | None = None,
                 auth: bool = True) -> dict:
        headers = dict(HEADERS)
        if auth:
            headers["authorization"] = f"Bearer {self._login()}"
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 401 and auth:
                self._token = ""          # expired early: one fresh login, then give up
                headers["authorization"] = f"Bearer {self._login()}"
                retry = urllib.request.Request(url, data=data, headers=headers, method=method)
                try:
                    with urllib.request.urlopen(retry, timeout=TIMEOUT) as response:
                        return json.load(response)
                except urllib.error.HTTPError as again:
                    exc = again
            raise EightSleepError(f"Eight Sleep API error {exc.code} for "
                                  f"{urllib.parse.urlsplit(url).path}") from None
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise EightSleepError(f"Eight Sleep not reachable: {exc}") from None

    def _login(self) -> str:
        if self._token and time.time() < self._expires - RENEW_BEFORE_SECONDS:
            return self._token
        if not config.email() or not config.password():
            raise EightSleepError("Set EIGHTSLEEP_EMAIL and EIGHTSLEEP_PASSWORD.")
        try:
            answer = self._request("POST", AUTH_URL, {
                "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
                "grant_type": "password", "username": config.email(),
                "password": config.password()}, auth=False)
        except EightSleepError as exc:
            raise EightSleepError(f"Eight Sleep login failed ({exc}).") from None
        self._token = answer["access_token"]
        self._expires = time.time() + float(answer.get("expires_in", 3600))
        self._user_id = answer["userId"]
        return self._token

    def profile(self) -> dict:
        """The user's profile (devices, current device with side and time zone), cached."""
        if self._profile is None:
            self._profile = self._request("GET", f"{API_URL}/users/me")["user"]
        return self._profile

    def timezone(self) -> str:
        """The `EIGHTSLEEP_TIMEZONE` override, else the device's time zone, else "UTC"."""
        return (config.timezone()
                or (self.profile().get("currentDevice") or {}).get("timeZone")
                or "UTC")

    def nights(self, first: date, last: date) -> list[dict]:
        """Per-night trend records ('day' = the day the user woke up), oldest first."""
        self._login()
        query = urllib.parse.urlencode({
            "tz": self.timezone(), "from": first.isoformat(), "to": last.isoformat(),
            "include-main": "false", "include-all-sessions": "true", "model-version": "v2"})
        days = self._request("GET", f"{API_URL}/users/{self._user_id}/trends?{query}")
        return sorted(days.get("days", []), key=lambda night: night.get("day", ""))
