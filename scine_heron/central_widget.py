#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the CentralWidget class.
"""

from PySide2.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PySide2.QtCore import QObject
from scine_heron.molecular_viewer import MolecularViewerWidget
from scine_heron.utilities import module_available
from typing import Optional


class CentralWidget(QWidget):
    """
    Sets up the central set of tabs.
    """

    def __init__(self, parent: QObject, haptic_client, method_family: Optional[str] = None,
                 program: Optional[str] = None):
        QWidget.__init__(self, parent)
        self.__layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.mol_view_tab = MolecularViewerWidget(self.tabs, haptic_client=haptic_client, method_family=method_family,
                                                  program=program)
        self.readuct_tab = QWidget()  # populated if ReaDuct is installed
        self.autocas_tab = QWidget()  # empty for now
        self.db_network_tab = QWidget()  # Empty, populated when DB is connected
        self.db_stats_tab = QWidget()  # Empty, populated when DB is connected
        self.db_viewer_tab = QWidget()  # Empty, populated when DB is connected
        self.chemoton_tab = QWidget()  # Empty, populated when DB is connected
        self.steering_tab = QWidget()  # Empty, populated when DB is connected
        self.kinetic_exploration_tab = QWidget()  # Empty, populated when DB is connected
        # Add tabs
        self.tabs.addTab(self.mol_view_tab, "Interactive")
        self.tabs.addTab(self.readuct_tab, "ReaDuct")
        self.tabs.addTab(self.autocas_tab, "AutoCAS")
        self.tabs.addTab(self.db_network_tab, "Reaction Network")
        self.tabs.addTab(self.db_stats_tab, "Network Statistics")
        self.tabs.addTab(self.db_viewer_tab, "Database Viewer")
        self.tabs.addTab(self.chemoton_tab, "Chemoton")
        self.tabs.addTab(self.steering_tab, "Steering Chemoton")
        self.tabs.addTab(self.kinetic_exploration_tab, "Kinetic Driven Exploration")
        # Disable tabs
        if module_available("scine_readuct"):
            from scine_heron.readuct.readuct_tab import ReaductTab
            self.readuct_tab = ReaductTab(self.tabs)
            self.tabs.removeTab(1)
            self.tabs.insertTab(1, self.readuct_tab, "Readuct")
        else:
            self.tabs.setTabEnabled(1, False)
            self.tabs.setTabVisible(1, False)
        if module_available("scine_autocas"):
            from scine_heron.autocas.autocas_widget import AutocasWidget
            self.autocas_tab = AutocasWidget(self.tabs)
            self.tabs.removeTab(2)
            self.tabs.insertTab(2, self.autocas_tab, "AutoCAS")
        else:
            self.tabs.setTabEnabled(2, False)
            self.tabs.setTabVisible(2, False)
        for i in range(3, 9):
            self.tabs.setTabVisible(i, False)
            self.tabs.setTabEnabled(i, False)
        # Add tabs to widget
        self.__layout.addWidget(self.tabs)
        self.setLayout(self.__layout)

    def toggle_db_dependent_tabs(
        self,
        compound_reaction: Optional[QWidget],
        database_monitor: Optional[QWidget],
        database_viewer: Optional[QWidget],
        chemoton_engines: Optional[QWidget],
        steering_wheel: Optional[QWidget],
        kinetic_exploration: Optional[QWidget],
    ) -> None:
        """
        Toggles the automatic update status and emits
        a signal if the status changed.
        """
        shift = int(module_available('scine_readuct')) + int(module_available("scine_autocas"))
        current = self.tabs.currentIndex()

        for index, (tab, member_attr, name) in enumerate(zip(
                [compound_reaction, database_monitor, database_viewer, chemoton_engines, steering_wheel,
                 kinetic_exploration],
                ["db_network_tab", "db_stats_tab", "db_viewer_tab", "chemoton_tab", "steering_tab",
                 "kinetic_exploration_tab"],
                ["Reaction Network", "Network Statistics", "Database Viewer", "Chemoton", "Steering Chemoton",
                 "Kinetics-Driven Exploration"]), 1 + shift):  # 1 because of Interactive
            if tab is not None:
                tab.setParent(self.tabs)
                setattr(self, member_attr, tab)
                self.tabs.removeTab(index)
                self.tabs.insertTab(index, tab, name)
                self.tabs.setTabEnabled(index, True)
                self.tabs.setTabVisible(index, True)
            else:
                self.tabs.setTabEnabled(index, False)
                self.tabs.setTabVisible(index, False)

        self.tabs.setCurrentIndex(current)
