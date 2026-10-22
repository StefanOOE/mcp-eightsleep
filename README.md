# mcp-eightsleep

Read-only MCP server (stdio) for the sleep data of an Eight Sleep mattress cover: one night as
ready-made text that an agent can quote instead of copying values out of JSON.

| Tool | What it returns |
|---|---|
| `get_night(target_date?, history_days=0)` | Sleep fitness score (quality/routine), time in bed and asleep, time to fall asleep, sleep duration vs. your average and sleep need, stages, wake-ups, HRV, heart rate and respiratory rate (each with your average, 7-day average and score), bed and room temperature, snoring. `target_date` is the day you woke up (default today); `history_days` adds one line per earlier night. |

It cannot change anything on the bed (no temperature, alarm or base control).

## Caveat

Eight Sleep has no public developer API. This server uses the app's API with the client id
that the Home Assistant community integration uses, and a password login. It may break when
Eight Sleep changes its app, and accounts that sign in with Apple/Google need a password set
in the app first. Keep the call rate low (one call per check-in is plenty).

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
```

Environment:

| Variable | Meaning |
|---|---|
| `EIGHTSLEEP_EMAIL`, `EIGHTSLEEP_PASSWORD` | account login (required) |
| `EIGHTSLEEP_TIMEZONE` | optional, default: the time zone of your device |

MCP client config:

```json
{"mcpServers": {"mcp-eightsleep": {
  "command": "/path/to/mcp-eightsleep/.venv/bin/python", "args": ["-m", "mcp_eightsleep"],
  "env": {"EIGHTSLEEP_EMAIL": "you@example.com", "EIGHTSLEEP_PASSWORD": "..."}}}}
```

## Tests

```bash
.venv/bin/pip install -e '.[dev]' && .venv/bin/python -m pytest -q
```

License: MIT
