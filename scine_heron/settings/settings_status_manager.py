#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the SettingsStatusManager class.
"""

from typing import Optional, Dict, Any, List, Tuple, TYPE_CHECKING
from PySide2.QtCore import QObject
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal

from scine_utilities import Settings

from scine_heron.settings.settings import (
    MolViewSettings,
    MoleculeStyle,
    LabelsStyle
)


class SettingsStatusManager(QObject):
    """
    A class that connects changes in the settings to signals that can be connected.
    """

    error_update = Signal(str)
    info_update = Signal(str)

    opaque_signal = Signal(list, bool)
    molecule_style_changed = Signal()
    labels_style_changed = Signal()
    selected_mo_changed = Signal(int)
    number_of_mos_changed = Signal()
    mouse_picked_atom_ids_changed = Signal()
    haptic_picked_atom_ids_changed = Signal()
    haptic_force_scaling_changed = Signal(float)
    gradients_scaling_changed = Signal(float)
    force_scaling_changed = Signal(float)

    molecular_charge_changed = Signal(int)
    spin_multiplicity_changed = Signal(int)
    spin_mode_changed = Signal(str)
    bond_display_changed = Signal(str)

    hamiltonian_changed = Signal()

    def __init__(self, parent: Optional[QObject] = None, settings_change_signal: Optional[Signal] = None):
        super().__init__(parent)
        self.__mol_view_settings = MolViewSettings()
        self.__settings_change_signal = settings_change_signal
        self.__calculator_method_family = ""
        self.__calculator_program = ""
        self.__calculator_settings: Optional[Settings] = None
        if self.__settings_change_signal is not None:
            self.__settings_change_signal.connect(self.__update_calculator_properties)  # pylint: disable=no-member
        self.__mediator_potential_active = True
        self.haptic_force_scaling_changed.connect(self.hamiltonian_changed)  # pylint: disable=no-member
        self.gradients_scaling_changed.connect(self.hamiltonian_changed)  # pylint: disable=no-member

    def get_calculator_args(self) -> Tuple[str, str]:
        return self.__calculator_method_family, self.__calculator_program

    def get_calculator_settings(self) -> Dict[str, Any]:
        if self.__calculator_settings is None:
            return {}
        return self.__calculator_settings.as_dict()

    def __update_calculator_properties(self, method_family: str, program: str, settings: Settings):
        self.__calculator_method_family = method_family
        self.__calculator_program = program
        self.__calculator_settings = settings
        if '/' in method_family and "qm_atoms" in settings:
            self.opaque_signal.emit(settings["qm_atoms"], True)
        self.hamiltonian_changed.emit()

    @property
    def error_message(self) -> str:
        return self.__mol_view_settings.error_message

    @error_message.setter
    def error_message(self, value: str) -> None:
        last_error = self.__mol_view_settings.error_message
        self.__mol_view_settings.error_message = value
        if value and value != last_error:
            self.error_update.emit(value)
        if not value and last_error:
            self.error_update.emit("Error was resolved")

    @property
    def info_message(self) -> str:
        return self.__mol_view_settings.info_message

    @info_message.setter
    def info_message(self, value: str) -> None:
        if value == self.__mol_view_settings.info_message or value == "":
            return

        self.__mol_view_settings.info_message = value
        self.info_update.emit(value)

    @property
    def molecule_style(self) -> MoleculeStyle:
        return self.__mol_view_settings.molecule_style

    @molecule_style.setter
    def molecule_style(self, value: MoleculeStyle) -> None:
        if value == self.__mol_view_settings.molecule_style:
            return
        self.__mol_view_settings.molecule_style = value
        self.molecule_style_changed.emit()

    @property
    def labels_style(self) -> LabelsStyle:
        return self.__mol_view_settings.labels_style

    @labels_style.setter
    def labels_style(self, value: LabelsStyle) -> None:
        if value == self.__mol_view_settings.labels_style:
            return
        self.__mol_view_settings.labels_style = value
        self.labels_style_changed.emit()

    @property
    def selected_molecular_orbital(self) -> Optional[int]:
        return self.__mol_view_settings.selected_molecular_orbital

    @selected_molecular_orbital.setter
    def selected_molecular_orbital(self, value: Optional[int]) -> None:
        self.__mol_view_settings.selected_molecular_orbital = value
        if not value:
            self.selected_mo_changed.emit(0)
        else:
            self.selected_mo_changed.emit(value)

    @property
    def number_of_molecular_orbital(self) -> Optional[int]:
        return self.__mol_view_settings.number_of_molecular_orbital

    @number_of_molecular_orbital.setter
    def number_of_molecular_orbital(self, value: Optional[int]) -> None:
        if value == self.__mol_view_settings.number_of_molecular_orbital:
            return
        self.__mol_view_settings.number_of_molecular_orbital = value
        self.number_of_mos_changed.emit()

    @property
    def mouse_picked_atom_ids(self) -> Optional[List[int]]:
        return self.__mol_view_settings.mouse_picked_atom_ids

    @mouse_picked_atom_ids.setter
    def mouse_picked_atom_ids(self, values: Optional[List[int]]) -> None:
        if values == self.__mol_view_settings.mouse_picked_atom_ids:
            return
        self.__mol_view_settings.mouse_picked_atom_ids = values
        self.mouse_picked_atom_ids_changed.emit()

    @property
    def haptic_picked_atom_id(self) -> Optional[int]:
        return self.__mol_view_settings.haptic_picked_atom_id

    @haptic_picked_atom_id.setter
    def haptic_picked_atom_id(self, value: Optional[int]) -> None:
        if value == self.__mol_view_settings.haptic_picked_atom_id:
            return
        self.__mol_view_settings.haptic_picked_atom_id = value
        self.haptic_picked_atom_ids_changed.emit()

    @property
    def molecular_orbital_value(self) -> float:
        return self.__mol_view_settings.molecular_orbital_value

    @molecular_orbital_value.setter
    def molecular_orbital_value(self, value: float) -> None:
        if value == self.__mol_view_settings.molecular_orbital_value:
            return
        self.__mol_view_settings.molecular_orbital_value = value
        self.selected_mo_changed.emit(value)

    def get_mediator_potential_setting(self) -> bool:
        return self.__mediator_potential_active

    def set_mediator_potential_setting(self, value: bool) -> None:
        self.__mediator_potential_active = value

    @property
    def haptic_force_scaling(self) -> float:
        return self.__mol_view_settings.haptic_force_scaling

    @haptic_force_scaling.setter
    def haptic_force_scaling(self, value: float) -> None:
        if value == self.__mol_view_settings.haptic_force_scaling:
            return
        self.__mol_view_settings.haptic_force_scaling = value
        self.haptic_force_scaling_changed.emit(value)

    @property
    def gradients_scaling(self) -> float:
        return self.__mol_view_settings.gradients_scaling

    @gradients_scaling.setter
    def gradients_scaling(self, value: float) -> None:
        if value == self.__mol_view_settings.gradients_scaling:
            return
        self.__mol_view_settings.gradients_scaling = value
        self.gradients_scaling_changed.emit(value)

    @property
    def bond_display(self) -> str:
        return self.__mol_view_settings.bond_display

    @bond_display.setter
    def bond_display(self, value: str) -> None:
        if value == self.__mol_view_settings.bond_display:
            return
        self.__mol_view_settings.bond_display = value
        self.bond_display_changed.emit(value)
