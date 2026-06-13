from __future__ import annotations

from dataclasses import dataclass

from effect.data import TaggedError


@dataclass(eq=False, kw_only=True)
class ShapeError(TaggedError):
    _tag = "ShapeError"
    message: str
    expected: tuple[int, ...] | None = None
    actual: tuple[int, ...] | None = None


@dataclass(eq=False, kw_only=True)
class ArrayError(TaggedError):
    _tag = "ArrayError"
    message: str
