# AGENTS.md

Posture is a FastAPI + SQLite backend with a Svelte 5 SPA. It controls one IKEA Idasen desk over a persistent BLE connection.

## Read first

- [GLOSSARY.md](GLOSSARY.md): names in code, UI and docs follow it. Never use `posture` for desk state; that is `Stance`.
- [CONTRIBUTING.md](CONTRIBUTING.md): code standards, commits, releases.
- [docs/adr/](docs/adr/): decisions you must not reverse silently.
- [PRODUCT.md](PRODUCT.md): who uses Posture and why.

Frontend follows DESIGN.md; read it before any UI change.

## Commands

```sh
mise run setup   # dependencies and git hooks
mise run check   # every hook: lint, format, types, tests, svelte-check
mise run test    # pytest, 100% branch coverage gate for posture.domain
mise run build   # frontend into frontend/dist
POSTURE_DESK_MAC=fake POSTURE_DB=/tmp/p.db POSTURE_LOG=/tmp/p.log uv run posture
```

The fake Desk lets you run the app without hardware. Use it; never move the real Desk without the owner present.

## Rules

- `src/posture/domain/` stays pure: no framework or I/O imports (ruff `TID251`), time passed in as `now`, 100% branch coverage, no `pragma: no cover`.
- Do not add lint or type suppressions or weaken the harness config without a short "why" comment.
- Never bypass hooks (`--no-verify`).
- The API endpoints `state`, `presets`, `move`, `stop`, `pause` are a stable contract for the owner's dmenu script. Do not change their shape.
- Conventional Commits. `main` must stay green. Branch and PR when the owner asks for one.
- English in code, comments, docs, UI and commits.
