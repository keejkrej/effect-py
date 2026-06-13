"""Effectful training loop primitives."""

from __future__ import annotations

from typing import Any, Never

import torch
import torch.nn as nn
import torch.nn.functional as F

import effect as Effect
from effect.data import TaggedError
from effect.effect import gen, succeed
from effect_pytorch.dataset import MNISTLoaders
from effect_pytorch.pipeline import from_torch


def train_step(
    model: nn.Module,
    optimizer: Any,
    data: Any,
    target: Any,
) -> Effect.Effect[float, TaggedError, Never]:
    """A single training step: forward → loss → backward → step.

    Returns the loss value as a float.
    """

    def _step() -> float:
        model.train()
        optimizer.zero_grad()
        output = model(data)
        loss = F.nll_loss(output, target)
        loss.backward()
        optimizer.step()
        return float(loss.item())

    return from_torch(_step)


@gen
def train_epoch(
    model: nn.Module,
    optimizer: Any,
    train_loader: Any,
    *,
    log_interval: int = 100,
) -> Any:
    """Train for one full epoch.

    Returns the average loss over all batches.
    """
    total_loss = 0.0
    n_batches = 0

    for batch_idx, (data, target) in enumerate(train_loader):
        loss = yield train_step(model, optimizer, data, target)
        total_loss += loss
        n_batches += 1

        if log_interval > 0 and (batch_idx + 1) % log_interval == 0:
            yield Effect.log_info(
                f"  batch {batch_idx + 1}/{len(train_loader)} | loss={loss:.4f}"
            )

    avg_loss = total_loss / max(n_batches, 1)
    return avg_loss


def evaluate(
    model: nn.Module,
    test_loader: Any,
) -> Effect.Effect[tuple[float, float], TaggedError, Never]:
    """Evaluate the model on the test set.

    Returns ``(avg_loss, accuracy_pct)``.
    """

    def _eval() -> tuple[float, float]:
        model.eval()
        test_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for data, target in test_loader:
                output = model(data)
                test_loss += F.nll_loss(output, target, reduction="sum").item()
                pred = output.argmax(dim=1)
                correct += pred.eq(target).sum().item()
                total += target.size(0)
        avg_loss = test_loss / max(total, 1)
        accuracy = 100.0 * correct / max(total, 1)
        return avg_loss, accuracy

    return from_torch(_eval)


@gen
def train_model(
    model: nn.Module,
    optimizer: Any,
    loaders: MNISTLoaders,
    *,
    epochs: int = 3,
    log_interval: int = 100,
) -> Any:
    """Full training loop for *epochs* epochs.

    Returns the final ``(test_loss, accuracy_pct)``.
    """
    for epoch in range(1, epochs + 1):
        yield Effect.log_info(f"Epoch {epoch}/{epochs}")

        avg_loss = yield train_epoch(
            model, optimizer, loaders.train, log_interval=log_interval
        )
        yield Effect.log_info(f"  avg train loss: {avg_loss:.4f}")

        test_loss, accuracy = yield evaluate(model, loaders.test)
        yield Effect.log_info(
            f"  test loss: {test_loss:.4f} | accuracy: {accuracy:.2f}%"
        )

    final = yield evaluate(model, loaders.test)
    return final
