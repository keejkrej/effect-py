# effect-py

Python port of [Effect-TS](https://effect.website/) — typed functional effects with a fiber runtime.

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest
```

Optional libtorch integration:

```bash
uv sync --group dev --group torch
uv run pytest tests/test_torch_slice.py
uv run python examples/matmul_pipeline.py
```

## Status

v0 core: sync/async `Effect`, `Cause`/`Exit`, `Context`/`Layer`, `Scope`/`Ref`, `Runtime`.

Optional `effect_torch`: tagged torch errors, `DeviceService`/`RngService` layers, matmul vertical slice.
