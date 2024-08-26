#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
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
from typing import Optional, Tuple, List, Any, Dict
from vtk import vtkMolecule


def create_molecule_animator(
    molecule_version: int,
    molecule: vtkMolecule,
    settings_status_manager: SettingsStatusManager,
    haptic_client: Optional[HapticClient],
    energy_status_manager: Optional[EnergyProfileStatusManager],
    electronic_data_status_manager: Optional[ElectronicDataStatusManager],
    charge_status_manager: StatusManager[Optional[List[float]]],
    force_status_manager: StatusManager[Optional[List[float]]],
) -> Animator:
    """
    Creates an Animator that calculates and applies gradients to the molecule
    on every update.
    """

    def provide_data() -> Tuple[
        int, List[Tuple[str, Tuple[float, float, float]]], Tuple[str, str], Dict[str, Any], bool, str,
    ]:
        return (
            molecule_version,
            molecule_to_list_of_atoms(molecule),
            settings_status_manager.get_calculator_args(),
            settings_status_manager.get_calculator_settings(),
            settings_status_manager.get_mediator_potential_setting(),
            settings_status_manager.bond_display,
        )

    def apply_results(result: GradientCalculationResult, time_interval: float) -> None:
        charge_status_manager.value = result.atomic_charges
        force_status_manager.value = result.gradients.tolist()

        if energy_status_manager is not None:
            if len(energy_status_manager) == 0:
                if result.energy != 0.0:
                    elapsed_time = time_interval
                    energy_profile_point = EnergyProfilePoint(
                        result.energy, elapsed_time
                    )
                    energy_status_manager.append(energy_profile_point)
            else:
                if result.energy != 0.0:
                    energy = result.energy
                    energy_profile_point = EnergyProfilePoint(
                        energy, 0.0
                    )
                    previous_time = energy_status_manager.value[-1].elapsed_time
                    delta = energy_profile_point.time_stamp - energy_status_manager.value[-1].time_stamp
                    delta_float = delta.total_seconds()
                    energy_profile_point.elapsed_time = previous_time + delta_float

                    energy_status_manager.append(energy_profile_point)

        settings_status_manager.error_message = result.error_msg
        settings_status_manager.info_message = result.info_msg

        if electronic_data_status_manager is not None:
            electronic_data_status_manager.molden_input = result.molden_input
        convert_gradients(result.gradients, boost_factor=settings_status_manager.gradients_scaling)
        apply_gradients(
            molecule,
            result.gradients,
            result.bond_orders,
            settings_status_manager.mouse_picked_atom_ids,
            settings_status_manager.haptic_picked_atom_id,
        )
        if haptic_client is not None:
            haptic_client.update_molecule(molecule)
            haptic_client.update_gradient(result.gradients, settings_status_manager.haptic_force_scaling)

    return Animator(calculate_gradient, provide_data, apply_results)
