from __future__ import annotations

import numpy as np

import effect as Effect
from effect import run_sync
from effect_numpy import array, matmul, randn, sum_all


def test_basic_array() -> None:
    arr = run_sync(array([1, 2, 3]))
    assert isinstance(arr, np.ndarray)
    assert np.array_equal(arr, np.array([1, 2, 3]))


def test_randn() -> None:
    arr = run_sync(randn((2, 3), seed=42))
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (2, 3)


def test_matmul_success() -> None:
    left = np.ones((2, 3))
    right = np.ones((3, 4))
    res = run_sync(matmul(left, right))
    assert res.shape == (2, 4)
    assert np.all(res == 3.0)


def test_matmul_shape_error() -> None:
    left = np.ones((2, 3))
    right = np.ones((4, 5))
    exit_val = run_sync(
        Effect.pipe(
            matmul(left, right),
            Effect.catch_tag("ShapeError", lambda err: Effect.succeed(str(err.message))),
        )
    )
    assert "Incompatible shapes" in exit_val


def test_sum_all() -> None:
    arr = np.array([[1, 2], [3, 4]])
    total = run_sync(sum_all(arr))
    assert total == 10
