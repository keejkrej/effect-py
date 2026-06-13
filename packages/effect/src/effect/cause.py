from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Generic, TypeVar, final

from effect.either import Left, Right, left, right
from effect.option import Option, Some, none, some

E = TypeVar("E")

CAUSE_TYPE_ID: str = "effect/Cause"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Empty:
    _tag: ClassVar[str] = "Empty"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Fail(Generic[E]):
    _tag: ClassVar[str] = "Fail"
    error: E


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Die:
    _tag: ClassVar[str] = "Die"
    defect: object


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Interrupt:
    _tag: ClassVar[str] = "Interrupt"
    fiber_id: int = 0


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Sequential(Generic[E]):
    _tag: ClassVar[str] = "Sequential"
    left: Cause[E]
    right: Cause[E]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Parallel(Generic[E]):
    _tag: ClassVar[str] = "Parallel"
    left: Cause[E]
    right: Cause[E]


Cause = Empty | Fail[E] | Die | Interrupt | Sequential[E] | Parallel[E]


def empty() -> Empty:
    return Empty()


def fail(error: E) -> Fail[E]:
    return Fail(error=error)


def die(defect: object) -> Die:
    return Die(defect=defect)


def interrupt(fiber_id: int = 0) -> Interrupt:
    return Interrupt(fiber_id=fiber_id)


def sequential(left_cause: Cause[E], right_cause: Cause[E]) -> Sequential[E]:
    return Sequential(left=left_cause, right=right_cause)


def parallel(left_cause: Cause[E], right_cause: Cause[E]) -> Parallel[E]:
    return Parallel(left=left_cause, right=right_cause)


def is_cause(value: object) -> bool:
    return isinstance(value, (Empty, Fail, Die, Interrupt, Sequential, Parallel))


def is_empty(cause: Cause[E]) -> bool:
    return isinstance(cause, Empty)


def is_failure(cause: Cause[E]) -> bool:
    return isinstance(failure_option(cause), Some)


def is_die(cause: Cause[E]) -> bool:
    return isinstance(cause, Die)


def is_interrupted(cause: Cause[E]) -> bool:
    if isinstance(cause, Interrupt):
        return True
    if isinstance(cause, (Sequential, Parallel)):
        return is_interrupted(cause.left) or is_interrupted(cause.right)
    return False


def failure_option(cause: Cause[E]) -> Option[E]:
    match cause:
        case Fail(error=error):
            return some(error)
        case Sequential(left=left, right=right):
            left_option = failure_option(left)
            if isinstance(left_option, Some):
                return left_option
            return failure_option(right)
        case Parallel(left=left, right=right):
            left_option = failure_option(left)
            if isinstance(left_option, Some):
                return left_option
            return failure_option(right)
        case _:
            return none()


def failure_or_cause(cause: Cause[E]) -> Left[E] | Right[Cause[E]]:
    option = failure_option(cause)
    if isinstance(option, Some):
        return left(option.value)
    return right(cause)


def pretty(cause: Cause[E]) -> str:
    match cause:
        case Empty():
            return "Cause(Empty)"
        case Fail(error=error):
            return f"Fail({error!r})"
        case Die(defect=defect):
            return f"Die({defect!r})"
        case Interrupt(fiber_id=fiber_id):
            return f"Interrupt({fiber_id})"
        case Sequential(left=left, right=right):
            return f"Sequential({pretty(left)}, {pretty(right)})"
        case Parallel(left=left, right=right):
            return f"Parallel({pretty(left)}, {pretty(right)})"
