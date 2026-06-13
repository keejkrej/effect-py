from __future__ import annotations

import asyncio
from typing import Any, TypeVar, cast

from effect._internal import core as internal
from effect._internal.core import Effect, async_, fail_cause, gen, succeed
from effect.exit import Failure, Success
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
