from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

A = TypeVar("A")
B = TypeVar("B")

LazyArg = Callable[[], A]


def identity(value: A) -> A:
    return value


def pipe(value: A, *fns: Callable[[Any], Any]) -> Any:
    result: Any = value
    for fn in fns:
        result = fn(result)
    return result


def dual(arity: int, body: Callable[..., Any]) -> Callable[..., Any]:
    if arity < 2:
        msg = f"Invalid arity {arity}"
        raise ValueError(msg)

    if arity == 2:

        def wrapped(a: Any, b: Any | None = None) -> Any:
            if b is not None:
                return body(a, b)
            return lambda self: body(self, a)

        return wrapped

    def wrapped(*args: Any) -> Any:
        if len(args) >= arity:
            return body(*args)
        captured = args

        def curried(self: Any) -> Any:
            return body(self, *captured)

        return curried

    return wrapped
