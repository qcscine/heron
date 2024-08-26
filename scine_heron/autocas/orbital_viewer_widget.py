#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional

from PySide2.QtWidgets import QFileDialog, QPushButton, QVBoxLayout, QWidget

# from scine_heron.autocas.autocas_settings import AutocasSettings
# from scine_heron.autocas.signal_handler import SignalHandler
# from scine_heron.electronic_data.molden_file_reader import MoldenFileReader
from scine_heron.molecule.molecule_widget import MoleculeWidget
from scine_heron.settings.settings_status_manager import SettingsStatusManager
from scine_heron.status_manager import StatusManager

from pathlib import Path


class OrbitalViewerWidget(QWidget):
    def __init__(self, parent, signal_handler, autocas_settings):
        QWidget.__init__(self, parent)
        self.__layout = QVBoxLayout()

        self.signal_handler = signal_handler
        self.autocas_settings = autocas_settings
        self.signal_handler.load_xyz_file_signal.connect(self.__load_molecule)
        self.signal_handler.load_molden_file_signal.connect(self.__load_orbitals)
        self.signal_handler.view_orbital.connect(self.__view_orbital)

        self.molecule_widget = QWidget(self)
        self.settings_status_manager = SettingsStatusManager()  # Settings())
        self.__enabled = StatusManager(True)

        self.__layout.addWidget(self.molecule_widget)

        self.button_load_molecule = QPushButton("Load Molecule")
        self.__layout.addWidget(self.button_load_molecule)
        # pylint: disable-next=E1101
        self.button_load_molecule.clicked.connect(self.__load_molecule)

        self.orbital_file = ""
        self.button_load_orbitals = QPushButton("Load Orbitals")
        self.__layout.addWidget(self.button_load_orbitals)
        # pylint: disable-next=E1101
        self.button_load_orbitals.clicked.connect(self.__load_orbitals)

        self.setLayout(self.__layout)

    def set_enabled(self, enabled: bool) -> None:
        """
        Set widgets enabled.
        """
        self.__enabled.value = enabled

    def __load_molecule(self, xyz_file: str = ""):
        # print("initial XYZ File", xyz_file)
        if xyz_file:
            self.autocas_settings.molecule_xyz_file = xyz_file
        else:
            self.autocas_settings.molecule_xyz_file, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("Open XYZ File"),  # type: ignore[arg-type]
                "",
                self.tr("Molecule (*.xyz)"),  # type: ignore[arg-type]
            )
            # print("Loading XYZ file")
            # print(self.autocas_settings.molecule_xyz_file)
        old_widget = self.molecule_widget
        self.molecule_widget = MoleculeWidget(
            settings_status_manager=self.settings_status_manager,
            parent=self,
            disable_modification=True,
            file=Path(self.autocas_settings.molecule_xyz_file),
        )

        self.layout().replaceWidget(old_widget, self.molecule_widget)

    def __load_orbitals(self, orbital_file: Optional[str] = None):
        if not isinstance(self.molecule_widget, MoleculeWidget):
            # print("No molecular structure available. Loading now!")
            self.__load_molecule(self.autocas_settings.molecule_xyz_file)
        if orbital_file:
            self.orbital_file = orbital_file
        else:
            self.orbital_file, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("Open Orbital File"),  # type: ignore[arg-type]
                "",
                self.tr("Molden file (*.molden)"),  # type: ignore[arg-type]
            )
            # print("Loading Molden file")
            # print(self.orbital_file)
        self.autocas_settings.molcas_orbital_file = self.orbital_file
        with open(self.orbital_file) as f:
            lines = f.read()

        self.molecule_widget.get_electronic_data_widget().read_molden_input(lines)
        self.autocas_settings.orbital_energies = self.molecule_widget.get_electronic_data_widget()\
            .get_electronic_data().get_orbital_energies()
        self.autocas_settings.orbital_occupations = self.molecule_widget.get_electronic_data_widget()\
            .get_electronic_data().get_occupations()
        self.signal_handler.update_mo_diagram.emit()
        self.molecule_widget.get_electronic_data_widget().view_orbital(5)

    def __view_orbital(self, index):
        self.molecule_widget.get_electronic_data_widget().view_orbital(index)

        # self.settings_status_manager.selected_mo_changed.emit(6)
        # self.molecule_widget.update()
        # self.settings_status_manager.selected_molecular_orbital = 4
        # self.__enabled.changed_signal.connect(self.button_load_orbitals.setEnabled)
        self.molecule_widget.update()
