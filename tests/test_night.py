"""get_night against a fake client: formatting, missing nights, history, error messages."""
import asyncio
from datetime import date

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from mcp_eightsleep import server
from mcp_eightsleep.client import EightSleepError


def _metric(current, average, week, score):
    return {"current": current, "average": average, "inclusive7DayAverage": week, "score": score}


NIGHT = {
    "day": "2026-10-22", "score": 78, "incomplete": False,
    "presenceStart": "2026-10-21T19:40:00.000Z", "presenceEnd": "2026-10-22T04:58:00.000Z",
    "presenceDuration": 33480, "sleepStart": "2026-10-21T20:05:00.000Z",
    "sleepEnd": "2026-10-22T04:50:00.000Z", "sleepDuration": 27900,
    "deepDuration": 5400, "deepPercent": 0.19, "remDuration": 6000, "remPercent": 0.21,
    "lightDuration": 16500, "wasoDuration": 1500, "wakeupCount": 3,
    "snoreDuration": 720, "snorePercent": 3,
    "sleepQualityScore": {
        "total": 80, "sleepDurationSeconds": _metric(27900, 26400, 27000, 85),
        "hrv": _metric(42.4, 40, 41.2, 80), "heartRate": _metric(55, 56.3, 56, 75),
        "respiratoryRate": _metric(14.2, 14.5, 14.4, 90),
        "sleepDebt": {"baselineSleepDurationSeconds": 27000, "dailySleepDebtSeconds": 2700}},
    "sleepRoutineScore": {"total": 70, "latencyAsleepSeconds": {"current": 900}},
    "sessions": [{"timeseries": {
        "tempBedC": [["t1", 26.1], ["t2", 28.4]], "tempRoomC": [["t1", 19.5], ["t2", 20.3]]}}],
}
EARLIER = {"day": "2026-10-20", "score": 70, "sleepDuration": 25200, "deepDuration": 4800,
           "sleepQualityScore": {"hrv": {"current": 38.6}, "heartRate": {"current": 57.7}}}


class FakeClient:
    """Returns the nights in the asked range, records the range."""

    def __init__(self, nights):
        self.all = nights
        self.asked = None
        self.error = None
        self.time_zone = "Europe/Vienna"
        self.timezone_error = None

    def timezone(self):
        """The configured time zone (possibly not a real one), or the configured failure."""
        if self.timezone_error is not None:
            raise self.timezone_error
        return self.time_zone

    def nights(self, first, last):
        """The nights in [first, last], or the configured failure."""
        if self.error is not None:
            raise self.error
        self.asked = (first, last)
        return [n for n in self.all if first.isoformat() <= n["day"] <= last.isoformat()]


@pytest.fixture(name="fake")
def _fake(monkeypatch):
    fake = FakeClient([EARLIER, NIGHT])
    monkeypatch.setattr(server, "_client", fake)
    return fake


def test_night_is_formatted_in_local_time(fake):
    """All values of the night, times in the device time zone, durations as h:mm."""
    lines = server.get_night("2026-10-22").splitlines()
    assert fake.asked == (date(2026, 10, 22), date(2026, 10, 22))
    assert lines == [
        "# Eight Sleep night (woke up Thu 22.10)",
        "Sleep fitness score 78: quality 80, routine 70",
        "In bed 21:40-06:58, asleep 22:05-06:50, fell asleep in 0h15",
        "Sleep 7h45 (your avg 7h20, 7-day 7h30, score 85/100); sleep need 7h30, sleep debt 0h45",
        "Stages: deep 1h30 (19%), REM 1h40 (21%), light 4h35; awake after falling asleep 0h25, "
        "3 wake-ups",
        "HRV 42 ms (your avg 40, 7-day 41, score 80/100)",
        "Heart rate 55 bpm (your avg 56, 7-day 56, score 75/100)",
        "Respiratory rate 14.2/min (your avg 14.5, 7-day 14.4, score 90/100)",
        "Temperature: bed 26.1-28.4 °C, room 19.5-20.3 °C",
        "Snoring 0h12 (3%)",
    ]


def test_history_and_missing_night(fake):
    """A night without data is named; history lists only nights with data."""
    text = server.get_night("2026-10-21", history_days=3)
    assert fake.asked == (date(2026, 10, 18), date(2026, 10, 21))
    assert "No Eight Sleep data for this night" in text
    assert text.endswith("## Nights before (1 with data)\n"
                         "- Tue 20.10: score 70, sleep 7h00, deep 1h20, HRV 39 ms, HR 58 bpm")


def test_tool_is_registered():
    """Exactly one tool, named get_night - the name an agent has to call."""
    tools = asyncio.run(server.mcp.list_tools())
    assert [tool.name for tool in tools] == ["get_night"]


def test_invalid_target_date_is_a_tool_error(fake):
    """A non-date target_date is explained, before any API call is made."""
    with pytest.raises(
            ToolError, match="target_date must be a date as YYYY-MM-DD, got 'yesterday'"):
        server.get_night("yesterday")
    assert fake.asked is None


def test_invalid_history_days_is_a_tool_error(fake):
    """A non-numeric history_days is explained, before any API call is made."""
    with pytest.raises(
            ToolError, match="history_days must be a whole number 0-13, got 'drei'"):
        server.get_night("2026-10-22", history_days="drei")  # type: ignore[arg-type]
    assert fake.asked is None


def test_unknown_time_zone_is_a_tool_error(fake):
    """A time zone the system does not know is named, before any API call is made."""
    fake.time_zone = "Mars/Olympus"
    with pytest.raises(ToolError, match="Mars/Olympus is not a known time zone"):
        server.get_night("2026-10-22")
    assert fake.asked is None


def test_api_error_keeps_its_message(fake):
    """A login or API failure reaches the caller with the client's own text."""
    fake.error = EightSleepError("Set EIGHTSLEEP_EMAIL and EIGHTSLEEP_PASSWORD.")
    with pytest.raises(ToolError, match="Set EIGHTSLEEP_EMAIL and EIGHTSLEEP_PASSWORD."):
        server.get_night("2026-10-22")


def test_time_zone_lookup_error_keeps_its_message(fake):
    """A profile call that fails (login needed) reaches the caller with the client's text.

    `timezone()` is itself an API call, so it can raise before the night is fetched.
    """
    fake.timezone_error = EightSleepError("Set EIGHTSLEEP_EMAIL and EIGHTSLEEP_PASSWORD.")
    with pytest.raises(ToolError, match="Set EIGHTSLEEP_EMAIL and EIGHTSLEEP_PASSWORD."):
        server.get_night("2026-10-22")
    assert fake.asked is None
