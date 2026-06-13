from __future__ import annotations

import asyncio
from typing import Any, Generic, Never, TypeVar

from effect._internal import core as internal
from effect._internal.core import Effect, async_, fail_cause, succeed
from effect.cause import die as cause_die
from effect.exit import Exit, Success
from effect.exit import fail as exit_fail

A = TypeVar("A")
E = TypeVar("E")


class Fiber(Generic[A, E]):
    def __init__(self, effect: Effect[A, E, Any]) -> None:
        self._effect = effect
        self._interrupted = False
        self._active_future: asyncio.Future[Any] | None = None
        self._task: asyncio.Task[Exit[A, E]] | None = None
        self._exit: Exit[A, E] | None = None
        self._join_futures: list[asyncio.Future[Exit[A, E]]] = []

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def _run(self) -> Exit[A, E]:
        try:
            exit_val = await internal._run_exit_async(self._effect, fiber=self)
            self._exit = exit_val
            return exit_val
        except Exception as e:
            exit_val = exit_fail(cause_die(e))
            self._exit = exit_val
            return exit_val
        finally:
            for fut in self._join_futures:
                if not fut.done():
                    fut.set_result(self._exit)
            self._join_futures.clear()

    def join(self) -> Effect[A, E, Never]:
        def register(resume):
            if self._exit is not None:
                if isinstance(self._exit, Success):
                    resume(succeed(self._exit.value))
                else:
                    resume(fail_cause(self._exit.cause))
            else:
                fut = asyncio.get_running_loop().create_future()
                self._join_futures.append(fut)

                def callback(f):
                    exit_val = f.result()
                    if isinstance(exit_val, Success):
                        resume(succeed(exit_val.value))
                    else:
                        resume(fail_cause(exit_val.cause))

                fut.add_done_callback(callback)

        return async_(register)

    def await_exit(self) -> Effect[Exit[A, E], Never, Never]:
        def register(resume):
            if self._exit is not None:
                resume(succeed(self._exit))
            else:
                fut = asyncio.get_running_loop().create_future()
                self._join_futures.append(fut)
                fut.add_done_callback(lambda f: resume(succeed(f.result())))

        return async_(register)

    def interrupt(self) -> Effect[Exit[A, E], Never, Never]:
        def register(resume):
            self._interrupted = True
            if self._active_future and not self._active_future.done():
                self._active_future.cancel()

            if self._exit is not None:
                resume(succeed(self._exit))
            else:
                fut = asyncio.get_running_loop().create_future()
                self._join_futures.append(fut)
                fut.add_done_callback(lambda f: resume(succeed(f.result())))

        return async_(register)


def fork(effect: Effect[A, E, Any]) -> Effect[Fiber[A, E], Never, Never]:
    def register(resume):
        fiber = Fiber(effect)
        fiber.start()
        resume(succeed(fiber))

    return async_(register)
