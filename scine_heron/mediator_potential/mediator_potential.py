#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the MediatorPotential class.
"""
import numpy as np
from typing import Any, cast, Dict, List, Optional

from .custom_results import CustomResult


class MediatorPotential:
    """
    This class contains the mediator potential & the updates of the settings
    New results from the electronic_structure_calculation are stored here
    and used to approximate the gradient & energy
    All in atomic units
    """

    def __init__(
        self,
        molecule_version: int,
        calculation_result: CustomResult,
    ):
        self.__molecule_version = molecule_version
        self.__energy = calculation_result.energy
        self.__gradients = calculation_result.gradients
        self.__atomic_hessians = calculation_result.hessian
        self.__well_center = calculation_result.positions
        self.__charges = calculation_result.atomic_charges
        self.__bond_orders = calculation_result.bond_orders
        self.__molden_input = calculation_result.molden_input
        self.__settings = calculation_result.settings

    @property
    def molecule_version(self) -> int:
        return self.__molecule_version

    @property
    def molden_input(self) -> str:
        return self.__molden_input

    @property
    def settings(self) -> Dict[str, Any]:
        return self.__settings

    @property
    def bond_orders(self) -> Optional[np.ndarray]:
        return self.__bond_orders

    def get_gradients(self, current_positions: np.ndarray) -> np.ndarray:
        if self.__gradients is None:
            return np.zeros(shape=current_positions.shape)
        if self.__atomic_hessians is None:
            return self.__gradients
        # Returns approximate gradient
        distance = (
            np.array(current_positions).flatten()
            - np.array(self.__well_center).flatten()
        )
        approx_gradients = (
            np.array(self.__gradients).flatten()
            + np.dot(np.array(self.__atomic_hessians), distance)
        ).reshape((len(self.__gradients), 3))
        return approx_gradients

    def get_energy(self, current_positions: np.ndarray) -> float:
        if self.__atomic_hessians is None:
            return self.__energy
        # Returns the approx. energy according to the Taylor series
        # E = E0 + grad * (x-x0) + 0.5 * (x-x0)^T * hessian * (x-x0)
        distance = (
            np.array(current_positions).flatten()
            - np.array(self.__well_center).flatten()
        )
        approx_energy = (
            self.__energy
            + np.dot(np.array(self.__gradients).flatten(), distance)
            + 0.5
            * np.dot(
                np.dot(np.transpose(distance), np.array(self.__atomic_hessians)),
                distance,
            )
        )
        return cast(float, approx_energy)

    def get_atomic_charges(self) -> Optional[List[float]]:
        """Returns the atomic charges that were most recently computed by Sparrow."""

        return self.__charges
