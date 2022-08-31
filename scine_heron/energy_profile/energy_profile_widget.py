#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the Energy Profile widget.
"""

import numpy as np
import time

from scine_heron.utilities import (
    color_axis,
    color_figure,
    get_font,
    get_primary_line_color
)

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from typing import List, Optional
from PySide2.QtCore import QSize
from PySide2.QtWidgets import (
    QDockWidget,
    QLabel,
    QWidget,
    QGridLayout,
    QSpinBox,
    QCheckBox,
    QComboBox,
)
from scine_heron.energy_profile.energy_profile_status_manager import (
    EnergyProfileStatusManager,
)

from scine_heron.energy_profile.energy_profile_point import EnergyProfilePoint


class EnergyProfileWidget(QDockWidget):
    class Canvas(FigureCanvasQTAgg):  # type: ignore
        def __init__(
            self,
            parent: Optional[QWidget] = None,  # pylint: disable=unused-argument
            width: float = 10,
            height: float = 3,
        ):

            self.fig = Figure(figsize=(width, height))

            self.ax1 = self.fig.add_subplot(1, 1, 1, position=[0.15, 0.15, 0.75, 0.75])
            super(EnergyProfileWidget.Canvas, self).__init__(self.fig)

            self.energies: List[float] = []
            self.time_stamps: List[float] = []
            self.fixed_time: bool = True
            self.fixed_time_interval: int = 10
            self.last_update: float = float(time.time())
            self.energy_units: List[str] = ["kJ/mol", "Hartree"]
            self._energy_conversions: List[float] = [2625.5, 1.0]
            self.energy_unit: int = 0
            self.relative_energy: int = 0

            (self.__line,) = self.ax1.plot([], [], color=get_primary_line_color())

            color_figure(self.fig)
            font = get_font()
            color_axis(self.ax1)
            self.ax1.set_title("Electronic Energy Profile", font)

            self.ax1.set_xlabel("Relative Time in s")
            if self.relative_energy:
                self.ax1.set_ylabel(
                    f"Relative energy in {self.energy_units[self.energy_unit]}"
                )
            else:
                self.ax1.set_ylabel(f"Energy in {self.energy_units[self.energy_unit]}")

            self.draw()

        def update_line(self) -> None:
            unit_conversion = self._energy_conversions[self.energy_unit]
            local_energies = self.energies
            local_time_stamps = self.time_stamps
            n = min(len(local_energies), len(local_time_stamps))
            if n < 2:
                return
            now = self.time_stamps[-1]
            if self.fixed_time:
                x = np.array(
                    [
                        i - now
                        for i in local_time_stamps[1:n]
                        if now - i < self.fixed_time_interval
                    ]
                )
                y = np.array(
                    [
                        i * unit_conversion
                        for i, j in zip(local_energies[1:n], local_time_stamps[1:n])
                        if now - j < self.fixed_time_interval
                    ]
                )
            else:
                x = np.array(local_time_stamps[1:n]) - now
                y = np.array(local_energies[1:n]) * unit_conversion

            if self.relative_energy == 1:
                ref = y[-1]
                y -= ref
            elif self.relative_energy == 2:
                ref = np.min(y)
                y -= ref

            if len(y) > 1 and len(x) > 1:
                y_min = np.min(y)
                y_max = np.max(y)
                y_diff = y_max - y_min
                y_corr = max((50 / 2625.5) * unit_conversion - y_diff, 0.1 * y_diff)
                y_min -= 0.5 * y_corr
                y_max += 0.5 * y_corr
                x_min = np.min(x)
                x_max = np.max(x)
                x_diff = max(x_max - x_min, self.fixed_time_interval)
                x_min -= 0.1 * x_diff
                x_max += 0.1 * x_diff

                self.__line.set_data(x, y)
                self.__line.axes.axis([x_min, x_max, y_min, y_max])
            self.draw()

        def redraw_axis(self) -> None:
            if self.relative_energy:
                self.ax1.set_ylabel(
                    f"Relative energy in {self.energy_units[self.energy_unit]}"
                )
            else:
                self.ax1.set_ylabel(f"Energy in {self.energy_units[self.energy_unit]}")
            self.draw()

    def __init__(
        self,
        _: Optional[QWidget] = None,
        width: float = 10,
        height: float = 3,
    ):
        super(EnergyProfileWidget, self).__init__()
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)

        self._inner_widget = QWidget(self)
        self.setWidget(self._inner_widget)

        self._layout = QGridLayout()
        self._layout.setRowMinimumHeight(0, 200)
        self._layout.setColumnMinimumWidth(0, 560)
        self._inner_widget.setLayout(self._layout)
        self.__widget_width = 130
        self.__widget_height = 30

        self.__canvas = self.Canvas(parent=self, width=width, height=height)
        EnergyProfileWidget.__canvas = self.__canvas

        self.energy_status_manager = EnergyProfileStatusManager()
        self.energy_status_manager.changed_signal.connect(self.update_energy_widget)
        self._layout.addWidget(self.__canvas, 0, 0, 6, 1)

        self._unit_label = QLabel()
        self._unit_label.setText("Unit of Energy:")
        self._unit_label.setFixedSize(QSize(self.__widget_width, self.__widget_height))
        self._layout.addWidget(self._unit_label, 1, 1, 1, 1)

        self._unit_cb = QComboBox()
        for e in self.__canvas.energy_units:
            self._unit_cb.addItem(e)
        self._unit_cb.currentIndexChanged.connect(self.update_energy_unit)  # pylint: disable=no-member
        self._unit_cb.setFixedSize(QSize(self.__widget_width, self.__widget_height))
        self._layout.addWidget(self._unit_cb, 2, 1, 1, 1)

        self._rel_unit_cb = QComboBox()
        # we assume later that every option after the first is a relative one
        for e in ["absolute", "relative to now", "relative to lowest"]:
            self._rel_unit_cb.addItem(e)
        self._rel_unit_cb.currentIndexChanged.connect(self.update_rel_energy_unit)  # pylint: disable=no-member
        self._rel_unit_cb.setFixedSize(QSize(self.__widget_width, self.__widget_height))
        self._layout.addWidget(self._rel_unit_cb, 3, 1, 1, 1)

        self._sliding_window_cbox = QCheckBox("Interval")
        self._sliding_window_cbox.setChecked(self.__canvas.fixed_time)
        self._sliding_window_cbox.toggled.connect(self.set_sliding_window)  # pylint: disable=no-member
        self._sliding_window_cbox.setFixedSize(
            QSize(self.__widget_width, self.__widget_height)
        )
        self._layout.addWidget(self._sliding_window_cbox, 4, 1, 1, 1)

        self._sliding_window_label = QLabel()
        self._sliding_window_label.setText("Interval in s:")
        self._sliding_window_label.setFixedSize(
            QSize(self.__widget_width, self.__widget_height)
        )
        self._layout.addWidget(self._sliding_window_label, 5, 1, 1, 1)

        self.__sliding_window_interval = QSpinBox()
        self.__sliding_window_interval.setMinimum(10)
        self.__sliding_window_interval.setMaximum(3600)
        self.__sliding_window_interval.setValue(self.__canvas.fixed_time_interval)
        self.__sliding_window_interval.valueChanged.connect(self.set_time_window)  # pylint: disable=no-member
        self.__sliding_window_interval.setFixedSize(
            QSize(self.__widget_width, self.__widget_height)
        )
        self._layout.addWidget(self.__sliding_window_interval, 6, 1, 1, 1)

    def set_sliding_window(self) -> None:
        self.__canvas.fixed_time = self._sliding_window_cbox.isChecked()

    def set_time_window(self, fixed_time_interval: int) -> None:
        self.__canvas.fixed_time_interval = fixed_time_interval

    def update_energy_widget(self, energy_profile: List[EnergyProfilePoint]) -> None:
        self.__canvas.energies.append(energy_profile[-1].energy)
        now = float(time.time())
        self.__canvas.time_stamps.append(now)
        self.__canvas.last_update = float(time.time())
        self.__canvas.update_line()

    def update_energy_unit(self, new_unit: int) -> None:
        self.__canvas.energy_unit = new_unit
        self.__canvas.redraw_axis()
        self.__canvas.update_line()

    def update_rel_energy_unit(self, new_unit: int) -> None:
        self.__canvas.relative_energy = new_unit
        self.__canvas.redraw_axis()
        self.__canvas.update_line()

    def reset(self) -> None:
        self.__canvas.energies = []
        self.__canvas.time_stamps = []
        self.__canvas.last_update = float(time.time())
        # Reset energy manager as well
        self.energy_status_manager.reset()
