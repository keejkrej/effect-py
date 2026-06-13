"""Effectful optimizer constructors wrapping ``torch.optim``."""

from __future__ import annotations

from typing import Any, Never

import torch.nn as nn
import torch.optim as optim

import effect as Effect
from effect.data import TaggedError
from effect_pytorch.pipeline import from_torch


def sgd(
    model: nn.Module,
    lr: float = 0.01,
    momentum: float = 0.0,
) -> Effect.Effect[optim.SGD, TaggedError, Never]:
    """Build an SGD optimizer inside an Effect."""
    return from_torch(lambda: optim.SGD(model.parameters(), lr=lr, momentum=momentum))


def adam(
    model: nn.Module,
    lr: float = 0.001,
) -> Effect.Effect[optim.Adam, TaggedError, Never]:
    """Build an Adam optimizer inside an Effect."""
    return from_torch(lambda: optim.Adam(model.parameters(), lr=lr))


def zero_grad(optimizer: Any) -> Effect.Effect[None, TaggedError, Never]:
    """Zero all parameter gradients."""
    return from_torch(lambda: optimizer.zero_grad())


def step(optimizer: Any) -> Effect.Effect[None, TaggedError, Never]:
    """Perform a single optimization step."""
    return from_torch(lambda: optimizer.step())
