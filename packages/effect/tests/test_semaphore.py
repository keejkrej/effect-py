from __future__ import annotations

import asyncio

import pytest

import effect as Effect
from effect import fork, run_async, semaphore_make, succeed


@pytest.mark.asyncio
async def test_semaphore_limit() -> None:
    running = 0
    max_running = 0

    @Effect.gen
    def task():
        nonlocal running, max_running
        running += 1
        max_running = max(max_running, running)

        def wait(r):
            asyncio.get_running_loop().call_later(0.01, lambda: r(succeed(None)))

        yield Effect.async_(wait)
        running -= 1
        return None

    @Effect.gen
    def program():
        sem = yield semaphore_make(2)
        fib1 = yield fork(sem.with_permit(task()))
        fib2 = yield fork(sem.with_permit(task()))
        fib3 = yield fork(sem.with_permit(task()))

        yield fib1.join()
        yield fib2.join()
        yield fib3.join()

    await run_async(program())
    assert max_running <= 2
