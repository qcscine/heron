#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the MolecularViewerWidget class.
"""

from pathlib import Path
from time import sleep
from typing import Any, Optional, List, TYPE_CHECKING
import PySide2
from PySide2.QtWidgets import (
    QWidget,
    QSplitter,
    QCheckBox,
    QVBoxLayout,
    QScrollArea,
    QScrollBar,
)
from PySide2.QtCore import QObject, QSize, QThread

import scine_utilities as utils

from scine_heron import get_core_tab
from scine_heron.calculators.create_calculator_widget import CreateCalculatorWidget
from scine_heron.molecule.molecule_widget import MoleculeWidget
from scine_heron.molecule.molecule_writer import write_molecule_to_file, write_trajectory_to_file
from scine_heron.edit_molecule.edit_molecule_widget import EditMoleculeWidget
from scine_heron.energy_profile.energy_profile_widget import EnergyProfileWidget
from scine_heron.settings.settings_status_manager import SettingsStatusManager
from scine_heron.settings.basic_settings_widget import BasicSettingsWidget
from scine_heron.status_manager import StatusManager
from scine_heron.haptic.haptic_client import HapticClient
from scine_heron.molecule.molecule_video import MoleculeVideoWithEnergyDialog
from scine_heron.utilities import thread_safe_error

if TYPE_CHECKING:
    Slot = Any
else:
    from PySide2.QtCore import Slot


class MolecularViewerWidget(QWidget):
    """
    Sets up a tab for molecular views.
    """
    settings_widget_layout = None

    def __init__(self, parent: QObject, haptic_client: HapticClient, method_family: Optional[str] = None,
                 program: Optional[str] = None):
        QWidget.__init__(self, parent)

        self.mol_widget: Optional[MoleculeWidget] = None
        self.__layout = QVBoxLayout()

        self.__haptic_client = haptic_client
        self.__trajectory_writer: Optional[TrajectoryWriter] = None

        self._settings_scroll_area = QScrollArea()
        self.vscrollbar = QScrollBar()
        self.create_calculator_widget = CreateCalculatorWidget(parent=self, method_family=method_family,
                                                               program=program)

        self.settings_status_manager = SettingsStatusManager(
            settings_change_signal=self.create_calculator_widget.settings_changed_signal
        )
        self.create_calculator_widget.emit_signal()
        self.visible = False
        self.basic_settings_widget = BasicSettingsWidget(self.settings_status_manager)
        self.basic_settings_widget.setMaximumWidth(300)

        # Edit Molecule - Add and remove atoms
        self.edit_molecule_widget = EditMoleculeWidget()
        self.edit_molecule_widget.setMaximumWidth(300)
        self.edit_molecule_widget.addAtom.connect(self.__add_atom_default_position)
        self.edit_molecule_widget.removeSelectedAtom.connect(self.__remove_selected_atoms)
        self.edit_molecule_widget.setVisible(False)

        self.hidden_button = QCheckBox("Edit Molecule Options")
        self.hidden_button.setFixedSize(QSize(320, 30))
        self.hidden_button.setChecked(False)
        self.hidden_button.toggled.connect(self.set_visible)  # pylint: disable=no-member

        self.energy_profile_widget = EnergyProfileWidget()

        self.continuously_update_positions = StatusManager(False)
        self.file_loaded = StatusManager(False)

        self.settings_widget: Optional[QWidget] = None
        self.create_molecule_widget(empty=True)

        self.settings_status_manager.opaque_signal.connect(
            self.__propagate_opacity
        )
        self.settings_status_manager.hamiltonian_changed.connect(
            self.deactivate_automatic_updates
        )

    def create_molecule_widget(
        self,
        file: Optional[Path] = None,
        atom_collection: Optional[Any] = None,
        bond_orders: Optional[Any] = None,
        empty: bool = False
    ) -> None:
        """
        Create molecule widget.
        """
        if file is None and atom_collection is None and not empty:
            self.settings_status_manager.error_message = "No Structure input provided."
            return
        if file is not None and atom_collection is not None:
            self.settings_status_manager.error_message = (
                "Cannot specify both AtomCollection and file to read."
            )
            return
        if file is not None and not file.exists():
            self.settings_status_manager.error_message = (
                "The input xyz file does not exist."
            )
            return
        if atom_collection is not None and len(atom_collection) == 0:
            self.settings_status_manager.error_message = (
                "The input AtomCollection is empty."
            )
            return

        self.deactivate_automatic_updates()
        self.__clean()

        # Update or add new widget
        if self.mol_widget is not None:
            self.mol_widget.update_molecule(
                file=file,
                atoms=atom_collection,
                bonds=bond_orders
            )
        else:
            self.mol_widget = MoleculeWidget(
                self.settings_status_manager,
                parent=self,
                file=file,
                atoms=atom_collection,
                bonds=bond_orders,
                haptic_client=self.__haptic_client,
                energy_status_manager=self.energy_profile_widget.energy_status_manager,
            )
            self.mol_widget.setMaximumHeight(2048)
            self.__fill_layout()

        if self.mol_widget.has_atoms():
            self.file_loaded.value = True
        else:
            self.file_loaded.value = False

        self.__trajectory_writer = TrajectoryWriter(self.mol_widget)
        self.__trajectory_writer.start()

    def update_molecule(
        self,
        file: Optional[Path] = None,
        atoms: Optional[object] = None,
        bonds: Optional[object] = None
    ):
        if self.mol_widget is not None:
            self.mol_widget.update_molecule(file=file, atoms=atoms, bonds=bonds)
            if self.mol_widget.has_atoms():
                self.file_loaded.value = True
            else:
                self.file_loaded.value = False

    def __fill_layout(self) -> None:
        vertical_splitter = QSplitter()
        vertical_splitter.setOrientation(PySide2.QtCore.Qt.Vertical)
        if self.mol_widget is None:
            vertical_splitter.addWidget(QWidget())
        else:
            vertical_splitter.addWidget(self.mol_widget)
        vertical_splitter.addWidget(self.energy_profile_widget)

        self.settings_widget = QWidget()

        MolecularViewerWidget.settings_widget_layout = QVBoxLayout()
        MolecularViewerWidget.settings_widget_layout.addWidget(self.basic_settings_widget)
        MolecularViewerWidget.settings_widget_layout.addWidget(self.create_calculator_widget)
        MolecularViewerWidget.settings_widget_layout.addWidget(self.hidden_button)
        MolecularViewerWidget.settings_widget_layout.addWidget(self.edit_molecule_widget)

        assert self.settings_widget_layout is not None
        self.settings_widget.setLayout(self.settings_widget_layout)

        self._settings_scroll_area.setWidget(self.settings_widget)
        self._settings_scroll_area.setWidgetResizable(True)
        self._settings_scroll_area.setHorizontalScrollBarPolicy(PySide2.QtCore.Qt.ScrollBarAlwaysOff)
        self.vscrollbar = self._settings_scroll_area.verticalScrollBar()
        self.vscrollbar.rangeChanged.connect(self.scroll)

        horizontal_splitter = QSplitter()
        horizontal_splitter.addWidget(vertical_splitter)
        horizontal_splitter.addWidget(self._settings_scroll_area)
        horizontal_splitter.setSizes([500, 300])

        self.__layout.addWidget(horizontal_splitter)
        self.setLayout(self.__layout)
        self.show()
        self.set_visible()

    def set_visible(self) -> None:
        self.visible = self.hidden_button.isChecked()
        self.edit_molecule_widget.setVisible(self.visible)
        if self.settings_widget is not None:
            self.settings_widget.updateGeometry()
        self.updateGeometry()

    @Slot(int, int)
    def scroll(self, minimum, maximum):
        value = maximum if self.visible else minimum
        self.vscrollbar.setValue(value)

    def save_molecule(self, file: Path) -> None:
        """
        Save molecule in a xyz file.
        """
        if self.mol_widget is not None:
            write_molecule_to_file(
                self.mol_widget.provide_data(), file
            )

    def show_history(self):
        if self.__layout.count() > 0 and self.__trajectory_writer is not None:
            trajectory = self.__trajectory_writer.get_trajectory()
            MoleculeVideoWithEnergyDialog(self, trajectory)

    def save_trajectory(self, file: Path) -> None:
        """
        Save trajectory in a xyz file.
        """
        if self.__layout.count() > 0 and self.__trajectory_writer is not None:
            traj = self.__trajectory_writer.get_trajectory()
            write_trajectory_to_file(traj, file)

    def revert_frames(self, n_frames: int = 25) -> None:
        """
        Reverts last n frames
        """
        if self.__layout.count() > 0 and self.__trajectory_writer is not None and self.mol_widget is not None:
            self.__trajectory_writer.pause()
            traj = self.__trajectory_writer.get_trajectory()
            n_back = min(n_frames, len(traj) - 1)
            wanted_frame = traj[-n_back]
            atoms = utils.AtomCollection(traj.elements, wanted_frame)
            # delete all frames after the wanted one
            # slices not supported in python bindings of delitem of trajectory when writing this
            for _ in range(n_back):
                del traj[-1]
            self.mol_widget.update_molecule(atoms=atoms)
            self.__trajectory_writer.unpause()

    def stop_trajectory_writing(self):
        if self.__trajectory_writer is not None:
            self.__trajectory_writer.cancel()

    def configure_main_widget_updates(self, status: bool) -> None:
        """
        Sets the state of automatic updates in the main widget.
        """
        if self.mol_widget is not None:
            self.mol_widget.set_calc_gradient_in_loop(status)

    def toggle_automatic_updates(self) -> None:
        """
        Toggles the automatic update status and emits
        a signal if the status changed.
        """
        self.continuously_update_positions.value = (
            not self.continuously_update_positions.value
        )

    def deactivate_automatic_updates(self) -> None:
        """
        Sets the automatic updates to enabled/disabled and emits
        a signal if the status changed.
        """
        if not self.continuously_update_positions.value:
            return

        self.continuously_update_positions.value = False

    def __clean(self) -> None:
        """
        Delete old widget.
        """
        if self.__trajectory_writer is not None:
            self.__trajectory_writer.cancel()

    def __add_atom_default_position(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.settings_status_manager.selected_molecular_orbital = None
        if self.mol_widget is None:
            self.create_molecule_widget(empty=True)
            self.file_loaded.value = False
        if self.mol_widget is not None:
            self.mol_widget.add_atom_default_position(*args, **kwargs)
            self.file_loaded.value = True

    def __remove_selected_atoms(self) -> None:
        if self.mol_widget is None:
            return
        self.settings_status_manager.selected_molecular_orbital = None
        self.mol_widget.remove_selected_atoms()
        if not self.mol_widget.has_atoms():
            self.file_loaded.value = False

    def __propagate_opacity(self, opaque_indices: List[int], exclude_mode: bool = False) -> None:
        if self.mol_widget is None:
            return
        self.mol_widget.make_indices_opaque(opaque_indices, exclude_mode)


class TrajectoryWriter(QThread):

    def __init__(self, parent: Optional[MoleculeWidget] = None):
        super(TrajectoryWriter, self).__init__(parent)
        self._was_canceled = False
        self._was_paused = False
        self._sleep_time = 0.1
        self._trajectory = utils.MolecularTrajectory(minimum_rmsd_for_addition=0.01)  # type: ignore
        if parent is not None:
            atoms = parent.get_atom_collection()
            self._trajectory.elements = atoms.elements
            self._trajectory.push_back(atoms.positions, energy=float('inf'))

    def get_trajectory(self):
        return self._trajectory

    def cancel(self):
        self._was_canceled = True
        sleep(2 * self._sleep_time)

    def pause(self):
        self._was_paused = True

    def unpause(self):
        self._was_paused = False

    def run(self):
        while not self._was_canceled:
            sleep(self._sleep_time)
            while self._was_paused:
                sleep(0.1 * self._sleep_time)
            atoms = self.parent().get_atom_collection()
            if atoms.size() == 0:
                continue
            energy = self.parent().get_energy()
            if atoms.elements != self._trajectory.elements:
                # restart if molecule was changed
                self._trajectory.clear()
                self._trajectory.elements = atoms.elements
            if energy is not None:
                self._trajectory.push_back(atoms.positions, energy=energy)
            else:
                self._trajectory.push_back(atoms.positions, energy=float('inf'))
        self.exit(0)


def get_mol_viewer_tab(want_atoms_there: bool, message_container: Optional[List[str]] = None) \
        -> Optional[MolecularViewerWidget]:
    """
    message_container avoids to directly write to status bar in case this function is called by a thread,
    list because str are copied by value
    """
    tab = get_core_tab('molecule_viewer')
    if tab is None or not isinstance(tab, MolecularViewerWidget) or tab.mol_widget is None:
        thread_safe_error("Could not find molecule viewer", message_container)
        return None
    if want_atoms_there and not tab.mol_widget.has_atoms():
        thread_safe_error("Molecule viewer does not have any molecule loaded", message_container)
        return None
    return tab
