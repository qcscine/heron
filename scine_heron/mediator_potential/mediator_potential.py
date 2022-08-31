#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the MediatorPotential class.
"""
import numpy as np
import typing

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
        self.__molden_input = calculation_result.molden_input
        self.__settings = calculation_result.settings

    @property
    def molecule_version(self) -> int:
        return self.__molecule_version

    @property
    def molden_input(self) -> str:
        return self.__molden_input

    @property
    def settings(self) -> typing.Dict[str, typing.Any]:
        return self.__settings

    def get_gradients(self, current_positions: np.ndarray) -> np.ndarray:
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
        return typing.cast(float, approx_energy)

    def get_atomic_charges(self) -> typing.Optional[typing.List[float]]:
        """Returns the atomic charges that were most recently computed by Sparrow."""

        return self.__charges
