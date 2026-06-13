#!/usr/bin/env python3
"""Vertical slice: tensor factory -> matmul -> sum -> scalar."""

from __future__ import annotations

import effect as Effect
from effect import pipe, run_sync
from effect_pytorch import MatmulPipelineInput, live_layer, matmul_pipeline


def main() -> None:
    spec = MatmulPipelineInput(left_shape=(32, 16), right_shape=(16, 8))
    layer = live_layer(device="cpu", seed=0)
    program = pipe(matmul_pipeline(spec), Effect.provide(layer))
    result = run_sync(program)
    print(f"matmul pipeline scalar: {result:.6f}")


if __name__ == "__main__":
    main()
