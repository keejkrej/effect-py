from __future__ import annotations

from collections.abc import Callable
from typing import Never, TypeVar, cast

from effect._internal import core as internal
from effect.concurrency import all as all_effect
from effect.concurrency import zip as zip_effect
from effect.concurrency import zip_par
from effect.deferred import Deferred, deferred_make
from effect.exit import Exit
from effect.fiber import Fiber, fork
from effect.function_ import LazyArg, dual, pipe
from effect.queue import Queue, queue_make

A = TypeVar("A")
E = TypeVar("E")
R = TypeVar("R")

Effect = internal.Effect
YieldWrap = internal.YieldWrap

is_effect = internal.is_effect
succeed = internal.succeed
fail = internal.fail
fail_cause = internal.fail_cause
die = internal.die
sync = internal.sync
suspend = internal.suspend
flat_map = dual(2, internal.flat_map)
map = dual(2, internal.map_)
catch_all = dual(2, internal.catch_all)
catch_all_cause = dual(2, internal.catch_all_cause)
catch_if = dual(3, internal.catch_if)
catch_tag = dual(3, internal.catch_tag)
match_effect = dual(2, internal.match_effect)
tap = dual(2, internal.tap)
on_exit = dual(2, internal.on_exit)
gen = internal.gen
async_ = internal.async_
tag = internal.tag_effect
context = internal.context_effect
provide_context = dual(2, internal.provide_context)
provide_some_context = dual(2, internal.provide_some_context)
provide_service = dual(3, internal.provide_service)
AsyncFiberException = internal.AsyncFiberException

all = all_effect
zip = zip_effect


def try_(thunk: LazyArg[A]) -> Effect[A, Exception, Never]:
    def attempt() -> Effect[A, Exception, Never]:
        try:
            return cast(Effect[A, Exception, Never], succeed(thunk()))
        except Exception as error:
            return cast(Effect[A, Exception, Never], fail(error))

    return suspend(attempt)


def run_sync(effect: Effect[A, E, Never]) -> A:
    return internal.run_sync(effect)


def run_sync_exit(effect: Effect[A, E, R]) -> Exit[A, E]:
    return internal.run_sync_exit(effect)


async def run_async(effect: Effect[A, E, Never]) -> A:
    return await internal.run_async(effect)


async def run_async_exit(effect: Effect[A, E, R]) -> Exit[A, E]:
    return await internal.run_async_exit(effect)


def provide(
    layer: object,
) -> Callable[[Effect[A, E, R]], Effect[A, E, Never]]:
    from effect.layer import Layer, provide_to

    if not isinstance(layer, Layer):
        msg = f"Expected Layer, got {type(layer)!r}"
        raise TypeError(msg)

    def wrapper(effect: Effect[A, E, R]) -> Effect[A, E, Never]:
        return cast(Effect[A, E, Never], provide_to(effect, layer))

    return wrapper


__all__ = [
    "AsyncFiberException",
    "Effect",
    "YieldWrap",
    "all",
    "async_",
    "catch_all",
    "catch_all_cause",
    "catch_if",
    "catch_tag",
    "context",
    "Deferred",
    "deferred_make",
    "die",
    "fail",
    "fail_cause",
    "Fiber",
    "flat_map",
    "fork",
    "gen",
    "is_effect",
    "map",
    "match_effect",
    "on_exit",
    "pipe",
    "provide",
    "provide_context",
    "provide_service",
    "provide_some_context",
    "Queue",
    "queue_make",
    "run_async",
    "run_async_exit",
    "run_sync",
    "run_sync_exit",
    "succeed",
    "suspend",
    "sync",
    "tap",
    "tag",
    "try_",
    "zip",
    "zip_par",
]
