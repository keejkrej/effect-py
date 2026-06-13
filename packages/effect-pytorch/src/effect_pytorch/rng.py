from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Never

from effect.context import GenericTag
from effect.layer import Layer
from effect.layer import succeed as layer_succeed

Rng = GenericTag("RngService")


@dataclass(frozen=True, slots=True)
class RngService:
    seed: int = 0


def live(seed: int = 0) -> Layer[Any, Never, Never]:
    return layer_succeed(Rng, RngService(seed=seed))
