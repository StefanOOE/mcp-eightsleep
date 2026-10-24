"""Client: login once, reuse the token, log in again after a 401, clear errors."""
import io
import json
import urllib.error
from datetime import date

import pytest

from mcp_eightsleep import client as client_module
from mcp_eightsleep.client import Client, EightSleepError


class Responses:  # pylint: disable=too-few-public-methods
    """Fake urlopen: answers by URL, can fail the first trends call with 401."""

    def __init__(self, fail_trends_once=False):
        self.calls = []
        self.fail = fail_trends_once

    def __call__(self, request, timeout):
        url = request.full_url
        self.calls.append(url.split("?")[0])
        if url.endswith("/tokens"):
            body = {"access_token": f"t{len(self.calls)}", "expires_in": 3600, "userId": "u1"}
        elif url.endswith("/users/me"):
            body = {"user": {"currentDevice": {"timeZone": "Europe/Vienna", "side": "left"}}}
        elif "/trends" in url:
            if self.fail:
                self.fail = False
                raise urllib.error.HTTPError(url, 401, "expired", {}, io.BytesIO())
            body = {"days": [{"day": "2026-10-22"}, {"day": "2026-10-21"}]}
        else:
            raise urllib.error.HTTPError(url, 404, "nope", {}, io.BytesIO())
        return io.BytesIO(json.dumps(body).encode())


@pytest.fixture(name="login")
def _login(monkeypatch):
    monkeypatch.setenv("EIGHTSLEEP_EMAIL", "you@example.com")
    monkeypatch.setenv("EIGHTSLEEP_PASSWORD", "secret")
    monkeypatch.delenv("EIGHTSLEEP_TIMEZONE", raising=False)


def test_nights_log_in_once_and_sort(monkeypatch, login):  # pylint: disable=unused-argument
    """One login for two calls; nights oldest first."""
    fake = Responses()
    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake)
    eight = Client()
    days = eight.nights(date(2026, 10, 21), date(2026, 10, 22))
    eight.nights(date(2026, 10, 21), date(2026, 10, 22))
    assert [d["day"] for d in days] == ["2026-10-21", "2026-10-22"]
    assert fake.calls.count(client_module.AUTH_URL) == 1
    assert f"{client_module.API_URL}/users/u1/trends" in fake.calls


def test_expired_token_logs_in_again(monkeypatch, login):  # pylint: disable=unused-argument
    """A 401 triggers one fresh login and a retry."""
    fake = Responses(fail_trends_once=True)
    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake)
    assert len(Client().nights(date(2026, 10, 21), date(2026, 10, 22))) == 2
    assert fake.calls.count(client_module.AUTH_URL) == 2


def test_missing_login_is_a_clear_error(monkeypatch):
    """No credentials: a message that names the variables."""
    monkeypatch.delenv("EIGHTSLEEP_EMAIL", raising=False)
    with pytest.raises(EightSleepError, match="EIGHTSLEEP_EMAIL"):
        Client().nights(date(2026, 10, 21), date(2026, 10, 22))


class NoZoneResponses(Responses):  # pylint: disable=too-few-public-methods
    """A profile without a device time zone."""

    def __call__(self, request, timeout):
        if request.full_url.endswith("/users/me"):
            return io.BytesIO(json.dumps({"user": {"currentDevice": {"side": "left"}}}).encode())
        return super().__call__(request, timeout)


def test_time_zone_override_wins(monkeypatch):
    """EIGHTSLEEP_TIMEZONE beats the device - no request needed."""
    monkeypatch.setenv("EIGHTSLEEP_TIMEZONE", "Asia/Tokyo")

    assert Client().timezone() == "Asia/Tokyo"


def test_time_zone_uses_the_device_zone(monkeypatch, login):  # pylint: disable=unused-argument
    """Without an override the device's own zone is used."""
    monkeypatch.setattr(client_module.urllib.request, "urlopen", Responses())

    assert Client().timezone() == "Europe/Vienna"


def test_time_zone_falls_back_to_utc(monkeypatch, login):  # pylint: disable=unused-argument
    """No override and no device zone: UTC, not a hard-coded European zone."""
    monkeypatch.setattr(client_module.urllib.request, "urlopen", NoZoneResponses())

    assert Client().timezone() == "UTC"
