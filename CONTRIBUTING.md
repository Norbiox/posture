# Contributing

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Node 24 (see `.nvmrc`).

```sh
uv sync
npm ci --prefix frontend
uv run pre-commit install   # installs pre-commit, commit-msg and pre-push hooks
```

## Checks

The hooks run these automatically. To run them by hand:

```sh
uv run pre-commit run --all-files                      # fast checks (pre-commit stage)
uv run pre-commit run --hook-stage pre-push --all-files # tests and svelte-check
uv run pytest                                          # fails if posture.domain is below 100% branch coverage
cd frontend && npm run lint && npm run format:check && npm run check && npm run build
```

CI runs the same checks on every push and pull request.

## Standards

- **Names follow [GLOSSARY.md](GLOSSARY.md).** For example `Stance` for Sitting or Standing,
  never `posture` as desk state. Update the glossary before introducing a new domain term.
- **Docstrings are not required.** Write one only where the name and types are not enough.
- **Comments explain why, not what.**
- **Domain code stays pure.** `src/posture/domain/` must not import frameworks or I/O (ruff
  `TID251` enforces this), must be 100% branch covered, and must not use `pragma: no cover`.
- **No lint or type-check suppressions** without a short comment saying why.

## Commits and releases

- [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, ...).
  The `commit-msg` hook enforces it.
- Commit directly on `main`.
- Releases use manual SemVer tags: `git tag vX.Y.Z && git push origin vX.Y.Z`. The tag runs CI
  and then publishes a GitHub Release with `posture-frontend-vX.Y.Z.tar.gz`.
