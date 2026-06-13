from __future__ import annotations

import asyncio
from typing import Any, Generic, Never, TypeVar

from effect._internal.core import Effect, async_, fail_cause, succeed, sync
from effect.cause import fail as cause_fail
from effect.exit import Exit, Success
from effect.exit import fail as exit_fail
from effect.exit import succeed as exit_succeed

A = TypeVar("A")
E = TypeVar("E")


class Deferred(Generic[A, E]):
    def __init__(self) -> None:
        self._future: asyncio.Future[Exit[A, E]] | None = None

    def _get_future(self) -> asyncio.Future[Exit[A, E]]:
        if self._future is None:
            self._future = asyncio.get_running_loop().create_future()
        return self._future

    def await_(self) -> Effect[A, E, Never]:
        def register(resume):
            fut = self._get_future()

            def callback(f):
                if not f.cancelled():
                    exit_val = f.result()
                    if isinstance(exit_val, Success):
                        resume(succeed(exit_val.value))
                    else:
                        resume(fail_cause(exit_val.cause))

            fut.add_done_callback(callback)

        return async_(register)

    def succeed(self, value: A) -> Effect[bool, Never, Never]:
        def complete() -> bool:
            fut = self._get_future()
            if fut.done():
                return False
            fut.set_result(exit_succeed(value))
            return True

        return sync(complete)

    def fail(self, error: E) -> Effect[bool, Never, Never]:
        def complete() -> bool:
            fut = self._get_future()
            if fut.done():
                return False
            fut.set_result(exit_fail(cause_fail(error)))
            return True

        return sync(complete)

    def done(self, exit_val: Exit[A, E]) -> Effect[bool, Never, Never]:
        def complete() -> bool:
            fut = self._get_future()
            if fut.done():
                return False
            fut.set_result(exit_val)
            return True

        return sync(complete)


def deferred_make() -> Effect[Deferred[Any, Any], Never, Never]:
    return sync(Deferred)
