# effect-py context

## Goal

Port Effect-TS core to Python with matching architecture and API shape (Python idioms: snake_case, asyncio).

## Dependency policy

- **Runtime (`effect`):** stdlib only (`dependencies = []`).
- **Optional (`effect_torch`):** `torch` via `[project.optional-dependencies.torch]`.
- **Dev (required):** Ruff, ty, pytest, uv.

## v0 module allowlist (core)

- `data`, `option`, `either`, `cause`, `exit`, `effect`, `runtime`, `function_`, `pipeable`
- `context`, `layer`, `scope`, `ref`

## Optional packages

- `effect_torch` — libtorch vertical slices; install with `uv sync --extra torch` or `--group torch`

## Deferred (separate packages later)

- Stream, STM, Schedule, Schema, Platform
- Full `nn.Module` / distributed / compile wrappers

## Python adaptations

- `Effect[A, E, R]` via `Generic` — runtime `Context` is authoritative for requirements.
- Async via `asyncio` (`run_async`, `Effect.async_`).
- PEP 8 naming: `flat_map`, `catch_tag`, etc.
- Tag requirements in types use marker classes (e.g. `ScopeTag`) where `Tag` instances cannot appear in annotations.

## Phase status

| Phase | Scope | Status |
|-------|--------|--------|
| 0–1 | Scaffold, Data, Cause, Exit | done |
| 2 | Sync Effect AST + interpreter | done |
| 3 | Async + Context requirements | done |
| 4 | Layer, Ref, Scope | done |
| 5 | `effect_torch` matmul slice | done |

## Reference

Symlink: `.repos/effect` → `../effect-ts/packages/effect` (Effect-TS source of truth).
