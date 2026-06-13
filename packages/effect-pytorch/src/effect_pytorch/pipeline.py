from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Never, TypeVar, cast

import effect as Effect
from effect.data import TaggedError
from effect.effect import fail, gen, succeed, suspend
from effect_pytorch.device import Device
from effect_pytorch.errors import AutogradError, CudaError, ShapeError
from effect_pytorch.rng import Rng

A = TypeVar("A")


def _map_torch_exception(error: Exception) -> TaggedError:
    message = str(error)
    lowered = message.lower()
    if "cuda" in lowered:
        return CudaError(message=message)
    if "shape" in lowered or "size" in lowered or "dimension" in lowered:
        return ShapeError(message=message)
    if "grad" in lowered or "backward" in lowered or "autograd" in lowered:
        return AutogradError(message=message)
    return CudaError(message=message)


def from_torch(thunk: Callable[[], A]) -> Effect.Effect[A, TaggedError, Never]:
    def attempt() -> Effect.Effect[A, TaggedError, Never]:
        try:
            return cast(Effect.Effect[A, TaggedError, Never], succeed(thunk()))
        except Exception as error:
            return cast(Effect.Effect[A, TaggedError, Never], fail(_map_torch_exception(error)))

    return suspend(attempt)


def randn(
    shape: tuple[int, ...],
    *,
    requires_grad: bool = False,
) -> Effect.Effect[Any, TaggedError, Any]:
    @gen
    def acquire():
        device_service = yield Device
        rng_service = yield Rng
        device = device_service.resolve()

        def create():
            import torch

            generator = torch.Generator(device="cpu")
            generator.manual_seed(rng_service.seed)
            tensor = torch.randn(shape, generator=generator, requires_grad=requires_grad)
            return tensor.to(device)

        value = yield from_torch(create)
        return value

    return acquire()


def matmul(
    left: Any,
    right: Any,
) -> Effect.Effect[Any, TaggedError, Never]:
    if left.shape[-1] != right.shape[-2]:
        return fail(
            ShapeError(
                message=(
                    f"Incompatible shapes for matmul: {tuple(left.shape)} x {tuple(right.shape)}"
                ),
                expected=(left.shape[-1],),
                actual=(right.shape[-2],),
            )
        )

    def compute():
        import torch

        return torch.matmul(left, right)

    return from_torch(compute)


def sum_all(tensor: Any) -> Effect.Effect[Any, TaggedError, Never]:
    return from_torch(lambda: tensor.sum())


def item(scalar_tensor: Any) -> Effect.Effect[float, TaggedError, Never]:
    return from_torch(lambda: float(scalar_tensor.item()))


@dataclass(frozen=True, slots=True)
class MatmulPipelineInput:
    left_shape: tuple[int, ...]
    right_shape: tuple[int, ...]
    requires_grad: bool = False


@gen
def matmul_pipeline(spec: MatmulPipelineInput):
    left = yield randn(spec.left_shape, requires_grad=spec.requires_grad)
    right = yield randn(spec.right_shape, requires_grad=spec.requires_grad)
    product = yield matmul(left, right)
    total = yield sum_all(product)
    scalar = yield item(total)
    return scalar


def live_layer(device: str = "cpu", seed: int = 0):
    from effect.layer import merge as merge_layers
    from effect_pytorch.device import live as live_device
    from effect_pytorch.rng import live as live_rng

    return merge_layers(live_device(device), live_rng(seed))
