from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Generic, Never, TypeVar

from effect._internal import core as internal
from effect._internal.core import Effect, sync

A = TypeVar("A")
B = TypeVar("B")
E = TypeVar("E")
R = TypeVar("R")

current_fiber_refs_var: ContextVar[dict[FiberRef[Any], Any] | None] = ContextVar(
    "current_fiber_refs", default=None
)


def _set_ref_value(ref: FiberRef[Any], value: Any) -> None:
    refs = current_fiber_refs_var.get(None)
    if refs is None:
        new_refs = {ref: value}
    else:
        new_refs = refs.copy()
        new_refs[ref] = value
    current_fiber_refs_var.set(new_refs)


class FiberRef(Generic[A]):
    def __init__(self, default_value: A) -> None:
        self._default_value = default_value

    def get(self) -> Effect[A, Never, Never]:
        def read() -> A:
            refs = current_fiber_refs_var.get(None)
            if refs is None:
                return self._default_value
            return refs.get(self, self._default_value)

        return sync(read)

    def set(self, value: A) -> Effect[None, Never, Never]:
        def write() -> None:
            _set_ref_value(self, value)

        return sync(write)

    def locally(self, *args: Any) -> Any:
        if len(args) == 2:
            effect, value = args
            return self._locally(effect, value)
        elif len(args) == 1:
            value = args[0]
            return lambda effect: self._locally(effect, value)
        else:
            raise TypeError("Expected 1 or 2 arguments")

    def _locally(self, effect: Effect[B, E, R], value: A) -> Effect[B, E, R]:
        @internal.gen
        def run():
            old = yield self.get()
            yield self.set(value)
            return (yield internal.on_exit(effect, lambda _: self.set(old)))

        return run()


def make(default_value: A) -> Effect[FiberRef[A], Never, Never]:
    return sync(lambda: FiberRef(default_value))
