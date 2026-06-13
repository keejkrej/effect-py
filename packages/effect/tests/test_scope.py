from __future__ import annotations

from typing import Never

import pytest

import effect as Effect
from effect import pipe, run_sync, succeed, sync
from effect.exit import Success
from effect.scope import ScopeTag, acquire_release, add_finalizer, scoped


class TestScope:
    def test_scoped_runs_finalizers(self) -> None:
        actions: list[tuple[str, int]] = []

        def resource(resource_id: int) -> Effect.Effect[int, Never, ScopeTag]:
            return pipe(
                sync(lambda: actions.append(("acquire", resource_id))),
                Effect.flat_map(
                    lambda _: add_finalizer(
                        lambda _exit: sync(lambda: actions.append(("release", resource_id)))
                    ),
                ),
                Effect.flat_map(lambda _: succeed(resource_id)),
            )

        @Effect.gen
        def program():
            resource_id = yield resource(1)
            actions.append(("use", resource_id))
            return resource_id

        assert run_sync(scoped(program())) == 1
        assert actions == [("acquire", 1), ("use", 1), ("release", 1)]

    def test_acquire_release_on_success(self) -> None:
        released: list[tuple[str, str]] = []

        def release(
            resource: str,
            exit: Effect.Exit[str, str],
        ) -> Effect.Effect[None, Never, Never]:
            status = "Success" if isinstance(exit, Success) else "Failure"
            return sync(lambda: released.append((resource, status)))

        program = scoped(acquire_release(succeed("resource"), release))
        assert run_sync(program) == "resource"
        assert released == [("resource", "Success")]

    def test_acquire_release_on_failure(self) -> None:
        released: list[str] = []

        @Effect.gen
        def program():
            yield acquire_release(
                succeed("resource"),
                lambda resource, _exit: sync(lambda: released.append(resource)),
            )
            err = yield Effect.fail("boom")
            return err

        with pytest.raises(RuntimeError, match="boom"):
            run_sync(scoped(program()))

        assert released == ["resource"]

    def test_nested_scoped_finalizers_lifo(self) -> None:
        order: list[int] = []

        def track(value: int) -> Effect.Effect[None, Never, ScopeTag]:
            return add_finalizer(lambda _exit: sync(lambda: order.append(value)))

        @Effect.gen
        def inner():
            yield track(1)
            yield track(2)
            return None

        assert run_sync(scoped(inner())) is None
        assert order == [2, 1]
