from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Generic, Never, TypeVar

from effect.effect import Effect, sync

A = TypeVar("A")
B = TypeVar("B")


@dataclass
class Ref(Generic[A]):
    _value: A
    _lock: Lock = field(default_factory=Lock, repr=False)

    def get(self) -> Effect[A, Never, Never]:
        return sync(lambda: self._read())

    def set(self, value: A) -> Effect[None, Never, Never]:
        def write() -> None:
            with self._lock:
                self._value = value

        return sync(write)

    def modify(self, f: Callable[[A], tuple[B, A]]) -> Effect[B, Never, Never]:
        return sync(lambda: self._modify(f))

    def _read(self) -> A:
        with self._lock:
            return self._value

    def _modify(self, f: Callable[[A], tuple[B, A]]) -> B:
        with self._lock:
            before, after = f(self._value)
            self._value = after
            return before


def make(value: A) -> Effect[Ref[A], Never, Never]:
    return sync(lambda: Ref(value))
