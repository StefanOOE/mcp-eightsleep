"""One night (and a few before it) as pre-formatted text."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def hm(seconds: float | None) -> str:
    """Seconds as '7h45'."""
    if seconds is None:
        return "-"
    minutes = round(seconds / 60)
    return f"{minutes // 60}h{minutes % 60:02d}"


def clock(stamp: str | None, tz: ZoneInfo) -> str:
    """An API time stamp (UTC) as local HH:MM."""
    if not stamp:
        return "?"
    moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    return moment.astimezone(tz).strftime("%H:%M")


def day_label(day: date) -> str:
    """'Thu 22.10'."""
    return f"{WEEKDAYS[day.weekday()]} {day:%d.%m}"


def _metric(night: dict, key: str) -> dict:
    return (night.get("sleepQualityScore") or {}).get(key) or {}


def _vs(metric: dict, unit: str, digits: int = 0) -> str:
    """'42 ms (your avg 40, 7-day 41, score 80)' from a trend metric."""
    def num(value):
        return "-" if value is None else (f"{value:.{digits}f}" if digits else str(round(value)))
    if metric.get("current") is None:
        return "-"
    extra = [f"your avg {num(metric.get('average'))}"]
    if metric.get("inclusive7DayAverage") is not None:
        extra.append(f"7-day {num(metric['inclusive7DayAverage'])}")
    if metric.get("score") is not None:
        extra.append(f"score {metric['score']}/100")
    return f"{num(metric['current'])}{unit} ({', '.join(extra)})"


def _range(series: list | None, unit: str) -> str:
    values = [point[1] for point in series or [] if isinstance(point, list) and len(point) > 1]
    return f"{min(values):.1f}-{max(values):.1f}{unit}" if values else "-"


def _need(debt: dict) -> str:
    """'; sleep need 7h30, sleep debt 0h45' (or surplus) - empty while calibrating."""
    if not debt.get("baselineSleepDurationSeconds"):
        return ""
    balance = debt.get("dailySleepDebtSeconds") or 0
    word = "sleep debt" if balance >= 0 else "sleep surplus"
    return f"; sleep need {hm(debt['baselineSleepDurationSeconds'])}, {word} {hm(abs(balance))}"


def night_lines(night: dict, tz: ZoneInfo) -> list[str]:
    """The full description of one night."""
    quality = night.get("sleepQualityScore") or {}
    routine = night.get("sleepRoutineScore") or {}
    session = (night.get("sessions") or [{}])[0]
    series = session.get("timeseries") or {}
    debt = quality.get("sleepDebt") or {}
    duration = _metric(night, "sleepDurationSeconds")
    latency = routine.get("latencyAsleepSeconds") or {}
    lines = [
        f"Sleep fitness score {night.get('score', '-')}: quality {quality.get('total', '-')}, "
        f"routine {routine.get('total', '-')}" + (" (night still incomplete)"
                                                  if night.get("incomplete") else ""),
        f"In bed {clock(night.get('presenceStart'), tz)}-{clock(night.get('presenceEnd'), tz)}, "
        f"asleep {clock(night.get('sleepStart'), tz)}-"
        f"{clock(night.get('sleepEnd'), tz)}, fell asleep in {hm(latency.get('current'))}",
        f"Sleep {hm(night.get('sleepDuration'))} (your avg {hm(duration.get('average'))}, "
        f"7-day {hm(duration.get('inclusive7DayAverage'))}, score {duration.get('score', '-')}/100)"
        + _need(debt),
        f"Stages: deep {hm(night.get('deepDuration'))} "
        f"({round((night.get('deepPercent') or 0) * 100)}%),"
        f" REM {hm(night.get('remDuration'))} "
        f"({round((night.get('remPercent') or 0) * 100)}%), light "
        f"{hm(night.get('lightDuration'))}; awake after falling asleep "
        f"{hm(night.get('wasoDuration'))}, {night.get('wakeupCount', '-')} wake-ups",
        f"HRV {_vs(_metric(night, 'hrv'), ' ms')}",
        f"Heart rate {_vs(_metric(night, 'heartRate'), ' bpm')}",
        f"Respiratory rate {_vs(_metric(night, 'respiratoryRate'), '/min', 1)}",
        f"Temperature: bed {_range(series.get('tempBedC'), ' °C')}, room "
        f"{_range(series.get('tempRoomC'), ' °C')}",
    ]
    if night.get("snoreDuration"):
        lines.append(f"Snoring {hm(night['snoreDuration'])} ({night.get('snorePercent', 0)}%)")
    return lines


def short_line(night: dict) -> str:
    """One earlier night in a line."""
    hrv = _metric(night, "hrv").get("current")
    heart = _metric(night, "heartRate").get("current")
    day = date.fromisoformat(night["day"])
    return (f"- {day_label(day)}: score {night.get('score', '-')}, sleep "
            f"{hm(night.get('sleepDuration'))}, deep {hm(night.get('deepDuration'))}, HRV "
            f"{'-' if hrv is None else round(hrv)} ms, "
            f"HR {'-' if heart is None else round(heart)} bpm")
