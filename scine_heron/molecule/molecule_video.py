#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the MoleculeWidget class.
"""
from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QSlider,
    QFileDialog,
    QMainWindow,
)
from scine_heron.utilities import (
    color_axis,
    color_figure,
    get_font,
    get_primary_line_color,
)
from scine_heron.molecule.molecule_widget import MoleculeWidget
from scine_heron.toolbar.io_toolbar import HeronToolBar
from PySide2.QtCore import QObject, Qt

from matplotlib.collections import PathCollection
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.text import Annotation

from scipy.signal import argrelextrema
import numpy as np

import scine_utilities as utils
from typing import Any, Tuple, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


class MoleculeVideo(QWidget):
    """
    Displays trajectory as interactive video
    """

    changed_frame = Signal(int, int)

    def __init__(
        self,
        parent: Optional[QObject],
        trajectory: utils.MolecularTrajectory,
        mol_widget: MoleculeWidget
    ):
        QWidget.__init__(self, parent)
        if trajectory.empty():
            raise RuntimeError("Empty Trajectory given to video")
        self._frame: int = 0
        self._n_frames: int = len(trajectory)
        self._trajectory: utils.MolecularTrajectory = trajectory
        self._mol_widget = mol_widget
        self._mol_widget.update_molecule(atoms=utils.AtomCollection(
            trajectory.elements, trajectory[0]))
        layout = QVBoxLayout()
        layout.addWidget(self._mol_widget)

        self._tool_bar: Optional[HeronToolBar] = None
        self.slider: Optional[QSlider] = None
        if self._n_frames > 1:
            self._tool_bar = HeronToolBar(parent=self)

            self.slider = QSlider(Qt.Horizontal)
            self.slider.setMinimum(0)
            self.slider.setMaximum(self._n_frames - 1)
            self.slider.setValue(0)
            self.slider.valueChanged.connect(self.slider_change)  # pylint: disable=no-member
            self._tool_bar.addWidget(self.slider)

            self._tool_bar.shortened_add_action("save_molecule.png", "Save frame", "",
                                                self._save_frame)
            self._tool_bar.addSeparator()
            self._tool_bar.shortened_add_action('save_trajectory.png', "Save trajectory", "",
                                                self._save_trajectory)

            layout.addWidget(self._tool_bar)

        self.setLayout(layout)

    def add_button_to_toolbar(self, *args, **kwargs):
        if self._tool_bar:
            self._tool_bar.shortened_add_action(*args, **kwargs)

    def slider_change(self) -> None:
        if self.slider is not None:
            self._frame = self.slider.value()
            self._mol_widget.update_molecule(atoms=utils.AtomCollection(
                self._trajectory.elements, self._trajectory[self._frame]))
            self.changed_frame.emit(self._frame, self._n_frames)

    def set_frame(self, frame: int) -> None:
        if self.slider is not None:
            if frame < 0 or frame >= self._n_frames:
                frame = 0
            self.slider.setValue(frame)

    def _save_trajectory(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Trajectory to File"),  # type: ignore[arg-type]
            "",
            self.tr("Molecule (*.xyz *.bin)"),  # type: ignore[arg-type]
        )
        if filename:
            if str(filename)[-3:].lower() == "xyz":
                traj_format = utils.io.TrajectoryFormat.Xyz
            elif str(filename)[-3:].lower() == "bin":
                traj_format = utils.io.TrajectoryFormat.Binary
            else:
                raise RuntimeError(f"Unknown trajectory format given in {str(filename)}, "
                                   f"please specify either 'xyz' or 'bin'.")
            utils.io.write_trajectory(traj_format, str(filename), self._trajectory)

    def _save_frame(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Frame to File"),  # type: ignore[arg-type]
            "",
            self.tr("Molecule (*.xyz *.mol *.pdb)"),  # type: ignore[arg-type]
        )
        if filename:
            atoms = utils.AtomCollection(self._trajectory.elements, self._trajectory[self._frame])
            utils.io.write(str(filename), atoms)


class TrajectoryEnergyWidget(FigureCanvasQTAgg):
    def __init__(
            self, parent: QWidget, trajectory: utils.MolecularTrajectory,
            width: float = 20, height: float = 3
    ):
        self.fig = Figure(figsize=(width, height))
        color_figure(self.fig)
        self.ax = self.fig.add_subplot(1, 1, 1)
        color_axis(self.ax)

        super(TrajectoryEnergyWidget, self).__init__(self.fig)
        self._energies = trajectory.get_energies()
        if self._energies:
            start = self._energies[0]
            self._rel_energies = [(self._energies[i] - start) * 2625.5 for i in range(len(self._energies))]
            self._extrema: np.ndarray = np.array([])
            self._prev_point = None
            self._parent = parent
            self._scatters: Optional[PathCollection] = None
            self._annotations: Optional[Annotation] = None
            self._mark_color = "#bc80bd"
        self.update_canvas()

    def update_canvas(self):
        if not self._energies:
            self.fig.set_visible(False)
            self.draw()
            return

        start = self._energies[0]
        maximum = np.max(self._energies)
        end = self._energies[-1]
        y = [(self._energies[i] - start) * 2625.5 for i in range(len(self._energies))]
        de = (end - start) * 2625.5
        dedf = (maximum - start) * 2625.5
        dedb = (maximum - end) * 2625.5
        self.ax.cla()
        self.ax.plot(list(range(len(self._energies))), y,
                     color=get_primary_line_color(), linestyle='--', marker='o', markersize=5,
                     picker=True, pickradius=5)
        font = get_font()
        self.ax.set_title(f"Maximum energy at {np.argmax(self._energies)}", font, color=get_primary_line_color())
        self.ax.set_xlabel(
            f"dE: {de:.1f}, Ef: {dedf:.1f}, Eb: {dedb:.1f}", font
        )
        self.ax.set_ylabel("Relative energy in kJ/mol", font)
        self.fig.tight_layout()
        if self._parent is not None and isinstance(self._parent, MoleculeVideoWithEnergy):
            self._parent.video.changed_frame.connect(self.draw_point)
        self.fig.canvas.mpl_connect('pick_event', self._onpick)
        self.fig.canvas.mpl_connect('motion_notify_event', self._hover)
        self._add_extrema_infos()
        self.draw_point(0, 1)

    def save_svg(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save File"),  # type: ignore[arg-type]
            "plot.svg",
            self.tr("Vector Graphics (*.svg)"),  # type: ignore[arg-type]
        )
        self.fig.savefig(filename)

    def draw_point(self, current_frame: int, _: int):
        if self._prev_point is not None:
            self._prev_point.remove()
            self._prev_point = None
        if not self._energies:
            return
        x = current_frame
        y = 0 if x == 0 else (self._energies[x] - self._energies[0]) * 2625.5
        self._prev_point = self.ax.scatter(x, y, color="C1", zorder=100)
        self.draw()

    def _find_local_minima_and_maxima(self, n_local: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        values = np.array(self._rel_energies)
        maxima = argrelextrema(values, np.greater, order=n_local)[0]
        minima = argrelextrema(values, np.less, order=n_local)[0]
        extrema = np.asarray(list(maxima) + list(minima))
        extreme_values = np.array([values[x] for x in extrema])
        self._extrema = extrema
        return extrema, extreme_values

    def _add_extrema_infos(self) -> None:
        sc_x, sc_y = self._find_local_minima_and_maxima()
        sc = self.ax.scatter(sc_x, sc_y, color=self._mark_color, zorder=99)
        self._scatters = sc
        annot = self.ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                                 bbox=dict(boxstyle="round", fc="w"), arrowprops=dict(arrowstyle="->"))
        annot.set_visible(False)
        self._annotations = annot

    def _update_annot(self, index) -> None:
        if self._scatters is not None and self._annotations is not None:
            index = index['ind'][0]
            text = "rel. energy: {0:.2f}".format(self._rel_energies[self._extrema[index]])
            annot = self._annotations
            annot.xy = self._scatters.get_offsets()[index]
            annot.set_text(text)
            annot.get_bbox_patch().set_facecolor(self._mark_color)
            annot.get_bbox_patch().set_alpha(0.4)

    def _hover(self, event) -> None:
        if event.inaxes == self.ax and self._scatters is not None and self._annotations is not None:
            contains, index = self._scatters.contains(event)
            annot = self._annotations
            visible = annot.get_visible()
            if contains:
                self._update_annot(index)
                annot.set_visible(True)
                self.fig.canvas.draw_idle()
            else:
                if visible:
                    annot.set_visible(False)
                    self.fig.canvas.draw_idle()

    def _onpick(self, event) -> None:
        if self._annotations is not None:
            self._annotations.set_visible(False)
            if self._parent is not None and isinstance(self._parent, MoleculeVideoWithEnergy):
                x = int(round(event.mouseevent.xdata))
                self._parent.video.set_frame(x)


class MoleculeVideoWithEnergy(QWidget):

    def __init__(
            self, parent: QWidget, trajectory: utils.MolecularTrajectory,
            width: float = 20, height: float = 3, alternative_zoom_controls: bool = False,
    ):
        QWidget.__init__(self, parent)
        self.molecule_widget = MoleculeWidget(
            parent=self,
            alternative_zoom_controls=alternative_zoom_controls,
            disable_modification=True
        )
        self.video = MoleculeVideo(parent=self, trajectory=trajectory, mol_widget=self.molecule_widget)
        self.plot = TrajectoryEnergyWidget(parent=self, trajectory=trajectory, width=width, height=height)

        self.plot_tool_bar = HeronToolBar(parent=self)
        self.plot_tool_bar.shortened_add_action('save_plot.png', "Save plot", "",
                                                self.plot.save_svg)

        layout = QVBoxLayout()
        layout.addWidget(self.video)
        layout.addWidget(self.plot)
        layout.addWidget(self.plot_tool_bar)
        self.setLayout(layout)


class MainVideo(QMainWindow):
    def __init__(
            self,
            trajectory,
            parent: Optional[QObject] = None,
    ):
        QMainWindow.__init__(self, parent)
        self.resize(1280, 1024)

        self.setWindowTitle(self.tr("Trajectory"))  # type: ignore[arg-type]
        self.setCentralWidget(MoleculeVideoWithEnergy(self, trajectory))
