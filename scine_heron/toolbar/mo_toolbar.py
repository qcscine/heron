#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the IOToolbar class.
"""

import os

from scine_heron.resources import resource_path

from PySide2.QtGui import QKeySequence, QIcon
from PySide2.QtWidgets import (
    QAction,
    QStyle,
    QToolBar,
    QFileDialog,
    QWidget,
)
from pathlib import Path
from typing import Optional, Any, Callable, TYPE_CHECKING
from PySide2.QtCore import QObject
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


class HeronToolBar(QToolBar):
    """
    Simplifying some interaction with the QToolBar
    """

    def __init__(self, parent: Optional[QObject] = None):
        super(HeronToolBar, self).__init__(parent=parent)

    def shortened_add_action(self, icon, text: str, shortcut: str, function: Callable) -> QAction:
        if shortcut == '':
            description_string = f'{text}</p>'
        else:
            q_shortcut = QKeySequence(shortcut)
            description_string = f'{text} ({q_shortcut.toString()})</p>'
        if isinstance(icon, str):
            icon = QIcon(os.path.join(resource_path(), 'icons', icon))
        else:
            icon = self.style().standardIcon(icon)
        action = self.addAction(
            icon,
            self.tr(f'<p style="color:black !important;">'  # type: ignore[arg-type]
                    f'{description_string}'),  # type: ignore[arg-type]
        )
        if shortcut != '':
            action.setShortcut(q_shortcut)
        action.triggered.connect(function)  # pylint: disable=no-member

        return action


class MOToolbar(HeronToolBar):
    """
    A toolbar with a load and a save button.
    """
    load_file_signal = Signal(Path)
    save_file_signal = Signal(Path)
    save_trajectory_signal = Signal(Path)
    back_signal = Signal()
    connect_db_signal = Signal(QWidget, QWidget, QWidget, QWidget, QWidget)
    toggle_updates_signal = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super(MOToolbar, self).__init__(parent=parent)
        self.db_manager: Optional[Any] = None

        self.shortened_add_action(QStyle.SP_DialogOpenButton, "Load Molecule", "Ctrl+O", self.__load_file)
        self.__save_mol = self.shortened_add_action(
            "save_molecule.png", "Save Molecule", "Ctrl+S", self.__save_file)
        self.__save_trj = self.shortened_add_action("save_trajectory.png", "Save Trajectory",
                                                    "Ctrl+Shift+S", self.__save_trajectory_file)
        self.__loop = self.shortened_add_action(QStyle.SP_MediaPlay, "Start updating positions with Sparrow", "Ctrl+F",
                                                self.__calc_gradient_in_loop)
        self.__loop.setCheckable(True)
        self.__revert = self.shortened_add_action(QStyle.SP_MediaSeekBackward, "Revert last frames",
                                                  "Ctrl+Z", self.__revert_frames)
        self.__loop.setEnabled(False)
        self.__save_mol.setEnabled(False)
        self.__save_trj.setEnabled(False)
        self.__revert.setEnabled(False)
        self.__automatic_updates = False

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

    def __save_trajectory_file(self) -> None:
        """
        Save trajectory to file.
        """
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save File"),  # type: ignore[arg-type]
            "trajectory.xyz",
            self.tr("Trajectory (*.xyz *.bin )"),  # type: ignore[arg-type]
        )

        if filename:
            self.save_trajectory_signal.emit(Path(filename))

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
