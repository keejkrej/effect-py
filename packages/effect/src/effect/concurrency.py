from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Never, TypeVar, cast

from effect._internal import core as internal
from effect._internal.core import Effect, async_, fail_cause, gen, succeed
from effect.data import TaggedError
from effect.exit import Exit, Failure, Success
from effect.fiber import Fiber

A = TypeVar("A")
B = TypeVar("B")
E = TypeVar("E")
E2 = TypeVar("E2")
R = TypeVar("R")
R2 = TypeVar("R2")


def _all_sequential_list(effects: list[Effect[Any, Any, Any]]) -> Effect[list[Any], Any, Any]:
    @gen
    def run():
        results = []
        for eff in effects:
            res = yield eff
            results.append(res)
        return results

    return run()


def _all_sequential_dict(
    effects: dict[Any, Effect[Any, Any, Any]],
) -> Effect[dict[Any, Any], Any, Any]:
    @gen
    def run():
        results = {}
        for k, eff in effects.items():
            results[k] = yield eff
        return results

    return run()


def _all_parallel_list(effects: list[Effect[Any, Any, Any]]) -> Effect[list[Any], Any, Any]:
    def register(resume):
        fibers = [Fiber(eff) for eff in effects]
        for fib in fibers:
            fib.start()

        async def monitor():
            tasks = [fib._task for fib in fibers if fib._task is not None]
            pending = set(tasks)
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                any_failed = False
                failed_cause = None
                for t in done:
                    exit_val = t.result()
                    if isinstance(exit_val, Failure):
                        any_failed = True
                        failed_cause = exit_val.cause
                        break

                if any_failed:
                    for fib in fibers:
                        fib._interrupted = True
                        if fib._active_future and not fib._active_future.done():
                            fib._active_future.cancel()

                    await asyncio.gather(*tasks, return_exceptions=True)
                    if failed_cause is not None:
                        resume(fail_cause(failed_cause))
                    else:
                        from effect.cause import empty as cause_empty

                        resume(fail_cause(cause_empty()))
                    return

            results = []
            for t in tasks:
                exit_val = t.result()
                if isinstance(exit_val, Success):
                    results.append(exit_val.value)
                else:
                    raise RuntimeError("Unexpected failure exit in successful concurrency run")
            resume(succeed(results))

        monitor_task = asyncio.create_task(monitor())

        if hasattr(resume, "on_cancel"):

            def cancel_all():
                monitor_task.cancel()
                for fib in fibers:
                    fib._interrupted = True
                    if fib._active_future and not fib._active_future.done():
                        fib._active_future.cancel()

            resume.on_cancel(cancel_all)

    return async_(register)


def all(
    effects: Any,
    *,
    concurrency: int | bool | None = None,
) -> Effect[Any, Any, Any]:
    if isinstance(effects, dict):
        keys = list(effects.keys())
        values = [cast(Effect[Any, Any, Any], v) for v in effects.values()]
        if concurrency is True or (isinstance(concurrency, int) and concurrency > 1):
            return internal.flat_map(
                _all_parallel_list(values),
                lambda results: succeed({keys[i]: results[i] for i in range(len(keys))}),
            )
        else:
            return _all_sequential_dict(effects)
    else:
        effect_list = [cast(Effect[Any, Any, Any], v) for v in effects]
        if concurrency is True or (isinstance(concurrency, int) and concurrency > 1):
            return _all_parallel_list(effect_list)
        else:
            return _all_sequential_list(effect_list)


def zip(left: Effect[A, E, R], right: Effect[B, E2, R2]) -> Effect[tuple[A, B], E | E2, R | R2]:
    @gen
    def run():
        l_val = yield left
        r_val = yield right
        return l_val, r_val

    return run()


def zip_par(left: Effect[A, E, R], right: Effect[B, E2, R2]) -> Effect[tuple[A, B], E | E2, R | R2]:
    return internal.flat_map(
        all([left, right], concurrency=True), lambda results: succeed(tuple(results))
    )


@dataclass(eq=False, kw_only=True)
class TimeoutException(TaggedError):
    _tag = "TimeoutException"
    message: str = "The operation timed out"


def sleep(seconds: float) -> Effect[None, Never, Never]:
    def sleep_register(resume):
        loop_event = asyncio.get_running_loop()
        task = loop_event.call_later(seconds, lambda: resume(succeed(None)))
        if hasattr(resume, "on_cancel"):
            resume.on_cancel(lambda: task.cancel())

    return async_(sleep_register)


def _from_exit(exit_val: Exit[Any, Any]) -> Effect[Any, Any, Any]:
    if isinstance(exit_val, Success):
        return succeed(exit_val.value)
    else:
        return fail_cause(exit_val.cause)


def race_first(
    left: Effect[A, E, R],
    right: Effect[B, E2, R2],
) -> Effect[A | B, E | E2, R | R2]:
    from effect.deferred import deferred_make
    from effect.fiber import fork

    @gen
    def run():
        fiber1 = yield fork(left)
        fiber2 = yield fork(right)

        deferred = yield deferred_make()
        winner_determined = False

        @gen
        def handle_completion(winner: Fiber[Any, Any], loser: Fiber[Any, Any]):
            nonlocal winner_determined
            if winner_determined:
                return
            winner_determined = True
            yield fork(loser.interrupt())
            winner_exit = yield winner.await_exit()
            yield deferred.done(winner_exit)

        @gen
        def monitor_fiber1():
            yield fiber1.await_exit()
            yield handle_completion(fiber1, fiber2)

        @gen
        def monitor_fiber2():
            yield fiber2.await_exit()
            yield handle_completion(fiber2, fiber1)

        yield fork(monitor_fiber1())
        yield fork(monitor_fiber2())

        res = yield deferred.await_()
        return res

    return run()


def race(
    left: Effect[A, E, R],
    right: Effect[B, E2, R2],
) -> Effect[A | B, E | E2, R | R2]:
    from effect.deferred import deferred_make
    from effect.fiber import fork

    @gen
    def run():
        fiber1 = yield fork(left)
        fiber2 = yield fork(right)

        deferred = yield deferred_make()
        f1_exit: Exit[Any, Any] | None = None
        f2_exit: Exit[Any, Any] | None = None
        winner_determined = False

        @gen
        def handle_f1():
            nonlocal f1_exit, winner_determined
            exit_val = yield fiber1.await_exit()
            f1_exit = exit_val
            if isinstance(exit_val, Success):
                if not winner_determined:
                    winner_determined = True
                    yield fork(fiber2.interrupt())
                    yield deferred.done(exit_val)
            else:
                if f2_exit is not None and not winner_determined:
                    winner_determined = True
                    yield deferred.done(exit_val)

        @gen
        def handle_f2():
            nonlocal f2_exit, winner_determined
            exit_val = yield fiber2.await_exit()
            f2_exit = exit_val
            if isinstance(exit_val, Success):
                if not winner_determined:
                    winner_determined = True
                    yield fork(fiber1.interrupt())
                    yield deferred.done(exit_val)
            else:
                if f1_exit is not None and not winner_determined:
                    winner_determined = True
                    yield deferred.done(exit_val)

        yield fork(handle_f1())
        yield fork(handle_f2())

        res = yield deferred.await_()
        return res

    return run()


def timeout(
    self: Effect[A, E, R],
    seconds: float,
) -> Effect[A, E | TimeoutException, R]:
    @gen
    def run():
        @gen
        def timer_effect():
            yield sleep(seconds)
            return (yield internal.fail(TimeoutException()))

        res = yield race_first(self, timer_effect())
        return res

    return run()
