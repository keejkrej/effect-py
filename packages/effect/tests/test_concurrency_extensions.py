from __future__ import annotations

import asyncio

import pytest

import effect as Effect
from effect import (
    TimeoutException,
    race,
    race_first,
    run_async,
    run_async_exit,
    sleep,
    succeed,
    timeout,
)
from effect.exit import Failure


@pytest.mark.asyncio
async def test_sleep() -> None:
    # Verify sleep delays execution
    start = asyncio.get_running_loop().time()
    await run_async(sleep(0.05))
    end = asyncio.get_running_loop().time()
    assert end - start >= 0.045


@pytest.mark.asyncio
async def test_race_left_succeeds_first() -> None:
    # Left succeeds first, right is interrupted
    right_interrupted = False

    @Effect.gen
    def left():
        yield sleep(0.01)
        return "left"

    def set_right_interrupted(exit_val):
        nonlocal right_interrupted
        from effect.cause import is_interrupted

        if isinstance(exit_val, Failure) and is_interrupted(exit_val.cause):
            right_interrupted = True
        return succeed(None)

    right_effect = Effect.on_exit(sleep(0.1), set_right_interrupted)

    res = await run_async(race(left(), right_effect))
    assert res == "left"
    # Allow some time for background interruption task to complete/run callbacks
    await asyncio.sleep(0.02)
    assert right_interrupted


@pytest.mark.asyncio
async def test_race_right_succeeds_first() -> None:
    # Right succeeds first, left is interrupted
    left_interrupted = False

    def set_left_interrupted(exit_val):
        nonlocal left_interrupted
        from effect.cause import is_interrupted

        if isinstance(exit_val, Failure) and is_interrupted(exit_val.cause):
            left_interrupted = True
        return succeed(None)

    left_effect = Effect.on_exit(sleep(0.1), set_left_interrupted)

    @Effect.gen
    def right():
        yield sleep(0.01)
        return "right"

    res = await run_async(race(left_effect, right()))
    assert res == "right"
    await asyncio.sleep(0.02)
    assert left_interrupted


@pytest.mark.asyncio
async def test_race_left_fails_right_succeeds() -> None:
    # Left fails first, but right succeeds later and wins
    @Effect.gen
    def left():
        yield sleep(0.01)
        yield Effect.fail("left_fail")

    @Effect.gen
    def right():
        yield sleep(0.05)
        return "right_success"

    res = await run_async(race(left(), right()))
    assert res == "right_success"


@pytest.mark.asyncio
async def test_race_both_fail() -> None:
    # Both fail, returns the last failure
    @Effect.gen
    def left():
        yield sleep(0.01)
        yield Effect.fail("left_fail")

    @Effect.gen
    def right():
        yield sleep(0.03)
        yield Effect.fail("right_fail")

    exit_val = await run_async_exit(race(left(), right()))
    assert isinstance(exit_val, Failure)
    from effect.cause import failure_option
    from effect.option import Some

    opt = failure_option(exit_val.cause)
    assert isinstance(opt, Some)
    assert opt.value == "right_fail"


@pytest.mark.asyncio
async def test_race_first_left_fails_wins() -> None:
    # race_first returns first completion, even if failure
    @Effect.gen
    def left():
        yield sleep(0.01)
        yield Effect.fail("left_fail")

    @Effect.gen
    def right():
        yield sleep(0.1)
        return "right"

    exit_val = await run_async_exit(race_first(left(), right()))
    assert isinstance(exit_val, Failure)
    from effect.cause import failure_option
    from effect.option import Some

    opt = failure_option(exit_val.cause)
    assert isinstance(opt, Some)
    assert opt.value == "left_fail"


@pytest.mark.asyncio
async def test_timeout_success() -> None:
    # Succeeds within timeout
    @Effect.gen
    def program():
        yield sleep(0.02)
        return "ok"

    res = await run_async(timeout(program(), 0.1))
    assert res == "ok"


@pytest.mark.asyncio
async def test_timeout_fail() -> None:
    # Fails with TimeoutException when timeout is exceeded
    @Effect.gen
    def program():
        yield sleep(0.1)
        return "ok"

    exit_val = await run_async_exit(timeout(program(), 0.02))
    assert isinstance(exit_val, Failure)
    from effect.cause import failure_option
    from effect.option import Some

    opt = failure_option(exit_val.cause)
    assert isinstance(opt, Some)
    assert isinstance(opt.value, TimeoutException)
