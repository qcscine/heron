#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Tuple

from scine_chemoton.utilities.model_combinations import ModelCombination
from scine_chemoton.utilities.uncertainties import ConstantUncertainty
from scine_chemoton.utilities.place_holder_model import construct_place_holder_model


class UncertaintyTuple:
    def __init__(self, model_combination: ModelCombination, free_energy_uncertainty: ConstantUncertainty,
                 activation_energy_uncertainty: ConstantUncertainty):
        """
        We cannot directly call isinstance(option, Tuple[ModelCombination, Uncertainty, Uncertainty]. Therefore,
        we use this dummy object to make the comparison.

        Parameters
        ----------
        model_combination : ModelCombination
            The model combination for which the uncertainties are valid.
        free_energy_uncertainty : Uncertainty
            The uncertainty object for the free energies.
        activation_energy_uncertainty : Uncertainty
            The uncertainty object for the activation energies.
        """
        self.model_combination = model_combination
        self.free_energy_uncertainty = free_energy_uncertainty
        self.activation_energy_uncertainty = activation_energy_uncertainty

    def get_tuple(self) -> Tuple[ModelCombination, ConstantUncertainty, ConstantUncertainty]:
        """
        Getter as a tuple.
        """
        return self.model_combination, self.free_energy_uncertainty, self.activation_energy_uncertainty

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UncertaintyTuple):
            return False
        return (other.model_combination == self.model_combination
                and other.free_energy_uncertainty.get_uncertainty_bounds()
                == self.free_energy_uncertainty.get_uncertainty_bounds()
                and other.activation_energy_uncertainty.get_uncertainty_bounds()
                == self.activation_energy_uncertainty.get_uncertainty_bounds())

    @staticmethod
    def get_default():
        return UncertaintyTuple(ModelCombination(construct_place_holder_model()),
                                ConstantUncertainty((0.0, 0.0)),
                                ConstantUncertainty((0.0, 0.0)))
