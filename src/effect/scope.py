from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Never, TypeVar

from effect._internal import core as internal
from effect.context import GenericTag
from effect.exit import Exit
from effect.pipeable import pipe_arguments

A = TypeVar("A")
E = TypeVar("E")
R = TypeVar("R")

Scope = GenericTag("effect/Scope")


class ScopeTag:
    """Type-level marker for `Effect[..., ScopeTag]` requirements."""


Finalizer = Callable[[Exit[Any, Any]], internal.Effect[Any, Any, Any]]


@dataclass
class CloseableScope:
    _finalizers: list[Finalizer] = field(default_factory=list)
    _closed: Exit[Any, Any] | None = field(default=None, repr=False)

    def pipe(self, *fns: Callable[[Any], Any]) -> Any:
        return pipe_arguments(self, fns)

    def add_finalizer(
        self,
        finalizer: internal.Effect[Any, Any, Any],
    ) -> internal.Effect[None, Never, Never]:
        return self.add_finalizer_exit(lambda _exit: finalizer)

    def add_finalizer_exit(self, finalizer: Finalizer) -> internal.Effect[None, Never, Never]:
        if self._closed is not None:
            return internal.map_(finalizer(self._closed), lambda _: None)
        self._finalizers.append(finalizer)
        return internal.succeed(None)

    def close(self, exit: Exit[Any, Any]) -> internal.Effect[None, Never, Never]:
        if self._closed is not None:
            return internal.succeed(None)

        self._closed = exit
        finalizers = list(reversed(self._finalizers))
        self._finalizers.clear()

        result: internal.Effect[None, Never, Never] = internal.succeed(None)
        for fin in finalizers:
            result = internal.flat_map(result, lambda _, f=fin: f(exit))
        return result


def make() -> internal.Effect[CloseableScope, Never, Never]:
    return internal.sync(CloseableScope)


def extend(
    effect: internal.Effect[A, E, R],
    scope: CloseableScope,
) -> internal.Effect[A, E, Never]:
    return internal.provide_service(effect, Scope, scope)


def use(
    effect: internal.Effect[A, E, R],
    scope: CloseableScope,
) -> internal.Effect[A, E, Never]:
    return internal.on_exit(extend(effect, scope), scope.close)


def scoped_with(
    f: Callable[[CloseableScope], internal.Effect[A, E, R]],
) -> internal.Effect[A, E, R]:
    return internal.flat_map(make(), lambda scope: use(f(scope), scope))


def scoped(
    effect: internal.Effect[A, E, R],
) -> internal.Effect[A, E, Never]:
    return internal.flat_map(make(), lambda scope: use(effect, scope))


def add_finalizer(
    finalizer: Finalizer,
) -> internal.Effect[None, Never, ScopeTag]:
    return internal.flat_map(
        internal.tag_effect(Scope),
        lambda scope: scope.add_finalizer_exit(finalizer),
    )


def acquire_release(
    acquire: internal.Effect[A, E, R],
    release: Callable[[A, Exit[Any, Any]], internal.Effect[Any, Never, Any]],
) -> internal.Effect[A, E, R | ScopeTag | Any]:
    return internal.flat_map(
        acquire,
        lambda resource: internal.tap(
            internal.succeed(resource),
            lambda _: add_finalizer(lambda exit: release(resource, exit)),
        ),
    )
