#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""


from .io_toolbar import HeronToolBar

from PySide2.QtWidgets import (
    QStyle,
    QFileDialog,
)
from pathlib import Path
from typing import Optional, Any, TYPE_CHECKING
from PySide2.QtCore import QObject
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal

from scine_heron import get_core_tab
from scine_heron.readuct.readuct_tab import ReaductTab
from scine_heron.utilities import write_error_message, module_available


class MOToolbar(HeronToolBar):
    """
    A toolbar with a load and a save button.
    """
    load_file_signal = Signal(Path)
    save_file_signal = Signal(Path)
    save_trajectory_signal = Signal(Path)
    back_signal = Signal()
    display_history = Signal()
    toggle_updates_signal = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super(MOToolbar, self).__init__(parent=parent)
        self.db_manager: Optional[Any] = None

        self.shortened_add_action(QStyle.SP_DialogOpenButton, "Load Molecule", "Ctrl+O", self.__load_file)
        self.__save_mol = self.shortened_add_action(
            "save_molecule.png", "Save Molecule", "Ctrl+S", self.__save_file)
        self.__save_trj = self.shortened_add_action("save_trajectory.png", "Save Trajectory",
                                                    "Ctrl+Shift+S", self.__show_history)
        self.__loop = self.shortened_add_action(QStyle.SP_MediaPlay, "Start updating positions with Sparrow", "Ctrl+F",
                                                self.__calc_gradient_in_loop)
        self.__loop.setCheckable(True)
        self.__revert = self.shortened_add_action(QStyle.SP_MediaSeekBackward, "Revert last frames",
                                                  "Ctrl+Z", self.__revert_frames)
        self.__readuct = self.shortened_add_action(QStyle.SP_ArrowForward, "Move to ReaDuct",
                                                   "Ctrl+R", self.__move_to_readuct)
        self.__readuct_available = module_available("scine_readuct")
        self.__loop.setEnabled(False)
        self.__save_mol.setEnabled(False)
        self.__save_trj.setEnabled(False)
        self.__revert.setEnabled(False)
        self.__readuct.setEnabled(False)
        self.__automatic_updates = False
        self.setMinimumWidth(3000)

    def reset_plot(self) -> None:
        from scine_heron.energy_profile.energy_profile_widget import (
            EnergyProfileWidget
        )
        ax = EnergyProfileWidget._EnergyProfileWidget__canvas._Canvas__line.axes
        ax.axis([-0.06, 0.06, -0.06, 0.06])
        EnergyProfileWidget._EnergyProfileWidget__canvas.draw()

    def __load_file(self) -> None:
        """
        Load molecule from file.
        """
        filename, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open File"),  # type: ignore[arg-type]
            "",
            self.tr("Molecule (*.xyz *.mol *.pdb)"),  # type: ignore[arg-type]
        )

        if filename:
            self.load_file_signal.emit(Path(filename))
            self.reset_plot()

    def __save_file(self) -> None:
        """
        Save molecule to file.
        """
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save File"),  # type: ignore[arg-type]
            "molecule.xyz",
            self.tr("Molecule (*.xyz *.mol *.pdb)"),  # type: ignore[arg-type]
        )

        if filename:
            self.save_file_signal.emit(Path(filename))

    def __show_history(self) -> None:
        self.display_history.emit()

    def __revert_frames(self) -> None:
        """
        Send signal to revert frames
        """
        self.back_signal.emit()

    def __calc_gradient_in_loop(self) -> None:
        """
        Start or stop calculating the gradient in an infinity loop.
        """
        self.__update_display()
        self.toggle_updates_signal.emit()

    def __update_display(self) -> None:
        """
        Updates the state of the `__loop` button.
        """
        self.__loop.setChecked(self.__automatic_updates)
        self.__loop.setIcon(
            self.style().standardIcon(QStyle.SP_MediaPause)
            if self.__automatic_updates
            else self.style().standardIcon(QStyle.SP_MediaPlay)
        )

    def __move_to_readuct(self) -> None:
        tab = get_core_tab('readuct')
        if tab is None or not isinstance(tab, ReaductTab):
            write_error_message("ReaDuct tab could not be localized")
            return
        tab.add_system_from_molecular_viewer()

    def show_updates_enabled(self, status: bool) -> None:
        """
        Display the provided automatic updates status.
        """
        if status == self.__automatic_updates:
            return

        self.__automatic_updates = status
        self.__update_display()

    def show_file_loaded(self, status: bool) -> None:
        """
        Adapt the display for a loaded file.
        """
        self.__loop.setEnabled(status)
        self.__save_mol.setEnabled(status)
        self.__save_trj.setEnabled(status)
        self.__revert.setEnabled(status)
        self.__readuct.setEnabled(status and self.__readuct_available)
