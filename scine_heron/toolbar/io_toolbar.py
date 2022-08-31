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
    QToolBar,
    QErrorMessage,
    QWidget,
    QLabel,
)
from pathlib import Path
from typing import Optional, Any, Callable, TYPE_CHECKING
from pkgutil import iter_modules
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


class IOToolbar(HeronToolBar):
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
        super(IOToolbar, self).__init__(parent=parent)
        self.db_manager: Optional[Any] = None

        self.shortened_add_action("db.png", "Connect to Database", "Ctrl+D",
                                  self.__db_connection)
        self.__db_label = QLabel("Database: Unavailable")
        if "scine_database" in (name for _, name, _ in iter_modules()):
            self.__db_label.setText("Database: Disconnected")
        self.addWidget(self.__db_label)

    def generate_db_manager(self, name: str, ip: str, port: int) -> None:
        if "scine_database" in (name for _, name, _ in iter_modules()):
            import scine_database
            self.db_manager = scine_database.Manager()
            credentials = scine_database.Credentials(ip, port, name)
            self.db_manager.set_credentials(credentials)
        else:
            self.db_manager = None
            return

    def __db_connection(self) -> None:
        """
        Opens dialog to connect to a SCINE DB
        """
        if "scine_database" in (name for _, name, _ in iter_modules()):
            from scine_heron.database.monitor_widget import DatabaseMonitorWidget
            from scine_heron.database.reaction_compound_widget import CompoundReactionWidget
            from scine_heron.database.database_viewer_widget import DatabaseViewerWidget
        else:
            error_dialog = QErrorMessage(parent=self)
            error_dialog.setWindowTitle("Missing SCINE Database Wrapper")
            error_dialog.showMessage(
                "The SCINE Database Wrapper could not be detected. Connections \
                    to a SCINE Database require it to be installed.\n"
            )
            return

        from scine_heron.database.connection_dialog import DatabaseConnectionDialog

        if self.db_manager is not None:
            old_credentials = self.db_manager.get_credentials()
            old_connection = self.db_manager.is_connected()
        else:
            old_credentials = None
            old_connection = False
        self.db_manager.is_connected()
        connector = DatabaseConnectionDialog(parent=self, db_manager=self.db_manager)
        self.db_manager = connector.get_db_manager()
        new_credentials = self.db_manager.get_credentials() != old_credentials
        newly_connected = self.db_manager.is_connected() and not old_connection

        chemoton_widget = None
        # Chemoton will be disabled until further notice.
        # if "scine_chemoton" in (name for _, name, _ in iter_modules()):
        #     from scine_heron.chemoton.chemoton_engines_widget import ChemotonEnginesWidget
        #     chemoton_widget = ChemotonEnginesWidget(self, self.db_manager)
        if (self.db_manager.is_connected() and new_credentials) or newly_connected:
            kinetic_exploration_widget = None
            # Kinetix will be disabled until feature complete
            # calculations = self.db_manager.get_collection("calculations")
            # if calculations.get_one_calculation(dumps({"job.order": "kinetx_kinetic_modeling"})):
            #     kinetic_exploration_widget = KineticExplorationProgressWidget(self, self.db_manager)
            self.connect_db_signal.emit(
                CompoundReactionWidget(self, self.db_manager),
                DatabaseMonitorWidget(self, self.db_manager),
                DatabaseViewerWidget(self, self.db_manager),
                chemoton_widget,
                kinetic_exploration_widget
            )
            self.__db_label.setText("Database: Connected")
        elif self.db_manager.is_connected():
            self.__db_label.setText("Database: Connected")
        else:
            self.connect_db_signal.emit(None, None, None, None, None)
            self.__db_label.setText("Database: Disconnected")
