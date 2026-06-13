from __future__ import annotations

from typing import Any, Never

from effect._internal.core import Effect, succeed, sync
from effect.context import GenericTag, Tag

LoggerTag: Tag[Any, Any] = GenericTag("effect/Logger")


class Logger:
    def log(self, message: str, level: str = "info", **kwargs) -> None:
        pass


class PrintLogger(Logger):
    def log(self, message: str, level: str = "info", **kwargs) -> None:
        from effect._internal.runtime_env import current_context

        ctx = current_context()
        meta = {k: v for k, v in ctx.services.items() if k != "effect/Logger"}
        meta.update(kwargs)
        meta_str = f" {meta}" if meta else ""
        print(f"[{level.upper()}] {message}{meta_str}")


class MockLogger(Logger):
    def __init__(self) -> None:
        self.logs: list[tuple[str, str, dict[str, Any]]] = []

    def log(self, message: str, level: str = "info", **kwargs) -> None:
        from effect._internal.runtime_env import current_context

        ctx = current_context()
        meta = {k: v for k, v in ctx.services.items() if k != "effect/Logger"}
        meta.update(kwargs)
        self.logs.append((level, message, meta))


def log(message: str, level: str = "info", **kwargs) -> Effect[None, Never, Any]:
    def run_log():
        from effect._internal.runtime_env import current_context
        from effect.context import unsafe_get

        try:
            logger = unsafe_get(current_context(), LoggerTag)
        except Exception:
            logger = PrintLogger()
        logger.log(message, level, **kwargs)
        return succeed(None)

    return sync(run_log)


def log_info(message: str, **kwargs) -> Effect[None, Never, Any]:
    return log(message, "info", **kwargs)


def log_error(message: str, **kwargs) -> Effect[None, Never, Any]:
    return log(message, "error", **kwargs)


def log_warning(message: str, **kwargs) -> Effect[None, Never, Any]:
    return log(message, "warning", **kwargs)


def log_debug(message: str, **kwargs) -> Effect[None, Never, Any]:
    return log(message, "debug", **kwargs)
