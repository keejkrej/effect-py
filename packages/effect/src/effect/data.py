from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any, ClassVar, TypeVar

E = TypeVar("E")


def struct(value: dict[str, Any]) -> dict[str, Any]:
    return dict(value)


def tagged(tag: str):
    def constructor(args: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = struct(args or {})
        payload["_tag"] = tag
        return payload

    return constructor


def case() -> type[Structural]:
    return Structural


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class Structural:
    def __eq__(self, other: object) -> bool:
        if not is_dataclass(other) or type(other) is not type(self):
            return False
        return all(
            getattr(self, field.name) == getattr(other, field.name) for field in fields(self)
        )

    def __hash__(self) -> int:
        return hash(tuple(getattr(self, field.name) for field in fields(self)))


def tagged_class(tag: str):
    class Base(Structural):
        _tag: ClassVar[str] = tag

    Base.__name__ = tag
    return Base


@dataclass(eq=False, kw_only=True)
class TaggedError(Exception):
    _tag: ClassVar[str]

    def __post_init__(self) -> None:
        Exception.__init__(self, str(self))

    def __str__(self) -> str:
        parts = [f"{field.name}={getattr(self, field.name)!r}" for field in fields(self)]
        return f"{self._tag}({', '.join(parts)})"


def tagged_error(tag: str) -> type[TaggedError]:
    @dataclass(eq=False, kw_only=True)
    class Base(TaggedError):
        _tag: ClassVar[str] = tag

    Base.__name__ = tag
    return Base


def error_tag(error: object) -> str | None:
    tag = getattr(error, "_tag", None)
    return tag if isinstance(tag, str) else None


def is_tagged(error: object, tag: str) -> bool:
    return error_tag(error) == tag


def has_tag(error: object, tag: str) -> bool:
    return is_tagged(error, tag)


def cast_tagged(error: E, tag: str) -> E:
    if not is_tagged(error, tag):
        msg = f"Expected tag {tag!r}, got {error_tag(error)!r}"
        raise TypeError(msg)
    return error
