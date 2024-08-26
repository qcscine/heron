#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
import numpy as np
from typing import Any, Optional, Tuple, TYPE_CHECKING
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

import scine_utilities as utils

from scine_heron.utilities import (
    color_axis,
    color_figure,
    get_font,
    get_primary_line_color,
    get_primary_light_color,
)
from scine_heron.toolbar.io_toolbar import HeronToolBar
from scine_heron.database.energy_diagram import EnergyDiagram

from PySide2.QtWidgets import (
    QWidget,
    QFileDialog,
    QHBoxLayout,
)

if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


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

        self._invert = False

        self.plot_tool_bar = HeronToolBar(parent=self)
        self.plot_tool_bar.shortened_add_action('save_plot.png', "Save plot", "",
                                                self.save_svg)

        layout = QHBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.plot_tool_bar)
        self.setLayout(layout)
        self.clear_canvas()

    def update_canvas(self,
                      spline: Optional[utils.bsplines.TrajectorySpline] = None,
                      barriers: Optional[Tuple[float, float]] = None,
                      draw_signal: Optional[Signal] = None,
                      invert: bool = False,
                      has_transition_state: bool = False):
        if spline is None and\
           (barriers is None or any(barrier is None for barrier in barriers)):
            self.clear_canvas()
            self._prepare_canvas()
            self.ax1.set_title("No data to plot, check specified model.", get_font())
            return
        self._invert = invert
        self._prepare_canvas()
        # All energies are always relative to shown lhs
        lhs_energy = 0.0
        if barriers is not None and self._invert:
            barriers = barriers[::-1]

        if spline is None and barriers is not None:
            rhs_energy = barriers[0] - barriers[1]
            if has_transition_state:
                self._plot_plateaus(lhs_energy, rhs_energy, (barriers[0], 0.5))
            else:
                self._plot_plateaus(lhs_energy, rhs_energy)
        else:
            assert spline
            ts_position = spline.ts_position if not self._invert else 1.0 - spline.ts_position
            if barriers is not None:
                rhs_energy = barriers[0] - barriers[1]
                self._plot_plateaus(lhs_energy, rhs_energy, (barriers[0], ts_position))
            spline_lhs_energy, spline_ts_energy, spline_rhs_energy = self._plot_spline(spline)

        # Legend Plotting
        if barriers is None or any(barrier is None for barrier in barriers):
            self._plot_xlabel((spline_ts_energy - spline_lhs_energy) * utils.KJPERMOL_PER_HARTREE,
                              (spline_ts_energy - spline_rhs_energy) * utils.KJPERMOL_PER_HARTREE,
                              from_spline=True)
        else:
            self._plot_xlabel(barriers[0], barriers[1])  # (ts - start) * utils.KJPERMOL_PER_HARTREE

        # Final formatting
        self.fig.tight_layout()
        if draw_signal is not None and spline is not None:
            draw_signal.connect(self.draw_point)  # pylint: disable=no-member
            self.draw_point(0, 1)

        self.canvas.draw()

    def clear_canvas(self):
        self.fig.set_visible(False)
        self.plot_tool_bar.hide()
        self.canvas.draw()

    def _prepare_canvas(self) -> None:
        self.fig.set_visible(True)
        self.plot_tool_bar.show()
        self.ax1.cla()
        color_figure(self.fig)
        font = get_font()
        color_axis(self.ax1)
        self.ax1.set_title("Interpolated Reaction Path", font)
        self.ax1.set_ylabel("Electronic Energy in kJ/mol", font)
        self.ax1.set_xticks([], minor=[])

    def _plot_plateaus(self, lhs_energy: float, rhs_energy: float, lhs_barrier: Optional[Tuple[float, float]] = None):
        # Style Dictionaries
        diagram = EnergyDiagram("auto")
        space_for_level = 0.4  # assuming 3 plateaus
        diagram.dimension = space_for_level * 0.25
        diagram.space = space_for_level * 0.75
        # Color scheme
        # TODO adapt to dark mode
        # TODO: Maybe as general setting
        default_line_color = '#85929e'
        ts_level_color = '#995151'
        alpha = 0.75
        # Add Levels
        diagram.add_level(lhs_energy, position=0.0,
                          top_text="", bottom_text="", color=default_line_color, linewidth=4.5, alpha=alpha)
        if lhs_barrier is not None:
            diagram.add_level(lhs_barrier[0], position=(lhs_barrier[1] - 0.05) / space_for_level,
                              top_text="", bottom_text="", color=ts_level_color, linewidth=4.5, alpha=alpha)
            diagram.add_level(rhs_energy, position=0.9 / space_for_level, top_text="", bottom_text="",
                              color=default_line_color, linewidth=4.5, alpha=alpha)
            diagram.add_link(1, 2, linewidth=2.0, color=default_line_color, alpha=alpha)
        else:
            diagram.add_level(rhs_energy, top_text="", bottom_text="",
                              color=default_line_color, linewidth=4.5)
        # Add Link
        diagram.add_link(0, 1, linewidth=2.0, color=default_line_color)

        diagram.plot(ax=self.ax1)

    def _plot_spline(self, spline: utils.bsplines.TrajectorySpline) -> Tuple[float, float, float]:
        self._spline = spline
        spline_points = 1000
        spline_start_energy, _ = spline.evaluate(0.0, self._spline_order)
        spline_ts_energy, _ = spline.evaluate(spline.ts_position, self._spline_order)
        spline_end_energy, _ = spline.evaluate(1.0, self._spline_order)
        spline_x_points = np.array([i / spline_points for i in range(spline_points + 1)])
        spline_energies = np.array([(spline.evaluate(i / spline_points, self._spline_order)[0])
                                    * utils.KJPERMOL_PER_HARTREE for i in range(spline_points + 1)])
        # invert energy plot if required
        if self._invert:
            spline_x_points = 1 - spline_x_points[::-1]
            spline_energies = spline_energies[::-1]
            # Invert spline end point energies
            tmp_spline_start = spline_start_energy
            spline_start_energy = spline_end_energy
            spline_end_energy = tmp_spline_start
        # # # Rebase spline energies to start energy
        spline_energies -= spline_start_energy * utils.KJPERMOL_PER_HARTREE
        # Plot curve
        self.ax1.plot(spline_x_points, spline_energies,
                      color=get_primary_line_color(), zorder=2.0)
        return spline_start_energy, spline_ts_energy, spline_end_energy

    def _plot_xlabel(self, barrier_forward: float, barrier_backward: float, from_spline=False):
        label = "Reaction Coordinate\n" + "$\\Delta_{\\mathrm{R}} E_{el}$: " +\
                f" {(barrier_forward-barrier_backward):.1f}, " +\
                " $\\Delta^{\\ddag} E_{el}^{f}$: " + f" {barrier_forward:.1f}, " +\
                " $\\Delta^{\\ddag} E_{el}^{b}$: " + f" {barrier_backward:.1f}"
        if from_spline:
            label += "\n$^{*}$ Energies from Spline"

        self.ax1.set_xlabel(label)

    def draw_point(self, current_frame: int, total_frames: int):
        if self._prev_point is not None:
            self._prev_point.remove()
        if self._spline is None:
            return
        x = current_frame / total_frames
        if self._invert:
            x = 1.0 - x
        if x < 1e-6:
            y = 0.0
        else:
            y_base = self._spline.evaluate(0, self._spline_order)[0] if not self._invert else\
                self._spline.evaluate(1, self._spline_order)[0]
            y = (self._spline.evaluate(x, self._spline_order)[0] - y_base) * utils.KJPERMOL_PER_HARTREE
        self._prev_point = self.ax1.scatter(current_frame / total_frames, y,
                                            color=get_primary_light_color(), zorder=2.5)
        self.canvas.draw()

    def save_svg(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save File"),  # type: ignore[arg-type]
            "plot.svg",
            self.tr("Vector Graphics (*.svg)"),  # type: ignore[arg-type]
        )
        if self._prev_point is not None:
            try:
                self._prev_point.remove()
                self._prev_point = None
            except BaseException:
                pass
        self.canvas.draw()
        self.fig.savefig(filename, transparent=True)
