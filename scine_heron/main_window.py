#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the MainWindow class.
"""
import os

from pathlib import Path
from typing import Any, Optional, Union, Tuple
from PySide2.QtCore import Qt, QObject, QSettings
from PySide2.QtWidgets import QMainWindow, QApplication, QWidget
from PySide2.QtGui import QCloseEvent, QIcon

import scine_utilities as su

from scine_heron.toolbar.mo_toolbar import MOToolbar
from scine_heron.molecular_viewer import MolecularViewerWidget

from scine_heron.io.text_box import yes_or_no_question
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
            method_family: Optional[str] = None,
            program: Optional[str] = None,
            db_credentials: Optional[Tuple[str, str, int]] = None,
            connect_with_db: bool = False
    ):
        QMainWindow.__init__(self, parent)

        # remember some basic stuff
        self.resize(1280, 1024)
        self.settings = QSettings("Scine", "Heron")
        if self.settings.contains("size"):
            self.resize(self.settings.value("size"))  # type: ignore
        if self.settings.contains("position"):
            self.move(self.settings.value("position"))  # type: ignore

        self.setWindowTitle(self.tr("SCINE Heron"))  # type: ignore[arg-type]

        # connect haptic device
        self.__haptic_client = HapticClient()
        self.__haptic_client.init_haptic_device()
        self.__server_process = ServerProcess()

        self.__central_widget = CentralWidget(self, haptic_client=self.__haptic_client, method_family=method_family,
                                              program=program)
        self.setCentralWidget(self.__central_widget)

        self.__status_bar = StatusBar(self)
        self.__central_widget.mol_view_tab.settings_status_manager.error_update.connect(
            lambda msg: self.__status_bar.update_error_status(msg, clear_status=True)
        )
        self.__central_widget.mol_view_tab.settings_status_manager.info_update.connect(
            self.__status_bar.update_status
        )
        self.setStatusBar(self.__status_bar)

        self.toolbar = IOToolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        # add function to DB connection symbol
        self.toolbar.connect_db_signal.connect(
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
        # add function to history button
        self.mo_toolbar.display_history.connect(
            self.__central_widget.mol_view_tab.show_history
        )
        # change update button symbol when signal is emitted
        self.mo_toolbar.toggle_updates_signal.connect(
            self.__continuous_updates_sanity_check
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
        QApplication.instance().aboutToQuit.connect(
            self.__save_settings
        )
        QApplication.instance().aboutToQuit.connect(
            lambda: self.__central_widget.chemoton_tab.closeEvent(QCloseEvent())
        )
        QApplication.instance().aboutToQuit.connect(
            lambda: self.__central_widget.steering_tab.closeEvent(QCloseEvent())
        )
        QApplication.instance().aboutToQuit.connect(
            self.__exit_handling
        )

        if file_name is not None:
            self.display_molecule_from_file(file_name)
        if atom_collection is not None:
            self.display_molecule_from_atom_collection(atom_collection, bond_orders)
        if db_credentials is not None:
            self.set_database_credentials(*db_credentials)
            if connect_with_db:
                self.toolbar.db_connection(silently=True)

    def __continuous_updates_sanity_check(self):
        value = self.__central_widget.mol_view_tab.basic_settings_widget.is_enabled()
        if value and self.__central_widget.mol_view_tab.basic_settings_widget.get_mediator_active():
            calc = self.__central_widget.mol_view_tab.create_calculator_widget.get_calculator()
            if su.Property.AtomicHessians not in calc.get_possible_properties():
                warning = "The current calculator does not support atomic Hessian, " \
                    + "hence the mediator potential requires a full Hessian, which might be slower, " \
                    + "or depending on the calculator even give wrong results. " \
                    + "Do you want to activate the updates still"
                activate = yes_or_no_question(self, warning)
                if not activate:
                    return
        # execute all the things connected with the automatic updates
        self.__update_server_process()
        self.__central_widget.mol_view_tab.toggle_automatic_updates()
        self.mo_toolbar.show_updates_enabled(value)
        self.__central_widget.mol_view_tab.configure_main_widget_updates(value)
        self.__central_widget.mol_view_tab.basic_settings_widget.set_enabled(not value)
        self.__central_widget.mol_view_tab.edit_molecule_widget.set_enabled(not value)
        self.__central_widget.mol_view_tab.create_calculator_widget.toggle_editable()

    def __save_settings(self) -> None:
        self.settings.setValue("size", self.size())
        self.settings.setValue("position", self.pos())

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
        self.toolbar.generate_db_manager(name, ip, port)

    def reject(self) -> None:
        self.__exit_handling()
        super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.__exit_handling()
        super().closeEvent(event)
        QApplication.instance().closeAllWindows()

    def __exit_handling(self):
        # Stop automatic updates of the molecule
        self.__server_process.terminate()
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
        elif tab_identifier == 'readuct':
            return self.__central_widget.readuct_tab
        elif tab_identifier == 'network_viewer':
            return self.__central_widget.db_network_tab
        elif tab_identifier == 'molecule_viewer':
            return self.__central_widget.mol_view_tab
        elif tab_identifier == 'autocas':
            return self.__central_widget.autocas_tab
        elif tab_identifier == 'chemoton':
            return self.__central_widget.chemoton_tab
        elif tab_identifier == 'steering':
            return self.__central_widget.steering_tab
        return None

    def get_reaction_template_storage(self):
        return self.toolbar.template_storage

    def get_status_bar(self) -> StatusBar:
        return self.__status_bar
