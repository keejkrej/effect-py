from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, Never, TypeVar, cast

from effect.pipeable import pipe_arguments

Identifier = TypeVar("Identifier")
S = TypeVar("S")
Services = TypeVar("Services")


class ServiceNotFoundError(KeyError):
    pass


@dataclass(frozen=True, slots=True)
class Tag(Generic[Identifier, S]):
    key: str

    def __iter__(self):
        from effect._internal.core import YieldWrap, tag_effect

        yield YieldWrap(tag_effect(self))

    def pipe(self, *fns: Callable[..., object]) -> object:
        return pipe_arguments(self, fns)


@dataclass(frozen=True, slots=True)
class Context(Generic[Services]):
    services: dict[str, object] = field(default_factory=dict)

    def pipe(self, *fns: Callable[..., object]) -> object:
        return pipe_arguments(self, fns)


def GenericTag(key: str) -> Tag[Any, Any]:
    return Tag(key=key)


TagClass = GenericTag


def empty() -> Context[Never]:
    return Context()


def make(tag: Tag[Identifier, S], service: S) -> Context[Identifier]:
    return Context(services={tag.key: service})


def add(
    context: Context[Services],
    tag: Tag[Identifier, S],
    service: S,
) -> Context[Services | Identifier]:
    services = dict(context.services)
    services[tag.key] = service
    return Context(services=services)


def merge(
    left: Context[Services],
    right: Context[Identifier],
) -> Context[Services | Identifier]:
    services = dict(left.services)
    services.update(right.services)
    return Context(services=services)


def get(context: Context[Services], tag: Tag[Identifier, S]) -> S:
    return unsafe_get(context, tag)


def unsafe_get(context: Context[Services], tag: Tag[Identifier, S]) -> S:
    if tag.key not in context.services:
        msg = f"Service not found: {tag.key}"
        raise ServiceNotFoundError(msg)
    return cast(S, context.services[tag.key])


def is_tag(value: object) -> bool:
    return isinstance(value, Tag)
