"""get_night against a fake client: formatting, missing nights, history."""
from datetime import date

import pytest

from mcp_eightsleep import server


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

    def timezone(self):
        """Fixed time zone."""
        return "Europe/Vienna"

    def nights(self, first, last):
        """The nights in [first, last]."""
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
