#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the SettingsWidget class.
"""
from pkgutil import iter_modules
from typing import List, Dict, Any, Callable
from functools import partial

from PySide2.QtCore import QSize, Qt
from PySide2.QtWidgets import (
    QDockWidget,
    QWidget,
    QSpinBox,
    QLabel,
    QDoubleSpinBox,
    QCheckBox,
)

from scine_heron.containers.combo_box import BaseBox
from scine_heron.containers.layouts import HorizontalLayout, VerticalLayout
from scine_heron.containers.buttons import TextPushButton
from scine_heron.settings.settings import MoleculeStyle, LabelsStyle
from scine_heron.settings.settings_status_manager import SettingsStatusManager
from scine_heron.status_manager import (
    Status,
    StatusManager,
)


class BasicSettingsWidget(QDockWidget):
    """
    Displays of display and molecular orbital settings
    """

    def __init__(self, settings_status_manager: SettingsStatusManager):
        """
        This is the display of the settings grid. Each setting is drawn depending on its type.
        :param settings_status_manager: class managing MO and display settings and propagating them
        """
        QDockWidget.__init__(self, "Basic Settings")
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.setMinimumWidth(500)

        self.__dockedWidget = QWidget(self)
        self.setWidget(self.__dockedWidget)

        self.__layout = VerticalLayout()
        self.__dockedWidget.setLayout(self.__layout)
        self.__layout.setAlignment(Qt.AlignTop)

        self.__settings_status_manager = settings_status_manager
        self.__settings_status_manager.number_of_mos_changed.connect(
            self.__update_number_of_mo
        )
        self.__settings_status_manager.selected_mo_changed.connect(
            self.__update_number_of_mo
        )

        self.__widgets_dict: Dict[str, Any] = {}

        self.__widget_height = 30
        self.__widget_width = 160

        self.__enabled = StatusManager(True)

        self.__add_style_setting(
            "Molecule Style",
            "molecule_style",
            [str(m.value) for m in MoleculeStyle.__members__.values()],
            self.__update_molecule_style,
            str(MoleculeStyle.BallAndStick.value),
            enabled=self.__enabled,
        )

        self.__add_style_setting(
            "Labels Style",
            "labels_style",
            [str(m.value) for m in LabelsStyle.__members__.values()],
            self.__update_labels_style,
            str(LabelsStyle.Empty.value),
            enabled=self.__enabled,
        )
        self.__add_style_setting(
            "Bond Display",
            "bond_display",
            ["distance", "el. density"],
            self.__update_bond_style,
            "distance",
            enabled=self.__enabled,
        )

        self.__add_mo_setting_at_layout(
            "Molecular Orbital", "molecular_orbital", self.__enabled
        )
        self.__add_double_spin_setting_at_layout(
            "Contour Value",
            "molecular_orbital_value",
            0.05,
            self.__update_molecular_orbital_value,
            self.__enabled,
        )
        self.__add_double_spin_setting_at_layout(
            "Scale Haptic Force",
            "scale_force",
            1.0,
            self.__update_force_scaling,
            self.__enabled,
            0.6,
            1.4,
        )
        self.__add_double_spin_setting_at_layout(
            "Scale applied gradients",
            "scale_gradients",
            0.1,
            self.__update_gradient_scaling,
            self.__enabled,
            0.01,
            10.0,
        )
        mediator_check = QCheckBox()
        mediator_check.setChecked(True)
        self.__enabled.changed_signal.connect(mediator_check.setEnabled)
        mediator_check.stateChanged.connect(self.__update_mediator_state)  # pylint: disable=no-member
        self.__widgets_dict["mediator_potential_active"] = mediator_check
        self.__layout.addLayout(HorizontalLayout([QLabel("Active mediator potential"), mediator_check]))

        if any(name == "scine_swoose" for _, name, __ in iter_modules()):
            from scine_heron.settings.swoose_settings import SwooseSettingsWidget
            swoose_settings_widget = SwooseSettingsWidget(self, self.__settings_status_manager)
            self.__layout.addWidget(swoose_settings_widget)

    def __update_number_of_mo(self) -> None:
        widget = self.__widgets_dict["molecular_orbital"]
        widget.setMinimum(1)

        if self.__settings_status_manager.number_of_molecular_orbital is not None:
            widget.setMaximum(
                self.__settings_status_manager.number_of_molecular_orbital
            )
        selected = self.__settings_status_manager.selected_molecular_orbital
        if selected is not None and selected > 0:
            widget.setValue(selected)

    def set_enabled(self, enabled: bool) -> None:
        """
        Set widgets enabled.
        """
        self.__enabled.value = enabled

    def is_enabled(self) -> bool:
        """
        Return whether widgets are enabled.
        """
        return self.__enabled.value

    def __add_mo_setting_at_layout(
        self, setting_name: str, setting_key: str, enabled: Status[bool],
    ) -> None:
        """
        Add QSpinBox widget for molecular orbital setting.
        setting_name is a setting display name.
        setting_key is a setting name in sparrow.
        """
        spin_edit = QSpinBox()
        spin_edit.setFixedSize(spin_edit.sizeHint())
        spin_edit.setMinimum(1)
        spin_edit.setValue(1)
        spin_edit.setMaximum(1)
        self.__widgets_dict[setting_key] = spin_edit
        enabled.changed_signal.connect(spin_edit.setEnabled)

        homo_button = TextPushButton("HOMO", partial(self.__update_molecular_orbital, setting_key, -1), self)
        enabled.changed_signal.connect(homo_button.setEnabled)

        lumo_button = TextPushButton("LUMO", partial(self.__update_molecular_orbital, setting_key, -2), self)
        enabled.changed_signal.connect(lumo_button.setEnabled)

        density_button = TextPushButton("El. Density", partial(self.__update_molecular_orbital, setting_key, -3), self)
        enabled.changed_signal.connect(density_button.setEnabled)

        calculate_button = TextPushButton("Go", partial(self.__update_molecular_orbital, setting_key), self)
        calculate_button.setFixedSize(calculate_button.sizeHint())
        enabled.changed_signal.connect(calculate_button.setEnabled)

        self.__layout.add_layouts([
            HorizontalLayout([QLabel(setting_name)]),
            HorizontalLayout([homo_button, lumo_button]),
            HorizontalLayout([density_button]),
            HorizontalLayout([QLabel("MO Index"), spin_edit, calculate_button]),
        ])

    def __add_double_spin_setting_at_layout(
        self,
        setting_name: str,
        setting_key: str,
        default_value: float,
        update_function: Callable[[float], None],
        enabled: Status[bool],
        min_value: float = -1000000000.0,
        max_value: float = 1000000000.0,
    ) -> QDoubleSpinBox:
        """
        Add QDoubleSpinBox widget.
        setting_name is a setting display name.
        setting_key is a setting name in sparrow.
        default_value is a default display value.
        """
        spin_edit = QDoubleSpinBox()
        spin_edit.setFixedSize(QSize(self.__widget_width, self.__widget_height))
        spin_edit.setMinimum(min_value)
        spin_edit.setMaximum(max_value)
        spin_edit.setValue(default_value)
        spin_edit.setSingleStep(0.01)
        spin_edit.setDecimals(2)
        enabled.changed_signal.connect(spin_edit.setEnabled)

        spin_edit.valueChanged.connect(update_function)  # pylint: disable=no-member

        self.__widgets_dict[setting_key] = spin_edit

        self.__layout.addLayout(HorizontalLayout([QLabel(setting_name), spin_edit]))

        return spin_edit

    def __add_style_setting(
        self,
        setting_name: str,
        setting_key: str,
        all_values: List[str],
        update: Callable[[List[str], int], None],
        default_value: str,
        enabled: Status[bool],
    ) -> None:
        """
        Add molecule style widget.
        setting_name is a setting display name.
        setting_key is a setting name in sparrow.
        all_values is a list of valid values.
        default_value is a default display value.
        """
        combo_box = self.__add_combo_box_at_layout(
            setting_name, setting_key, all_values
        )
        combo_box.currentIndexChanged.connect(partial(update, all_values))  # pylint: disable=no-member
        combo_box.setCurrentIndex(all_values.index(default_value))
        enabled.changed_signal.connect(combo_box.setEnabled)

    def __add_combo_box_at_layout(
        self, setting_name: str, setting_key: str, all_values: List[str],
    ) -> BaseBox:
        """
        Add QComboBox widget.
        setting_name is a setting display name.
        setting_key is a setting name in sparrow.
        all_values is a list of valid values.
        """
        combo_box = BaseBox()
        combo_box.addItems(all_values)
        combo_box.setFixedSize(QSize(self.__widget_width, self.__widget_height + 1))

        self.__widgets_dict[setting_key] = combo_box

        self.__layout.addLayout(HorizontalLayout([QLabel(setting_name), combo_box]))

        return combo_box

    def __update_molecule_style(self, all_values: List[str], index: int) -> None:
        """
        Update molecule style.
        """
        self.__settings_status_manager.molecule_style = MoleculeStyle(all_values[index])

    def __update_molecular_orbital(
        self, setting_key: str, special_case: int = 0
    ) -> None:
        """
        Update molecule orbital.
        """
        if special_case:
            self.__settings_status_manager.selected_molecular_orbital = special_case
        else:
            self.__settings_status_manager.selected_molecular_orbital = self.__widgets_dict[
                setting_key
            ].value()

    def __update_molecular_orbital_value(self, value: float) -> None:
        """
        Update molecule orbital value.
        """
        self.__settings_status_manager.molecular_orbital_value = value

    def __update_force_scaling(self, value: float) -> None:
        """
        Update scaling for haptic feedback.
        """
        self.__settings_status_manager.haptic_force_scaling = value

    def __update_gradient_scaling(self, value: float) -> None:
        """
        Update scaling of applied gradients.
        """
        self.__settings_status_manager.gradients_scaling = value

    def __update_labels_style(self, all_values: List[str], index: int) -> None:
        """
        Update molecule style.
        """
        self.__settings_status_manager.labels_style = LabelsStyle(all_values[index])

    def __update_bond_style(self, all_values: List[str], index: int) -> None:
        """
        Update criterion for drawing bonds.
        """
        self.__settings_status_manager.bond_display = all_values[index]

    def __update_mediator_state(self, value: bool) -> None:
        """
        Update if the mediator potential should be active.

        Parameters
        ----------
        value : bool
            The new value.
        """
        self.__settings_status_manager.set_mediator_potential_setting(value)

    def get_mediator_active(self) -> bool:
        return self.__settings_status_manager.get_mediator_potential_setting()
