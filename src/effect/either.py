from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar, Generic, TypeVar, final

A = TypeVar("A")
E = TypeVar("E")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Left(Generic[E]):
    _tag: ClassVar[str] = "Left"
    _op: ClassVar[str] = "Left"
    left: E

    def pipe(self, *fns: Callable[..., object]) -> object:
        from effect.pipeable import pipe_arguments

        return pipe_arguments(self, fns)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Right(Generic[A]):
    _tag: ClassVar[str] = "Right"
    _op: ClassVar[str] = "Right"
    right: A

    def pipe(self, *fns: Callable[..., object]) -> object:
        from effect.pipeable import pipe_arguments

        return pipe_arguments(self, fns)


type Either[A, E] = Left[E] | Right[A]


def left(error: E) -> Left[E]:
    return Left(left=error)


def right(value: A) -> Right[A]:
    return Right(right=value)


def is_either(value: object) -> bool:
    return isinstance(value, (Left, Right))


def is_left(value: Either[A, E]) -> bool:
    return isinstance(value, Left)


def is_right(value: Either[A, E]) -> bool:
    return isinstance(value, Right)


def from_nullable(value: A | None, on_null: E) -> Either[A, E]:
    if value is None:
        return left(on_null)
    return right(value)
