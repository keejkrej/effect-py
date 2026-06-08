from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar, Generic, TypeVar, final

from effect.cause import Cause
from effect.option import Option, none, some

A = TypeVar("A")
E = TypeVar("E")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Success(Generic[A, E]):
    _tag: ClassVar[str] = "Success"
    _op: ClassVar[str] = "Success"
    value: A

    @property
    def effect_instruction_i0(self) -> A:
        return self.value

    def pipe(self, *fns: Callable[..., object]) -> object:
        from effect.pipeable import pipe_arguments

        return pipe_arguments(self, fns)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Failure(Generic[A, E]):
    _tag: ClassVar[str] = "Failure"
    _op: ClassVar[str] = "Failure"
    cause: Cause[E]

    @property
    def effect_instruction_i0(self) -> Cause[E]:
        return self.cause

    def pipe(self, *fns: Callable[..., object]) -> object:
        from effect.pipeable import pipe_arguments

        return pipe_arguments(self, fns)


Exit = Success[A, E] | Failure[A, E]


def succeed(value: A) -> Success[A, E]:
    return Success(value=value)


def fail(cause: Cause[E]) -> Failure[A, E]:
    return Failure(cause=cause)


def is_exit(value: object) -> bool:
    return isinstance(value, (Success, Failure))


def is_success(exit: Exit[A, E]) -> bool:
    return isinstance(exit, Success)


def is_failure(exit: Exit[A, E]) -> bool:
    return isinstance(exit, Failure)


def is_interrupted(exit: Exit[A, E]) -> bool:
    if isinstance(exit, Failure):
        from effect.cause import is_interrupted as cause_is_interrupted

        return cause_is_interrupted(exit.cause)
    return False


def cause_option(exit: Exit[A, E]) -> Option[Cause[E]]:
    if isinstance(exit, Failure):
        return some(exit.cause)
    return none()


def get_or_else(exit: Exit[A, E], fallback: A) -> A:
    if isinstance(exit, Success):
        return exit.value
    return fallback


def match(
    exit: Exit[A, E],
    *,
    on_failure: Callable[[Cause[E]], object],
    on_success: Callable[[A], object],
) -> object:
    if isinstance(exit, Success):
        return on_success(exit.value)
    return on_failure(exit.cause)
