# Agent guide — buildarr

This file is the repo's primary, tool-agnostic agent guide (read by Cursor,
Claude Code, Copilot, Codex, etc.). It holds the repo-wide orientation; the
bundled plugin packages have a shared nested guide.

## Subsystem guides (nested AGENTS.md)

- `buildarr_sonarr/AGENTS.md` — how to author/extend a bundled plugin
  (`buildarr_sonarr` is the canonical example; `buildarr_radarr`,
  `buildarr_prowlarr`, `buildarr_jellyseerr` follow the same shape).

## What this is

This is **the Buildarr tool itself** — a Python package, not a config repo that
*uses* Buildarr. Buildarr is config-as-code for the *Arr stack
(Sonarr/Radarr/Prowlarr/Jellyseerr): you describe the desired state of each
application instance in a single YAML file (`buildarr.yml`) and Buildarr
idempotently drives the live instances to match over their HTTP APIs. It can run
once (`buildarr run`) or as a long-lived service (`buildarr daemon`), and can
pull recommended values from TRaSH-Guides.

**This is a customized fork** (upstream: `buildarr/buildarr`; default branch
here: `fork`; `main` tracks upstream). **Keep the upstream diff minimal and
rebase-friendly** — concentrate fork-specific work (the monorepo bundling, the
`Dockerfile`, the homelab CI/CD) so it stays easy to rebase, and prefer upstream
conventions over inventing new ones. The key fork-specific divergences:

- **Monorepo plugin bundling.** Upstream ships the core `buildarr` package and
  each plugin as *separate* PyPI packages. This fork vendors four plugins into
  one repo / one `pyproject.toml` so the Docker image has them all built in:
  `buildarr_sonarr`, `buildarr_radarr`, `buildarr_prowlarr`,
  `buildarr_jellyseerr` (see the `packages` and `[tool.poetry.plugins]` blocks
  in `pyproject.toml`).
- **Homelab CI/CD.** `.github/workflows/homelab-cicd.yml` builds the `Dockerfile`
  on push to `fork`, pushes to GHCR (`ghcr.io/<owner>/buildarr`), and bumps the
  image tag in the `homelab-manifests` ArgoCD repo (`apps/arr-stack/values.yaml`).

**Stack:** Python 3.8+ (Docker image is 3.11), Poetry, Pydantic **v1**
(`>=1.10,<2.0` — do not upgrade to v2), Click CLI, `stevedore` for plugin
entry-point discovery, `requests` for *Arr APIs, `schedule` + `watchdog` for
daemon mode, MkDocs for docs.

## How to run things

```bash
# --- Dev environment (Poetry) ---
poetry install                 # install core + all bundled plugins + dev tools
poetry shell                   # or prefix commands with `poetry run`

# --- The CLI (entry point: buildarr.cli.main:main) ---
buildarr test-config [CONFIG]  # validate a config file without touching instances
buildarr run [CONFIG]          # one-shot: apply the config to live instances
buildarr daemon [CONFIG]       # run as a service (initial sync + scheduled runs)
buildarr compose [CONFIG]      # generate a Docker Compose file from the config
buildarr --log-level DEBUG run # verbose run (the canonical bug-report command)
# CONFIG defaults to ./buildarr.yml. Per-plugin subcommands are added dynamically,
# e.g. `buildarr sonarr dump-config http://sonarr:8989` to dump a live instance.

# --- Quality tooling (see Quality gate) ---
poetry run ruff check .        # lint (autofix is on via pyproject `fix = true`)
poetry run black .             # format (line length 100)
poetry run mypy buildarr buildarr_sonarr buildarr_radarr buildarr_prowlarr buildarr_jellyseerr
pre-commit install && pre-commit run --all-files  # run the whole gate at once

# --- Docs ---
poetry run mkdocs serve        # preview docs/ (core docs only; plugin docs are external)
```

There is **no `npm`/test runner here** — see Quality gate. `requirements.txt` is
a generated export of `poetry.lock` (a pre-commit hook regenerates it); don't
hand-edit it.

### Docker

```bash
docker build -t buildarr:dev .                          # builds core + all bundled plugins
docker run -d --name buildarr -v "$(pwd):/config" \
  -e PUID="$(id -u)" -e PGID="$(id -g)" buildarr:dev     # daemon (default CMD)
```

`Dockerfile` is the fork's monorepo image (`pip install /src`, all plugins built
in). `test.Dockerfile` is the legacy upstream-style image that `pip install`s
plugins from PyPI at pinned versions via `scripts/bootstrap.sh` — not used by the
fork's CI. The container runs as an unprivileged `buildarr` user created at
runtime from `PUID`/`PGID`; `/config` is the config volume.

## Quality gate

CI (`.github/workflows/pre-commit.yml`) runs **pre-commit on every PR and push to
`main`**. There is **no automated test suite** in this repo (unit tests are an
explicit upstream to-do; no `tests/` dir, no pytest). So the gate is the
pre-commit stack — all must pass:

1. `ruff` (with `--exit-non-zero-on-fix`) — 0 findings, see `[tool.ruff]` in `pyproject.toml`.
2. `black` — formatted (line length 100).
3. `mypy` (Python 3.8 target, with `types-pyyaml` / `types-requests`) — clean.
4. `poetry-check` + `poetry-lock --no-update` + `poetry-export` to `requirements.txt`.
5. Hygiene hooks: trailing-whitespace, end-of-file-fixer, detect-private-key, check-merge-conflict, large-file guard.

Before declaring a change done: `pre-commit run --all-files` green, and
`buildarr test-config` against a representative `buildarr.yml` if you touched
config models. If you changed a config field exposed to users, also check the
relevant `docs/`.

## Conventions

- **Pydantic v1 only.** All config and secrets models subclass the v1 Pydantic
  base classes in `buildarr/config/base.py` / `buildarr/secrets/base.py`. v1
  idioms (`validator`, `Config` inner class, `.dict()`) are correct here — do not
  port to v2.
- **The plugin architecture is the core abstraction.** A plugin is a class
  subclassing `buildarr.plugins.Plugin` (`buildarr/plugins/models.py`) that wires
  together four things for one *Arr app: `config` (a `ConfigPlugin` model),
  `secrets` (a `SecretsPlugin` model), `manager` (a `ManagerPlugin` that does the
  fetch/diff/update against the live instance), and an optional `cli` (a Click
  group, mounted as a `buildarr <plugin>` subcommand). Buildarr discovers plugins
  via the `buildarr.plugins` entry-point group (declared in `pyproject.toml`).
  Full plugin detail: **`buildarr_sonarr/AGENTS.md`**.
- **Idempotent, declarative.** Config defines desired state; the manager only
  changes what differs. Anything not in the config is left alone (and can be
  deleted via the unmanaged-resource pass). Preserve this — never make a manager
  write unconditionally.
- **`from __future__ import annotations` is required** at the top of every module
  (`[tool.ruff.isort] required-imports`), plus combined-as-imports and
  one-blank-line-between-import-types.
- **Imports are relative within a package** (`from ..state import state`,
  `from .config import SonarrConfig`) — the established style; there is no `src/`
  layout or import alias.
- **GPL-3.0 license header** tops most source files. Match the surrounding files
  when adding a new module.
- **CLI commands** live in `buildarr/cli/<command>.py`, each a `@cli.command`
  registered on the shared `cli` group in `buildarr/cli/__init__.py`, then
  imported in `buildarr/cli/main.py`.

## Where things live

```
buildarr/                     # core package (the runtime; app-agnostic)
├── cli/                      # Click CLI: main.py + one file per command
│   ├── main.py               #   entry point — loads plugins, mounts their CLIs
│   ├── run.py, daemon.py     #   the `run` / `daemon` commands
│   ├── test_config.py        #   the `test-config` validator (multi-stage check)
│   └── compose.py            #   the `compose` command
├── config/                   # config loading + base Pydantic models, instance
│   │                         #   dependency resolution + render passes
│   ├── base.py, buildarr.py, load.py, models.py
│   ├── resolve_instance_dependencies.py, render_instance_configs.py, post_init_render.py
├── plugins/                  # plugin contract + discovery
│   ├── models.py             #   the `Plugin` base class (the contract)
│   ├── load.py               #   stevedore entry-point discovery
│   └── dummy/                #   the built-in `dummy` plugin (reference impl)
├── secrets/                  # base secrets model + store
├── manager/                  # ManagerPlugin base + loader
├── state.py                  # global run state (loaded plugins/config/managers)
├── trash.py                  # TRaSH-Guides metadata fetch/cleanup
├── types.py, util.py, exceptions.py, logging.py
buildarr_sonarr/              # bundled plugins (one package each) — see its AGENTS.md
buildarr_radarr/              #   plugin (config/ split into settings/ subpackage)
buildarr_prowlarr/
buildarr_jellyseerr/
docs/                         # MkDocs sources (core only; plugin docs are external URLs)
scripts/bootstrap.sh          # legacy test.Dockerfile entrypoint (installs plugins at runtime)
Dockerfile                    # fork monorepo image (builds in all plugins)
test.Dockerfile               # legacy upstream-style image (plugins from PyPI)
pyproject.toml                # Poetry: deps, plugin entry points, ruff/black/mypy config
.pre-commit-config.yaml       # the quality gate
.github/workflows/            # pre-commit, release (PyPI), homelab-cicd (GHCR+ArgoCD)
```

## Adding / changing — walkthroughs

### Add support for a new *Arr application (a new plugin)

1. Create a new top-level package `buildarr_<app>/` mirroring `buildarr_sonarr/`:
   `plugin.py`, `config/` (or `config.py`), `secrets.py`, `manager.py`,
   `cli.py`, `api.py`, `__init__.py` (with `__version__`), `py.typed`. See
   `buildarr_sonarr/AGENTS.md` for what each must implement.
2. Define a `Plugin` subclass in `buildarr_<app>/plugin.py` setting `config`,
   `secrets`, `manager`, optional `cli`, and `version` (see
   `buildarr_sonarr/plugin.py`).
3. Register it: add the package to `packages` and add an entry-point line under
   `[tool.poetry.plugins."buildarr.plugins"]` in `pyproject.toml`
   (`"<app>" = "buildarr_<app>.plugin:<App>Plugin"`). This is what makes the new
   `<app>:` config key and `buildarr <app>` CLI work.
4. Add its third-party API/runtime deps to `[tool.poetry.dependencies]`, then
   `poetry lock --no-update` (the pre-commit hook also re-exports `requirements.txt`).
5. Quality gate: `pre-commit run --all-files`, then `buildarr test-config`
   against a config that exercises the new plugin.

### Add or change a config field on an existing plugin

Edit the relevant Pydantic model under `buildarr_<app>/config/` and the matching
fetch/update logic in that plugin's `manager.py` (and `api.py` if a new API call
is needed). Keep the change idempotent and additive. Validate with
`buildarr test-config`; update the plugin's docs if user-facing. Detail:
`buildarr_sonarr/AGENTS.md`.

### Add a top-level CLI command

Add `buildarr/cli/<command>.py` with a `@cli.command`-decorated function, import
it in `buildarr/cli/main.py`. Follow `test_config.py` for the
load→validate→report shape.

## When stuck

- **Buildarr usage / config schema:** upstream docs at <https://buildarr.github.io>
  (`docs/` here mirrors the core sections; plugin pages are external links in
  `mkdocs.yml`).
- **Plugin internals:** `buildarr_sonarr/AGENTS.md`, the `dummy` plugin
  (`buildarr/plugins/dummy/`) as the minimal reference, and the docstrings on
  `buildarr/plugins/models.py`.
- **Why is my config rejected?** Run `buildarr --log-level DEBUG test-config`;
  it walks load → managers → instance configs → dependency resolution → TRaSH
  render, reporting which stage failed.
- **CI/deploy questions:** `.github/workflows/homelab-cicd.yml` (this fork) and
  `.github/workflows/release.yml` (upstream PyPI publish on GitHub release).
- **Upstream contributions** target separate per-plugin repos; this fork
  deliberately bundles them — keep fork-specific work on the `fork` branch.