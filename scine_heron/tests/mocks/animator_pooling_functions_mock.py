#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Mocks for the animator_pooling_functions module.
"""
from typing import Tuple, List

import numpy as np

from scine_heron.tests.mocks.settings import CalculatorSettings
from scine_heron.molecule.animator_pooling_functions import GradientCalculationResult


def calculate_gradient(
    parameters: Tuple[List[Tuple[str, Tuple[float, float, float]]], CalculatorSettings, float]
) -> GradientCalculationResult:
    return GradientCalculationResult(
        gradients=np.array([[-0.15099689, 0.0, 0.0], [0.15099689, 0.0, 0.0], ]),
        energy=0,
        atomic_charges=None,
        settings=parameters[1],  # type: ignore[arg-type]
        bond_orders=None,
        molden_input=str(),
        error_msg=str(),
        info_msg=str(),
    )
