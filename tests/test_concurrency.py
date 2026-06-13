from __future__ import annotations

import asyncio

import pytest

import effect as Effect
from effect import all, fail, run_async, run_async_exit, succeed, sync, zip_par
from effect import zip as eff_zip
from effect.exit import Failure


@pytest.mark.asyncio
async def test_all_sequential_list() -> None:
    effects = [succeed(1), succeed(2), succeed(3)]
    res = await run_async(all(effects))
    assert res == [1, 2, 3]


@pytest.mark.asyncio
async def test_all_parallel_list() -> None:
    order = []

    def wait_and_add(val, delay):
        def register(resume):
            asyncio.get_running_loop().call_later(
                delay, lambda: (order.append(val), resume(succeed(val)))
            )

        return Effect.async_(register)

    effects = [wait_and_add(1, 0.05), wait_and_add(2, 0.01)]
    res = await run_async(all(effects, concurrency=True))
    assert res == [1, 2]
    assert order == [2, 1]


@pytest.mark.asyncio
async def test_all_sequential_dict() -> None:
    effects = {"a": succeed(1), "b": succeed(2)}
    res = await run_async(all(effects))
    assert res == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_all_parallel_dict() -> None:
    effects = {"a": succeed(1), "b": succeed(2)}
    res = await run_async(all(effects, concurrency=True))
    assert res == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_all_parallel_interrupt_on_failure() -> None:
    interrupted = []

    def hang():
        @Effect.gen
        def run():
            yield Effect.on_exit(
                Effect.async_(lambda resume: None),
                lambda _exit: sync(lambda: interrupted.append("ok")),
            )

        return run()

    effects = [hang(), fail("boom")]
    exit_val = await run_async_exit(all(effects, concurrency=True))
    assert isinstance(exit_val, Failure)
    assert "ok" in interrupted


@pytest.mark.asyncio
async def test_zip_sequential() -> None:
    res = await run_async(eff_zip(succeed(1), succeed(2)))
    assert res == (1, 2)


@pytest.mark.asyncio
async def test_zip_parallel() -> None:
    res = await run_async(zip_par(succeed(1), succeed(2)))
    assert res == (1, 2)
