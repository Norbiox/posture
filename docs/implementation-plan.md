# Implementation plan: Posture v0.1

Source of truth for names: [GLOSSARY.md](../GLOSSARY.md). Architecture decision: [ADR 0001](adr/0001-persistent-ble-connection.md). Quality rules: [CONTRIBUTING.md](../CONTRIBUTING.md).

## Settled decisions

- One Desk, one person, LAN only, no auth.
- Alpine Linux VM, OpenRC service, user `posture`, Python 3.14 via `uv`. No Docker.
- Persistent BLE connection with automatic reconnect, using the `idasen` library from PyPI (heights in metres there, centimetres everywhere in Posture). Height is what the Desk reports, no correction.
- Every client (web UI, dmenu script) talks to the Desk only through Posture's HTTP API.
- Stance (Sitting/Standing) from a threshold set in the UI, default 90 cm. Stance is always derived from stored Heights, so changing the threshold recalculates history.
- Statistics cover the whole day, every day. Time while Posture is disconnected from the Desk is not counted (assumption, confirm in PR review).
- Automations (Schedule, Timer) run only inside Work Hours on Workdays that are not Holidays, move the Desk without confirmation, and stop for the day on Pause.
- Configuration:
  - environment variables: timezone, Desk MAC, retry count, paths, bind address;
  - UI (stored in SQLite): Work Hours, Workdays, Holidays, Stance threshold, Presets, Automations.
- UI in English, 5 tabs, responsive.

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `POSTURE_DESK_MAC` | required | Desk BLE MAC. The value `fake` uses an in-memory simulated Desk for development. |
| `POSTURE_TZ` | `Europe/Warsaw` | Timezone for Work Hours, Schedules and statistics. |
| `POSTURE_RETRIES` | `5` | Automation retries, 1 minute apart. |
| `POSTURE_DB` | `/var/lib/posture/posture.db` | SQLite file. |
| `POSTURE_LOG` | `/var/log/posture/posture.log` | Log file. |
| `POSTURE_STATIC_DIR` | `frontend/dist` | Built SPA served at `/`. |
| `POSTURE_HOST` / `POSTURE_PORT` | `0.0.0.0` / `8000` | Bind address. |

Read them with `os.environ` into one frozen dataclass in `src/posture/config.py`. No settings library.

## Module layout

```
src/posture/
  domain/          pure logic, no I/O (TID251), 100% branch coverage
    stance.py      Stance, stance_for (exists)
    calendar.py    is_work_time(now, work_hours, workdays, holidays)
    stats.py       stance totals for a time range; per-minute Height series for a day
    automation.py  Schedule, Timer, timer_due(...), should_retry(...)
  config.py        env vars → Config
  db.py            stdlib sqlite3, schema.sql applied on start, small query functions
  schema.sql       CREATE TABLE IF NOT EXISTS ...
  desk.py          DeskController: persistent connection, reconnect, moves, fake Desk
  engine.py        APScheduler jobs for Automations and retries
  logs.py          loguru setup: file sink (rotation 10 MB, retention 5), stderr, WebSocket sink, std logging intercepted
  api.py           FastAPI app: REST, WebSocket, StaticFiles
  __main__.py      `python -m posture` / `posture` script → uvicorn
```

Use `asyncio.to_thread` for sqlite3 calls. All datetimes are timezone-aware (ruff `DTZ`). Store timestamps as UTC ISO strings.

## Data model (`schema.sql`)

- `height_events(ts TEXT, height_cm REAL NULL)`: one row per rest Height after each move, plus a row with `NULL` when the connection drops, plus the current Height on every (re)connect. `NULL` means "unknown until next row".
- `presets(id, name UNIQUE, height_cm)`
- `automations(id, kind CHECK IN ('schedule','timer'), enabled, preset_id, time_of_day NULL, stance NULL, minutes NULL)`
- `holidays(date PRIMARY KEY, name)`: manual dates. Polish public holidays come from the `holidays` library at read time and are merged in.
- `settings(key PRIMARY KEY, value TEXT JSON)`: `work_start` (07:00), `work_end` (17:00), `workdays` ([0..4]), `threshold_cm` (90), `pause_until` (null or ISO datetime).

## Domain rules (all unit-tested, 100% branches)

1. **Work time:** `now` is inside `[work_start, work_end)` on a Workday that is not a Holiday.
2. **Stats:** totals per Stance over `[start, end)` from height events, using the last event before `start` as the initial state. `NULL` stretches are excluded. Per-minute series for the day chart: the Height in force at each minute, `None` when unknown.
3. **Timer due** when all hold:
   - it is work time and not paused,
   - the Desk is in the Timer's Stance,
   - `now - max(stance_since, today's work_start) >= minutes`,
   - it has not already fired in this Stance period.

   A Height change inside the same Stance does not reset `stance_since`.
4. **Schedule due** at `time_of_day` when it is work time and not paused.
5. **Retry:** after a failed Automation move, retry every 60 s, at most `POSTURE_RETRIES` times. Stop when work time ends, Pause turns on, or the Stance changed since the first attempt.
6. **Collisions:**
   - A new command cancels the running move and goes to the new target.
   - An Automation skips (no retry) when a human-started move is in progress.

## Desk controller

- One `IdasenDesk` instance, connected at startup, kept open. Use `monitor()` notifications for live Height. Reconnect loop with backoff (1 s → 30 s max), logged.
- Live Height and moving state are broadcast to WebSocket clients. Write a `height_events` row when the Desk stops (speed 0, or no notification for ~1 s).
- Moves: `move_to(height_cm, source)`, `start_hold(direction)` (repeat `move_up`/`move_down` until released), `stop()`. Each move runs as one asyncio task, and a new move cancels the old task. `source` is `human` or `automation`.
- Fake Desk (`POSTURE_DESK_MAC=fake`): same interface, simulates ~4 cm/s, keeps Height in memory. Needed to run and click through the app without hardware.

## API

Stable contract for the dmenu script (do not change shape later without a major version):

- `GET /api/state` → `{height_cm, stance, moving, connected, paused}`
- `GET /api/presets` → `[{id, name, height_cm}]`
- `POST /api/move` with `{"preset": "<name>"}` or `{"height_cm": 110}` → state after the move
- `POST /api/stop`
- `POST /api/pause` (until end of today), `DELETE /api/pause`

UI-only (may change):

- presets: create (also "save current Height"), update, delete
- automations: list, create, update, enable/disable, delete
- settings: get/put Work Hours, Workdays, threshold
- holidays: list (manual + PL), add, delete manual
- `GET /api/stats/day?date=YYYY-MM-DD` → per-minute series + totals
- `GET /api/stats/daily?days=7|30` → per-day totals
- `GET /api/logs?lines=200`
- `WS /ws`:
  - server → client: `{"type":"height",...}`, `{"type":"state",...}`, `{"type":"log",...}`
  - client → server: `{"type":"hold","direction":"up"|"down"}`, `{"type":"release"}`

Validate input with Pydantic models (FastAPI). Heights outside 62–127 cm → 422. `StaticFiles(html=True)` mounted last at `/`.

## Frontend (Svelte 5, Tailwind 4, uPlot)

One page, 5 tabs:

1. **Control:**
   - live Height and Stance, connection badge,
   - hold-to-move Up/Down (pointer down → `hold`, pointer up/leave/cancel → `release`),
   - Preset buttons, "Save current as Preset", Pause toggle.
2. **Stats:**
   - day chart: step line of Height per minute, x axis 00:00–24:00 with ticks every 30 min, y axis Height, horizontal threshold line,
   - totals per Stance beside the chart; drag-select a range on the chart narrows the totals to it,
   - ←/→ day switch, default today,
   - below: 7/30-day stacked bars of daily totals.
3. **Automations:** list with enable toggle, add/edit/delete Schedule and Timer.
4. **Settings:** Work Hours, Workdays, Holidays (PL marked as automatic, manual removable), threshold, Presets management.
5. **Logs:** last 200 lines, live append over WebSocket, level filter INFO/WARNING/ERROR.

Vite dev server proxies `/api` and `/ws` to `localhost:8000`.

## deploy.sh (POSIX sh, Alpine)

- `install`:
  1. `apk add bluez dbus curl tar uv` (fall back to the official uv installer if the `uv` package is missing).
  2. `rc-update add dbus`, `rc-update add bluetooth`, start both.
  3. Check that the adapter is visible (`bluetoothctl list`).
  4. Create user `posture` with BlueZ D-Bus access, and the dirs `/opt/posture`, `/var/lib/posture`, `/var/log/posture`.
  5. Download the latest release: source tarball + `posture-frontend-<tag>.tar.gz`.
  6. Run `uv sync --frozen --no-dev`.
  7. Write `/etc/init.d/posture` (supervise-daemon). Write `/etc/conf.d/posture` only if it does not exist.
  8. Check pairing with `bluetoothctl info <MAC>`. If the Desk is not paired, ask the user to hold the Desk's pairing button, then pair and trust it.
  9. Enable and start the service.

  Running `install` again must be safe.
- `update`: compare `/opt/posture/VERSION` with the latest release tag. If newer, download, swap, `uv sync`, restart. Print what happened.

## Stages (one Conventional Commit or more per stage)

1. Domain: calendar, stats, automation rules + tests (100% branch).
2. Config, schema, db.
3. Desk controller with fake Desk.
4. Logging (loguru).
5. API + WebSocket + static serving.
6. Automation engine (APScheduler) with retries.
7. Frontend tabs.
8. deploy.sh + OpenRC files.
9. README: run locally with `POSTURE_DESK_MAC=fake`, deploy, dmenu example with `curl`.

## Out of scope for v0.1

Multiple desks or users, auth, check-in endpoint, i18n, frontend tests, API tests beyond domain (manual testing on the real Desk).
