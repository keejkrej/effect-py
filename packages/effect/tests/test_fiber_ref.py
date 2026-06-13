from __future__ import annotations

import pytest

import effect as Effect
from effect import FiberRef, fiber_ref_make, fork, run_async


@pytest.mark.asyncio
async def test_fiber_ref_basic() -> None:
    ref: FiberRef[int] = await run_async(fiber_ref_make(10))
    val1 = await run_async(ref.get())
    assert val1 == 10

    await run_async(ref.set(20))
    val2 = await run_async(ref.get())
    assert val2 == 20


@pytest.mark.asyncio
async def test_fiber_ref_locally() -> None:
    ref: FiberRef[int] = await run_async(fiber_ref_make(10))

    @Effect.gen
    def program():
        val_inside = yield ref.get()
        assert val_inside == 99
        return "ok"

    res = await run_async(ref.locally(program(), 99))
    assert res == "ok"

    val_outside = await run_async(ref.get())
    assert val_outside == 10


@pytest.mark.asyncio
async def test_fiber_ref_locally_pipe() -> None:
    ref: FiberRef[int] = await run_async(fiber_ref_make(10))

    @Effect.gen
    def program():
        val = yield ref.get()
        assert val == 42
        return "ok"

    res = await run_async(Effect.pipe(program(), ref.locally(42)))
    assert res == "ok"


@pytest.mark.asyncio
async def test_fiber_ref_inheritance_and_isolation() -> None:
    ref: FiberRef[int] = await run_async(fiber_ref_make(10))

    # Set value in parent fiber
    await run_async(ref.set(100))

    # Fork child fiber
    @Effect.gen
    def child_program():
        # Child inherits parent value
        val1 = yield ref.get()
        assert val1 == 100

        # Child mutates value
        yield ref.set(200)
        val2 = yield ref.get()
        assert val2 == 200
        return "child_done"

    child_fiber = await run_async(fork(child_program()))

    # Wait for child fiber to finish
    await run_async(child_fiber.join())

    # Parent value remains unchanged
    parent_val = await run_async(ref.get())
    assert parent_val == 100
