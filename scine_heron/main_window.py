#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the MainWindow class.
"""
import os

from pathlib import Path
from typing import Any, Optional, Union
from PySide2.QtCore import Qt, QObject
from PySide2.QtWidgets import QMainWindow, QApplication, QWidget
from PySide2.QtGui import QCloseEvent, QIcon

from scine_heron.toolbar.mo_toolbar import MOToolbar
from scine_heron.molecular_viewer import MolecularViewerWidget

from scine_heron.toolbar.io_toolbar import IOToolbar
from scine_heron.statusbar.status_bar import StatusBar
from scine_heron.central_widget import CentralWidget
from scine_heron.haptic.haptic_client import HapticClient
from scine_heron.mediator_potential.server_process import ServerProcess


class MainWindow(QMainWindow):
    """
    A main window with a molecule viewer and an IO toolbar.

    If file_name is not None then a molecule is loaded from this file.
    """

    def __init__(
        self,
        file_name: Optional[Path] = None,
        atom_collection: Optional[Any] = None,
        bond_orders: Optional[Any] = None,
        parent: Optional[QObject] = None,
    ):
        QMainWindow.__init__(self, parent)
        self.resize(1280, 1024)

        self.setWindowTitle(self.tr("SCINE Heron"))  # type: ignore[arg-type]

        # connect haptic device
        self.__haptic_client = HapticClient()
        self.__haptic_client.init_haptic_device()
        self.__server_process = ServerProcess()

        self.__central_widget = CentralWidget(self, haptic_client=self.__haptic_client)
        self.setCentralWidget(self.__central_widget)

        self.__status_bar = StatusBar(self)
        self.__central_widget.mol_view_tab.settings_status_manager.error_update.connect(
            self.__status_bar.update_error_status
        )
        self.__central_widget.mol_view_tab.settings_status_manager.info_update.connect(
            self.__status_bar.update_status
        )
        self.setStatusBar(self.__status_bar)

        self.__toolbar = IOToolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.__toolbar)
        # add function to DB connection symbol
        self.__toolbar.connect_db_signal.connect(
            self.__central_widget.toggle_db_dependent_tabs
        )

        self.mo_toolbar = MOToolbar(self)
        MolecularViewerWidget.settings_widget_layout.setMenuBar(self.mo_toolbar)  # type: ignore

        # add function to load button
        self.mo_toolbar.load_file_signal.connect(self.display_molecule_from_file)
        # reset energy when molecule is loaded
        self.mo_toolbar.load_file_signal.connect(
            self.__central_widget.mol_view_tab.energy_profile_widget.reset
        )
        # add function to save button
        self.mo_toolbar.save_file_signal.connect(
            self.__central_widget.mol_view_tab.save_molecule
        )
        # add function to save button
        self.mo_toolbar.save_trajectory_signal.connect(
            self.__central_widget.mol_view_tab.save_trajectory
        )
        # add function to go back
        self.mo_toolbar.back_signal.connect(
            self.__central_widget.mol_view_tab.revert_frames
        )
        # handle server when update signal is emitted
        self.mo_toolbar.toggle_updates_signal.connect(
            self.__update_server_process
        )
        # change value in mol view when update signal is emitted
        self.mo_toolbar.toggle_updates_signal.connect(
            self.__central_widget.mol_view_tab.toggle_automatic_updates
        )
        # change update button symbol when signal is emitted
        self.__central_widget.mol_view_tab.continuously_update_positions.changed_signal.connect(
            self.mo_toolbar.show_updates_enabled
        )
        self.__central_widget.mol_view_tab.continuously_update_positions.changed_signal.connect(
            self.__central_widget.mol_view_tab.configure_main_widget_updates
        )
        self.__central_widget.mol_view_tab.continuously_update_positions.changed_signal.connect(
            lambda value: self.__central_widget.mol_view_tab.basic_settings_widget.set_enabled(
                not value
            )
        )
        self.__central_widget.mol_view_tab.continuously_update_positions.changed_signal.connect(
            lambda value: self.__central_widget.mol_view_tab.advanced_settings_widget.set_enabled(
                not value
            )
        )
        self.__central_widget.mol_view_tab.file_loaded.changed_signal.connect(
            self.mo_toolbar.show_file_loaded
        )

        # end continuous functions when quitting
        QApplication.instance().aboutToQuit.connect(
            self.__central_widget.mol_view_tab.deactivate_automatic_updates
        )
        QApplication.instance().aboutToQuit.connect(
            self.__central_widget.mol_view_tab.stop_trajectory_writing
        )

        if file_name is not None:
            self.display_molecule_from_file(file_name)
        if atom_collection is not None:
            self.display_molecule_from_atom_collection(atom_collection, bond_orders)

    def __update_server_process(self) -> None:
        """
        If the server is running, stop it, otherwise start it.
        """
        if self.__server_process.is_server_running:
            self.__server_process.stop()
            self.__server_process.is_server_running = False
        else:
            self.__server_process.start()
            self.__server_process.is_server_running = True

    def display_molecule_from_file(self, file: Path) -> None:
        """
        Imports a xyz file and displays the contained molecule.
        """
        self.__central_widget.mol_view_tab.create_molecule_widget(
            file=file,
        )

    def display_molecule_from_atom_collection(
        self, atom_collection: Any, bond_orders: Optional[Any] = None
    ) -> None:
        """
        Imports an AtomCollection and displays it.
        """
        self.__central_widget.mol_view_tab.create_molecule_widget(
            atom_collection=atom_collection,
            bond_orders=bond_orders,
        )

    def set_database_credentials(self, name: str, ip: str, port: int) -> None:
        self.__toolbar.generate_db_manager(name, ip, port)

    def closeEvent(self, _: QCloseEvent) -> None:
        # Stop automatic updates of the molecule
        self.__server_process.stop()
        # Stop to save trajectory frames
        self.__central_widget.mol_view_tab.stop_trajectory_writing()
        # Disconnect haptic device
        self.__haptic_client.exit_haptic_device()

    def setIcon(self):
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, 'resources', 'heron_logo.png')
        appIcon = QIcon(filename)
        self.setWindowIcon(appIcon)

    def get_tab(self, tab_identifier: str) -> Union[QWidget, None]:
        if tab_identifier == 'database_viewer':
            return self.__central_widget.db_viewer_tab
        elif tab_identifier == 'network_viewer':
            return self.__central_widget.db_network_tab
        elif tab_identifier == 'molecule_viewer':
            return self.__central_widget.mol_view_tab
        elif tab_identifier == 'autocas':
            return self.__central_widget.autocas_tab
        elif tab_identifier == 'chemoton':
            return self.__central_widget.chemoton_tab
        return None

    def get_status_bar(self) -> StatusBar:
        return self.__status_bar
