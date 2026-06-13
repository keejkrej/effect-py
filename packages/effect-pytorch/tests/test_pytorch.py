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
nn = pytest.importorskip("torch.nn")


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


# ──────────────────────────────────────────────────────────
# Training pipeline tests (using synthetic data)
# ──────────────────────────────────────────────────────────

from effect_pytorch.model import MNISTMLP
from effect_pytorch.optimizer import adam, sgd
from effect_pytorch.optimizer import step as optim_step
from effect_pytorch.optimizer import zero_grad
from effect_pytorch.train import evaluate, train_step


class TestOptimizer:
    def test_sgd_builds(self) -> None:
        model = MNISTMLP()
        opt = run_sync(sgd(model, lr=0.01, momentum=0.9))
        assert opt is not None
        assert hasattr(opt, "step")

    def test_adam_builds(self) -> None:
        model = MNISTMLP()
        opt = run_sync(adam(model, lr=0.001))
        assert opt is not None
        assert hasattr(opt, "step")

    def test_zero_grad_and_step(self) -> None:
        model = MNISTMLP()
        opt = run_sync(sgd(model, lr=0.01))
        run_sync(zero_grad(opt))
        # step with no grad is a no-op but should not raise
        run_sync(optim_step(opt))


class TestTrainStep:
    def _make_synthetic_batch(self, batch_size: int = 16):
        """Create a synthetic batch of MNIST-like data."""
        data = torch.randn(batch_size, 1, 28, 28)
        target = torch.randint(0, 10, (batch_size,))
        return data, target

    def test_single_train_step(self) -> None:
        model = MNISTMLP()
        opt = run_sync(sgd(model, lr=0.01, momentum=0.9))
        data, target = self._make_synthetic_batch()

        loss = run_sync(train_step(model, opt, data, target))
        assert isinstance(loss, float)
        assert loss > 0  # NLL loss on random data should be > 0

    def test_loss_decreases_over_steps(self) -> None:
        model = MNISTMLP()
        opt = run_sync(sgd(model, lr=0.01, momentum=0.9))
        data, target = self._make_synthetic_batch(batch_size=64)

        # Train on the same batch multiple times — loss should decrease
        losses = []
        for _ in range(20):
            loss = run_sync(train_step(model, opt, data, target))
            losses.append(loss)

        assert losses[-1] < losses[0], f"Loss did not decrease: {losses[0]:.4f} → {losses[-1]:.4f}"


class TestEvaluate:
    def test_evaluate_synthetic(self) -> None:
        model = MNISTMLP()
        # Create a synthetic test loader
        data = torch.randn(32, 1, 28, 28)
        target = torch.randint(0, 10, (32,))
        dataset = torch.utils.data.TensorDataset(data, target)
        loader = torch.utils.data.DataLoader(dataset, batch_size=16)

        test_loss, accuracy = run_sync(evaluate(model, loader))
        assert isinstance(test_loss, float)
        assert isinstance(accuracy, float)
        assert 0 <= accuracy <= 100


class TestModel:
    def test_mnist_mlp_forward(self) -> None:
        model = MNISTMLP()
        x = torch.randn(4, 1, 28, 28)
        out = model(x)
        assert out.shape == (4, 10)

    def test_mnist_mlp_log_softmax(self) -> None:
        model = MNISTMLP()
        x = torch.randn(2, 1, 28, 28)
        out = model(x)
        # log_softmax outputs should be <= 0
        assert (out <= 0).all()
        # exp(log_softmax) should sum to ~1
        probs = out.exp().sum(dim=1)
        assert torch.allclose(probs, torch.ones(2), atol=1e-5)
