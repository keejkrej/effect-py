from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Never

from effect.context import GenericTag
from effect.layer import Layer
from effect.layer import succeed as layer_succeed

Device = GenericTag("DeviceService")


@dataclass(frozen=True, slots=True)
class DeviceService:
    device: str = "cpu"

    def resolve(self, device: str | None = None) -> str:
        return device or self.device


def live(device: str = "cpu") -> Layer[Any, Never, Never]:
    return layer_succeed(Device, DeviceService(device=device))
