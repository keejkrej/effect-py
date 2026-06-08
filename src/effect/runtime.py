from __future__ import annotations

from typing import Never, TypeVar

from effect._internal import core as internal
from effect.effect import Effect
from effect.exit import Exit

A = TypeVar("A")
E = TypeVar("E")
R = TypeVar("R")


class Runtime:
    def run_sync(self, effect: Effect[A, E, Never]) -> A:
        return internal.run_sync(effect)

    def run_sync_exit(self, effect: Effect[A, E, R]) -> Exit[A, E]:
        return internal.run_sync_exit(effect)

    async def run_async(self, effect: Effect[A, E, Never]) -> A:
        return await internal.run_async(effect)

    async def run_async_exit(self, effect: Effect[A, E, R]) -> Exit[A, E]:
        return await internal.run_async_exit(effect)


default_runtime = Runtime()


def run_sync(effect: Effect[A, E, Never]) -> A:
    return default_runtime.run_sync(effect)


def run_sync_exit(effect: Effect[A, E, R]) -> Exit[A, E]:
    return default_runtime.run_sync_exit(effect)


async def run_async(effect: Effect[A, E, Never]) -> A:
    return await default_runtime.run_async(effect)


async def run_async_exit(effect: Effect[A, E, R]) -> Exit[A, E]:
    return await default_runtime.run_async_exit(effect)
