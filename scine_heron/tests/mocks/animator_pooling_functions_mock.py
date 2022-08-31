#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Mocks for the animator_pooling_functions module.
"""
from typing import Tuple, List
from scine_heron.settings.settings import CalculatorSettings
from scine_heron.molecule.animator_pooling_functions import GradientCalculationResult


def calculate_gradient(
    parameters: Tuple[List[Tuple[str, Tuple[float, float, float]]], CalculatorSettings]
) -> GradientCalculationResult:
    return GradientCalculationResult(
        gradients=[[-0.15099689, 0.0, 0.0], [0.15099689, 0.0, 0.0], ],
        energy=0,
        atomic_charges=None,
        settings=parameters[1],  # type: ignore[arg-type]
        molden_input=str(),
        error_msg=str(),
        info_msg=str(),
    )
