#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional

from scine_heron.autocas.mo_diagram import MODiagram
from scine_heron.autocas.result_widget import ResultWidget
from scine_heron.autocas.signal_handler import SignalHandler
from scine_heron.autocas.autocas_settings import AutocasSettings
import scine_heron.utilities as utils

from PySide2.QtWidgets import QHBoxLayout, QWidget, QMenu


class AutocasProjectWidget(QWidget):
    def __init__(self, parent: Optional[QWidget], signal_handler: SignalHandler, autocas_settings: AutocasSettings,
                 label: Optional[str] = None, single_window: bool = False):
        QWidget.__init__(self, parent)

        self.signal_handler = signal_handler
        self.autocas_settings = autocas_settings

        self.__layout = QHBoxLayout()
        self.__results_widget = ResultWidget(self, self.signal_handler, self.autocas_settings)
        self.__mo_diagram_widget = utils.vertical_scroll_area_wrap(
            MODiagram(self, self.signal_handler, self.autocas_settings))

        self.__layout.addWidget(self.__results_widget)
        self.__layout.addWidget(self.__mo_diagram_widget)
        self.setLayout(self.__layout)
        self.__expanded_view: Optional[QWidget] = None
        self.__single_window = single_window
        if label is None:
            label = "Project"
        self.__project_label = label
        # If this is a pop up, we should check if the original widget already displays orbitals etc. and load
        # them if possible to this window, too.
        if single_window:
            if self.autocas_settings.molecule_xyz_file:
                self.signal_handler.load_xyz_file_signal.emit(self.autocas_settings.molecule_xyz_file)
            if self.autocas_settings.molcas_orbital_file:
                self.signal_handler.load_molden_file_signal.emit(self.autocas_settings.molcas_orbital_file)

    def contextMenuEvent(self, event):
        """
        Override QWidget function to add a custom context menu.
        """
        if not self.__single_window:
            self.menu_function(event)

    def menu_function(self, event):
        menu = QMenu()
        expand_action = menu.addAction('Expand')
        action = menu.exec_(event.globalPos())  # type: ignore
        if action == expand_action:
            self.__show_project_in_new_window()

    def __show_project_in_new_window(self):
        self.__expanded_view = AutocasProjectWidget(None, self.signal_handler, self.autocas_settings,
                                                    self.__project_label, True)
        self.__expanded_view.setWindowTitle(self.__project_label)
        self.__expanded_view.resize(600, 500)
        self.__expanded_view.show()
