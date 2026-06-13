from __future__ import annotations

import pytest

import effect as Effect
from effect import fail, recurs, repeat, retry, run_async, succeed


@pytest.mark.asyncio
async def test_schedule_recurs() -> None:
    count = 0

    def action():
        nonlocal count
        count += 1
        return succeed(count)

    res = await run_async(repeat(Effect.suspend(action), recurs(3)))
    assert res == 2
    assert count == 4


@pytest.mark.asyncio
async def test_retry_spaced() -> None:
    count = 0

    def action():
        nonlocal count
        count += 1
        if count < 3:
            return fail("boom")
        return succeed("ok")

    res = await run_async(retry(Effect.suspend(action), recurs(5)))
    assert res == "ok"
    assert count == 3
