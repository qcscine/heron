#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the SettingsWidget class.
"""

from typing import List, Dict, Any
from functools import partial
from PySide2.QtCore import QSize
from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSpinBox,
    QLabel,
    QComboBox,
)

from scine_heron.settings.settings_status_manager import SettingsStatusManager
from scine_heron.status_manager import (
    Status,
    StatusManager,
)


class AdvancedSettingsWidget(QWidget):
    """
    Displays sparrow settings in QDockWidget.
    """

    def __init__(self, settings_status_manager: SettingsStatusManager):
        """
        This is the display of the settings grid. Each setting is drawn depending on its type.
        """
        super(AdvancedSettingsWidget, self).__init__()

        self.__layout = QVBoxLayout()
        self.setLayout(self.__layout)

        self.__settings_status_manager = settings_status_manager
        self.__settings_status_manager.spin_multiplicity_changed.connect(
            self.__update_spin_multiplicity
        )
        self.__settings_status_manager.spin_mode_changed.connect(
            self.__update_spin_mode
        )
        self.__widgets_dict: Dict[str, Any] = {}

        self.__widget_height = 30
        self.__widget_width = 130

        self.__enabled = StatusManager(True)
        self.combo_box = None
        self.label = None

        self.display_scf = ["none", "DIIS", "EDIIS", "EDIIS / DIIS"]
        self.sparrow_scf = ["no_mixer", "diis", "ediis", "ediis_diis"]

        self.__add_combo_box_setting_at_layout(
            "Method",
            "method",
            ["MNDO", "AM1", "RM1", "PM3", "PM6", "DFTB0", "DFTB2", "DFTB3"],
            "PM6",
            enabled=self.__enabled,
        )
        self.__add_calculator_setting_at_layout(
            "Spin Multiplicity", "spin_multiplicity", 1, self.__enabled, 1,
        )
        self.__add_combo_box_setting_at_layout(
            "Spin Mode",
            "spin_mode",
            ["unrestricted", "restricted"],
            "unrestricted",
            self.__enabled,
        )
        self.__add_combo_box_setting_at_layout(
            "SCF Accelerator",
            "scf_mixer",
            self.sparrow_scf,
            "DIIS",
            self.__enabled,
            self.display_scf,
        )

    def __update_spin_multiplicity(self, value: int) -> None:
        widget = self.__widgets_dict["spin_multiplicity"]
        widget.setValue(value)

    def __update_spin_mode(self, value: str) -> None:
        combo_box = self.__widgets_dict["spin_mode"]
        combo_box.setCurrentIndex(["unrestricted", "restricted"].index(value))

    def set_enabled(self, enabled: bool) -> None:
        """
        Set widgets enabled.
        """
        self.__enabled.value = enabled

    def __add_calculator_setting_at_layout(
        self,
        setting_name: str,
        setting_key: str,
        default_value: int,
        enabled: Status[bool],
        min_value: int = -1000000000,
        max_value: int = 1000000000,
    ) -> None:
        """
        Add QSpinBox widget for sparrow setting.
        setting_name is a setting display name.
        setting_key is a setting name in sparrow.
        default_value is a default display value.
        """
        widget = self.__add_spin_setting_at_layout(setting_name, setting_key, min_value, max_value)
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
        min_value: int = -1000000000,
        max_value: int = 1000000000,
    ) -> QSpinBox:
        """
        Add QSpinBox widget.
        setting_name is a setting display name.
        setting_key is a setting name in sparrow.
        default_value is a default display value.
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

    def __add_combo_box_setting_at_layout(
        self,
        setting_name: str,
        setting_key: str,
        all_values: List[str],
        default_value: str,
        enabled: Status[bool],
        display_values: List[str] = None,
    ) -> None:
        """
        Add QComboBox sparrow setting widget.
        setting_name is a setting display name.
        setting_key is a setting name in sparrow.
        all_values is a list of valid values.
        default_value is a default display value.
        """
        if not display_values:
            display_values = all_values
        combo_box = self.__add_combo_box_at_layout(
            setting_name, setting_key, display_values
        )
        combo_box.currentIndexChanged.connect(  # pylint: disable=no-member
            partial(self.__update_setting_value_index, setting_key, all_values)
        )

        if not hasattr(self.__settings_status_manager, setting_key):
            raise KeyError(f'No setting {setting_key} in StatusManager')
        setattr(self.__settings_status_manager, setting_key, all_values[display_values.index(default_value)])
        enabled.changed_signal.connect(combo_box.setEnabled)

    def __add_combo_box_at_layout(
        self, setting_name: str, setting_key: str, display_values: List[str],
    ) -> QComboBox:
        """
        Add QComboBox widget.
        setting_name is a setting display name.
        setting_key is a setting name in sparrow.
        all_values is a list of valid values.
        """
        combo_box = QComboBox()
        combo_box.addItems(display_values)
        combo_box.setFixedSize(QSize(self.__widget_width, self.__widget_height + 1))
        self.combo_box = combo_box  # type: ignore

        self.__widgets_dict[setting_key] = combo_box

        label = QLabel(setting_name)
        self.label = label  # type: ignore

        layout = QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(combo_box)
        self.__layout.addLayout(layout)

        return combo_box

    def __update_setting_value(self, setting_key: str, value: int) -> None:
        """
        Update settings from QSpinBox with correct type.
        """
        if not hasattr(self.__settings_status_manager, setting_key):
            raise KeyError(f'No setting {setting_key} in StatusManager')
        setattr(self.__settings_status_manager, setting_key, value)

    def __update_setting_value_index(
        self, setting_key: str, all_values: List[str], index: int
    ) -> None:
        """
        Update settings from QComboBox with correct type.
        """
        if not hasattr(self.__settings_status_manager, setting_key):
            raise KeyError(f'No setting {setting_key} in StatusManager')
        setattr(self.__settings_status_manager, setting_key, all_values[index])

        if setting_key == "method" and index == 5:
            self.combo_box.setParent(None)  # type: ignore
            self.label.setParent(None)  # type: ignore
            self.__add_combo_box_setting_at_layout(
                "SCF Accelerator",
                "scf_mixer",
                [self.sparrow_scf[0]],
                "none",
                self.__enabled,
                [self.display_scf[0]],
            )
        elif setting_key == "method" and index == 6 or index == 7:
            self.combo_box.setParent(None)  # type: ignore
            self.label.setParent(None)  # type: ignore
            self.__add_combo_box_setting_at_layout(
                "SCF Accelerator",
                "scf_mixer",
                self.sparrow_scf[1:],
                "DIIS",
                self.__enabled,
                self.display_scf[1:],
            )
        elif setting_key == "method":
            self.combo_box.setParent(None)  # type: ignore
            self.label.setParent(None)  # type: ignore
            self.__add_combo_box_setting_at_layout(
                "SCF Accelerator",
                "scf_mixer",
                self.sparrow_scf,
                "none",
                self.__enabled,
                self.display_scf,
            )
