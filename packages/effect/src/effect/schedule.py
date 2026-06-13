from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from typing import Any, Generic, Never, TypeVar

from effect._internal import core as internal
from effect._internal.core import Effect, async_, fail, succeed
from effect.option import Option, Some, none, some

State = TypeVar("State")
In = TypeVar("In")
Out = TypeVar("Out")
A = TypeVar("A")
E = TypeVar("E")
R = TypeVar("R")


class Schedule(Generic[State, In, Out]):
    def __init__(
        self,
        initial: State,
        step: Callable[[State, In], Effect[Option[tuple[State, Out, float]], Never, Never]],
    ) -> None:
        self.initial = initial
        self.step = step

    def add_jitter(self) -> Schedule[State, In, Out]:
        def new_step(
            state: State, _in: In
        ) -> Effect[Option[tuple[State, Out, float]], Never, Never]:
            def adjust(opt: Option[tuple[State, Out, float]]) -> Option[tuple[State, Out, float]]:
                if isinstance(opt, Some):
                    next_state, out, delay = opt.value
                    jitter = delay * random.random()
                    return some((next_state, out, delay + jitter))
                return none()

            return internal.map_(self.step(state, _in), adjust)

        return Schedule(self.initial, new_step)


def spaced(seconds: float) -> Schedule[int, Any, int]:
    def step(state: int, _in: Any) -> Effect[Option[tuple[int, int, float]], Never, Never]:
        return succeed(some((state + 1, state, seconds)))

    return Schedule(0, step)


def recurs(n: int) -> Schedule[int, Any, int]:
    def step(state: int, _in: Any) -> Effect[Option[tuple[int, int, float]], Never, Never]:
        if state >= n:
            return succeed(none())
        return succeed(some((state + 1, state, 0.0)))

    return Schedule(0, step)


def exponential(base: float, factor: float = 2.0) -> Schedule[int, Any, float]:
    def step(state: int, _in: Any) -> Effect[Option[tuple[int, float, float]], Never, Never]:
        delay = base * (factor**state)
        return succeed(some((state + 1, delay, delay)))

    return Schedule(0, step)


def retry(effect: Effect[A, E, R], schedule: Schedule[State, E, Out]) -> Effect[A, E, R]:
    def loop(state: State) -> Effect[Any, Any, Any]:
        def on_failure(err: E) -> Effect[Any, Any, Any]:
            def handle_step(decision: Option[tuple[State, Out, float]]) -> Effect[Any, Any, Any]:
                if isinstance(decision, Some):
                    next_state, _, delay = decision.value
                    if delay > 0:

                        def sleep_register(resume):
                            loop_event = asyncio.get_running_loop()
                            task = loop_event.call_later(delay, lambda: resume(succeed(None)))
                            if hasattr(resume, "on_cancel"):
                                resume.on_cancel(lambda: task.cancel())

                        return internal.flat_map(async_(sleep_register), lambda _: loop(next_state))
                    else:
                        return loop(next_state)
                else:
                    return fail(err)

            return internal.flat_map(schedule.step(state, err), handle_step)

        return internal.match_effect(effect, on_failure=on_failure, on_success=succeed)

    return loop(schedule.initial)


def repeat(effect: Effect[A, E, R], schedule: Schedule[State, A, Out]) -> Effect[Any, E, R]:
    def loop(state: State, last_out: Out | None) -> Effect[Any, Any, Any]:
        def on_success(a: A) -> Effect[Any, Any, Any]:
            def handle_step(decision: Option[tuple[State, Out, float]]) -> Effect[Any, Any, Any]:
                if isinstance(decision, Some):
                    next_state, out, delay = decision.value
                    if delay > 0:

                        def sleep_register(resume):
                            loop_event = asyncio.get_running_loop()
                            task = loop_event.call_later(delay, lambda: resume(succeed(None)))
                            if hasattr(resume, "on_cancel"):
                                resume.on_cancel(lambda: task.cancel())

                        return internal.flat_map(
                            async_(sleep_register), lambda _: loop(next_state, out)
                        )
                    else:
                        return loop(next_state, out)
                else:
                    if last_out is not None:
                        return succeed(last_out)
                    return succeed(a)

            return internal.flat_map(schedule.step(state, a), handle_step)

        return internal.match_effect(effect, on_failure=fail, on_success=on_success)

    return loop(schedule.initial, None)
