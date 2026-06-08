from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class Pipeable(Protocol):
    def pipe(self, *fns: Callable[[Any], Any]) -> Any: ...


def pipe_arguments(self: Pipeable, fns: tuple[Callable[[Any], Any], ...]) -> Any:
    from effect.function_ import pipe

    return pipe(self, *fns)
