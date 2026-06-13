#!/usr/bin/env python3
"""Train MNIST using the effect-pytorch framework.

This demonstrates the full Effect pipeline:
1. Load MNIST data  → ``effect_pytorch.dataset.mnist``
2. Build a model    → ``effect_pytorch.model.MNISTMLP``
3. Build optimizer  → ``effect_pytorch.optimizer.sgd``
4. Train loop       → ``effect_pytorch.train.train_model``

All PyTorch operations are wrapped in Effects, giving composable
error handling and injectable services (device, rng, logger).

Usage::

    uv run python examples/train_mnist.py
"""

from __future__ import annotations

import effect as Effect
from effect.effect import gen, run_sync
from effect_pytorch.dataset import mnist
from effect_pytorch.model import MNISTMLP
from effect_pytorch.optimizer import sgd
from effect_pytorch.train import train_model


@gen
def program():
    # 1. Load MNIST
    yield Effect.log_info("Loading MNIST dataset...")
    loaders = yield mnist(data_dir="./data", batch_size=64)

    # 2. Create model
    model = MNISTMLP()
    yield Effect.log_info(f"Model: {model.__class__.__name__}")

    # 3. Create optimizer
    optimizer = yield sgd(model, lr=0.01, momentum=0.9)
    yield Effect.log_info("Optimizer: SGD(lr=0.01, momentum=0.9)")

    # 4. Train
    test_loss, accuracy = yield train_model(
        model, optimizer, loaders, epochs=3, log_interval=200
    )

    yield Effect.log_info(f"Final — test_loss={test_loss:.4f}, accuracy={accuracy:.2f}%")
    return accuracy


def main() -> None:
    result = run_sync(program())
    print(f"\n✅ MNIST training complete! Final accuracy: {result:.2f}%")


if __name__ == "__main__":
    main()
