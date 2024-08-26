#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from PySide2.QtGui import QColor, QPalette
from PySide2.QtWidgets import (QHBoxLayout,
                               QTabWidget, QVBoxLayout, QWidget)

from scine_heron.autocas.entanglement_diagram import EntanglementDiagramWidget
from scine_heron.autocas.orbital_viewer_widget import OrbitalViewerWidget
from scine_heron.autocas.signal_handler import SignalHandler
from scine_heron.autocas.options import OptionsWidget
# from scine_heron.autocas.autocas_settings import AutocasSettings
# from scine_heron.autocas.mo_diagram import MODiagram
import scine_heron.utilities as utils


class LogoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.__layout = QHBoxLayout()
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("red"))
        palette.setColor(QPalette.Background, QColor("red"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self.setLayout(self.__layout)


class ResultWidget(QWidget):
    def __init__(
        self, parent: QWidget, signal_handler: SignalHandler, autocas_settings
    ):
        QWidget.__init__(self, parent)

        self.signal_handler = signal_handler
        self.autocas_settings = autocas_settings

        self.signal_handler.open_entanglement_widget_signal.connect(
            self.activate_entanglement
        )
        self.signal_handler.open_molecule_widget_signal.connect(self.activate_molecule)

        self.entanglement_diagram = EntanglementDiagramWidget(self, self.signal_handler)
        # handles all autocas options
        self.options = utils.vertical_scroll_area_wrap(OptionsWidget(self, self.signal_handler, self.autocas_settings))

        self.__layout = QVBoxLayout()
        self.__tabs = QTabWidget()
        self.__tabs.addTab(self.options, "Calculation Settings")
        self.__orbital_viewer_widget = OrbitalViewerWidget(self, self.signal_handler, self.autocas_settings)
        self.__tabs.addTab(self.__orbital_viewer_widget, "Orbital Viewer")
        self.__tabs.addTab(self.entanglement_diagram, "Orbital Entropies")
        # self.__tabs.addTab(self.entanglement_diagram, "Threshold Diagram")
        self.__tabs.setCurrentIndex(0)
        self.__layout.addWidget(self.__tabs)
        self.setLayout(self.__layout)

    def activate_molecule(self):
        self.__tabs.setCurrentIndex(0)

    def activate_entanglement(self):
        self.__tabs.setCurrentIndex(1)

    def activate_threshold(self):
        self.__tabs.setCurrentIndex(2)
