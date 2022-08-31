#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
import numpy as np
from typing import Optional
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

import scine_utilities as utils

from scine_heron.utilities import (
    color_axis,
    color_figure,
    get_font,
    get_primary_line_color,
    get_secondary_line_color
)
from scine_heron.molecule.molecule_video import MoleculeVideo
from scine_heron.toolbar.io_toolbar import HeronToolBar

from PySide2.QtWidgets import (
    QWidget,
    QFileDialog,
    QHBoxLayout,
)


class ReactionProfileWidget(QWidget):  # type: ignore
    def __init__(
        self,
        parent: Optional[QWidget] = None,  # pylint: disable=unused-argument
        width: float = 5,
        height: float = 3
    ):
        super(ReactionProfileWidget, self).__init__(parent)
        self.fig = Figure(figsize=(width, height))
        self.ax1 = self.fig.add_subplot(1, 1, 1)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setMinimumHeight(150)
        self.canvas.setMinimumWidth(250)
        self._spline_order = 3
        self._spline: Optional[utils.bsplines.TrajectorySpline] = None
        self._prev_point = None

        self.plot_tool_bar = HeronToolBar(parent=self)
        self.plot_tool_bar.shortened_add_action('save_plot.png', "Save plot", "",
                                                self.save_svg)

        layout = QHBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.plot_tool_bar)
        self.setLayout(layout)
        self.update_canvas()

    def update_canvas(self, spline: Optional[utils.bsplines.TrajectorySpline] = None,
                      energy_difference: Optional[float] = None):
        if spline is None and energy_difference is None:
            self.fig.set_visible(False)
            self.plot_tool_bar.hide()
            self.canvas.draw()
            return
        self.fig.set_visible(True)
        self.plot_tool_bar.show()
        self.ax1.cla()
        color_figure(self.fig)
        font = get_font()
        color_axis(self.ax1)
        self.ax1.set_title("Interpolated Reaction Path", font)
        self.ax1.set_ylabel("Energy in kJ/mol", font)
        self.ax1.set_xticks([], minor=[])
        if spline is None:
            cap_style = 'butt'
            assert energy_difference is not None
            start = 0.0
            ts = max(energy_difference, 0.0)
            end = energy_difference
            x = np.arange(0, 6, 1.0)
            y = np.array([0.0, 0.0, end * 2625.5, end * 2625.5])
            # Plot Plateaus
            self.ax1.plot(x[:2], y[:2], color=get_primary_line_color(), linestyle='-', lw=4.5, solid_capstyle=cap_style)
            self.ax1.plot(x[-2:], y[-2:], color=get_primary_line_color(),
                          linestyle='-', lw=4.5, solid_capstyle=cap_style)
            # Plot connecting line
            self.ax1.plot([x[1], x[-2]], y[1:3], color=get_secondary_line_color(),
                          linestyle='--', lw=2.0, solid_capstyle=cap_style)
            self.ax1.set_xlim(x[0] - 0.25, x[-1] + 0.25)
            # Add 10% space to upper and lower bond
            if start < end:
                self.ax1.set_ylim(y[0] - abs(end - start) * 2625.5 * 0.1,
                                  y[-1] + abs(end - start) * 2625.5 * 0.1)
            else:
                self.ax1.set_ylim(y[-1] - abs(end - start) * 2625.5 * 0.1,
                                  y[0] + abs(end - start) * 2625.5 * 0.1)
        else:
            self._spline = spline
            start, _ = spline.evaluate(0.0, self._spline_order)
            ts, _ = spline.evaluate(spline.ts_position, self._spline_order)
            end, _ = spline.evaluate(1.0, 3)
            x = [i / 1000 for i in range(1001)]
            y = [(spline.evaluate(i / 1000, self._spline_order)[0] - start) * 2625.5 for i in range(1001)]
            self.ax1.plot(x, y, color=get_primary_line_color(), zorder=1.0)
        de = (end - start) * 2625.5
        dedf = (ts - start) * 2625.5
        dedb = (ts - end) * 2625.5
        self.ax1.set_xlabel(
            "Reaction Coordinate\n" + f"dE: {de:.1f}, Ef: {dedf:.1f}, Eb: {dedb:.1f}"
        )
        self.fig.tight_layout()
        if self.parent() is not None and isinstance(self.parent().mol_widget, MoleculeVideo) and spline is not None:
            self.parent().mol_widget.changed_frame.connect(self.draw_point)
            self.draw_point(0, 1)
        self.canvas.draw()

    def draw_point(self, current_frame: int, total_frames: int):
        if self._prev_point is not None:
            self._prev_point.remove()
        if self._spline is None:
            return
        x = current_frame / total_frames
        if x < 1e-6:
            y = 0.0
        else:
            y = (self._spline.evaluate(x, self._spline_order)[0] -
                 self._spline.evaluate(0, self._spline_order)[0]) * 2625.5
        # TODO: Get pointer color from theme
        self._prev_point = self.ax1.scatter(x, y, color="C1", zorder=1.5)
        self.canvas.draw()

    def save_svg(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save File"),  # type: ignore[arg-type]
            "plot.svg",
            self.tr("Vector Graphics (*.svg)"),  # type: ignore[arg-type]
        )
        self.fig.savefig(filename)
