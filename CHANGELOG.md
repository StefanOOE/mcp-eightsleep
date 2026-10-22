# Changelog

## 0.1.0

Initial release.

- `get_night(target_date, history_days)`: one Eight Sleep night as pre-formatted text (sleep
  fitness score, times, stages, HRV, heart and respiratory rate vs. own averages, bed/room
  temperature, snoring) plus optional short lines for earlier nights.
- Read-only client for the unofficial app API: password-grant login, token kept in memory and
  renewed, one retry after `401`.
