from __future__ import annotations

from collections.abc import Callable
from typing import Generic, Never, TypeVar

from effect._internal import core as internal
from effect._internal.core import Effect
from effect.ref import Ref
from effect.semaphore import Semaphore

A = TypeVar("A")
B = TypeVar("B")
E = TypeVar("E")
R = TypeVar("R")


class SynchronizedRef(Generic[A]):
    def __init__(self, ref: Ref[A], semaphore: Semaphore) -> None:
        self._ref = ref
        self._semaphore = semaphore

    def get(self) -> Effect[A, Never, Never]:
        return self._ref.get()

    def set(self, value: A) -> Effect[None, Never, Never]:
        return self._semaphore.with_permit(self._ref.set(value))

    def update(self, f: Callable[[A], A]) -> Effect[None, Never, Never]:
        return self.modify(lambda a: (None, f(a)))

    def update_effect(self, f: Callable[[A], Effect[A, E, R]]) -> Effect[None, E, R]:
        return self.modify_effect(lambda a: internal.map_(f(a), lambda new_a: (None, new_a)))

    def modify(self, f: Callable[[A], tuple[B, A]]) -> Effect[B, Never, Never]:
        return self._semaphore.with_permit(self._ref.modify(f))

    def modify_effect(self, f: Callable[[A], Effect[tuple[B, A], E, R]]) -> Effect[B, E, R]:
        @internal.gen
        def run():
            a = yield self._ref.get()
            b, new_a = yield f(a)
            yield self._ref.set(new_a)
            return b

        return self._semaphore.with_permit(run())


def make(initial_value: A) -> Effect[SynchronizedRef[A], Never, Never]:
    from effect.ref import make as ref_make
    from effect.semaphore import semaphore_make

    @internal.gen
    def run():
        ref = yield ref_make(initial_value)
        sem = yield semaphore_make(1)
        return SynchronizedRef(ref, sem)

    return run()
