#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the EngineWidget class.
"""

from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)
from PySide2.QtCore import QObject
from typing import Dict
from scine_chemoton.engine import Engine  # pylint: disable=import-error
from scine_chemoton import gears  # pylint: disable=import-error
from scine_heron.chemoton.gear_options_widget import GearOptionsWidget


class EngineWidget(QWidget):
    """
    Widget for any engine
    """

    def __init__(
        self,
        parent: QObject,
        engine: Engine,
        gear: gears.Gear,
        engine_label: str,
        gear_name: str,
        filter_description: str = "None",
    ) -> None:
        QWidget.__init__(self, parent)

        self.engine = engine
        self.gear = gear
        self.__docstring_dict: Dict[str, str] = {}
        self.__engine_is_working = False

        # Create layout and add widgets
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(QLabel(engine_label))

        self.__add_gear_at_layout(gear_name)
        self.__add_filter_at_layout(filter_description)

        self.button_settings = QPushButton("Settings")
        self.button_start_stop = QPushButton("Start")
        self.button_delete = QPushButton("Delete")

        self.__layout.addWidget(self.button_start_stop)
        self.__layout.addWidget(self.button_settings)
        self.__layout.addWidget(self.button_delete)

        self.button_start_stop.clicked.connect(self.__start_stop_engine)  # pylint: disable=no-member
        self.button_settings.clicked.connect(self.__show_settings)  # pylint: disable=no-member

        self.setLayout(self.__layout)

        self.setMaximumWidth(300)
        self.setMinimumWidth(300)
        self.setMaximumHeight(300)
        self.setMinimumHeight(300)

    def set_docstring_dict(self, doc_string: Dict[str, str]) -> None:
        self.__docstring_dict = doc_string

    def stop_engine_if_working(self) -> None:
        if self.__engine_is_working:
            self.engine.stop()

    def __start_stop_engine(self) -> None:
        if self.__engine_is_working:
            self.engine.stop()
            self.button_start_stop.setText("Start")
        else:
            self.engine.run()
            self.button_start_stop.setText("Stop")
        self.__engine_is_working = not self.__engine_is_working

    def __add_gear_at_layout(self, gear_name: str) -> None:
        layout = QHBoxLayout()

        self.gear_label = QLabel("Gear:")
        self.gear_widget = QLineEdit(gear_name)
        self.gear_widget.setReadOnly(True)

        layout.addWidget(self.gear_label)
        layout.addWidget(self.gear_widget)

        self.__layout.addLayout(layout)

    def __add_filter_at_layout(self, filter_description: str) -> None:
        layout = QHBoxLayout()

        self.filter_label = QLabel("Filter(s):")
        self.filter = QLineEdit(filter_description)
        self.filter.setReadOnly(True)

        layout.addWidget(self.filter_label)
        layout.addWidget(self.filter)
        self.__layout.addLayout(layout)

    def __show_settings(self) -> None:
        setting_widget = GearOptionsWidget(
            self.gear, self.__docstring_dict, parent=self
        )
        setting_widget.exec_()
