#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional, Any, Callable, TYPE_CHECKING
from pkgutil import iter_modules
import os

from PySide2.QtGui import QKeySequence, QIcon
from PySide2.QtWidgets import (
    QAction,
    QToolBar,
    QErrorMessage,
    QWidget,
    QLabel,
    QStyle,
)
from PySide2.QtCore import QObject, QSize
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal

import scine_heron.config as config
from scine_heron.resources import resource_path
from scine_heron.toolbar.about_dialog import AboutDialog


class HeronToolBar(QToolBar):
    """
    Simplifying some interaction with the QToolBar
    """

    def __init__(self, parent: Optional[QObject] = None):
        super(HeronToolBar, self).__init__(parent=parent)

    def shortened_add_action(self, icon_cmd, text: str, shortcut: str, function: Callable) -> QAction:
        if shortcut:
            q_shortcut = QKeySequence(shortcut)
            description_string = f'{text} ({q_shortcut.toString()})</p>'
        else:
            description_string = f'{text}</p>'
        if isinstance(icon_cmd, str):
            icon = QIcon(os.path.join(resource_path(), 'icons', icon_cmd))
        else:
            icon = self.style().standardIcon(icon_cmd)

        action = self.addAction(
            icon,
            self.tr(
                f'<p>{description_string}'  # type: ignore[arg-type]
            ),
        )
        if shortcut:
            action.setShortcut(q_shortcut)
        action.triggered.connect(function)  # pylint: disable=no-member
        # the following lines are necessary due to a bug in qt-widgets
        # we have to overwrite the size and stylesheet
        # because the height is incorrectly defined for QToolButtons
        # that are part of a toolbar that is set in some widgets / layouts
        # such as the DictOptionsWidget
        tool_button = self.widgetForAction(action)
        size = tool_button.size()
        # double widths is not a typo, but chosen
        # because the height is ill-defined
        tool_button.setFixedSize(QSize(int(round(size.width() * 0.75)), int(round(size.width() * 0.75))))
        style = f"""
           QToolButton {{ background-color: none;}}
           QToolButton:hover {{ background-color: {config.COLORS['secondaryDarkColor']};}}
        """
        tool_button.setStyleSheet(style)
        self.updateGeometry()

        return action


class ToolBarWithSaveLoad(HeronToolBar):

    def __init__(self, save_call: Callable, load_call: Callable, parent: Optional[QObject] = None,
                 hover_text_save="Save Setup", hover_text_load="Save Setup"):
        super().__init__(parent=parent)

        self.shortened_add_action(
            QStyle.SP_DialogSaveButton, hover_text_save, "Ctrl+S", save_call
        )
        self.shortened_add_action(
            QStyle.SP_DialogOpenButton, hover_text_load, "Ctrl+O", load_call
        )


class IOToolbar(HeronToolBar):
    """
    A toolbar determining the possible main tabs
    """
    connect_db_signal = Signal(QWidget, QWidget, QWidget, QWidget, QWidget, QWidget)

    def __init__(self, parent: Optional[QObject] = None):
        super(IOToolbar, self).__init__(parent=parent)
        self.db_manager: Optional[Any] = None

        self.shortened_add_action("db.png", "Connect to Database", "Ctrl+D",
                                  self.db_connection)
        self.__db_label = QLabel("Database: Unavailable")
        if "scine_database" in (name for _, name, _ in iter_modules()):
            self.__db_label.setText("Database: Disconnected")
        self.addWidget(self.__db_label)
        self.shortened_add_action("db.png", "Reaction Templates", "Ctrl+T",
                                  self.__art_view)
        self.__art_label = QLabel("Reaction Templates: Unavailable")
        self.template_storage = None
        if "scine_art" in (name for _, name, _ in iter_modules()):
            from scine_heron.reaction_templates.reaction_template_storage import ReactionTemplateStorage
            self.template_storage = ReactionTemplateStorage()
            self.__art_label.setText("Reaction Templates: 0")
            self.template_storage.reaction_template_count_changed.connect(self.__update_template_count)
            self.__rtd = None
        self.addWidget(self.__art_label)
        self.__about_label = QLabel("About")
        self.shortened_add_action(QStyle.SP_TitleBarContextHelpButton, "About Heron", "Ctrl+H",
                                  self.__about_view)
        self.addWidget(self.__about_label)
        self.__about = None

    def generate_db_manager(self, db_name: str, ip: str, port: int) -> None:
        if "scine_database" in (name for _, name, _ in iter_modules()):
            import scine_database
            self.db_manager = scine_database.Manager()
            credentials = scine_database.Credentials(ip, port, db_name)
            self.db_manager.set_credentials(credentials)
        else:
            self.db_manager = None
            return

    def current_credentials(self) -> Optional[Any]:
        if self.db_manager is None:
            return None
        return self.db_manager.get_credentials()

    def __art_view(self):
        if "scine_art" in (name for _, name, _ in iter_modules()):
            from scine_heron.reaction_templates.reaction_template_dialog import ReactionTemplateDialog
            self.__rtd = ReactionTemplateDialog(self.parent().parent(), self.template_storage)
            self.__rtd.show()

    def __about_view(self):
        self.__about = AboutDialog(self.parent().parent())
        self.__about.show()

    def __update_template_count(self, count: int) -> None:
        self.__art_label.setText(f"Reaction Templates: {count}")

    def db_connection(self, silently: bool = False) -> None:
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
        if silently:
            try:
                self.db_manager.connect(expect_initialized_db=True)
            except RuntimeError:
                # cannot connect directly, call the dialog, which has better handling
                silently = False
        if not silently:
            connector = DatabaseConnectionDialog(parent=self, db_manager=self.db_manager)
            self.db_manager = connector.get_db_manager()
        new_credentials = self.db_manager.get_credentials() != old_credentials
        newly_connected = self.db_manager.is_connected() and not old_connection

        chemoton_widget = None
        steering_widget = None
        if (self.db_manager.is_connected() and new_credentials) or newly_connected:
            if "scine_chemoton" in (name for _, name, _ in iter_modules()):
                from scine_heron.chemoton.chemoton_widget_container import ChemotonWidgetContainer
                from scine_heron.chemoton.create_chemoton_widget import CreateEngineWidget
                from scine_chemoton import gears
                chemoton_widget = ChemotonWidgetContainer(self, self.db_manager, [gears.Gear], [CreateEngineWidget])
            if "scine_chemoton" in (name for _, name, _ in iter_modules()):
                from scine_heron.steering.display_widget import SteeringDisplay
                from scine_heron.chemoton.create_chemoton_widget import CreateStep, CreateSelection
                from scine_chemoton.steering_wheel.network_expansions import NetworkExpansion
                from scine_chemoton.steering_wheel.selections import Selection
                steering_widget = SteeringDisplay(self, self.db_manager, [Selection, NetworkExpansion],
                                                  [CreateSelection, CreateStep])
            self.__db_label.setText("Database: Connecting")
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
                steering_widget,
                kinetic_exploration_widget
            )
            self.__db_label.setText("Database: Connected")
        elif self.db_manager.is_connected():
            self.__db_label.setText("Database: Connected")
        else:
            self.connect_db_signal.emit(None, None, None, None, None, None)
            self.__db_label.setText("Database: Disconnected")
