"""effect-torch — optional libtorch integration for effect-py."""

from effect_pytorch.dataset import MNISTLoaders, mnist
from effect_pytorch.device import Device, DeviceService
from effect_pytorch.device import live as live_device
from effect_pytorch.errors import AutogradError, CudaError, ShapeError
from effect_pytorch.model import MNISTMLP
from effect_pytorch.optimizer import adam, sgd
from effect_pytorch.optimizer import step as optimizer_step
from effect_pytorch.optimizer import zero_grad
from effect_pytorch.pipeline import MatmulPipelineInput, live_layer, matmul_pipeline
from effect_pytorch.rng import Rng, RngService
from effect_pytorch.rng import live as live_rng
from effect_pytorch.train import evaluate, train_epoch, train_model, train_step

__all__ = [
    "AutogradError",
    "CudaError",
    "Device",
    "DeviceService",
    "MNISTMLP",
    "MNISTLoaders",
    "MatmulPipelineInput",
    "Rng",
    "RngService",
    "ShapeError",
    "adam",
    "evaluate",
    "live_device",
    "live_layer",
    "live_rng",
    "matmul_pipeline",
    "mnist",
    "optimizer_step",
    "sgd",
    "train_epoch",
    "train_model",
    "train_step",
    "zero_grad",
]
