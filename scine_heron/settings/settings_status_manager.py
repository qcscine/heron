#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the SettingsStatusManager class.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from PySide2.QtCore import QObject
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal

from scine_heron.settings.settings import (
    CalculatorSettings,
    MolViewSettings,
    MoleculeStyle,
    LabelsStyle
)


class SettingsStatusManager(QObject):

    error_update = Signal(str)
    info_update = Signal(str)

    molecule_style_changed = Signal()
    labels_style_changed = Signal()
    selected_mo_changed = Signal(int)
    number_of_mos_changed = Signal()
    mouse_picked_atom_id_changed = Signal()
    haptic_picked_atom_id_changed = Signal()

    molecular_charge_changed = Signal(int)
    spin_multiplicity_changed = Signal(int)
    spin_mode_changed = Signal(str)
    method_changed = Signal(str)
    scf_mixer_changed = Signal(str)
    self_consistence_criterion_changed = Signal(float)

    hamiltonian_changed = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.__mol_view_settings = MolViewSettings()
        self.__calculator_setting = CalculatorSettings()
        self.molecular_charge_changed.connect(self.__hamiltonian_changed)  # pylint: disable=no-member
        self.spin_multiplicity_changed.connect(self.__hamiltonian_changed)  # pylint: disable=no-member
        self.spin_mode_changed.connect(self.__hamiltonian_changed)  # pylint: disable=no-member
        self.method_changed.connect(self.__hamiltonian_changed)  # pylint: disable=no-member

    def __hamiltonian_changed(self, *args, **kwargs) -> None:
        self.hamiltonian_changed.emit()

    def get_calculator_settings(self) -> Dict[str, Any]:
        return self.__calculator_setting.__dict__

    @property
    def error_message(self) -> str:
        return self.__mol_view_settings.error_message

    @error_message.setter
    def error_message(self, value: str) -> None:
        if value == "":
            return

        self.__mol_view_settings.error_message = value
        self.error_update.emit(value)

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
    def mouse_picked_atom_id(self) -> Optional[int]:
        return self.__mol_view_settings.mouse_picked_atom_id

    @mouse_picked_atom_id.setter
    def mouse_picked_atom_id(self, value: Optional[int]) -> None:
        if value == self.__mol_view_settings.mouse_picked_atom_id:
            return
        self.__mol_view_settings.mouse_picked_atom_id = value
        self.mouse_picked_atom_id_changed.emit()

    @property
    def haptic_picked_atom_id(self) -> Optional[int]:
        return self.__mol_view_settings.haptic_picked_atom_id

    @haptic_picked_atom_id.setter
    def haptic_picked_atom_id(self, value: Optional[int]) -> None:
        if value == self.__mol_view_settings.haptic_picked_atom_id:
            return
        self.__mol_view_settings.haptic_picked_atom_id = value
        self.haptic_picked_atom_id_changed.emit()

    @property
    def molecular_orbital_value(self) -> float:
        return self.__mol_view_settings.molecular_orbital_value

    @molecular_orbital_value.setter
    def molecular_orbital_value(self, value: float) -> None:
        if value == self.__mol_view_settings.molecular_orbital_value:
            return
        self.__mol_view_settings.molecular_orbital_value = value
        self.selected_mo_changed.emit(value)

    @property
    def method(self) -> str:
        return self.__calculator_setting.method

    @method.setter
    def method(self, value: str) -> None:
        if value == self.__calculator_setting.method:
            return
        self.__calculator_setting.method = value
        self.method_changed.emit(value)

    @property
    def molecular_charge(self) -> int:
        return self.__calculator_setting.molecular_charge

    @molecular_charge.setter
    def molecular_charge(self, value: int) -> None:
        if value == self.__calculator_setting.molecular_charge:
            return
        self.__calculator_setting.molecular_charge = value
        self.molecular_charge_changed.emit(value)

    @property
    def spin_multiplicity(self) -> int:
        return self.__calculator_setting.spin_multiplicity

    @spin_multiplicity.setter
    def spin_multiplicity(self, value: int) -> None:
        if value == self.__calculator_setting.spin_multiplicity:
            return
        self.__calculator_setting.spin_multiplicity = value
        self.spin_multiplicity_changed.emit(value)

    @property
    def spin_mode(self) -> str:
        return self.__calculator_setting.spin_mode

    @spin_mode.setter
    def spin_mode(self, value: str) -> None:
        if value == self.__calculator_setting.spin_mode:
            return
        self.__calculator_setting.spin_mode = value
        self.spin_mode_changed.emit(value)

    @property
    def self_consistence_criterion(self) -> float:
        return self.__calculator_setting.self_consistence_criterion

    @self_consistence_criterion.setter
    def self_consistence_criterion(self, value: float) -> None:
        if value == self.__calculator_setting.self_consistence_criterion:
            return
        self.__calculator_setting.self_consistence_criterion = value
        self.self_consistence_criterion_changed.emit(value)

    @property
    def scf_mixer(self) -> str:
        return self.__calculator_setting.scf_mixer

    @scf_mixer.setter
    def scf_mixer(self, value: str) -> None:
        if value == self.__calculator_setting.scf_mixer:
            return
        self.__calculator_setting.scf_mixer = value
        self.scf_mixer_changed.emit(value)
