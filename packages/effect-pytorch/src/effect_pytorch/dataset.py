"""Effectful dataset loaders wrapping ``torchvision.datasets``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Never

import torch.utils.data as data

import effect as Effect
from effect.data import TaggedError
from effect_pytorch.pipeline import from_torch


@dataclass(frozen=True, slots=True)
class MNISTLoaders:
    """Holds both train and test DataLoaders for MNIST."""

    train: data.DataLoader[Any]
    test: data.DataLoader[Any]


def mnist(
    *,
    data_dir: str = "./data",
    batch_size: int = 64,
    num_workers: int = 0,
) -> Effect.Effect[MNISTLoaders, TaggedError, Never]:
    """Load the MNIST dataset, downloading if necessary.

    Returns an ``MNISTLoaders`` containing train and test
    :class:`~torch.utils.data.DataLoader` instances.
    """

    def _load() -> MNISTLoaders:
        from torchvision import datasets, transforms

        transform = transforms.Compose(
            [transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))]
        )

        train_dataset = datasets.MNIST(
            data_dir, train=True, download=True, transform=transform
        )
        test_dataset = datasets.MNIST(
            data_dir, train=False, download=True, transform=transform
        )

        train_loader = data.DataLoader(
            train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers
        )
        test_loader = data.DataLoader(
            test_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers
        )

        return MNISTLoaders(train=train_loader, test=test_loader)

    return from_torch(_load)
