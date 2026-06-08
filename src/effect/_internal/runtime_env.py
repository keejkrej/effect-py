from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import Any

from effect.context import Context, empty


@dataclass(frozen=True, slots=True)
class RunConfig:
    allow_async: bool = False


_current_context: contextvars.ContextVar[Context[Any] | None] = contextvars.ContextVar(
    "effect_current_context",
    default=None,
)

_run_config: contextvars.ContextVar[RunConfig | None] = contextvars.ContextVar(
    "effect_run_config",
    default=None,
)


def current_context() -> Context[Any]:
    context = _current_context.get()
    if context is None:
        return empty()
    return context


def set_context(context: Context[Any]) -> contextvars.Token[Context[Any] | None]:
    return _current_context.set(context)


def reset_context(token: contextvars.Token[Context[Any] | None]) -> None:
    _current_context.reset(token)


def get_run_config() -> RunConfig:
    config = _run_config.get()
    if config is None:
        return RunConfig(allow_async=False)
    return config


def set_run_config(config: RunConfig) -> contextvars.Token[RunConfig | None]:
    return _run_config.set(config)


def reset_run_config(token: contextvars.Token[RunConfig | None]) -> None:
    _run_config.reset(token)
