from __future__ import annotations

import pytest

import effect as Effect
from effect import pipe, run_sync
from effect.layer import merge as merge_layers
from effect.layer import provide_to
from effect_pytorch.device import Device
from effect_pytorch.device import live as live_device
from effect_pytorch.errors import ShapeError
from effect_pytorch.pipeline import MatmulPipelineInput, matmul, matmul_pipeline
from effect_pytorch.rng import Rng
from effect_pytorch.rng import live as live_rng

torch = pytest.importorskip("torch")


class TestTorchErrors:
    def test_tagged_errors(self) -> None:
        err = ShapeError(message="bad", expected=(2, 3), actual=(3, 2))
        assert err._tag == "ShapeError"
        assert "bad" in str(err)


class TestTorchServices:
    def test_device_and_rng_layers(self) -> None:
        @Effect.gen
        def program():
            device = yield Device
            rng = yield Rng
            return device.device, rng.seed

        layer = merge_layers(live_device("cpu"), live_rng(42))
        assert run_sync(provide_to(program(), layer)) == ("cpu", 42)


class TestMatmulPipeline:
    def test_vertical_slice(self) -> None:
        spec = MatmulPipelineInput(left_shape=(2, 3), right_shape=(3, 4))
        layer = merge_layers(live_device("cpu"), live_rng(7))
        program = pipe(matmul_pipeline(spec), Effect.provide(layer))
        result = run_sync(program)
        assert isinstance(result, float)

    def test_shape_error_without_torch_compute(self) -> None:
        left = torch.ones(2, 3)
        right = torch.ones(4, 5)

        result = run_sync(
            pipe(
                matmul(left, right),
                Effect.catch_tag("ShapeError", lambda err: Effect.succeed(str(err.message))),
            )
        )
        assert "Incompatible shapes" in result

    def test_reproducible_with_seed(self) -> None:
        spec = MatmulPipelineInput(left_shape=(4,), right_shape=(4, 1))
        layer = merge_layers(live_device("cpu"), live_rng(99))

        first = run_sync(pipe(matmul_pipeline(spec), Effect.provide(layer)))
        second = run_sync(pipe(matmul_pipeline(spec), Effect.provide(layer)))
        assert first == second
