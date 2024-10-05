#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2024 Théo Morales <theo.morales.fr@gmail.com>
#
# Distributed under terms of the MIT license.

"""
Mean Squared Error (MSE) loss.
"""

from typing import Dict

import torch
from torch import Tensor


class MSELoss:
    def __init__(self, reduction: str):
        self._reduction = reduction

    def __call__(self, y_pred: Tensor, y_true: Tensor) -> Dict[str, Tensor]:
        return {
            "mse": torch.nn.functional.mse_loss(
                y_pred, y_true, reduction=self._reduction
            )
        }
