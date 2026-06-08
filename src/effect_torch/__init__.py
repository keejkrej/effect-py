"""effect-torch — optional libtorch integration for effect-py."""

from effect_torch.device import Device, DeviceService
from effect_torch.device import live as live_device
from effect_torch.errors import AutogradError, CudaError, ShapeError
from effect_torch.pipeline import MatmulPipelineInput, live_layer, matmul_pipeline
from effect_torch.rng import Rng, RngService
from effect_torch.rng import live as live_rng

__all__ = [
    "AutogradError",
    "CudaError",
    "Device",
    "DeviceService",
    "MatmulPipelineInput",
    "Rng",
    "RngService",
    "ShapeError",
    "live_device",
    "live_layer",
    "live_rng",
    "matmul_pipeline",
]
