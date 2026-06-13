from __future__ import annotations

import asyncio
from typing import Any, Generic, Never, TypeVar

from effect._internal.core import Effect, async_, succeed, sync

A = TypeVar("A")


class Queue(Generic[A]):
    def __init__(self, max_size: int = 0) -> None:
        self._async_queue: asyncio.Queue[A] | None = None
        self._max_size = max_size

    def _get_queue(self) -> asyncio.Queue[A]:
        if self._async_queue is None:
            self._async_queue = asyncio.Queue(maxsize=self._max_size)
        return self._async_queue

    def take(self) -> Effect[A, Never, Never]:
        def register(resume):
            q = self._get_queue()
            task = asyncio.create_task(q.get())

            def callback(fut):
                if not fut.cancelled():
                    resume(succeed(fut.result()))

            task.add_done_callback(callback)

            if hasattr(resume, "on_cancel"):
                resume.on_cancel(lambda: task.cancel())

        return async_(register)

    def offer(self, value: A) -> Effect[None, Never, Never]:
        def register(resume):
            q = self._get_queue()
            task = asyncio.create_task(q.put(value))

            def callback(fut):
                if not fut.cancelled():
                    resume(succeed(None))

            task.add_done_callback(callback)

            if hasattr(resume, "on_cancel"):
                resume.on_cancel(lambda: task.cancel())

        return async_(register)

    def size(self) -> Effect[int, Never, Never]:
        return sync(lambda: self._get_queue().qsize())


def queue_make(max_size: int = 0) -> Effect[Queue[Any], Never, Never]:
    return sync(lambda: Queue(max_size))
