from __future__ import annotations

import asyncio

import pytest

import effect as Effect
from effect import deferred_make, fork, run_async, run_async_exit, succeed
from effect.exit import Failure


@pytest.mark.asyncio
async def test_deferred_succeed() -> None:
    @Effect.gen
    def program():
        d = yield deferred_make()
        loop = asyncio.get_running_loop()

        def register(r):
            loop.call_later(0.01, lambda: r(succeed(None)))

        yield fork(
            Effect.async_(register).pipe(lambda eff: Effect.flat_map(eff, lambda _: d.succeed(42)))
        )
        val = yield d.await_()
        return val

    assert await run_async(program()) == 42


@pytest.mark.asyncio
async def test_deferred_fail() -> None:
    @Effect.gen
    def program():
        d = yield deferred_make()
        yield d.fail("boom")
        val = yield d.await_()
        return val

    exit_val = await run_async_exit(program())
    assert isinstance(exit_val, Failure)


@pytest.mark.asyncio
async def test_deferred_multiple_awaiters() -> None:
    @Effect.gen
    def program():
        d = yield deferred_make()
        fib1 = yield fork(d.await_())
        fib2 = yield fork(d.await_())
        yield d.succeed("hello")
        v1 = yield fib1.join()
        v2 = yield fib2.join()
        return v1, v2

    assert await run_async(program()) == ("hello", "hello")


@pytest.mark.asyncio
async def test_deferred_complete_once() -> None:
    @Effect.gen
    def program():
        d = yield deferred_make()
        first = yield d.succeed(1)
        second = yield d.succeed(2)
        val = yield d.await_()
        return first, second, val

    assert await run_async(program()) == (True, False, 1)
