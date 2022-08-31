#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the SparrowClient class.
"""

from pkgutil import iter_modules
from typing import Any, Dict, List

import scine_utilities as su
import numpy as np

from .custom_results import CustomResult

if "scine_sparrow" in (name for _, name, _ in iter_modules()):
    import scine_sparrow  # noqa # pylint: disable=unused-import


class SparrowClient:
    def __init__(
        self, atomic_hessian_switch: bool,
        settings: Dict[str, Any],
        molecule_version: int,
    ):
        self.__atomic_hessian_switch = atomic_hessian_switch
        self.__settings = settings
        self.__molecule_version_current = molecule_version
        self.__molecule_version_prev = -1
        self.__n_electrons_for_uncharged_species = 0
        self.__atom_collection = su.AtomCollection()
        self.__master_calculator = self.__create_calculator()
        self.__error_msg = ""
        self.__info_msg = ""

    def __create_calculator(self) -> su.core.Calculator:
        """
        Prepare Calculator
        """
        calc_method = "PM6"  # default method

        if "method" not in self.__settings:
            self.__settings["method"] = calc_method
        settings = self.__settings

        calculator = su.core.get_calculator(settings["method"], self.__settings["program"])
        self.__settings.pop("program")
        if calculator is None:
            raise RuntimeError("Could not find calculator supporting " + settings["method"])
        assert isinstance(calculator, su.core.Calculator)

        for key in list(settings):
            calculator.settings[key] = settings[key]

        calculator.log = su.core.Log.silent()

        if self.__atomic_hessian_switch:
            calculator.set_required_properties(
                [
                    su.Property.Energy,
                    su.Property.Gradients,
                    su.Property.AtomicHessians,
                    su.Property.AtomicCharges,
                    su.Property.SuccessfulCalculation,
                ]
            )
        else:
            calculator.set_required_properties(
                [
                    su.Property.Energy,
                    su.Property.Gradients,
                    su.Property.Hessian,
                    su.Property.AtomicCharges,
                    su.Property.SuccessfulCalculation,
                ]
            )
        return calculator

    def update_system(self, element_strings: List[str]) -> None:
        """
        Update elements and n_electrons_for_uncharged_species
        if there is a new system loaded.
        """
        elms = []
        n_electrons = 0
        for element_string in element_strings:
            elm = su.ElementInfo.element_from_symbol(element_string)
            elms.append(elm)
            n_electrons += su.ElementInfo.Z(elm)
        self.__atom_collection.elements = elms
        self.__n_electrons_for_uncharged_species = n_electrons

    def update_calculator(
        self,
        pos: np.ndarray,
        element_strings: List[str],
        settings: Dict[str, Any],
    ) -> None:
        """
        Set molecule in calculator
        Check validity of settings and update calculator accordingly
        """
        self.__error_msg = ""

        # Update electrons of uncharged species, if new system was loaded
        if self.__molecule_version_prev != self.__molecule_version_current:
            self.update_system(element_strings)
            self.__molecule_version_prev = self.__molecule_version_current
        self.__atom_collection.positions = pos

        # Check settings
        settings = self.__settings
        for key in list(settings):
            if (
                key == "spin_multiplicity"
                or key == "spin_mode"
            ):
                self.__check_setting_validity(key)
            if (
                key != "method"
                and key != "molecular_charge"
                and self.__settings[key] != self.__master_calculator.settings[key]
            ):
                self.__master_calculator.settings[key] = self.__settings[key]
        self.__master_calculator.settings["molecular_charge"] = self.__settings["molecular_charge"]

        # Update structure of calculator
        self.__master_calculator.structure = self.__atom_collection

    def calculate_gradients(self) -> CustomResult:
        """
        carries out Sparrow calculations
        returns all parameters needed for the mediator potential
        """
        error_msg = self.__error_msg
        info_msg = self.__info_msg
        results = self.__master_calculator.calculate()
        if not results.successful_calculation:
            # if calculation did not converge, do not update mediator potential
            return CustomResult()

        molden_input = su.core.to_wf_generator(
            self.__master_calculator
        ).output_wavefunction()

        return CustomResult(
            result=results,
            molden_input=molden_input,
            positions=self.__master_calculator.structure.positions,
            error_msg=error_msg,
            info_msg=info_msg,
            settings=self.__settings
        )

    def __check_setting_validity(self, key: str) -> None:
        """
        Check validity of setting key and alter if needed
        """
        n_electrons_uncharged = self.__n_electrons_for_uncharged_species
        settings = self.__settings
        n_electrons = n_electrons_uncharged - settings["molecular_charge"]
        info_msg = ""
        if key == "spin_multiplicity":
            if settings["method"] == "DFTB0" and settings[key] != 1:
                settings[key] = 1
                info_msg += (
                    "The spin multiplicity was automatically changed to "
                    + str(settings[key])
                    + " as "
                    + str(settings["method"])
                    + " has no spin-unrestricted."
                )
                self.__check_setting_validity(key)
            if (settings[key] + n_electrons) % 2 == 0:
                if settings["method"] == "DFTB0":
                    self.__settings["molecular_charge"] -= 1
                    info_msg += (
                        "The molecular charge was automatically changed to "
                        + str(settings["molecular_charge"])
                        + ". "
                    )
                elif settings[key] % 2 == 0:
                    settings[key] = max(settings[key] - 1, 1)
                    info_msg += (
                        "The spin multiplicity was automatically changed to "
                        + str(settings[key])
                        + ". "
                    )
                else:
                    settings[key] = 2
                    info_msg += (
                        "The spin multiplicity was automatically changed to "
                        + str(settings[key])
                        + ". "
                    )
        if key == "spin_mode":
            if (
                "spin_multiplicity" in settings
                and settings["spin_multiplicity"] > 1
                and settings[key] == "restricted"
                and settings["method"] != "DFTB0"
            ):
                settings[key] = "unrestricted"
                info_msg += (
                    "The spin mode was changed to unrestricted due to spin multiplicity = "
                    + str(settings["spin_multiplicity"])
                    + ". "
                )
        self.__settings[key] = settings[key]
        if info_msg:
            self.__info_msg = info_msg
