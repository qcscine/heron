#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the SettingsWidget class.
"""
from typing import List, Dict, Any, Callable
from functools import partial
from PySide2.QtCore import QSize, Qt
from PySide2.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSpinBox,
    QLabel,
    QComboBox,
    QDoubleSpinBox,
    QPushButton,
)

from scine_heron.settings.settings import MoleculeStyle, LabelsStyle
from scine_heron.settings.settings_status_manager import SettingsStatusManager
from scine_heron.status_manager import (
    Status,
    StatusManager,
)


class BasicSettingsWidget(QDockWidget):
    """
    Displays sparrow settings in QDockWidget.
    """

    def __init__(self, settings_status_manager: SettingsStatusManager):
        """
        This is the display of the settings grid. Each setting is drawn depending on its type.
        :param settings_status_manager: sparrow settings that should be displayed.
        """
        QDockWidget.__init__(self, "Basic Settings")
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)

        self.__dockedWidget = QWidget(self)
        self.setWidget(self.__dockedWidget)

        self.__layout = QVBoxLayout()
        self.__dockedWidget.setLayout(self.__layout)
        self.__layout.setAlignment(Qt.AlignTop)

        self.__settings_status_manager = settings_status_manager
        self.__settings_status_manager.number_of_mos_changed.connect(
            self.__update_number_of_mo
        )
        self.__settings_status_manager.selected_mo_changed.connect(
            self.__update_number_of_mo
        )
        self.__settings_status_manager.molecular_charge_changed.connect(
            self.__update_molecular_charge
        )
        self.__widgets_dict: Dict[str, Any] = {}

        self.__widget_height = 30
        self.__widget_width = 130

        self.__enabled = StatusManager(True)

        self.__add_style_setting(
            "Molecule Style",
            "molecule_style",
            [m.value for m in MoleculeStyle.__members__.values()],
            self.__update_molecule_style,
            MoleculeStyle.BallAndStick.value,
            enabled=self.__enabled,
        )

        self.__add_style_setting(
            "Labels Style",
            "labels_style",
            [m.value for m in LabelsStyle.__members__.values()],
            self.__update_labels_style,
            LabelsStyle.Empty.value,
            enabled=self.__enabled,
        )

        self.__add_calculator_setting_at_layout(
            "Molecular Charge", "molecular_charge", 0, self.__enabled
        )
        self.__add_mo_setting_at_layout(
            "Molecular Orbital", "molecular_orbital", self.__enabled
        )
        self.__add_double_spin_setting_at_layout(
            "Contour Value", "molecular_orbital_value", 0.05, self.__enabled,
        )

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

    def __update_molecular_charge(self, value: int) -> None:
        widget = self.__widgets_dict["molecular_charge"]
        widget.setValue(value)

    def set_enabled(self, enabled: bool) -> None:
        """
        Set widgets enabled.
        """
        self.__enabled.value = enabled

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

        homo_button = QPushButton("HOMO", self)
        homo_button.clicked.connect(  # pylint: disable=no-member
            partial(self.__update_molecular_orbital, setting_key, -1)
        )
        enabled.changed_signal.connect(homo_button.setEnabled)

        lumo_button = QPushButton("LUMO", self)
        lumo_button.clicked.connect(  # pylint: disable=no-member
            partial(self.__update_molecular_orbital, setting_key, -2)
        )
        enabled.changed_signal.connect(lumo_button.setEnabled)

        density_button = QPushButton("El. Density", self)
        density_button.clicked.connect(  # pylint: disable=no-member
            partial(self.__update_molecular_orbital, setting_key, -3)
        )
        enabled.changed_signal.connect(density_button.setEnabled)

        calculate_button = QPushButton("Go", self)
        calculate_button.setFixedSize(calculate_button.sizeHint())
        calculate_button.clicked.connect(  # pylint: disable=no-member
            partial(self.__update_molecular_orbital, setting_key)
        )
        enabled.changed_signal.connect(calculate_button.setEnabled)

        layout = QHBoxLayout()
        layout.addWidget(QLabel(setting_name))
        self.__layout.addLayout(layout)
        layout = QHBoxLayout()
        layout.addWidget(homo_button)
        layout.addWidget(lumo_button)
        self.__layout.addLayout(layout)
        layout = QHBoxLayout()
        layout.addWidget(density_button)
        self.__layout.addLayout(layout)
        layout = QHBoxLayout()
        layout.addWidget(QLabel("MO Index"))
        layout.addWidget(spin_edit)
        layout.addWidget(calculate_button)
        self.__layout.addLayout(layout)

    def __add_calculator_setting_at_layout(
        self,
        setting_name: str,
        setting_key: str,
        default_value: int,
        enabled: Status[bool],
    ) -> None:
        """
        Add QSpinBox widget for sparrow setting.
        setting_name is a setting display name.
        setting_key is a setting name in sparrow.
        default_value is a default display value.
        """
        widget = self.__add_spin_setting_at_layout(setting_name, setting_key)
        enabled.changed_signal.connect(widget.setEnabled)

        widget.valueChanged.connect(partial(self.__update_setting_value, setting_key))  # pylint: disable=no-member
        if default_value is not None:
            widget.setValue(default_value)
            if not hasattr(self.__settings_status_manager, setting_key):
                raise KeyError(f'No setting {setting_key} in StatusManager')
            setattr(self.__settings_status_manager, setting_key, default_value)

    def __add_spin_setting_at_layout(
        self,
        setting_name: str,
        setting_key: str,
        min_value: int = -20,
        max_value: int = 20,
    ) -> QSpinBox:
        """
        Add QSpinBox widget.
        setting_name is a setting display name.
        setting_key is a setting name in sparrow.
        """
        spin_edit = QSpinBox()
        spin_edit.setFixedSize(QSize(self.__widget_width, self.__widget_height))
        spin_edit.setMinimum(min_value)
        spin_edit.setMaximum(max_value)
        self.__widgets_dict[setting_key] = spin_edit

        layout = QHBoxLayout()
        layout.addWidget(QLabel(setting_name))
        layout.addWidget(spin_edit)
        self.__layout.addLayout(layout)

        return spin_edit

    def __add_double_spin_setting_at_layout(
        self,
        setting_name: str,
        setting_key: str,
        default_value: float,
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

        spin_edit.valueChanged.connect(self.__update_molecular_orbital_value)  # pylint: disable=no-member

        self.__widgets_dict[setting_key] = spin_edit

        layout = QHBoxLayout()
        layout.addWidget(QLabel(setting_name))
        layout.addWidget(spin_edit)
        self.__layout.addLayout(layout)

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
    ) -> QComboBox:
        """
        Add QComboBox widget.
        setting_name is a setting display name.
        setting_key is a setting name in sparrow.
        all_values is a list of valid values.
        """
        combo_box = QComboBox()
        combo_box.addItems(all_values)
        combo_box.setFixedSize(QSize(self.__widget_width, self.__widget_height + 1))

        self.__widgets_dict[setting_key] = combo_box

        layout = QHBoxLayout()
        layout.addWidget(QLabel(setting_name))
        layout.addWidget(combo_box)
        self.__layout.addLayout(layout)

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

    def __update_labels_style(self, all_values: List[str], index: int) -> None:
        """
        Update molecule style.
        """
        self.__settings_status_manager.labels_style = LabelsStyle(all_values[index])

    def __update_setting_value(self, setting_key: str, value: int) -> None:
        """
        Update settings from QSpinBox with correct type.
        """
        if not hasattr(self.__settings_status_manager, setting_key):
            raise KeyError(f'No setting {setting_key} in StatusManager')
        setattr(self.__settings_status_manager, setting_key, value)
