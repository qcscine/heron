#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import List, Optional

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide2.QtWidgets import QDockWidget, QGridLayout, QWidget
from scine_autocas.plots.entanglement_plot import EntanglementPlot

from scine_heron.autocas.signal_handler import SignalHandler


class EntanglementDiagramWidget(QDockWidget):
    class Canvas(FigureCanvasQTAgg):
        def __init__(
            self,
            # pylint: disable-next=W0613
            mode: str = "dark",
            # pylint: disable-next=W0613
            parent: Optional[QWidget] = None,
            width: float = 10,
            height: float = 10,
        ):

            self.entang_plot = EntanglementPlot()
            self.entang_plot.alpha_mut_inf = 1
            self.entang_plot.alpha_s1 = 1
            self.entang_plot.s1_position = 1.0
            # self.entang_plot.label_ofset = 0.35

            self.fig = Figure(figsize=(width, height))
            self.ax1 = self.fig.add_subplot(
                111, polar=True, position=[0.05, 0.05, 0.9, 0.9]
            )
            super(EntanglementDiagramWidget.Canvas, self).__init__(self.fig)

            self.s1 = np.array([1.0, 1.0])
            self.mutual_information = np.array([[1.0, 1.0], [1.0, 1.0]])
            self.order: List[int] = [0, 1]

            # self.__lines = self.entang_plot._entanglement_plot(
            #     self.ax1, self.s1, self.mutual_information, self.order
            # )
            self.entang_plot._entanglement_plot(
                self.ax1, self.s1, self.mutual_information, self.order
            )

            self.draw()

        def update_lines(self, s1=None, mutual_information=None, order=None):
            if s1 is None:
                s1 = np.array([0.0, 0.0])
            if mutual_information is None:
                mutual_information = np.array([[0.0, 0.0], [0.0, 0.0]])

            self.s1 = s1
            self.mutual_information = mutual_information
            self.order = order
            # self.entang_plot._entanglement_plot(
            #    self.ax1, self.s1, self.mutual_information, None
            # )
            # self.__line = self.entang_plot._entanglement_plot(
            #     self.ax1, self.s1, self.mutual_information, self.order
            # )
            self.entang_plot._entanglement_plot(
                self.ax1, self.s1, self.mutual_information, self.order
            )
            # local_x = self.x
            # local_y = self.y
            # x = np.array(local_x)
            # y = np.array(local_y)
            # x_min = np.min(x)
            # x_max = np.max(x)
            # y_min = np.min(y)
            # y_max = np.max(y)
            # self.__line.set_data(x, y)
            # self.__line.axes.axis([x_min, x_max, y_min, y_max])

            self.draw()

    def __init__(
        self,
        # pylint: disable-next=W0613
        parent: Optional[QWidget],
        signal_handler: SignalHandler,
        # pylint: disable-next=W0613
        mode: str = "dark",
        width: float = 10,
        height: float = 10,
    ) -> None:
        super(EntanglementDiagramWidget, self).__init__()
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)

        self.signal_handler = signal_handler
        self.signal_handler.update_entanglement_plot_signal.connect(self.update_plot)

        self._inner_widget = QWidget(self)
        self.setWidget(self._inner_widget)
        self._layout = QGridLayout()
        self._layout.setRowMinimumHeight(0, 200)
        self._layout.setColumnMinimumWidth(0, 200)
        self._inner_widget.setLayout(self._layout)
        # self.__widget_width = 130
        # self.__widget_height = 130
        self.__canvas = self.Canvas(parent=self, width=width, height=height, mode=mode)
        self._layout.addWidget(self.__canvas, 0, 0, 1, 1)
        self.__canvas.update_lines()

    def update_plot(self, s1, mut_inf, order=None):
        self.__canvas.ax1.cla()
        self.__canvas.update_lines(s1, mut_inf, order)
        self.__canvas.draw()

    def plot_entanglement(self):
        pass

    def plot_threshold(self):
        pass
