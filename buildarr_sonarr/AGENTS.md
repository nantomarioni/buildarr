# Agent guide — Buildarr plugins (`buildarr_sonarr`, `buildarr_radarr`, `buildarr_prowlarr`, `buildarr_jellyseerr`)

Folder-specific guide for the bundled plugin packages. Sonarr is the canonical
example; the other three follow the same shape. Repo-wide orientation,
quality gate, and the run commands live in the root `../AGENTS.md`.

## What a plugin is

A plugin teaches Buildarr how to manage one *Arr application instance. It is a
single class subclassing `buildarr.plugins.Plugin` (contract:
`../buildarr/plugins/models.py`) that wires together four pieces. Buildarr finds
it through the `buildarr.plugins` entry-point group declared in
`../pyproject.toml` — the entry-point name (`"sonarr"`) becomes both the
top-level config key (`sonarr:` in `buildarr.yml`) and the CLI subcommand
(`buildarr sonarr ...`).

## The four pieces (study `buildarr_sonarr/`)

| Attribute on `Plugin` | File | What it is |
|---|---|---|
| `config` | `config/` (or `config.py`) | Root Pydantic **v1** config model (a `ConfigPlugin`) + the per-instance `*InstanceConfig`. Defines the YAML schema the user writes. |
| `secrets` | `secrets.py` | A `SecretsPlugin` model holding per-instance runtime secrets (API key, resolved host/port). Knows how to fetch/validate against the live instance. |
| `manager` | `manager.py` | A `ManagerPlugin[InstanceConfig, Secrets]` — the fetch/diff/update engine. Often just `pass` (inherits the base) when no custom behavior is needed. |
| `cli` (optional) | `cli.py` | A `@click.group` mounted as `buildarr <plugin>`, e.g. `dump-config` to read a live instance into YAML. |
| `version` | `__init__.py` | `__version__`, read from package metadata. |

`plugin.py` just imports and assigns these (see `buildarr_sonarr/plugin.py`).

## Layout

```
buildarr_<app>/
├── plugin.py        # the Plugin subclass (wires config/secrets/manager/cli/version)
├── __init__.py      # __version__ (see fork note below)
├── config/          # Pydantic v1 models, split by settings area
│   │                #   (sonarr: general.py, quality.py, profiles/, indexers.py, ...)
│   └── ...          #   radarr nests these under config/settings/
├── secrets.py       # SecretsPlugin model + live-instance secret fetch/validation
├── manager.py       # ManagerPlugin subclass
├── cli.py           # Click group (ad-hoc commands like dump-config)
├── api.py           # thin HTTP helpers against the app's API (or uses *-py SDK)
├── types.py         # plugin-specific constrained types / enums
├── exceptions.py    # plugin error types
└── py.typed         # PEP 561 marker — keep it
```

Radarr and Prowlarr use the official typed API clients (`radarr-py`,
`prowlarr-py`, declared in `../pyproject.toml`); Sonarr/Jellyseerr use their own
`api.py` against `requests`. Match whatever the plugin you're editing already does.

## Conventions

- **Pydantic v1.** Config/secrets models use v1 (`validator`, inner `Config`,
  `.dict()`). Do not port to v2 — Buildarr is pinned `pydantic>=1.10,<2.0`.
- **Reuse core types.** Pull shared constrained types from `buildarr.types`
  (`NonEmptyStr`, `Port`, `Password`, etc.) rather than redefining them; only put
  genuinely app-specific types in the plugin's `types.py`.
- **Idempotent managers.** The manager fetches remote state, diffs against the
  desired config, and only writes differences — and logs each change
  (`<plugin> (instance) field: old -> new`). Never write unconditionally; never
  delete a resource outside the sanctioned unmanaged-resource pass.
- **`from __future__ import annotations`** tops every module (enforced by ruff
  isort `required-imports`). Heavy/circular types go under `if TYPE_CHECKING:`.
- **Relative imports within the package** (`from .config import SonarrConfig`,
  `from .api import api_get`). Import core surfaces from their package roots
  (`from buildarr.manager import ManagerPlugin`).
- **GPL-3.0 header** on every source file — copy from a sibling module.

### Fork note: `__version__`

In this monorepo fork, a plugin package isn't `pip install`ed under its own
distribution name, so `__init__.py` falls back to the **core `buildarr`** version
when `version("buildarr-<app>")` raises `PackageNotFoundError`. Preserve that
fallback when adding a new plugin (copy `buildarr_sonarr/__init__.py`).

## Adding a config field (the common task)

1. Add the field to the right model under `config/` (match the existing
   field/`Field(...)` style and validators in that file).
2. Wire it in `manager.py`: include it in the remote-state fetch + diff and the
   update call (and add the API call in `api.py` if one is needed).
3. Keep it additive and idempotent; ensure a config that omits it still validates
   and leaves the remote value untouched.
4. Validate: `buildarr test-config` against a config exercising the field, then
   the root quality gate (`pre-commit run --all-files`). Update the plugin's docs
   if the field is user-facing (plugin docs are hosted in the external per-plugin
   doc sites linked from `../mkdocs.yml`).

## When stuck

- Minimal reference plugin: `../buildarr/plugins/dummy/` (the built-in `dummy`
  plugin) and the `Plugin` docstrings in `../buildarr/plugins/models.py`.
- The manager/secrets/config base contracts: `../buildarr/manager/`,
  `../buildarr/secrets/base.py`, `../buildarr/config/base.py`.
- Per-app config schema reference: the external plugin docs linked in
  `../mkdocs.yml` (`https://buildarr.github.io/plugins/<app>`).
