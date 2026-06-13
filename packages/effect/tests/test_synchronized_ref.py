from __future__ import annotations

from typing import Never

import pytest

import effect as Effect
from effect import SynchronizedRef, fork, run_async, sleep, succeed, synchronized_ref_make


@pytest.mark.asyncio
async def test_synchronized_ref_basic() -> None:
    ref: SynchronizedRef[int] = await run_async(synchronized_ref_make(10))
    val1 = await run_async(ref.get())
    assert val1 == 10

    await run_async(ref.set(20))
    val2 = await run_async(ref.get())
    assert val2 == 20


@pytest.mark.asyncio
async def test_synchronized_ref_update() -> None:
    ref: SynchronizedRef[int] = await run_async(synchronized_ref_make(10))
    await run_async(ref.update(lambda x: x + 5))
    val = await run_async(ref.get())
    assert val == 15


@pytest.mark.asyncio
async def test_synchronized_ref_modify() -> None:
    ref: SynchronizedRef[int] = await run_async(synchronized_ref_make(10))
    ret = await run_async(ref.modify(lambda x: ("result", x + 5)))
    assert ret == "result"
    val = await run_async(ref.get())
    assert val == 15


@pytest.mark.asyncio
async def test_synchronized_ref_update_effect() -> None:
    ref: SynchronizedRef[int] = await run_async(synchronized_ref_make(10))

    def effectful_update(x: int) -> Effect.Effect[int, Never, Never]:
        return succeed(x + 20)

    await run_async(ref.update_effect(effectful_update))
    val = await run_async(ref.get())
    assert val == 30


@pytest.mark.asyncio
async def test_synchronized_ref_modify_effect() -> None:
    ref: SynchronizedRef[int] = await run_async(synchronized_ref_make(10))

    def effectful_modify(x: int) -> Effect.Effect[tuple[str, int], Never, Never]:
        return succeed(("ret", x + 25))

    ret = await run_async(ref.modify_effect(effectful_modify))
    assert ret == "ret"
    val = await run_async(ref.get())
    assert val == 35


@pytest.mark.asyncio
async def test_synchronized_ref_mutual_exclusion() -> None:
    # Verify updates execute sequentially
    ref: SynchronizedRef[list[str]] = await run_async(synchronized_ref_make([]))

    # update_effect 1: append "start1", sleep 0.05s, append "end1"
    @Effect.gen
    def f1(x):
        new_x = [*x, "start1"]
        yield sleep(0.05)
        return [*new_x, "end1"]

    # update_effect 2: append "start2", sleep 0.05s, append "end2"
    @Effect.gen
    def f2(x):
        new_x = [*x, "start2"]
        yield sleep(0.05)
        return [*new_x, "end2"]

    # Fork update1 and then update2 (with a tiny gap to ensure update1 starts first)
    @Effect.gen
    def program():
        fib1 = yield fork(ref.update_effect(f1))
        yield sleep(0.01)
        fib2 = yield fork(ref.update_effect(f2))
        yield fib1.join()
        yield fib2.join()

    await run_async(program())
    val = await run_async(ref.get())
    # Mutual exclusion ensures update1 completes before update2 starts
    assert val == ["start1", "end1", "start2", "end2"]
