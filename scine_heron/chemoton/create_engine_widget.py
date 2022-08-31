#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the CreateEngineWidget class.
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
from scine_database import Manager
from scine_chemoton.engine import Engine  # pylint: disable=import-error
from scine_heron.chemoton.engines_widget import EngineWidget
from scine_heron.chemoton.gear_searcher import GearSearcher
from scine_heron.chemoton.grouped_combo_box import GroupedComboBox


class CreateEngineWidget(QWidget):
    """
    Widget that create and add new chemoton engine.
    """

    def __init__(
        self, parent: QObject, db_manager: Manager, gear_searcher: GearSearcher
    ) -> None:
        QWidget.__init__(self, parent)
        self.db_manager = db_manager
        self.gear_searcher = gear_searcher

        self.__layout = QVBoxLayout()
        self.__layout.addWidget(QLabel("Add New Engine"))

        self.__add_name_at_layout()
        self.__add_gear_at_layout()
        self.__add_filter_at_layout()

        self.button_add = QPushButton("Add Engine")
        self.button_add.clicked.connect(self.generate_new_engine_widget)  # pylint: disable=no-member
        self.__layout.addWidget(self.button_add)

        self.setLayout(self.__layout)
        self.setMaximumWidth(300)
        self.setMinimumWidth(300)
        self.setMaximumHeight(200)
        self.setMinimumHeight(200)

    def __add_gear_at_layout(self) -> None:
        layout = QHBoxLayout()

        self.gear_label = QLabel("Gear:")
        self.gear = GroupedComboBox(self, self.gear_searcher)

        layout.addWidget(self.gear_label)
        layout.addWidget(self.gear)
        self.__layout.addLayout(layout)

    def __add_filter_at_layout(self) -> None:
        layout = QHBoxLayout()

        self.filter_label = QLabel("Filter:")
        self.filter = QLineEdit("None")
        self.button_set_filter = QPushButton("Set Filter")

        layout.addWidget(self.filter_label)
        layout.addWidget(self.filter)
        layout.addWidget(self.button_set_filter)
        self.__layout.addLayout(layout)

    def __add_name_at_layout(self) -> None:
        layout = QHBoxLayout()

        self.name_label = QLabel("Name:")
        self.name = QLineEdit("MyEngine")

        layout.addWidget(self.name_label)
        layout.addWidget(self.name)
        self.__layout.addLayout(layout)

    def generate_new_engine_widget(self) -> None:
        gear_name = self.gear.currentText().strip()

        credentials = self.db_manager.get_credentials()
        engine = Engine(credentials)
        gear = self.gear_searcher.gears[gear_name]()
        engine.set_gear(gear)

        engine_name = self.name.text()
        if engine_name == "MyEngine":
            engine_name = gear_name

        new_widget = EngineWidget(
            self.parent(),
            engine,
            gear,
            self.name.text(),
            gear_name,
            self.filter.text(),
        )
        self.parent().add_engine(new_widget)
