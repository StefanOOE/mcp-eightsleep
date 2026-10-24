"""MCP server: read-only Eight Sleep sleep data as pre-formatted text."""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import config
from .client import Client, EightSleepError
from .night import day_label, night_lines, short_line

mcp = MCPServer(
    "mcp-eightsleep",
    version="0.1.0",
    instructions=(
        "Sleep data measured by the Eight Sleep mattress cover (contact-free, no watch): "
        "get_night(target_date) for one night - scores, times, stages, HRV, heart and "
        "respiratory rate against the user's own averages, bed and room temperature. "
        "Read-only, it cannot control the bed."),
)
_client = Client()


@mcp.tool()
def get_night(target_date: str | None = None, history_days: int = 0) -> str:
    """One night measured by the Eight Sleep mattress, as ready-made text: sleep fitness
    score, time in bed and asleep, stages, HRV, heart rate and respiratory rate (each with
    the user's average, 7-day average and score), bed/room temperature. `target_date`
    (YYYY-MM-DD) is the day the user WOKE UP - 'last night' = today (default).
    `history_days` (0-13) adds one short line per earlier night. Quote the numbers as they are."""
    if target_date is not None:
        try:
            woke = date.fromisoformat(target_date)
        except ValueError:
            raise ToolError(
                f"target_date must be a date as YYYY-MM-DD, got {target_date!r}") from None
    else:
        woke = None
    try:
        history_days = int(history_days)
    except (TypeError, ValueError):
        raise ToolError(
            f"history_days must be a whole number 0-13, got {history_days!r}") from None
    history_days = max(0, min(history_days, 13))
    try:
        zone = _client.timezone()
    except EightSleepError as exc:
        raise ToolError(str(exc)) from None
    try:
        tz = ZoneInfo(zone)
    except ZoneInfoNotFoundError:
        raise ToolError(
            f"{zone} is not a known time zone "
            "(set EIGHTSLEEP_TIMEZONE to an IANA name)") from None
    if woke is None:
        woke = datetime.now(tz).date()
    try:
        nights = {night.get("day"): night
                  for night in _client.nights(woke - timedelta(days=history_days), woke)}
    except EightSleepError as exc:
        raise ToolError(str(exc)) from None
    night = nights.get(woke.isoformat())
    lines = [f"# Eight Sleep night (woke up {day_label(woke)})"]
    if night is None:
        lines.append("No Eight Sleep data for this night (not in bed, away mode, other side, "
                     "or not processed yet).")
    else:
        lines += night_lines(night, tz)
    earlier = [nights[day] for day in sorted(nights) if day < woke.isoformat()]
    if history_days:
        lines.append(f"## Nights before ({len(earlier)} with data)")
        lines += [short_line(n) for n in earlier] or ["- none"]
    return "\n".join(lines)


def main() -> None:
    """Run the server on stdio, warning on stderr when the login is not configured."""
    if not config.email() or not config.password():
        print("mcp-eightsleep: EIGHTSLEEP_EMAIL/EIGHTSLEEP_PASSWORD not set - "
              "get_night will fail", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
