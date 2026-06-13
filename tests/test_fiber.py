from __future__ import annotations

import asyncio

import pytest

import effect as Effect
from effect import fail, fork, run_async, run_async_exit, succeed, sync
from effect.cause import is_interrupted
from effect.exit import Failure


@pytest.mark.asyncio
async def test_fork_join_success() -> None:
    @Effect.gen
    def program():
        fib = yield fork(succeed(42))
        res = yield fib.join()
        return res

    assert await run_async(program()) == 42


@pytest.mark.asyncio
async def test_fork_join_failure() -> None:
    @Effect.gen
    def program():
        fib = yield fork(fail("boom"))
        res = yield fib.join()
        return res

    exit_val = await run_async_exit(program())
    assert isinstance(exit_val, Failure)


@pytest.mark.asyncio
async def test_fork_interrupt() -> None:
    actions = []

    def register(resume):
        async def work():
            try:
                await asyncio.sleep(1)
                resume(succeed("done"))
            except asyncio.CancelledError:
                pass

        asyncio.create_task(work())
        if hasattr(resume, "on_cancel"):
            resume.on_cancel(lambda: actions.append("cancelled"))

    @Effect.gen
    def background():
        yield Effect.on_exit(
            Effect.async_(register), lambda _exit: sync(lambda: actions.append("cleanup"))
        )
        return "ok"

    @Effect.gen
    def program():
        fib = yield fork(background())
        loop = asyncio.get_running_loop()

        def wait(r):
            loop.call_later(0.01, lambda: r(succeed(None)))

        yield Effect.async_(wait)
        exit_val = yield fib.interrupt()
        return exit_val

    exit_val = await run_async(program())
    assert isinstance(exit_val, Failure)
    assert is_interrupted(exit_val.cause)
    assert "cancelled" in actions
    assert "cleanup" in actions
