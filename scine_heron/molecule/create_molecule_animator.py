#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the `create_molecule_animator` function.
"""
from scine_heron.status_manager import StatusManager
from scine_heron.haptic.haptic_client import HapticClient
from scine_heron.electronic_data.electronic_data_status_manager import (
    ElectronicDataStatusManager,
)
from scine_heron.energy_profile.energy_profile_point import EnergyProfilePoint
from scine_heron.energy_profile.energy_profile_status_manager import (
    EnergyProfileStatusManager,
)
from scine_heron.molecule.utils.molecule_utils import (
    molecule_to_list_of_atoms,
    convert_gradients,
    apply_gradients,
)
from scine_heron.settings.settings_status_manager import SettingsStatusManager
from scine_heron.molecule.animator_pooling_functions import (
    calculate_gradient,
    GradientCalculationResult,
)
from scine_heron.molecule.animator import Animator
from typing import Optional, Tuple, List, Any, Dict, TYPE_CHECKING
from vtk import vtkMolecule
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


def create_molecule_animator(
    molecule_version: int,
    molecule: vtkMolecule,
    settings_status_manager: SettingsStatusManager,
    haptic_client: Optional[HapticClient],
    energy_status_manager: Optional[EnergyProfileStatusManager],
    electronic_data_status_manager: Optional[ElectronicDataStatusManager],
    charge_status_manager: StatusManager[Optional[List[float]]],
    settings_changed: Signal,
) -> Animator:
    """
    Creates an Animator that calculates and applies gradients to the molecule
    on every update.
    """

    def provide_data() -> Tuple[
        int, List[Tuple[str, Tuple[float, float, float]]], Dict[str, Any]
    ]:
        return (
            molecule_version,
            molecule_to_list_of_atoms(molecule),
            settings_status_manager.get_calculator_settings(),
        )

    def apply_results(result: GradientCalculationResult, time_interval: float,) -> None:
        charge_status_manager.value = result.atomic_charges

        if energy_status_manager is not None:
            if len(energy_status_manager) == 0:
                if result.energy != 0.0:
                    elapsed_time = time_interval
                    energy_profile_point = EnergyProfilePoint(
                        result.energy, elapsed_time, time_interval
                    )
                    energy_status_manager.append(energy_profile_point)
            else:
                elapsed_time = (
                    energy_status_manager.value[-1].elapsed_time + time_interval
                )
                if result.energy != 0.0:
                    energy = result.energy
                else:
                    energy = energy_status_manager.value[-1].energy
                energy_profile_point = EnergyProfilePoint(
                    energy, elapsed_time, time_interval
                )
                energy_status_manager.append(energy_profile_point)

        settings_status_manager.error_message = result.error_msg
        settings_status_manager.info_message = result.info_msg
        if result.settings:
            if result.settings["molecular_charge"] != settings_status_manager.molecular_charge or \
                    result.settings["spin_multiplicity"] != settings_status_manager.spin_multiplicity or \
                    result.settings["spin_mode"] != settings_status_manager.spin_mode:
                settings_changed.emit(
                    result.settings["molecular_charge"],
                    result.settings["spin_multiplicity"],
                    result.settings["spin_mode"],
                )

        if electronic_data_status_manager is not None:
            electronic_data_status_manager.molden_input = result.molden_input
        convert_gradients(result.gradients)
        apply_gradients(
            molecule,
            result.gradients,
            settings_status_manager.mouse_picked_atom_id,
            settings_status_manager.haptic_picked_atom_id,
        )
        if haptic_client is not None:
            haptic_client.update_molecule(molecule)
            haptic_client.update_gradient(result.gradients)

    return Animator(calculate_gradient, provide_data, apply_results)
