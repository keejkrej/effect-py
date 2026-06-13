from __future__ import annotations

import pytest

import effect as Effect
from effect import pubsub_make, run_async, scoped


@pytest.mark.asyncio
async def test_pubsub_broadcast() -> None:
    @Effect.gen
    def program():
        hub = yield pubsub_make()

        @Effect.gen
        def run_in_scope():
            q1 = yield hub.subscribe()
            q2 = yield hub.subscribe()

            yield hub.publish("hello")
            yield hub.publish("world")

            v1_1 = yield q1.take()
            v1_2 = yield q1.take()

            v2_1 = yield q2.take()
            v2_2 = yield q2.take()

            return v1_1, v1_2, v2_1, v2_2

        res = yield scoped(run_in_scope())
        return res

    assert await run_async(program()) == ("hello", "world", "hello", "world")
