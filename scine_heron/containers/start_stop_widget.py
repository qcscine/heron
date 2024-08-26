#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from abc import abstractmethod
from typing import Dict, Optional, Any, List

from PySide2.QtGui import QPalette, QColor
from PySide2.QtWidgets import (
    QWidget,
    QLabel,
    QTextEdit,
)
from PySide2.QtCore import QObject


from scine_heron.containers.buttons import TextPushButton
from scine_heron.containers.layouts import HorizontalLayout, VerticalLayout
from scine_heron.containers.wrapped_label import WrappedLabel
from scine_heron.settings.docstring_parser import DocStringParser


class StartStopWidget(QWidget):
    """
    An abstract base class for widgets that hold a clas that can run some longer running process.
    And allows to start and stop this process by buttons, possibly interact with some settings,
    and display a status/progress by colors.

    Notes
    -----
    Does not inherit explicitly from ABC, because that would conflict with QObject.
    """

    # some predefined colors, possible to be moved to global style file
    green: str = "#5aa36b"
    orange: str = "#e8a01a"
    red: str = "#e8321a"

    def __init__(self, parent: Optional[QObject], *args, **kwargs):
        """
        Initialize with the underlying objects and construct the layout and buttons.
        """
        super().__init__(parent, *args, **kwargs)
        self._default_color = self.palette()
        self._layout = VerticalLayout()
        self._docstring_dict: Dict[str, str] = {}  # pylint: disable=unused-private-member
        self.button_settings: Optional[TextPushButton] = None
        self.button_delete: Optional[TextPushButton] = None
        self.button_copy_results: Optional[TextPushButton] = None
        self.filter_label: Optional[QLabel] = None
        self.filter: Optional[QTextEdit] = None
        self.init_arguments: List[Any] = [None]  # None for parent
        self.setLayout(self._layout)

    @abstractmethod
    def join(self, force_join: bool = False) -> Optional[Any]:
        """
        Join any forked process or threads

        Parameters
        ----------
        force_join : bool, optional
            If the process should also be joined, even if it never ran, by default False

        Returns
        -------
        Optional[Any]
           An optional returned object from the underlying process.
        """

    @abstractmethod
    def start_stop(self, start_all: bool = False, stop_all: bool = False) -> None:
        """
        Start or stop the underlying process depending on the current status

        Parameters
        ----------
        start_all : bool, optional
            Whether this method was triggered in a list of StartStopWidgets being started, by default False
        stop_all : bool, optional
            Whether this method was triggered in a list of StartStopWidgets being stopped, by default False
        """

    @abstractmethod
    def set_docstring_dict(self, doc_string_parser: DocStringParser) -> None:
        """
        Set the docstring information to the settings based on the given parser.

        Parameters
        ----------
        doc_string_parser : DocStringParser
            The parser that can extract the information from our objects.
        """

    @abstractmethod
    def stop_class_if_working(self) -> None:
        """
        Stop the underlying process if it is running
        """

    def _add_settings_and_delete_buttons(self):
        """
        Add two buttons to our layout that enable a settings access and a deletion of this widget.
        """
        self.button_settings = TextPushButton("Settings", self._show_settings)
        self.button_delete = TextPushButton("Delete")
        self._layout.add_widgets([self.button_settings, self.button_delete])

    def _show_settings(self) -> None:
        """
        Display the settings.
        """

    def _add_filter_at_layout(self, filter_description: str) -> None:
        """
        Add a textbox that describes the held filters with the given description.

        Parameters
        ----------
        filter_description : str
            The text to be displayed in the textbox.
        """

        self.filter_label = WrappedLabel("Filter(s):")
        self.filter = QTextEdit(filter_description)
        self.filter.setReadOnly(True)

        layout = HorizontalLayout([self.filter_label, self.filter])
        self._layout.addLayout(layout)

    def change_color(self, color: str = "") -> None:
        """
        Change the background color of this widget. If no color is given, the default color is used.

        Parameters
        ----------
        color : str, optional
            The color as a possible argument to the QColor constructor, by default ""
        """
        if color:
            palette = self.palette()
            palette.setColor(QPalette.Window, QColor(color))
            self.setPalette(palette)
            self.setAutoFillBackground(True)
        else:
            self.setPalette(self._default_color)
            self.setAutoFillBackground(False)
