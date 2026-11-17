# Posture

Posture lets one person control their IKEA Idasen desk over the local network, tracks how long
they sit and stand, and moves the desk automatically during work hours. Terms (Desk, Height,
Preset, Stance, Work Hours, ...) are defined in [GLOSSARY.md](GLOSSARY.md). Why Posture keeps a
permanent Bluetooth connection is in [ADR 0001](docs/adr/0001-persistent-ble-connection.md).

There is no authentication: run it on a trusted LAN only. The IKEA/Linak phone app cannot connect
to the Desk while Posture runs.

## Run locally without a Desk

```sh
mise trust && mise install
mise run setup
mise run build                       # builds the web UI into frontend/dist
POSTURE_DESK_MAC=fake uv run posture # simulated Desk, UI on http://localhost:8000
```

`POSTURE_DESK_MAC=fake` uses an in-memory Desk that moves at about 4 cm/s. For a throwaway
database and log, also set `POSTURE_DB` and `POSTURE_LOG` (the defaults live under `/var`).

For UI work, run the backend as above and `npm --prefix frontend run dev`. Vite proxies `/api` and
`/ws` to `localhost:8000`.

## Configuration

Environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `POSTURE_DESK_MAC` | required | Desk BLE MAC address, or `fake` for a simulated Desk. |
| `POSTURE_TZ` | `Europe/Warsaw` | Timezone for Work Hours, Schedules and statistics. |
| `POSTURE_RETRIES` | `5` | Automation retries, one minute apart. |
| `POSTURE_DB` | `/var/lib/posture/posture.db` | SQLite file. |
| `POSTURE_LOG` | `/var/log/posture/posture.log` | Log file (rotated at 10 MB, 5 kept). |
| `POSTURE_STATIC_DIR` | `frontend/dist` | Built web UI served at `/`. |
| `POSTURE_HOST` / `POSTURE_PORT` | `0.0.0.0` / `8000` | Bind address. |

Work Hours, Workdays, Holidays, the Stance threshold, retries after an Interruption, Presets and
Automations are set in the web UI and stored in SQLite.

## Deploy on Alpine Linux

On the Alpine VM with the Bluetooth adapter passed through, as root:

```sh
wget https://raw.githubusercontent.com/Norbiox/posture/main/deploy.sh
sh deploy.sh install   # safe to run again
sh deploy.sh update    # installs the latest release if it is newer
```

`install` installs BlueZ, D-Bus and uv, creates the `posture` user, downloads the latest GitHub
Release, pairs the Desk (hold its pairing button when asked) and starts an OpenRC service.
Settings are in `/etc/conf.d/posture`, logs in `/var/log/posture/posture.log`.

`update` and `install` copy the database to `posture.db.<previous version>.bak` before they replace
the code and keep the last 5 copies. If an update fails halfway, Posture stays stopped and the next
`sh deploy.sh update` retries it. Fetch `deploy.sh` again before updating so you run its latest
version.

Releases are tagged by hand: `git tag vX.Y.Z && git push origin vX.Y.Z`.

## HTTP API

Stable, used by scripts:

| Request | Result |
|---|---|
| `GET /api/state` | `{height_cm, stance, moving, connected, paused}` |
| `GET /api/presets` | `[{id, name, height_cm}]`, highest first |
| `POST /api/move` `{"preset": "Stand"}` or `{"height_cm": 110}` | State after the Desk arrived |
| `POST /api/stop` | Stops the Desk |
| `POST /api/pause`, `DELETE /api/pause` | Pause Automations until the end of today, or resume |

Heights outside 62-127 cm are rejected with 422. The other endpoints (Presets, Automations,
settings, Holidays, statistics, logs, `WS /ws`) belong to the web UI and may change; see
`src/posture/api.py`.

### dmenu: `menu-idasen`

[`scripts/menu-idasen`](scripts/menu-idasen) moves the Desk from any Linux desktop with dmenu. It
lists the Presets with their Heights; pick one, or type a Height such as `105` or `105 cm`. Needs
`curl`, `jq` and `dmenu`; `notify-send` is used when present.

```sh
install -m 755 scripts/menu-idasen ~/.local/bin/
POSTURE_URL=http://posture.lan:8000 menu-idasen
```

| Variable | Default | Meaning |
|---|---|---|
| `POSTURE_URL` | `http://posture.lan:8000` | Posture address. |
| `POSTURE_MENU` | `dmenu -i -l 20` | Menu command, e.g. `rofi -dmenu -i` or `bemenu -i`. |

Bind it to a key in your window manager.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). `mise run check`, `mise run test` and `mise run build`
run the same checks as CI.
