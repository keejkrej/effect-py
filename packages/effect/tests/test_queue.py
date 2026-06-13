from __future__ import annotations

import asyncio

import pytest

import effect as Effect
from effect import fork, queue_make, run_async, succeed


@pytest.mark.asyncio
async def test_queue_fifo() -> None:
    @Effect.gen
    def program():
        q = yield queue_make()
        yield q.offer(1)
        yield q.offer(2)
        v1 = yield q.take()
        v2 = yield q.take()
        size = yield q.size()
        return v1, v2, size

    assert await run_async(program()) == (1, 2, 0)


@pytest.mark.asyncio
async def test_queue_take_blocks() -> None:
    @Effect.gen
    def program():
        q = yield queue_make()
        take_fib = yield fork(q.take())

        def wait1(r):
            loop = asyncio.get_running_loop()
            loop.call_later(0.01, lambda: r(succeed(None)))

        yield Effect.async_(wait1)
        yield q.offer(42)

        res = yield take_fib.join()
        return res

    assert await run_async(program()) == 42


@pytest.mark.asyncio
async def test_queue_taker_cancellation_no_leak() -> None:
    @Effect.gen
    def program():
        q = yield queue_make()
        take_fib = yield fork(q.take())

        def wait2(r):
            loop = asyncio.get_running_loop()
            loop.call_later(0.01, lambda: r(succeed(None)))

        yield Effect.async_(wait2)
        yield take_fib.interrupt()

        yield q.offer(99)

        size = yield q.size()
        val = yield q.take()
        return size, val

    assert await run_async(program()) == (1, 99)
