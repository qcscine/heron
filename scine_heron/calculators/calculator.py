#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from copy import deepcopy
from pkgutil import iter_modules
from typing import Any, Dict, List, Optional

import numpy as np
import scine_sparrow  # noqa # pylint: disable=unused-import
import scine_utilities as su
from scine_utilities import settings_names

from scine_heron.mediator_potential.custom_results import CustomResult
from scine_heron.utilities import write_error_message, write_info_message, docstring_dict_from_scine_settings
from scine_heron.settings.docstring_parser import DocStringParser

# import all optional calculator modules if available
for _, name, __ in iter_modules():
    if name == "scine_ams_wrapper":
        try:
            import scine_ams_wrapper  # noqa # pylint: disable=(unused-import,import-error)
        except ImportError as exception:
            write_error_message(f"Could not import scine_ams_wrapper: {exception}")
    elif name == "scine_dftbplus_wrapper":
        try:
            import scine_dftbplus_wrapper  # noqa # pylint: disable=(unused-import,import-error)
        except ImportError as exception:
            write_error_message(f"Could not import scine_dftbplus_wrapper: {exception}")
    elif name == "scine_serenity":
        try:
            import scine_serenity_wrapper  # noqa # pylint: disable=(unused-import,import-error)
        except ImportError as exception:
            write_error_message(f"Could not import scine_serenity_wrapper: {exception}")
    elif name == "scine_swoose":
        try:
            import scine_swoose  # noqa # pylint: disable=(unused-import,import-error)
        except ImportError as exception:
            write_error_message(f"Could not import scine_swoose: {exception}")
    elif name == "scine_xtb_wrapper":
        try:
            import scine_xtb_wrapper  # noqa # pylint: disable=(unused-import,import-error)
        except ImportError as exception:
            write_error_message(f"Could not import scine_xtb_wrapper: {exception}")


class CalculatorLoadingFailed(Exception):
    pass


class ScineCalculatorWrapper:
    _calculator: Optional[su.core.Calculator]

    def __init__(self, method_family: str, program: str, hessian_required: bool,
                 settings: Optional[Dict[str, Any]] = None, atoms: Optional[su.AtomCollection] = None) -> None:
        self.__hessian_required = hessian_required
        self.__bond_orders_required = False
        self._docstring_parser = DocStringParser()
        success = self.load_calculator(method_family, program, atoms, settings)
        if not success:
            raise CalculatorLoadingFailed
        self.prev_molecule_version: Optional[int] = None if atoms is None else -1
        if success:
            self._set_required_properties()

    def get_structure(self) -> Optional[su.AtomCollection]:
        if self._calculator is not None and self.prev_molecule_version is not None:
            return self._calculator.structure
        return None

    def set_hessian_flag(self, value: bool) -> None:
        self.__hessian_required = value
        self._set_required_properties()

    def set_bond_orders_flag(self, value: bool) -> None:
        self.__bond_orders_required = value
        self._set_required_properties()

    def _set_required_properties(self) -> None:
        if self._calculator is None:
            return
        default_properties = [su.Property.Energy, su.Property.Gradients, su.Property.AtomicCharges,
                              su.Property.SuccessfulCalculation]
        additional_properties = []
        if self.__hessian_required:
            if self._calculator.get_possible_properties().contains_subset(su.PropertyList(su.Property.AtomicHessians)):
                additional_properties.append(su.Property.AtomicHessians)
            else:
                additional_properties.append(su.Property.Hessian)
        if self.__bond_orders_required:
            if not self._calculator.get_possible_properties().contains_subset(
                    su.PropertyList(su.Property.BondOrderMatrix)
            ):
                raise RuntimeError(f"Bond orders are not available for {self._calculator.name()}")
            additional_properties.append(su.Property.BondOrderMatrix)
        self._calculator.set_required_properties(default_properties + additional_properties)

    def calculate(self) -> su.Results:
        if self._calculator is None:
            return su.Results()
        return self._calculator.calculate()

    def calculate_custom_result(self) -> CustomResult:
        if self._calculator is None:
            return CustomResult()
        self._calculator.log = su.core.Log.silent()
        scine_results = su.Results()
        try:
            scine_results = self._calculator.calculate()
        except RuntimeError as exc:
            exception_to_raise: Optional[RuntimeError] = exc
            if self._multiplicity_convenience_check(exc):
                # could fix problem, by changing multiplicity, try again
                try:
                    scine_results = self._calculator.calculate()
                    exception_to_raise = None
                except RuntimeError as another_exc:
                    exception_to_raise = another_exc
            if exception_to_raise is not None:
                return self._failed_result(str(exception_to_raise))
        if not scine_results.successful_calculation:
            # if calculation did not converge, return empty
            return self._failed_result("Calculation was not successful")
        wf_generator = su.core.to_wf_generator(self._calculator)
        molden_input = "" if wf_generator is None else wf_generator.output_wavefunction()

        return CustomResult(
            result=scine_results,
            molden_input=molden_input,
            positions=self._calculator.structure.positions,
            error_msg="",
            info_msg="",
            settings=self._calculator.settings.as_dict()
        )

    def _failed_result(self, error: str) -> CustomResult:
        result = CustomResult()
        if self._calculator is None:
            return result
        result.error_msg = error
        result.settings = self._calculator.settings.as_dict()
        return result

    def update_system(self, molecule_version: int, elements: List[str], positions: np.ndarray,
                      settings: Optional[Dict[str, Any]] = None) -> None:
        if self._calculator is None:
            return
        if self.prev_molecule_version is None or molecule_version != self.prev_molecule_version:
            atoms = su.AtomCollection([su.ElementInfo.element_from_symbol(e) for e in elements], positions)
            self._calculator.structure = atoms
            self.prev_molecule_version = molecule_version
        else:
            self._calculator.positions = positions
        if settings is not None:
            self.update_settings(settings)

    def get_calculator(self) -> su.core.Calculator:
        if self._calculator is None:
            raise RuntimeError("Error retrieving calculator")
        return self._calculator

    def get_settings(self) -> su.Settings:
        if self._calculator is None:
            return su.Settings("empty", {})
        return self._calculator.settings

    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        if self._calculator is None:
            return False
        prev_settings = deepcopy(self._calculator.settings.as_dict())
        self._calculator.settings.update(new_settings)
        if not self._calculator.settings.valid():
            try:
                self._calculator.settings.throw_incorrect_settings()  # type: ignore
            except RuntimeError as e:
                write_error_message(str(e))
                self._calculator.settings.update(prev_settings)
                return False
        for key in new_settings.keys():
            if key not in self._calculator.settings.keys():
                write_error_message(f"Given setting {key} is not available for {self._calculator.name()}")
        return new_settings != prev_settings

    def load_calculator(self, method_family: str, program: str, atoms: Optional[su.AtomCollection] = None,
                        settings: Optional[Dict[str, Any]] = None) -> bool:
        try:
            calculator = su.core.get_calculator(method_family, program)
        except RuntimeError:
            write_error_message(f"Could not find calculator supporting {method_family} in {program} program")
            return False
        if calculator is None:
            write_error_message(f"Could not find calculator supporting {method_family} in {program} program")
            return False
        self._calculator = calculator
        if settings is not None:
            self.update_settings(settings)
        if atoms is not None:
            try:
                self._calculator.structure = atoms
            except RuntimeError as e:
                if self._multiplicity_convenience_check(e):
                    self._calculator.structure = atoms
                else:
                    write_error_message(str(e))
                    return False
        self._set_required_properties()
        self.prev_molecule_version = None
        return True

    def _multiplicity_convenience_check(self, exc: RuntimeError) -> bool:
        if self._calculator is not None and "chosen spin multiplicity" in str(exc):
            # assume we want to switch from even to uneven or vice versa
            current_mult: int = self._calculator.settings.get(settings_names.spin_multiplicity)  # type: ignore
            current_charge: int = self._calculator.settings.get(settings_names.molecular_charge)  # type: ignore
            new_min_mult = 1 if (current_mult % 2) == 0 else 2
            new_mult = max(current_mult - 1, new_min_mult)
            write_info_message(f"Loaded structure, set spin multiplicity to {new_mult} "
                               f"and molecular charge to {current_charge}")
            self._calculator.settings[settings_names.spin_multiplicity] = new_mult
            return True
        return False

    def get_docstring_dict(self) -> Dict[str, str]:
        if self._calculator is None:
            return {}
        return docstring_dict_from_scine_settings(self._calculator.settings)
