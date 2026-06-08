from __future__ import annotations

import asyncio

import pytest

import effect as Effect
from effect import pipe, run_async, run_sync, succeed
from effect.context import GenericTag, make, merge
from effect.layer import merge as merge_layers
from effect.layer import provide_to
from effect.layer import succeed as layer_succeed
from effect.ref import make as ref_make


class TestContext:
    def test_tag_gen(self) -> None:
        Port = GenericTag("Port")

        @Effect.gen
        def program():
            port = yield Port
            return port

        ctx = make(Port, 8080)
        assert run_sync(Effect.provide_context(program(), ctx)) == 8080

    def test_provide_service(self) -> None:
        Port = GenericTag("Port")

        @Effect.gen
        def program():
            port = yield Port
            return port * 2

        assert run_sync(Effect.provide_service(program(), Port, 21)) == 42

    def test_merge_context(self) -> None:
        Port = GenericTag("Port")
        Host = GenericTag("Host")
        ctx = merge(make(Port, 8080), make(Host, "localhost"))

        @Effect.gen
        def program():
            port = yield Port
            host = yield Host
            return f"{host}:{port}"

        assert run_sync(Effect.provide_context(program(), ctx)) == "localhost:8080"


class TestLayer:
    def test_layer_succeed(self) -> None:
        Port = GenericTag("Port")

        @Effect.gen
        def program():
            port = yield Port
            return port

        layer = layer_succeed(Port, 3000)
        assert run_sync(provide_to(program(), layer)) == 3000

    def test_layer_merge(self) -> None:
        Port = GenericTag("Port")
        Host = GenericTag("Host")

        @Effect.gen
        def program():
            port = yield Port
            host = yield Host
            return f"{host}:{port}"

        layer = merge_layers(layer_succeed(Port, 8080), layer_succeed(Host, "127.0.0.1"))
        assert run_sync(provide_to(program(), layer)) == "127.0.0.1:8080"

    def test_effect_provide(self) -> None:
        Port = GenericTag("Port")

        @Effect.gen
        def program():
            port = yield Port
            return port

        program = pipe(program(), Effect.provide(layer_succeed(Port, 9000)))
        assert run_sync(program) == 9000


class TestRef:
    def test_ref_get_set(self) -> None:
        @Effect.gen
        def program():
            counter = yield ref_make(0)
            yield counter.set(1)
            value = yield counter.get()
            return value

        assert run_sync(program()) == 1

    def test_ref_modify(self) -> None:
        @Effect.gen
        def program():
            counter = yield ref_make(10)
            previous = yield counter.modify(lambda n: (n, n + 5))
            current = yield counter.get()
            return previous, current

        assert run_sync(program()) == (10, 15)


class TestAsync:
    @pytest.mark.asyncio
    async def test_async_sleep(self) -> None:
        def register(resume) -> None:
            async def waiter() -> None:
                await asyncio.sleep(0.01)
                resume(succeed(99))

            asyncio.create_task(waiter())

        assert await run_async(Effect.async_(register)) == 99

    @pytest.mark.asyncio
    async def test_async_with_context(self) -> None:
        Port = GenericTag("Port")

        @Effect.gen
        def program():
            port = yield Port
            return port

        def register(resume) -> None:
            async def waiter() -> None:
                await asyncio.sleep(0.01)
                resume(Effect.provide_service(program(), Port, 7777))

            asyncio.create_task(waiter())

        assert await run_async(Effect.async_(register)) == 7777

    def test_run_sync_rejects_async(self) -> None:
        def register(_resume) -> None:
            pass

        with pytest.raises(Effect.AsyncFiberException):
            run_sync(Effect.async_(register))
