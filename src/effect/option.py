from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar, Generic, TypeVar, final

A = TypeVar("A")

TYPE_ID: str = "effect/Option"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class None_(Generic[A]):
    _tag: ClassVar[str] = "None"
    _op: ClassVar[str] = "None"

    def pipe(self, *fns: Callable[..., object]) -> object:
        from effect.pipeable import pipe_arguments

        return pipe_arguments(self, fns)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Some(Generic[A]):
    _tag: ClassVar[str] = "Some"
    _op: ClassVar[str] = "Some"
    value: A

    def pipe(self, *fns: Callable[..., object]) -> object:
        from effect.pipeable import pipe_arguments

        return pipe_arguments(self, fns)


Option = None_[A] | Some[A]


def none() -> None_[A]:
    return None_()


def some(value: A) -> Some[A]:
    return Some(value=value)


def is_option(value: object) -> bool:
    return isinstance(value, (None_, Some))


def is_none(value: Option[A]) -> bool:
    return isinstance(value, None_)


def is_some(value: Option[A]) -> bool:
    return isinstance(value, Some)


def get_or_else(option: Option[A], fallback: A) -> A:
    if isinstance(option, Some):
        return option.value
    return fallback


def get_or_none(option: Option[A]) -> A | None:
    if isinstance(option, Some):
        return option.value
    return None
