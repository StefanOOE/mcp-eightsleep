# mcp-eightsleep

[![CI](https://github.com/StefanOOEOrg/mcp-eightsleep/actions/workflows/ci.yml/badge.svg)](https://github.com/StefanOOEOrg/mcp-eightsleep/actions/workflows/ci.yml)
[![M8ven Verified](https://m8ven.ai/badge/mcp/stefanooeorg-mcp-eightsleep-12r7ux?variant=verified)](https://m8ven.ai/mcp/stefanooeorg-mcp-eightsleep-12r7ux)
[![M8ven Score](https://m8ven.ai/badge/mcp/stefanooeorg-mcp-eightsleep-12r7ux?v=485a7b236507d71c20099e7ef36b0d9b)](https://m8ven.ai/mcp/stefanooeorg-mcp-eightsleep-12r7ux?s=readme)

A small, **read-only** [Model Context Protocol](https://modelcontextprotocol.io) server (stdio)
for the sleep data of an [Eight Sleep](https://www.eightsleep.com) mattress cover.

It returns one night as **ready-made text** - scores, times, stages, HRV, heart and respiratory
rate against your own averages, bed and room temperature - so an agent can quote the numbers
instead of digging them out of a large JSON document (and mixing them up). Built for a daily
morning check-in, next to data from a sports watch.

> **Unofficial.** This project is not affiliated with or endorsed by Eight Sleep. Eight Sleep
> publishes no developer API; see [How it works](#how-it-works) and use it at your own risk.

## Tool

### `get_night(target_date?, history_days=0)`

| Parameter | Meaning |
|---|---|
| `target_date` | `YYYY-MM-DD`, the day you **woke up** ("last night" = today, the default) |
| `history_days` | `0`-`13`: one short line per earlier night |

Example output (made-up numbers):

```
# Eight Sleep night (woke up Thu 22.10)
Sleep fitness score 78: quality 80, routine 70
In bed 21:40-06:58, asleep 22:05-06:50, fell asleep in 0h15
Sleep 7h45 (your avg 7h20, 7-day 7h30, score 85/100); sleep need 7h30, sleep debt 0h45
Stages: deep 1h30 (19%), REM 1h40 (21%), light 4h35; awake after falling asleep 0h25, 3 wake-ups
HRV 42 ms (your avg 40, 7-day 41, score 80/100)
Heart rate 55 bpm (your avg 56, 7-day 56, score 75/100)
Respiratory rate 14.2/min (your avg 14.5, 7-day 14.4, score 90/100)
Temperature: bed 26.1-28.4 °C, room 19.5-20.3 °C
Snoring 0h12 (3%)
## Nights before (1 with data)
- Tue 20.10: score 70, sleep 7h00, deep 1h20, HRV 39 ms, HR 58 bpm
```

Times are shown in the time zone of your device (or `EIGHTSLEEP_TIMEZONE`). A night without
data (away, other side of the bed, not processed yet) is named as such, not skipped.

The server cannot change anything: no temperature, alarm, base or away-mode control.

## Setup

Requires **Python 3.10 or newer** (the CI runs 3.10 and 3.14).

```bash
git clone https://github.com/StefanOOEOrg/mcp-eightsleep.git
cd mcp-eightsleep
cp .env.template .env      # fill in EIGHTSLEEP_EMAIL / EIGHTSLEEP_PASSWORD
python3 -m venv .venv && .venv/bin/pip install .
```

| Environment variable | Meaning |
|---|---|
| `EIGHTSLEEP_EMAIL`, `EIGHTSLEEP_PASSWORD` | your Eight Sleep login (required) |
| `EIGHTSLEEP_TIMEZONE` | optional IANA time zone, default: the one of your device |

Accounts that sign in with Apple or Google need a password set in the Eight Sleep app first.

MCP client configuration (e.g. Claude Desktop, Claude Code or any other MCP client):

```json
{
  "mcpServers": {
    "mcp-eightsleep": {
      "command": "/path/to/mcp-eightsleep/.venv/bin/python",
      "args": ["-m", "mcp_eightsleep"],
      "env": {"EIGHTSLEEP_EMAIL": "you@example.com", "EIGHTSLEEP_PASSWORD": "..."}
    }
  }
}
```

Keep the password out of shared config files - pass it from a secret store or an `.env` that
your MCP client expands.

## How it works

- Login: OAuth password grant against `auth-api.8slp.net`, with the client id/secret of the
  Eight Sleep Android app as used by the community
  [Home Assistant integration](https://github.com/lukas-clarke/eight_sleep). The token is kept
  in memory, renewed before it expires, and once more after a `401`.
- Data: `GET client-api.8slp.net/v1/users/{id}/trends` (model version `v2`) for the requested
  days - one record per night, filed under the day you woke up.
- Only the Python standard library plus the `mcp` SDK; no data is stored on disk.

Because the API is private, it can change without notice. Keep the call rate low - one call
per check-in is plenty.

## Project structure

```
mcp-eightsleep/
├── src/mcp_eightsleep/
│   ├── __init__.py
│   ├── __main__.py          # python -m mcp_eightsleep
│   ├── client.py            # login, token renewal, profile, per-night trends
│   ├── config.py            # EIGHTSLEEP_* from the environment
│   ├── night.py             # one night as pre-formatted lines
│   └── server.py            # the MCP tool get_night + main()
├── tests/
│   ├── test_client.py       # login once, renewal after 401, time zone order
│   ├── test_night.py        # formatting, history, ToolError paths
│   └── test_server.py       # start without credentials: one hint, still runs
├── .github/workflows/ci.yml # pytest + pylint on 3.10 and 3.14
├── .env.template            # copy to .env, fill in the login
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
└── README.md
```

## Development

```bash
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint src tests    # lint gate, must stay clean
```

The tests use a fake HTTP layer and a fake client - no account or network needed.

## Scope / Limitations

- A single-user tool, not a service: it runs locally over stdio - no network port, no
  authentication, no multi-user support.
- Read-only by design: it reads scores and metrics, nothing can be changed (no temperature,
  alarm, base or away-mode control).
- It talks to the private Eight Sleep app API through reverse-engineered endpoints (see
  [How it works](#how-it-works)); that API can change or break at any time.
- Credentials are stored in plain text in your client config or `.env` - keep them out of
  shared files and out of logs.
- Accounts that sign in with Apple or Google need a password set in the Eight Sleep app first.
- `EIGHTSLEEP_TIMEZONE` is only needed when the account reports no device time zone; the
  fallback then is `UTC`.

## License

[MIT](LICENSE)
