from __future__ import annotations

import asyncio
from collections.abc import Callable, Generator, Iterator
from dataclasses import dataclass, field
from typing import Any, Generic, Never, TypeVar, cast

from effect._internal.op_codes import effect as OpCodes
from effect._internal.runtime_env import (
    current_context,
    reset_context,
    set_context,
)
from effect.cause import Cause, failure_or_cause
from effect.cause import fail as cause_fail
from effect.cause import interrupt as cause_interrupt
from effect.context import Context, ServiceNotFoundError, Tag, merge, unsafe_get
from effect.either import Left, Right
from effect.exit import Exit, Failure, Success
from effect.exit import fail as exit_fail
from effect.exit import succeed as exit_succeed
from effect.function_ import LazyArg
from effect.option import Some
from effect.pipeable import pipe_arguments

A = TypeVar("A")
E = TypeVar("E")
R = TypeVar("R")

EFFECT_TYPE_ID = "effect/Effect"


@dataclass(eq=False)
class YieldWrap:
    effect: Effect[Any, Any, Any]


class Effect(Generic[A, E, R]):
    _op: str
    effect_instruction_i0: Any = field(default=None, repr=False)
    effect_instruction_i1: Any = field(default=None, repr=False)
    effect_instruction_i2: Any = field(default=None, repr=False)
    commit: Callable[[], Effect[Any, Any, Any]] | None = field(default=None, repr=False)

    def __init__(self, op: str) -> None:
        self._op = op
        self._tag = op

    def pipe(self, *fns: Callable[[Any], Any]) -> Any:
        return pipe_arguments(self, fns)

    def __iter__(self) -> Generator[YieldWrap, Any, Any]:
        yield YieldWrap(self)


def is_effect(value: object) -> bool:
    return isinstance(value, Effect)


def succeed(value: A) -> Effect[A, Never, Never]:
    effect = Effect[A, Never, Never](OpCodes.OP_SUCCESS)
    effect.effect_instruction_i0 = value
    return effect


def fail(error: E) -> Effect[Never, E, Never]:
    return fail_cause(cause_fail(error))


def fail_cause(cause: Cause[E]) -> Effect[Never, E, Never]:
    effect = Effect[Never, E, Never](OpCodes.OP_FAILURE)
    effect.effect_instruction_i0 = cause
    return effect


def die(defect: object) -> Effect[Never, Never, Never]:
    from effect.cause import die as cause_die

    return fail_cause(cause_die(defect))


def sync(thunk: LazyArg[A]) -> Effect[A, Never, Never]:
    effect = Effect[A, Never, Never](OpCodes.OP_SYNC)
    effect.effect_instruction_i0 = thunk
    return effect


def suspend(evaluate: LazyArg[Effect[A, E, R]]) -> Effect[A, E, R]:
    effect = Effect[A, E, R](OpCodes.OP_COMMIT)

    def commit() -> Effect[A, E, R]:
        return evaluate()

    effect.commit = commit
    return effect


def flat_map(
    self: Effect[A, E, R],
    f: Callable[[A], Effect[Any, Any, Any]],
) -> Effect[Any, Any, Any]:
    effect = Effect(OpCodes.OP_ON_SUCCESS)
    effect.effect_instruction_i0 = self
    effect.effect_instruction_i1 = f
    return effect


def map_(
    self: Effect[A, E, R],
    f: Callable[[A], Any],
) -> Effect[Any, E, R]:
    return flat_map(self, lambda value: sync(lambda: f(value)))


def catch_all_cause(
    self: Effect[A, E, R],
    f: Callable[[Cause[E]], Effect[Any, Any, Any]],
) -> Effect[Any, Any, Any]:
    effect = Effect(OpCodes.OP_ON_FAILURE)
    effect.effect_instruction_i0 = self
    effect.effect_instruction_i1 = f
    return effect


def catch_all(
    self: Effect[A, E, R],
    f: Callable[[E], Effect[Any, Any, Any]],
) -> Effect[Any, Any, Any]:
    from effect.cause import failure_option

    def on_cause(cause: Cause[E]) -> Effect[Any, Any, Any]:
        option = failure_option(cause)
        if isinstance(option, Some):
            return f(option.value)
        return fail_cause(cause)

    return catch_all_cause(self, on_cause)


def catch_if(
    self: Effect[A, E, R],
    predicate: Callable[[E], bool],
    f: Callable[[E], Effect[Any, Any, Any]],
) -> Effect[Any, Any, Any]:
    def on_cause(cause: Cause[E]) -> Effect[Any, Any, Any]:
        either = failure_or_cause(cause)
        if isinstance(either, Left):
            if predicate(either.left):
                return f(either.left)
            return fail_cause(cause)
        if isinstance(either, Right):
            return fail_cause(either.right)
        raise AssertionError("unreachable")

    return catch_all_cause(self, on_cause)


def catch_tag(
    self: Effect[A, E, R],
    tag: str,
    f: Callable[[E], Effect[Any, Any, Any]],
) -> Effect[Any, Any, Any]:
    from effect.data import is_tagged

    return catch_if(self, lambda error: is_tagged(error, tag), f)


def match_effect(
    self: Effect[A, E, R],
    *,
    on_failure: Callable[[E], Effect[Any, Any, Any]],
    on_success: Callable[[A], Effect[Any, Any, Any]],
) -> Effect[Any, Any, Any]:
    from effect.cause import failure_option

    def on_cause(cause: Cause[E]) -> Effect[Any, Any, Any]:
        option = failure_option(cause)
        if isinstance(option, Some):
            return on_failure(option.value)
        return fail_cause(cause)

    effect = Effect(OpCodes.OP_ON_SUCCESS_AND_FAILURE)
    effect.effect_instruction_i0 = self
    effect.effect_instruction_i1 = on_cause
    effect.effect_instruction_i2 = on_success
    return effect


def tap(
    self: Effect[A, E, R],
    f: Callable[[A], Effect[Any, Any, Any]],
) -> Effect[A, E | Any, R | Any]:
    return flat_map(self, lambda value: flat_map(f(value), lambda _: succeed(value)))


def on_exit(
    self: Effect[A, E, R],
    cleanup: Callable[[Exit[A, E]], Effect[Any, Any, Any]],
) -> Effect[A, E | Any, R | Any]:
    effect = Effect(OpCodes.OP_ON_EXIT)
    effect.effect_instruction_i0 = self
    effect.effect_instruction_i1 = cleanup
    return effect


def from_iterator(iterator: Iterator[YieldWrap | Effect[Any, Any, Any]]) -> Effect[Any, Any, Any]:
    effect = Effect(OpCodes.OP_ITERATOR)
    effect.effect_instruction_i0 = iterator
    return effect


GeneratorEffect = Generator[YieldWrap | Effect[Any, Any, Any], Any, Any]


def gen(
    f: Callable[..., GeneratorEffect],
) -> Callable[..., Effect[Any, Any, Any]]:
    def wrapper(*args: Any, **kwargs: Any) -> Effect[Any, Any, Any]:
        return suspend(lambda: from_iterator(f(*args, **kwargs)))

    return wrapper


def tag_effect(tag: Tag[Any, Any]) -> Effect[Any, ServiceNotFoundError, Tag[Any, Any]]:
    effect = Effect(OpCodes.OP_TAG)
    effect.effect_instruction_i0 = tag
    return effect


def context_effect() -> Effect[Context[Any], Never, Never]:
    return sync(current_context)


def provide_context(
    self: Effect[A, E, R],
    context: Context[R],
) -> Effect[A, E, Never]:
    effect = Effect[A, E, Never](OpCodes.OP_WITH_CONTEXT)
    effect.effect_instruction_i0 = self
    effect.effect_instruction_i1 = context
    return effect


def provide_some_context(
    self: Effect[A, E, R],
    context: Context[Any],
) -> Effect[A, E, Never]:
    effect = Effect[A, E, Never](OpCodes.OP_WITH_SOME_CONTEXT)
    effect.effect_instruction_i0 = self
    effect.effect_instruction_i1 = context
    return effect


def provide_service(
    self: Effect[A, E, R],
    tag: Tag[Any, Any],
    service: object,
) -> Effect[A, E, Never]:
    from effect.context import add, empty

    return provide_some_context(self, add(empty(), tag, service))


Resume = Callable[[Effect[Any, Any, Any]], None]


def async_(
    register: Callable[[Resume], None],
) -> Effect[A, E, Never]:
    effect = Effect[A, E, Never](OpCodes.OP_ASYNC)
    effect.effect_instruction_i0 = register
    return effect


class AsyncFiberException(Exception):
    def __init__(self) -> None:
        super().__init__(
            "Fiber cannot be resolved synchronously. "
            "This is caused by using run_sync on an effect that performs async work"
        )


def run_sync_exit(effect: Effect[A, E, R]) -> Exit[A, E]:
    return _run_exit(effect, allow_async=False)


async def run_async_exit(effect: Effect[A, E, R]) -> Exit[A, E]:
    return await _run_exit_async(effect)


def _run_exit(effect: Effect[A, E, R], *, allow_async: bool) -> Exit[A, E]:
    current: Effect[Any, Any, Any] | Exit[Any, Any] = effect

    while True:
        if isinstance(current, (Success, Failure)):
            return current

        op = current._op

        if op == OpCodes.OP_SUCCESS:
            return exit_succeed(current.effect_instruction_i0)

        if op == OpCodes.OP_FAILURE:
            return exit_fail(current.effect_instruction_i0)

        if op == OpCodes.OP_SYNC:
            current = succeed(current.effect_instruction_i0())
            continue

        if op == OpCodes.OP_COMMIT:
            if current.commit is None:
                msg = "Commit effect missing commit callback"
                raise RuntimeError(msg)
            current = current.commit()
            continue

        if op == OpCodes.OP_ON_SUCCESS:
            inner_exit = _run_exit(current.effect_instruction_i0, allow_async=allow_async)
            if isinstance(inner_exit, Failure):
                return inner_exit
            current = current.effect_instruction_i1(inner_exit.value)
            continue

        if op == OpCodes.OP_ON_FAILURE:
            inner_exit = _run_exit(current.effect_instruction_i0, allow_async=allow_async)
            if isinstance(inner_exit, Success):
                return inner_exit
            current = current.effect_instruction_i1(inner_exit.cause)
            continue

        if op == OpCodes.OP_ON_SUCCESS_AND_FAILURE:
            inner_exit = _run_exit(current.effect_instruction_i0, allow_async=allow_async)
            if isinstance(inner_exit, Failure):
                current = current.effect_instruction_i1(inner_exit.cause)
            else:
                current = current.effect_instruction_i2(inner_exit.value)
            continue

        if op == OpCodes.OP_ITERATOR:
            return _run_iterator(current.effect_instruction_i0, allow_async=allow_async)

        if op == OpCodes.OP_TAG:
            try:
                service = unsafe_get(current_context(), current.effect_instruction_i0)
            except ServiceNotFoundError as error:
                return cast(Exit[A, E], exit_fail(cause_fail(error)))
            current = succeed(service)
            continue

        if op == OpCodes.OP_WITH_CONTEXT:
            token = set_context(current.effect_instruction_i1)
            try:
                return _run_exit(current.effect_instruction_i0, allow_async=allow_async)
            finally:
                reset_context(token)

        if op == OpCodes.OP_WITH_SOME_CONTEXT:
            merged = merge(current_context(), current.effect_instruction_i1)
            token = set_context(merged)
            try:
                return _run_exit(current.effect_instruction_i0, allow_async=allow_async)
            finally:
                reset_context(token)

        if op == OpCodes.OP_ON_EXIT:
            inner_exit = _run_exit(current.effect_instruction_i0, allow_async=allow_async)
            cleanup_exit = _run_exit(
                current.effect_instruction_i1(inner_exit),
                allow_async=allow_async,
            )
            if isinstance(cleanup_exit, Failure):
                return cleanup_exit
            return inner_exit

        if op == OpCodes.OP_ASYNC:
            if allow_async:
                msg = "Async op encountered in sync runner with allow_async=True"
                raise RuntimeError(msg)
            raise AsyncFiberException()

        msg = f"Unsupported sync op: {op}"
        raise RuntimeError(msg)


async def _run_exit_async(
    effect: Effect[A, E, R],
    fiber: Any | None = None,
) -> Exit[A, E]:
    current: Effect[Any, Any, Any] | Exit[Any, Any] = effect

    while True:
        if isinstance(current, (Success, Failure)):
            return current

        op = current._op

        if op == OpCodes.OP_SUCCESS:
            return exit_succeed(current.effect_instruction_i0)

        if op == OpCodes.OP_FAILURE:
            return exit_fail(current.effect_instruction_i0)

        if op == OpCodes.OP_SYNC:
            current = succeed(current.effect_instruction_i0())
            continue

        if op == OpCodes.OP_COMMIT:
            if current.commit is None:
                msg = "Commit effect missing commit callback"
                raise RuntimeError(msg)
            current = current.commit()
            continue

        if op == OpCodes.OP_ON_SUCCESS:
            inner_exit = await _run_exit_async(current.effect_instruction_i0, fiber=fiber)
            if isinstance(inner_exit, Failure):
                return inner_exit
            current = current.effect_instruction_i1(inner_exit.value)
            continue

        if op == OpCodes.OP_ON_FAILURE:
            inner_exit = await _run_exit_async(current.effect_instruction_i0, fiber=fiber)
            if isinstance(inner_exit, Success):
                return inner_exit
            current = current.effect_instruction_i1(inner_exit.cause)
            continue

        if op == OpCodes.OP_ON_SUCCESS_AND_FAILURE:
            inner_exit = await _run_exit_async(current.effect_instruction_i0, fiber=fiber)
            if isinstance(inner_exit, Failure):
                current = current.effect_instruction_i1(inner_exit.cause)
            else:
                current = current.effect_instruction_i2(inner_exit.value)
            continue

        if op == OpCodes.OP_ITERATOR:
            return await _run_iterator_async(current.effect_instruction_i0, fiber=fiber)

        if op == OpCodes.OP_TAG:
            try:
                service = unsafe_get(current_context(), current.effect_instruction_i0)
            except ServiceNotFoundError as error:
                return cast(Exit[A, E], exit_fail(cause_fail(error)))
            current = succeed(service)
            continue

        if op == OpCodes.OP_WITH_CONTEXT:
            token = set_context(current.effect_instruction_i1)
            try:
                return await _run_exit_async(current.effect_instruction_i0, fiber=fiber)
            finally:
                reset_context(token)

        if op == OpCodes.OP_WITH_SOME_CONTEXT:
            merged = merge(current_context(), current.effect_instruction_i1)
            token = set_context(merged)
            try:
                return await _run_exit_async(current.effect_instruction_i0, fiber=fiber)
            finally:
                reset_context(token)

        if op == OpCodes.OP_ON_EXIT:
            inner_exit = await _run_exit_async(current.effect_instruction_i0, fiber=fiber)
            cleanup_exit = await _run_exit_async(
                current.effect_instruction_i1(inner_exit),
                fiber=fiber,
            )
            if isinstance(cleanup_exit, Failure):
                return cleanup_exit
            return inner_exit

        if op == OpCodes.OP_ASYNC:
            if fiber and fiber._interrupted:
                current = fail_cause(cause_interrupt())
                continue

            loop = asyncio.get_running_loop()
            future: asyncio.Future[Effect[Any, Any, Any]] = loop.create_future()
            cancel_callback = None

            def resume(
                cont: Effect[Any, Any, Any],
                pending: asyncio.Future[Effect[Any, Any, Any]] = future,
            ) -> None:
                if not pending.done():
                    pending.set_result(cont)

            def on_cancel(cb: Callable[[], None]) -> None:
                nonlocal cancel_callback
                cancel_callback = cb

            cast(Any, resume).on_cancel = on_cancel

            current.effect_instruction_i0(resume)

            if fiber:
                fiber._active_future = future

            try:
                current = await future
            except asyncio.CancelledError:
                if cancel_callback:
                    import contextlib

                    with contextlib.suppress(Exception):
                        cancel_callback()
                current = fail_cause(cause_interrupt())
            finally:
                if fiber:
                    fiber._active_future = None
            continue

        msg = f"Unsupported async op: {op}"
        raise RuntimeError(msg)


def _run_iterator(
    iterator: Generator[YieldWrap | Effect[Any, Any, Any], Any, Any],
    *,
    allow_async: bool,
) -> Exit[Any, Any]:
    send_value: object = None
    while True:
        try:
            if send_value is None:
                yielded = next(iterator)
            else:
                yielded = iterator.send(send_value)
                send_value = None
        except StopIteration as stop:
            return exit_succeed(stop.value)

        child: Effect[Any, Any, Any]
        if isinstance(yielded, YieldWrap):
            child = yielded.effect
        elif isinstance(yielded, Tag):
            child = tag_effect(yielded)
        elif is_effect(yielded):
            child = yielded
        else:
            msg = f"Expected Effect from generator, got {type(yielded)!r}"
            raise TypeError(msg)

        child_exit = _run_exit(child, allow_async=allow_async)
        if isinstance(child_exit, Failure):
            return child_exit
        send_value = child_exit.value


async def _run_iterator_async(
    iterator: Generator[YieldWrap | Effect[Any, Any, Any], Any, Any],
    fiber: Any | None = None,
) -> Exit[Any, Any]:
    send_value: object = None
    while True:
        try:
            if send_value is None:
                yielded = next(iterator)
            else:
                yielded = iterator.send(send_value)
                send_value = None
        except StopIteration as stop:
            return exit_succeed(stop.value)

        child: Effect[Any, Any, Any]
        if isinstance(yielded, YieldWrap):
            child = yielded.effect
        elif isinstance(yielded, Tag):
            child = tag_effect(yielded)
        elif is_effect(yielded):
            child = yielded
        else:
            msg = f"Expected Effect from generator, got {type(yielded)!r}"
            raise TypeError(msg)

        child_exit = await _run_exit_async(child, fiber=fiber)
        if isinstance(child_exit, Failure):
            return child_exit
        send_value = child_exit.value


def run_sync(effect: Effect[A, E, R]) -> A:
    exit = run_sync_exit(effect)
    if isinstance(exit, Failure):
        from effect.cause import Fail, failure_option
        from effect.option import Some

        option = failure_option(exit.cause)
        if isinstance(option, Some):
            error = option.value
            if isinstance(error, BaseException):
                raise error
            raise RuntimeError(error)
        if isinstance(exit.cause, Fail):
            error = exit.cause.error
            if isinstance(error, BaseException):
                raise error
            raise RuntimeError(error)
        raise RuntimeError(exit.cause)
    return exit.value


async def run_async(effect: Effect[A, E, Never]) -> A:
    exit = await run_async_exit(effect)
    if isinstance(exit, Failure):
        from effect.cause import Fail, failure_option
        from effect.option import Some

        option = failure_option(exit.cause)
        if isinstance(option, Some):
            error = option.value
            if isinstance(error, BaseException):
                raise error
            raise RuntimeError(error)
        if isinstance(exit.cause, Fail):
            error = exit.cause.error
            if isinstance(error, BaseException):
                raise error
            raise RuntimeError(error)
        raise RuntimeError(exit.cause)
    return exit.value
