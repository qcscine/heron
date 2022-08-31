#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the CentralWidget class.
"""

from PySide2.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PySide2.QtCore import QObject
from scine_heron.molecular_viewer import MolecularViewerWidget
from pkgutil import iter_modules
from typing import Optional


class CentralWidget(QWidget):
    """
    Sets up the central set of tabs.
    """

    def __init__(self, parent: QObject, haptic_client):
        QWidget.__init__(self, parent)
        self.__layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.mol_view_tab = MolecularViewerWidget(self.tabs, haptic_client=haptic_client)
        self.autocas_tab = QWidget()  # empty for now
        self.db_network_tab = QWidget()  # Empty, populated when DB is connected
        self.db_stats_tab = QWidget()  # Empty, populated when DB is connected
        self.db_viewer_tab = QWidget()  # Empty, populated when DB is connected
        self.chemoton_tab = QWidget()  # Empty, populated when DB is connected
        self.kinetic_exploration_tab = QWidget()  # Empty, populated when DB is connected
        # Add tabs
        self.tabs.addTab(self.mol_view_tab, "Molecular Viewer")
        self.tabs.addTab(self.autocas_tab, "AutoCAS")
        self.tabs.addTab(self.db_network_tab, "Reaction Network")
        self.tabs.addTab(self.db_stats_tab, "Network Statistics")
        self.tabs.addTab(self.db_viewer_tab, "Database Viewer")
        self.tabs.addTab(self.chemoton_tab, "Chemoton")
        self.tabs.addTab(self.kinetic_exploration_tab, "Kinetic Driven Exploration")
        # Disable tabs
        if "autocas" in (name for _, name, _ in iter_modules()):
            self.tabs.setTabEnabled(1, False)
            self.tabs.setTabVisible(1, False)
            # TODO enable upon AutoCAS release and tab completion
            # self.autocas_tab = QWidget()
            # self.tabs.removeTab(1)
            # self.tabs.insertTab(1, self.autocas_tab, "AutoCAS")
        else:
            self.tabs.setTabEnabled(1, False)
            self.tabs.setTabVisible(1, False)
        self.tabs.setTabVisible(2, False)
        self.tabs.setTabVisible(3, False)
        self.tabs.setTabVisible(4, False)
        self.tabs.setTabVisible(5, False)
        self.tabs.setTabVisible(6, False)
        self.tabs.setTabEnabled(2, False)
        self.tabs.setTabEnabled(3, False)
        self.tabs.setTabEnabled(4, False)
        self.tabs.setTabEnabled(5, False)
        self.tabs.setTabEnabled(6, False)
        # Add tabs to widget
        self.__layout.addWidget(self.tabs)
        self.setLayout(self.__layout)

    def toggle_db_dependent_tabs(
        self,
        compound_reaction: Optional[QWidget],
        database_monitor: Optional[QWidget],
        database_viewer: Optional[QWidget],
        chemoton_engines: Optional[QWidget],
        kinetic_exploration: Optional[QWidget],
    ) -> None:
        """
        Toggles the automatic update status and emits
        a signal if the status changed.
        """
        current = self.tabs.currentIndex()
        if compound_reaction is not None:
            compound_reaction.setParent(self.tabs)
            self.db_network_tab = compound_reaction
            self.tabs.removeTab(2)
            self.tabs.insertTab(2, self.db_network_tab, "Reaction Network")
            self.tabs.setTabEnabled(2, True)
            self.tabs.setTabVisible(2, True)
        else:
            self.tabs.setTabEnabled(2, False)
            self.tabs.setTabVisible(2, False)

        if database_monitor is not None:
            database_monitor.setParent(self.tabs)
            self.db_stats_tab = database_monitor
            self.tabs.removeTab(3)
            self.tabs.insertTab(3, self.db_stats_tab, "Network Statistics")
            self.tabs.setTabEnabled(3, True)
            self.tabs.setTabVisible(3, True)
        else:
            self.tabs.setTabEnabled(3, False)
            self.tabs.setTabVisible(3, False)

        if database_viewer is not None:
            database_viewer.setParent(self.tabs)
            self.db_viewer_tab = database_viewer
            self.tabs.removeTab(4)
            self.tabs.insertTab(4, self.db_viewer_tab, "Database Viewer")
            self.tabs.setTabEnabled(4, True)
            self.tabs.setTabVisible(4, True)
        else:
            self.tabs.setTabEnabled(4, False)
            self.tabs.setTabVisible(4, False)

        if chemoton_engines is not None:
            chemoton_engines.setParent(self.tabs)
            self.chemoton_tab = chemoton_engines
            self.tabs.removeTab(5)
            self.tabs.insertTab(5, self.chemoton_tab, "Chemoton")
            self.tabs.setTabEnabled(5, True)
            self.tabs.setTabVisible(5, True)
        else:
            self.tabs.setTabEnabled(5, False)
            self.tabs.setTabVisible(5, False)

        if kinetic_exploration is not None:
            kinetic_exploration.setParent(self.tabs)
            self.kinetic_exploration_tab = kinetic_exploration
            self.tabs.removeTab(6)
            self.tabs.insertTab(6, self.kinetic_exploration_tab, "Kinetics-Driven Exploration")
            self.tabs.setTabEnabled(6, True)
            self.tabs.setTabVisible(6, True)
        else:
            self.tabs.setTabEnabled(6, False)
            self.tabs.setTabVisible(6, False)
        self.tabs.setCurrentIndex(current)
