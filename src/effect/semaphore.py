from __future__ import annotations

import asyncio
from typing import Never, TypeVar

from effect._internal import core as internal
from effect._internal.core import Effect, async_, succeed, sync

A = TypeVar("A")
E = TypeVar("E")
R = TypeVar("R")


class Semaphore:
    def __init__(self, permits: int) -> None:
        self._async_semaphore: asyncio.Semaphore | None = None
        self._permits = permits

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._async_semaphore is None:
            self._async_semaphore = asyncio.Semaphore(self._permits)
        return self._async_semaphore

    def acquire(self) -> Effect[None, Never, Never]:
        def register(resume):
            sem = self._get_semaphore()
            task = asyncio.create_task(sem.acquire())

            def callback(fut):
                if not fut.cancelled():
                    resume(succeed(None))

            task.add_done_callback(callback)

            if hasattr(resume, "on_cancel"):
                resume.on_cancel(lambda: task.cancel())

        return async_(register)

    def release(self) -> Effect[None, Never, Never]:
        return sync(lambda: self._get_semaphore().release())

    def with_permit(self, effect: Effect[A, E, R]) -> Effect[A, E, R]:
        return internal.flat_map(
            self.acquire(), lambda _: internal.on_exit(effect, lambda _: self.release())
        )


def semaphore_make(permits: int) -> Effect[Semaphore, Never, Never]:
    return sync(lambda: Semaphore(permits))
