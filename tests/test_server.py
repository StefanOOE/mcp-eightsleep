"""main(): a start without credentials must say so instead of staying silent.

`get_night` now explains missing credentials (WP1), but the server itself starts quietly:
a first-time user sees nothing until the tool call fails. The start has to warn once on
stderr and still run - the process must live so the client gets an answer at all.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HINT = "mcp-eightsleep: EIGHTSLEEP_EMAIL/EIGHTSLEEP_PASSWORD not set - get_night will fail"


def _start(env_extra: dict[str, str]) -> subprocess.CompletedProcess:
    """Start `python -m mcp_eightsleep` with stdin closed, without inherited EIGHTSLEEP_*."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("EIGHTSLEEP_")}
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "mcp_eightsleep"],
        cwd=REPO_ROOT, env=env, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, timeout=60, check=False,
    )


def test_start_without_credentials_warns_once_and_keeps_running():
    """No env: exactly this one line on stderr, no traceback, and the server still starts."""
    result = _start({})

    assert result.returncode == 0, result.stderr
    assert result.stderr.strip().splitlines() == [HINT]
    assert "Traceback" not in result.stderr


def test_start_with_credentials_does_not_warn():
    """With both variables set the start is silent - the hint is not unconditional."""
    result = _start({"EIGHTSLEEP_EMAIL": "you@example.com", "EIGHTSLEEP_PASSWORD": "secret"})

    assert result.returncode == 0, result.stderr
    assert "EIGHTSLEEP_EMAIL/EIGHTSLEEP_PASSWORD not set" not in result.stderr
