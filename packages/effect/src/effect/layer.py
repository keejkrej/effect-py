from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, Never, TypeVar

from effect.context import Context, Tag, add, empty
from effect.effect import Effect, flat_map, provide_context
from effect.effect import map as effect_map
from effect.effect import succeed as effect_succeed

ROut = TypeVar("ROut")
E = TypeVar("E")
RIn = TypeVar("RIn")


@dataclass(frozen=True, slots=True)
class Layer(Generic[ROut, E, RIn]):
    build: Callable[[Context[Any]], Effect[Context[ROut], E, RIn]]

    def pipe(self, *fns: Callable[[Any], Any]) -> Any:
        from effect.pipeable import pipe_arguments

        return pipe_arguments(self, fns)


def succeed(tag: Tag[Any, Any], resource: object) -> Layer[Any, Never, Never]:
    return Layer(lambda ctx: effect_succeed(add(ctx, tag, resource)))


def effect(
    tag: Tag[Any, Any],
    acquire: Effect[Any, E, RIn],
) -> Layer[Any, E, RIn]:
    def build(ctx: Context[Any]) -> Effect[Context[Any], E, RIn]:
        return effect_map(acquire, lambda service: add(ctx, tag, service))

    return Layer(build)


def merge(
    left: Layer[ROut, E, RIn],
    right: Layer[Any, Any, Any],
) -> Layer[ROut | Any, E | Any, RIn | Any]:
    def build(ctx: Context[Any]) -> Effect[Context[ROut | Any], E | Any, RIn | Any]:
        return flat_map(left.build(ctx), right.build)

    return Layer(build)


def build(
    layer: Layer[ROut, E, RIn],
    context: Context[Any] | None = None,
) -> Effect[Context[ROut], E, RIn]:
    return layer.build(context or empty())


def provide_to(
    effect: Effect[Any, Any, Any],
    layer: Layer[ROut, E, RIn],
) -> Effect[Any, E | Any, RIn | Any]:
    return flat_map(build(layer), lambda ctx: provide_context(effect, ctx))
