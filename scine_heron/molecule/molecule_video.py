#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
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
    QDialog,
    QApplication,
)
from scine_heron.utilities import (
    color_axis,
    color_figure,
    get_font,
    get_primary_line_color,
    get_secondary_line_color,
)
from scine_heron.molecule.molecule_widget import MoleculeWidget
from scine_heron.toolbar.io_toolbar import HeronToolBar
from PySide2.QtCore import QObject, Qt

from matplotlib.collections import PathCollection
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.text import Annotation
from matplotlib.widgets import RectangleSelector


from scipy.signal import argrelextrema
import numpy as np
from pkgutil import iter_modules

import scine_utilities as utils
from typing import Any, Tuple, Optional, List, Set, TYPE_CHECKING
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
        # By adding the mol widget to this layout it is losing its original layout info
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
                self._trajectory.elements, self._trajectory[self._frame]), reset_camera=False)
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
            width: float = 20, height: float = 3, selectable: bool = True
    ):
        self.fig = Figure(figsize=(width, height))
        color_figure(self.fig)
        self.ax = self.fig.add_subplot(1, 1, 1)
        color_axis(self.ax)

        super(TrajectoryEnergyWidget, self).__init__(self.fig)
        self.__selectable: bool = selectable
        self._energies = trajectory.get_energies()
        if self._energies:
            self.start = 1.0
            for e in self._energies:
                if e != float('inf'):
                    self.start = e
                    break
            self.end = 1.0
            for e in reversed(self._energies):
                if e != float('inf'):
                    self.end = e
                    break
            self.x = list(range(len(self._energies)))
            for i in reversed(range(len(self._energies))):
                if self._energies[i] == float('inf'):
                    self.x.pop(i)
            self.from_frame_map: List[Optional[int]] = [None for _ in range(len(self._energies))]
            counter = 0
            for i in range(len(self._energies)):
                if self._energies[i] != float('inf'):
                    self.from_frame_map[i] = counter
                    counter += 1
            self.y = [(self._energies[i] - self.start) * 2625.5 for i in self.x]
            self.y_plus_interpolation = []
            self.y_interpolation = []
            self.x_interpolation = []
            current_x = 0
            if self.from_frame_map[0] is None:
                for current_x, val in enumerate(self.from_frame_map):
                    if val is not None:
                        break
                    if len(self.y) > 0:
                        self.y_plus_interpolation.append(self.y[0])
                        self.y_interpolation.append(self.y[0])
                    else:
                        self.y_plus_interpolation.append(0.0)
                        self.y_interpolation.append(0.0)
                    self.x_interpolation.append(current_x)
            for i in range(len(self.x) - 1):
                if self.x[i + 1] != self.x[i] + 1:
                    stride = (self.x[i + 1] - self.x[i])
                    diff = (self.y[i + 1] - self.y[i])
                    for j in range(stride):
                        value = self.y[i] + j * diff / stride
                        self.y_plus_interpolation.append(value)
                        self.y_interpolation.append(value)
                        self.x_interpolation.append(current_x)
                        current_x += 1
                else:
                    self.y_plus_interpolation.append(self.y[i])
                    current_x += 1
            if len(self.y) > 0:
                self.y_plus_interpolation.append(self.y[-1])
            else:
                self.y_plus_interpolation.append(0.0)
            current_x += 1
            for x in range(current_x, len(self._energies)):
                if len(self.y) > 0:
                    self.y_plus_interpolation.append(self.y[-1])
                    self.y_interpolation.append(self.y[-1])
                else:
                    self.y_plus_interpolation.append(0.0)
                    self.y_interpolation.append(0.0)
                self.x_interpolation.append(x)
            self._extrema: np.ndarray = np.array([])
            self._prev_point = None
            self._parent = parent
            self._scatters: Optional[PathCollection] = None
            self._annotations: Optional[Annotation] = None
            self._mark_color = "#bc80bd"
        self.selected_points: Set[int] = set()
        self.update_canvas()

    def update_canvas(self):
        if not self._energies:
            self.fig.set_visible(False)
            self.draw()
            return
        if len(self.y) > 0:
            rel_maximum = np.max(self.y)
            rel_max_pos = self.x[np.argmax(self.y)]
        else:
            rel_maximum = 0.0
            rel_max_pos = 0
        de = (self.end - self.start) * 2625.5
        dedf = rel_maximum
        dedb = rel_maximum + (self.start - self.end) * 2625.5
        self.ax.cla()
        self.ax.plot(self.x_interpolation, self.y_interpolation,
                     color=get_primary_line_color(), linestyle='', marker='x', markersize=5,
                     picker=True, pickradius=5)
        self.ax.plot(self.x, self.y,
                     color=get_primary_line_color(), linestyle='', marker='o', markersize=5,
                     picker=True, pickradius=5)
        start_x = 0
        for i in range(len(self.x) - 1):
            if self.x[i + 1] != self.x[i] + 1:
                self.ax.plot(self.x[start_x:i + 1], self.y[start_x:i + 1],
                             color=get_primary_line_color(), linestyle='--')
                start_x = i + 1
            elif i + 2 == len(self.x):
                self.ax.plot(self.x[start_x:i + 2], self.y[start_x:i + 2],
                             color=get_primary_line_color(), linestyle='--')
        font = get_font()
        self.ax.set_title(
            f"Maximum energy at ({rel_max_pos}, {rel_maximum:.1f})",
            font, color=get_primary_line_color()
        )
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

        # Handle selection of trajectory points
        self.selected_points = set()
        if self.__selectable:
            self.selection, = self.ax.plot([], [],
                                           color=get_secondary_line_color(), linestyle='', marker='o', markersize=10,
                                           picker=True, pickradius=5, zorder=0)

            def toggle_selector(event):
                print(' Key pressed.')
                if event.key in ['Q', 'q'] and toggle_selector.RS.active:
                    print(' RectangleSelector deactivated.')
                    toggle_selector.RS.set_active(False)
                if event.key in ['A', 'a'] and not toggle_selector.RS.active:
                    print(' RectangleSelector activated.')
                    toggle_selector.RS.set_active(True)
            toggle_selector.RS = RectangleSelector(self.ax, self.line_select_callback,
                                                   drawtype='box', useblit=True,
                                                   button=[1, 3],  # don't use middle button
                                                   minspanx=5, minspany=5,
                                                   spancoords='pixels',
                                                   interactive=False)
            self.fig.canvas.mpl_connect('key_press_event', toggle_selector)

    def line_select_callback(self, eclick, erelease):
        'eclick and erelease are the press and release events'
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata
        newly_selected_points: Set[int] = set()
        for x, y in zip(range(len(self._energies)), self.y_plus_interpolation):
            if not (x1 > x > x2 or x2 > x > x1):
                continue
            if not (y1 > y > y2 or y2 > y > y1):
                continue
            newly_selected_points.add(x)
        if eclick.button == 1:
            self.selected_points.update(newly_selected_points)
        elif eclick.button == 3:
            self.selected_points = self.selected_points - newly_selected_points
        self.update_selection()

    def update_selection(self):
        x = list(self.selected_points)
        self.selection.set_xdata(x)
        self.selection.set_ydata([self.y_plus_interpolation[i] for i in x])
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

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
        current_y = self.y_plus_interpolation[current_frame]
        self._prev_point = self.ax.scatter(current_frame, current_y, color="C1", zorder=100)
        self.draw()

    def _find_local_minima_and_maxima(self, n_local: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        values = np.array(self.y_plus_interpolation)
        maxima = argrelextrema(values, np.greater, order=n_local)[0]
        minima = argrelextrema(values, np.less, order=n_local)[0]
        extrema = np.asarray(list(maxima) + list(minima))
        extreme_values = np.array([values[x] for x in extrema])
        self._extrema = extrema
        return self._extrema, extreme_values

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
            text = "rel. energy: {0:.2f}".format(self.y_plus_interpolation[self._extrema[index]])
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


def find_main_window() -> Optional[QMainWindow]:
    # Global function to find the (open) QMainWindow in application
    # Copy of function in __init__.py as this file is imported there
    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            return widget
    return None


class MoleculeVideoWithEnergy(QWidget):

    def __init__(
            self, parent: QWidget, trajectory: utils.MolecularTrajectory,
            width: float = 20, height: float = 3, alternative_zoom_controls: bool = False,
            selectable: bool = True
    ):
        QWidget.__init__(self, parent)
        self.molecule_widget = MoleculeWidget(
            parent=self,
            alternative_zoom_controls=alternative_zoom_controls,
            disable_modification=True
        )
        self.__trajectory = trajectory
        self.video = MoleculeVideo(parent=self, trajectory=trajectory, mol_widget=self.molecule_widget)
        self.plot = TrajectoryEnergyWidget(parent=self, trajectory=trajectory,
                                           width=width, height=height, selectable=selectable)

        self.plot_tool_bar = HeronToolBar(parent=self)
        self.plot_tool_bar.shortened_add_action('save_plot.png', "Save plot", "",
                                                self.plot.save_svg)
        if selectable:
            self.plot_tool_bar.shortened_add_action('save_trajectory.png', "Save Selected Trajectory", "",
                                                    self.__save_selected_trajectory)
            self.plot_tool_bar.shortened_add_action('save_trajectory.png', "Preview Selected Trajectory", "",
                                                    self.__preview_trajectory)

            # Check if there is Scine Art and something to store templates in
            main_window = find_main_window()
            has_rt_storage = False
            if main_window is not None and hasattr(main_window, 'get_reaction_template_storage'):
                rt_storage = main_window.get_reaction_template_storage()
                if rt_storage is not None:
                    has_rt_storage = True

            if "scine_art" in (name for _, name, _ in iter_modules()) and has_rt_storage:
                # If available allow for template extraction from the trajectory
                self.plot_tool_bar.shortened_add_action(
                    'save_trajectory.png',
                    'Extract Reaction Template from Selected Trajectory',
                    '',
                    self.__extract_template
                )

        layout = QVBoxLayout()
        layout.addWidget(self.video)
        layout.addWidget(self.plot)
        layout.addWidget(self.plot_tool_bar)
        self.setLayout(layout)

    def __save_selected_trajectory(self):
        selected_frames = list(self.plot.selected_points)
        if not selected_frames:
            trajectory = self.__trajectory
        else:
            trajectory = utils.MolecularTrajectory(self.__trajectory.elements)
            for i in selected_frames:
                trajectory.push_back(self.__trajectory[i], self.__trajectory.get_energies()[i])

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
            utils.io.write_trajectory(traj_format, str(filename), trajectory)

    def __preview_trajectory(self):
        selected_frames = list(self.plot.selected_points)
        if not selected_frames:
            MoleculeVideoWithEnergyDialog(self, self.__trajectory, selectable=False)
        else:
            selected_trajectory = utils.MolecularTrajectory(self.__trajectory.elements)
            for i in selected_frames:
                selected_trajectory.push_back(self.__trajectory[i], self.__trajectory.get_energies()[i])
            MoleculeVideoWithEnergyDialog(self, selected_trajectory, selectable=False)

    def __extract_template(self):
        selected_frames = list(self.plot.selected_points)
        if not selected_frames:
            trajectory = self.__trajectory
        else:
            trajectory = utils.MolecularTrajectory(self.__trajectory.elements)
            for i in selected_frames:
                trajectory.push_back(self.__trajectory[i], self.__trajectory.get_energies()[i])
        from scine_art.reaction_template import ReactionTemplate
        main_window = find_main_window()
        rt_storage = main_window.get_reaction_template_storage()
        reaction_template = ReactionTemplate.from_trajectory(trajectory)
        rt_storage.add_reaction_template(reaction_template)


class MoleculeVideoWithEnergyDialog(QDialog):
    def __init__(
            self, parent: QWidget, trajectory: utils.MolecularTrajectory,
            width: float = 20, height: float = 3, alternative_zoom_controls: bool = False,
            selectable: bool = True, window_title: str = "Trajectory History",
    ) -> None:
        super(MoleculeVideoWithEnergyDialog, self).__init__(parent)
        self.setWindowTitle(window_title)

        # Create layout and add widgets
        layout = QVBoxLayout()
        self.video = MoleculeVideoWithEnergy(self, trajectory, width, height,
                                             alternative_zoom_controls, selectable)
        layout.addWidget(self.video)

        # Set dialog layout
        self.setLayout(layout)
        self.exec_()


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
