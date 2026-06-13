from __future__ import annotations

from collections.abc import Callable
from typing import Any, Never, TypeVar, cast

import numpy as np

from effect._internal.core import Effect, fail, succeed, suspend
from effect.data import TaggedError
from effect_numpy.errors import ArrayError, ShapeError

A = TypeVar("A")


def _map_numpy_exception(error: Exception) -> TaggedError:
    message = str(error)
    lowered = message.lower()
    if isinstance(error, ValueError) and (
        "shape" in lowered or "size" in lowered or "dimension" in lowered or "matmul" in lowered
    ):
        return ShapeError(message=message)
    return ArrayError(message=message)


def from_numpy(thunk: Callable[[], A]) -> Effect[A, TaggedError, Never]:
    def attempt() -> Effect[A, TaggedError, Never]:
        try:
            return cast(Effect[A, TaggedError, Never], succeed(thunk()))
        except Exception as error:
            return cast(Effect[A, TaggedError, Never], fail(_map_numpy_exception(error)))

    return suspend(attempt)


def array(object: Any, dtype: Any = None) -> Effect[np.ndarray, TaggedError, Never]:
    return from_numpy(lambda: np.array(object, dtype=dtype))


def randn(
    shape: tuple[int, ...],
    seed: int | None = None,
) -> Effect[np.ndarray, TaggedError, Never]:
    def create():
        rng = np.random.default_rng(seed)
        return rng.standard_normal(size=shape)

    return from_numpy(create)


def matmul(left: Any, right: Any) -> Effect[np.ndarray, TaggedError, Never]:
    try:
        left_shape = left.shape
        right_shape = right.shape
        if len(left_shape) >= 2 and len(right_shape) >= 2 and left_shape[-1] != right_shape[-2]:
            return cast(
                Effect[np.ndarray, TaggedError, Never],
                fail(
                    ShapeError(
                        message=f"Incompatible shapes for matmul: {left_shape} x {right_shape}",
                        expected=(left_shape[-1],),
                        actual=(right_shape[-2],),
                    )
                ),
            )
    except AttributeError:
        pass

    return from_numpy(lambda: np.matmul(left, right))


def sum_all(a: Any) -> Effect[Any, TaggedError, Never]:
    return from_numpy(lambda: np.sum(a))
