#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from typing import Dict, Optional, Any, List, Union
import json
import numpy as np

import scine_database as db
import scine_utilities as utils
from scine_heron.utilities import (
    color_axis,
    color_figure,
    get_font,
    get_primary_line_color,
    qcolor_by_key,
    build_brush,
    build_pen
)
from scine_heron.database.graphics_items import Compound, Structure, Reaction
from scine_heron.database.compound_and_flasks_helper import get_compound_or_flask
from scine_heron.molecule.molecule_widget import MoleculeWidget
from scine_heron.molecule.molecule_video import MoleculeVideo
from scine_heron.database.energy_query_functions import get_energy_for_structure
from scine_heron.utilities import copy_text_to_clipboard
from scine_heron import get_core_tab

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide2.QtWidgets import (
    QWidget,
    QGraphicsView,
    QGraphicsItem,
    QGraphicsScene,
    QVBoxLayout,
    QHBoxLayout,
    QMenu,
)
from PySide2.QtGui import (
    QPainterPath,
    QGuiApplication,
    QKeySequence,
)
from PySide2.QtCore import (
    Qt,
    QPoint,
    QTimeLine,
    QEvent,
)


class ExpandCompound(QWidget):

    def __init__(self, parent: Optional[QWidget], db_manager: db.Manager, selected_aggregate: dict) -> None:
        super(ExpandCompound, self).__init__(parent=parent)

        self.__selected_aggregate = selected_aggregate
        self.__structures = db_manager.get_collection('structures')
        self.__properties = db_manager.get_collection('properties')

        self.__molecular_viewer = MoleculeWidget(
            parent=self,
            alternative_zoom_controls=True,
            disable_modification=True
        )
        self.__molecular_viewer.setMinimumHeight(200)
        self.__molecular_viewer.setMinimumWidth(200)
        self.__figure = Figure(figsize=(3, 6))
        self.__plot_widget = FigureCanvasQTAgg(self.__figure)
        self.__plot_widget.setMinimumHeight(200)
        self.__plot_widget.setMinimumWidth(200)
        self.__network_widget = ExpandedSingleCompoundNetwork(self, db_manager, selected_aggregate)
        self.__network_widget.setMinimumHeight(400)
        self.__network_widget.setMinimumWidth(400)

        vbox_widget = QWidget()
        vbox = QVBoxLayout()
        vbox.addWidget(self.__molecular_viewer)
        vbox.addWidget(self.__plot_widget)
        vbox_widget.setLayout(vbox)
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__network_widget)
        self.__layout.addWidget(vbox_widget)
        self.setLayout(self.__layout)

        self.__none_duplicate_structures: List[str] = []
        self.__structure_energies_by_id: Dict[str, Optional[float]] = {}
        self.__min_energy: float = 0.0
        self.__number_of_highlights: int = 0
        self.__gather_data()
        self.__init_plot()
        self.__update_plot()

    def __gather_data(self):
        for sid in [x['$oid'] for x in self.__selected_aggregate['structures']]:
            structure = db.Structure(db.ID(sid))
            structure.link(self.__structures)
            # TODO in the future users should have control over this model
            model = structure.get_model()
            if structure.get_label() == db.Label.DUPLICATE:
                continue
            self.__none_duplicate_structures.append(sid)
            energy = get_energy_for_structure(
                structure,
                'electronic_energy',
                model,
                self.__structures,
                self.__properties
            )
            self.__structure_energies_by_id[sid] = energy
        self.__min_energy = min(self.__structure_energies_by_id.values())

    def __init_plot(self):
        self.__ax = self.__figure.add_subplot(1, 1, 1)
        color_figure(self.__figure)
        font = get_font()
        color_axis(self.__ax)
        self.__ax.set_title("Conformer Distribution", font)
        self.__ax.set_ylabel("Relative Electronic Energy in kJ/mol", font)
        self.__ax.set_xlabel(
            f"Min. Conformer Energy: {self.__min_energy:.5f} Hartree"
        )
        self.__ax.set_xticks([])
        self.__ax.xaxis.set_ticklabels([])
        # self.__ax.axes.xaxis.set_visible(False)
        x = [1.0, 2.0]
        for sid in self.__none_duplicate_structures:
            energy = self.__structure_energies_by_id[sid]
            if energy is None:
                continue
            rel_energy = (energy - self.__min_energy) * 2625.5
            y = [rel_energy, rel_energy]
            self.__ax.plot(x, y, color=get_primary_line_color())
        self.__plot_widget.draw()

    def __update_plot(self, highlights: Optional[List[str]] = None):
        x = [1.0, 2.0]
        for _ in range(self.__number_of_highlights):
            self.__ax.lines.pop(-1)
        self.__number_of_highlights = 0
        if highlights is None:
            return
        for sid in highlights:
            energy = self.__structure_energies_by_id[sid]
            if energy is None:
                continue
            rel_energy = (energy - self.__min_energy) * 2625.5
            y = [rel_energy, rel_energy]
            self.__ax.plot(x, y, color="#D40000", linewidth=2)
            self.__number_of_highlights += 1
        self.__plot_widget.draw()

    def update_plot_only(self, structure_id: Optional[str], additional_highlights: Optional[List[str]] = None):
        if structure_id is None or structure_id not in self.__none_duplicate_structures:
            self.__update_plot(highlights=additional_highlights)
        else:
            if additional_highlights is not None:
                self.__update_plot(highlights=[structure_id] + additional_highlights)
            else:
                self.__update_plot(highlights=[structure_id])

    def update_selection_dependent_widgets(
        self,
        structure_id: Optional[str],
        additional_highlights: Optional[List[str]] = None
    ):
        if structure_id is None or structure_id not in self.__none_duplicate_structures:
            atoms = utils.AtomCollection()
            self.__molecular_viewer.update_molecule(atoms=atoms)
            self.__update_plot(highlights=additional_highlights)
        else:
            structure = db.Structure(db.ID(structure_id))
            structure.link(self.__structures)
            atoms = structure.get_atoms()
            self.__molecular_viewer.update_molecule(atoms=atoms)
            if additional_highlights is not None:
                self.__update_plot(highlights=[structure_id] + additional_highlights)
            else:
                self.__update_plot(highlights=[structure_id])


class ExpandedSingleCompoundNetwork(QGraphicsView):
    def __init__(self, parent: Optional[QWidget], db_manager: db.Manager,
                 selected_aggregate: dict, unique_structures: Optional[List[str]] = None) -> None:
        self.scene_object = QGraphicsScene()
        super(ExpandedSingleCompoundNetwork, self).__init__(self.scene_object, parent=parent)
        self.setMouseTracking(True)
        self.setInteractive(True)

        # settings regarding presentation
        self.compound_color = qcolor_by_key('compoundColor')
        self.highlight_color = qcolor_by_key('highlightColor')
        self.border_color = qcolor_by_key('borderColor')
        self.edge_color = qcolor_by_key('edgeColor')
        self.structure_color = qcolor_by_key('structureColor')

        self.structure_brush = build_brush(self.structure_color)
        self.structure_pen = build_pen(self.border_color)
        self.compound_brush = build_brush(self.compound_color)
        self.compound_pen = build_pen(self.border_color)
        self.hover_brush = build_brush(self.highlight_color)
        self.hover_pen = build_pen(self.highlight_color, width=2)
        self.path_pen = build_pen(self.edge_color)

        self.__unique_structures = unique_structures
        if not self.__unique_structures:
            self.__unique_structures = []
            structure_collection = db_manager.get_collection("structures")
            for sid in [x['$oid'] for x in selected_aggregate['structures']]:
                structure = db.Structure(db.ID(sid))
                structure.link(structure_collection)
                if structure.get_label() == db.Label.DUPLICATE:
                    continue
                self.__unique_structures.append(sid)

        # Add all data
        self.db_manager: db.Manager = db_manager
        self.compounds: Dict[Union[str, int], Compound] = {}
        self.centroid_item: Optional[Compound] = None
        self.__current_focus: Optional[str] = None

        self.selected_compound: dict = selected_aggregate
        self.current_hover: Optional[str] = None
        self.item_list: List[List[db.ID]] = [[], []]

        self.plot_network_compound()

    def plot_network_compound(self) -> None:
        # Create singular timer for all added animated items
        self.timer = QTimeLine(1000)
        self.frames = 40
        self.timer.setFrameRange(0, self.frames)

        # db-info of selected compound
        compound_collection = self.db_manager.get_collection("compounds")
        flask_collection = self.db_manager.get_collection("flasks")
        structure_collection = self.db_manager.get_collection("structures")

        # Reset storage
        self.compounds = {}

        # draw selected compound in center
        o_id = db.ID(self.selected_compound['_id']["$oid"])
        if self.selected_compound["_objecttype"] == "compound":
            self.centroid_compound: Union[db.Compound, db.Flask] = db.Compound(o_id, compound_collection)
        elif self.selected_compound["_objecttype"] == "flask":
            self.centroid_compound = db.Flask(o_id, flask_collection)

        self.centroid_item = Compound(
            0, 0, pen=self.compound_pen, brush=self.compound_brush
        )
        self.centroid_item.db_representation = self.centroid_compound

        self.__bind_functions_to_object(self.centroid_item)
        cid_string = self.centroid_compound.id().string()
        self.compounds[cid_string] = self.centroid_item
        self.scene_object.addItem(self.compounds[cid_string])
        self.item_list[0].append(self.centroid_item)

        # calculate angle depending on number of nodes
        if not self.__unique_structures:
            return
        number_of_structures = len(self.__unique_structures)
        angle_alpha = 360 / number_of_structures
        list_of_angles = []
        for i in range(number_of_structures):
            list_of_angles.append(i * angle_alpha)

        # position of nodes in circle around center
        pos = []
        for angle in list_of_angles:
            pos.append((np.cos(np.pi * (angle / 180)), np.sin(np.pi * (angle / 180))))

        # make circle around center-compound out of structure-nodes
        for i, sid in enumerate(self.__unique_structures):
            s = db.Structure(db.ID(sid))
            s.link(structure_collection)

            x = 250 * pos[i][0]
            y = 250 * pos[i][1]
            self.compounds[i] = Structure(
                x, y, pen=self.structure_pen, brush=self.structure_brush
            )
            self.compounds[i].db_representation = s
            self.__bind_functions_to_object(self.compounds[i])
            self.scene_object.addItem(self.compounds[i])
            self.item_list[1].append(self.compounds[i])

            # draw edges between center node and structures
            side_point = QPoint(self.centroid_item.center())
            path = QPainterPath(self.compounds[i].center())
            path.lineTo(side_point)
            self.scene_object.addPath(path, pen=self.path_pen)

        # Move nodes above lines
        self.__move_to_foreground(self.compounds)
        self.timer.start()

    def wheelEvent(self, event):
        modifiers = QGuiApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            zoomInFactor = 1.25
            zoomOutFactor = 1 / zoomInFactor

            # Save the scene pos
            oldPos = self.mapToScene(event.pos())

            # Zoom
            if event.angleDelta().y() > 0:
                zoomFactor = zoomInFactor
            else:
                zoomFactor = zoomOutFactor
            self.scale(zoomFactor, zoomFactor)

            # Get the new position
            newPos = self.mapToScene(event.pos())

            # Move scene to old position
            delta = newPos - oldPos
            self.translate(delta.x(), delta.y())
        elif event.modifiers() == Qt.ShiftModifier:
            self.horizontalScrollBar().wheelEvent(event)
        else:
            self.verticalScrollBar().wheelEvent(event)

    def __move_to_foreground(self, dictionary: Dict[Union[str, int], QGraphicsItem]) -> None:
        for k in dictionary:
            self.scene_object.removeItem(dictionary[k])
            self.scene_object.addItem(dictionary[k])

    def __bind_functions_to_object(self, object: Any) -> None:
        object.bind_mouse_press_function(self.mouse_press_function)
        object.setAcceptHoverEvents(True)
        object.bind_hover_enter_function(self.hover_enter_function)
        object.bind_hover_leave_function(self.hover_leave_function)
        object.bind_menu_function(self.menu_function)

    def menu_function(self, event, item: QGraphicsItem) -> None:
        menu = QMenu()
        copyid_action = menu.addAction('Copy ID')
        copy_masm_graph_action = menu.addAction('Copy Molassembler Graph')
        if isinstance(item, Structure):
            move_action = menu.addAction('Move to Molecular Viewer')
        _ = menu.addAction('Close Menu')
        action = menu.exec_(event.screenPos())  # type: ignore

        if action == copyid_action:
            current_id = item.db_representation.id().string()
            copy_text_to_clipboard(current_id)
        elif action == copy_masm_graph_action:
            if isinstance(item, Compound):
                s = db.Structure(item.db_representation.get_centroid())
                structures = self.db_manager.get_collection("structures")
                s.link(structures)
            if isinstance(item, Structure):
                s = item.db_representation
            if not s.has_graph("masm_cbor_graph"):
                return
            masm_graph = s.get_graph("masm_cbor_graph")
            copy_text_to_clipboard(masm_graph)
        elif isinstance(item, Structure):
            if action == move_action:
                tab = get_core_tab('molecule_viewer')
                if tab is not None:
                    s = item.db_representation
                    tab.update_molecule(atoms=s.get_atoms())

    def keyPressEvent(self, event):
        if (event.type() == QEvent.KeyPress and event == QKeySequence.Copy):
            if self.__current_focus is not None:
                copy_text_to_clipboard(self.__current_focus)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            if not self.itemAt(self.mapToScene(ev.pos()).toPoint()) and self.__current_focus:
                self.__current_focus = None
                self.parent().update_selection_dependent_widgets(None)
                self.__reset_item_colors()
        super().mousePressEvent(ev)

    def __reset_item_colors(self):
        for i in self.item_list[0]:
            i.setPen(self.structure_pen)  # type: ignore
            i.reset_brush()
        for i in self.item_list[1]:
            i.setPen(self.compound_pen)  # type: ignore
            i.reset_brush()

    def mouse_press_function(self, _, item: QGraphicsItem) -> None:
        self.__current_focus = item.db_representation.id().string()
        self.__reset_item_colors()
        item.setPen(self.hover_pen)
        item.setBrush(self.hover_brush)
        item.update()
        if isinstance(item, Compound):
            self.parent().update_selection_dependent_widgets(None)
        elif isinstance(item, Structure):
            self.parent().update_selection_dependent_widgets(self.__current_focus)

    def hover_enter_function(self, _, item: QGraphicsItem) -> None:
        item_db_id_h = item.db_representation.id().string()
        if isinstance(item, Structure):
            self.parent().update_plot_only(
                self.__current_focus,
                additional_highlights=[item_db_id_h]
            )
        if item_db_id_h != self.__current_focus:
            item.setPen(self.hover_pen)
            item.setBrush(self.hover_brush)
            item.update()

    def hover_leave_function(self, _, item: QGraphicsItem) -> None:
        item_db_id = item.db_representation.id().string()
        self.parent().update_plot_only(self.__current_focus, additional_highlights=[])
        if item_db_id != self.__current_focus:
            if isinstance(item, Compound):
                item.setPen(self.compound_pen)
                item.setBrush(self.compound_brush)
            elif isinstance(item, Structure):
                item.setPen(self.structure_pen)
                item.setBrush(self.structure_brush)
            item.update()


class ExpandReaction(QWidget):

    def __init__(self, parent: Optional[QWidget], db_manager: db.Manager, selected_aggregate: dict) -> None:
        super(ExpandReaction, self).__init__(parent=parent)

        self.__selected_aggregate = selected_aggregate
        self.__structures = db_manager.get_collection('structures')
        self.__elementary_steps = db_manager.get_collection('elementary_steps')

        self.__molecular_viewer = MoleculeWidget(
            parent=self,
            alternative_zoom_controls=True,
            disable_modification=True
        )
        self.__molecular_viewer.setMinimumHeight(200)
        self.__molecular_viewer.setMinimumWidth(200)
        self.__molecule_widget = self.__molecular_viewer
        self.__figure = Figure(figsize=(5, 5))
        self.__plot_widget = FigureCanvasQTAgg(self.__figure)
        self.__plot_widget.setMinimumHeight(200)
        self.__plot_widget.setMinimumWidth(200)
        self.__network_widget = ExpandedSingleReactionNetwork(self, db_manager, selected_aggregate)
        self.__network_widget.setMinimumHeight(400)
        self.__network_widget.setMinimumWidth(400)

        self.__vbox_widget = QWidget()
        self.__vbox = QVBoxLayout()
        self.__vbox.addWidget(self.__molecule_widget)
        self.__vbox.addWidget(self.__plot_widget)
        self.__vbox_widget.setLayout(self.__vbox)
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__network_widget)
        self.__layout.addWidget(self.__vbox_widget)
        self.setLayout(self.__layout)

        self.__elementary_step_ids: List[str] = []
        self.__compound_ids: List[str] = []
        self.__mep_splines_fits_by_id: Dict[str, Optional[Any]] = {}
        self.__min_energy: float = 0.0
        self.__number_of_highlights: int = 0
        self.__spline_order: int = 3
        self.__prev_point = None
        self.__current_focus: Optional[str] = None
        self.__gather_data()
        self.__init_plot()

    def __gather_data(self):
        for cid in [x['id']['$oid'] for x in self.__selected_aggregate['lhs']]:
            self.__compound_ids.append(cid)
        for cid in [x['id']['$oid'] for x in self.__selected_aggregate['rhs']]:
            self.__compound_ids.append(cid)
        lhs_energies: List[float] = []
        for sid in [x['$oid'] for x in self.__selected_aggregate['elementary_steps']]:
            step = db.ElementaryStep(db.ID(sid))
            step.link(self.__elementary_steps)
            self.__elementary_step_ids.append(sid)
            if step.has_spline():
                spline = step.get_spline()
                lhs_energies.append(spline.evaluate(0.0, self.__spline_order)[0])
            else:
                spline = None
            self.__mep_splines_fits_by_id[sid] = spline
        if lhs_energies:
            self.__min_energy = min(lhs_energies)

    def __init_plot(self):
        self.__ax = self.__figure.add_subplot(1, 1, 1)
        color_figure(self.__figure)
        font = get_font()
        color_axis(self.__ax)
        self.__ax.set_title("Minimum Energy Paths", font)
        self.__ax.set_ylabel("Relative Electronic Energy in kJ/mol", font)
        self.__ax.set_xlabel(
            f"Relative to: {self.__min_energy:.5f} Hartree"
        )
        x = [i / 1000 for i in range(1001)]
        for spline in self.__mep_splines_fits_by_id.values():
            if spline is None:
                continue
            y = [(spline.evaluate(i / 1000, self.__spline_order)[0] - self.__min_energy) * 2625.5 for i in range(1001)]
            self.__ax.plot(x, y, color=get_primary_line_color())
        self.__plot_widget.draw()

    def __update_plot_highlights(self, highlights: Optional[List[str]] = None):
        x = [i / 1000 for i in range(1001)]
        for _ in range(self.__number_of_highlights):
            self.__ax.lines.pop(-1)
        self.__number_of_highlights = 0
        if highlights is None:
            return
        for sid in highlights:
            if sid not in self.__mep_splines_fits_by_id:
                continue
            spline = self.__mep_splines_fits_by_id[sid]
            if spline is None:
                continue
            y = [(spline.evaluate(i / 1000, self.__spline_order)[0] - self.__min_energy) * 2625.5 for i in range(1001)]
            self.__ax.plot(x, y, color="#D40000", linewidth=2)
            self.__number_of_highlights += 1
        self.__plot_widget.draw()
        if self.__current_focus is None:
            self.__draw_point(0)

    def __draw_point(self, current_frame: int):
        if self.__prev_point is not None:
            self.__prev_point.remove()
            self.__prev_point = None
        if self.__current_focus is None:
            return
        if self.__current_focus not in self.__elementary_step_ids:
            return
        x = current_frame / 49.0
        spline = self.__mep_splines_fits_by_id[self.__current_focus]
        if spline is not None:
            spline_value = spline.evaluate(x, self.__spline_order)[0]
            y = (spline_value - self.__min_energy) * 2625.5
            self.__prev_point = self.__ax.scatter(x, y, color="C1", zorder=100)
            self.__plot_widget.draw()

    @staticmethod
    def __spline_to_trajectory(spline: utils.bsplines.TrajectorySpline, n_frames: int = 50) \
            -> utils.MolecularTrajectory:
        trajectory = utils.MolecularTrajectory()
        _, atoms = spline.evaluate(0, 3)
        trajectory.elements = atoms.elements
        for i in range(n_frames):
            p = i / n_frames
            energy, atoms = spline.evaluate(p, 3)
            trajectory.push_back(atoms.positions, energy)
        return trajectory

    def __update_molecule_widget(self, current_focus):
        if current_focus in self.__elementary_step_ids:
            trajectory: Any = utils.MolecularTrajectory()
            if self.__mep_splines_fits_by_id[current_focus] is not None:
                trajectory = self.__spline_to_trajectory(self.__mep_splines_fits_by_id[current_focus])
            else:
                # barrierless reaction
                s = utils.AtomCollection()
                trajectory.elements = s.elements
                trajectory.push_back(s.positions)
            old_widget = self.__molecule_widget
            n = self.__vbox.indexOf(self.__molecule_widget)
            self.__molecule_widget = MoleculeVideo(
                parent=self,
                trajectory=trajectory,
                mol_widget=self.__molecular_viewer
            )
            if self.__molecule_widget.slider is not None:
                self.__molecule_widget.slider.valueChanged.connect(self.__draw_point)  # pylint: disable=no-member
            self.__vbox.insertWidget(n, self.__molecule_widget)
            if isinstance(old_widget, MoleculeVideo):
                old_widget.close()
            self.__draw_point(0.0)
            return
        elif current_focus in self.__compound_ids or current_focus is None:
            atoms = utils.AtomCollection()
        else:
            structure = db.Structure(db.ID(current_focus))
            structure.link(self.__structures)
            atoms = structure.get_atoms()
        old_widget = self.__molecule_widget
        n = self.__vbox.indexOf(self.__molecule_widget)
        self.__molecule_widget = self.__molecular_viewer
        self.__vbox.insertWidget(n, self.__molecule_widget)
        self.__molecular_viewer.update_molecule(atoms=atoms)
        if isinstance(old_widget, MoleculeVideo):
            old_widget.close()

    def update_selection_dependent_widgets(
        self,
        current_focus: Optional[str] = None,
        current_hover: Optional[str] = None
    ):
        highlights = []
        if current_focus is not None:
            highlights.append(current_focus)
        if current_hover is not None and current_hover != current_focus:
            highlights.append(current_hover)
        if self.__current_focus != current_focus:
            self.__current_focus = current_focus
            self.__update_molecule_widget(current_focus)
        self.__update_plot_highlights(highlights)


class ExpandedSingleReactionNetwork(QGraphicsView):
    # window regarding expand compound
    def __init__(self, parent: Optional[QWidget], db_manager: db.Manager, selected_reaction: dict) -> None:
        self.window_width = 1296   # golden ratio: 800 * 1,62 = 1296
        self.window_height = 800
        self.scene_object = QGraphicsScene(0, 0, self.window_width, self.window_height)
        super(ExpandedSingleReactionNetwork, self).__init__(self.scene_object, parent=parent)

        self.setMouseTracking(True)
        self.setInteractive(True)

        # settings regarding presentation
        self.compound_color = qcolor_by_key('compoundColor')
        self.highlight_color = qcolor_by_key('highlightColor')
        self.border_color = qcolor_by_key('borderColor')
        self.edge_color = qcolor_by_key('edgeColor')
        self.structure_color = qcolor_by_key('structureColor')
        self.elementary_step_color = qcolor_by_key('elementaryStepColor')

        self.structure_brush = build_brush(self.structure_color)
        self.structure_pen = build_pen(self.border_color)
        self.compound_brush = build_brush(self.compound_color)
        self.compound_pen = build_pen(self.border_color)
        self.elementary_step_brush = build_brush(self.elementary_step_color)
        self.elementary_step_pen = build_pen(self.border_color)
        self.hover_brush = build_brush(self.highlight_color)
        self.hover_pen = build_pen(self.highlight_color, width=2)
        self.path_pen = build_pen(self.edge_color)

        # Add all data
        self.__current_focus: Optional[str] = None
        self.__current_hover: Optional[str] = None
        self.recolored_items: List[List[db.ID]] = [[], [], [], []]

        self.selected_reaction = selected_reaction
        self.total_number_compound_rhs = self.selected_reaction["rhs"]
        self.total_number_compound_lhs = self.selected_reaction["lhs"]
        self.total_number_elementary_steps = self.selected_reaction["elementary_steps"]

        self.total_number_structures_rhs: List[dict] = []
        self.total_number_structures_lhs: List[dict] = []

        self.line_items1: Dict[str, Any] = {}
        self.line_items2: Dict[str, Any] = {}
        self.line_items4: Dict[str, Any] = {}
        self.line_items5: Dict[str, Any] = {}
        self.line_lists = [self.line_items1, self.line_items5, self.line_items2, self.line_items4]

        self.db_manager: db.Manager = db_manager
        self.compounds_rhs: Dict[str, Compound] = {}
        self.compounds_lhs: Dict[str, Compound] = {}
        self.structure_rhs: Dict[str, Structure] = {}
        self.structure_lhs: Dict[str, Structure] = {}
        self.elementary: Dict[str, Reaction] = {}

        self.plot_network_reaction()

    def __getitem__(self, i):
        # get information of database
        # to make subscriptable
        return f"{i}"

    def plot_network_reaction(self) -> None:
        # Create singular timer for all added animated items
        self.timer = QTimeLine(1000)
        self.frames = 40
        self.timer.setFrameRange(0, self.frames)

        # db-info of selected compound
        structure_collection = self.db_manager.get_collection("structures")
        compound_collection = self.db_manager.get_collection("compounds")
        flask_collection = self.db_manager.get_collection("flasks")
        elementary_step_collection = self.db_manager.get_collection("elementary_steps")

        # Reset storage
        self.lhs_node_types = []
        self.rhs_node_types = []
        self.compounds_rhs = {}
        self.structure_rhs = {}
        self.elementary = {}
        self.compounds_lhs = {}
        self.structure_lhs = {}

        # Layers #
        pos_elementary_steps_x = self.window_width / 2
        pos_compounds_rhs_x = 40
        pos_structures_rhs_x = (self.window_width / 2 + pos_compounds_rhs_x) / 2
        pos_structures_lhs_x = (3 * self.window_width / 2 - pos_compounds_rhs_x) / 2
        pos_compounds_lhs_x = self.window_width - pos_compounds_rhs_x

        # structure rhs
        list_add_rhs = []
        for rhs_element in self.selected_reaction["rhs"]:
            list_add_rhs.append(rhs_element["id"])
            self.rhs_node_types.append(rhs_element["type"])
            rhs_id = db.ID(rhs_element["id"]["$oid"])
            if rhs_element["type"] == "compound":
                ag: Union[db.Compound, db.Flask] = db.Compound(rhs_id, compound_collection)
                rhs_aggregate = json.loads(str(ag))
            elif rhs_element["type"] == "flask":
                ag = db.Flask(rhs_id, flask_collection)
                rhs_aggregate = json.loads(str(ag))
            else:
                raise RuntimeError("Unknown aggregate type in database.")
            self.total_number_structures_rhs.extend(rhs_aggregate["structures"])
            list_add_rhs.append(rhs_aggregate["structures"])

        self.total_number_structures_rhs = [dict(tupleized) for tupleized in set(
            tuple(item.items()) for item in self.total_number_structures_rhs)]  # reduce duplicated structure

        pos3_y = self.window_height / 2
        all_structure_ids = set()
        for i in range(len(self.total_number_elementary_steps)):
            if i % 2 == 0 or i == 0:
                pos3_y = pos3_y - i * 30
            else:
                pos3_y = pos3_y + i * 30

            elementary_reaction_step = db.ElementaryStep(db.ID(self.total_number_elementary_steps[i]["$oid"]),
                                                         elementary_step_collection)
            self.elementary_reaction_step_item = Reaction(
                pos_elementary_steps_x, pos3_y, pen=self.elementary_step_pen, brush=self.elementary_step_brush
            )
            self.elementary_reaction_step_item.db_representation = elementary_reaction_step
            lhs, rhs = elementary_reaction_step.get_reactants(db.Side.BOTH)
            for lhs_id in lhs:
                all_structure_ids.add(str(lhs_id))
            for rid in rhs:
                all_structure_ids.add(str(rid))

            self.__bind_functions_to_object(self.elementary_reaction_step_item)
            elemen_string = elementary_reaction_step.id().string()
            self.elementary[elemen_string] = self.elementary_reaction_step_item
            self.scene_object.addItem(self.elementary[elemen_string])

        # layer 1 for compound_rhs
        for i in range(len(self.total_number_compound_rhs)):
            pos1_y = self.window_height / 2
            if len(self.total_number_compound_rhs) == 1:
                pos1_y = self.window_height / 2
            else:
                if i % 2 == 0 or i == 0:
                    pos1_y -= 150
                else:
                    pos1_y += 150
            type_str = self.total_number_compound_rhs[i]["type"]
            a_id = db.ID(self.total_number_compound_rhs[i]["id"]["$oid"])
            a_type = db.CompoundOrFlask.COMPOUND if type_str == "compound" else db.CompoundOrFlask.FLASK
            compound_in = get_compound_or_flask(a_id, a_type, compound_collection, flask_collection)
            self.compound_in_item = Compound(
                pos_compounds_rhs_x, pos1_y, pen=self.compound_pen, brush=self.compound_brush
            )
            self.compound_in_item.db_representation = compound_in

            self.__bind_functions_to_object(self.compound_in_item)
            cid_string = compound_in.id().string()
            self.compounds_rhs[cid_string] = self.compound_in_item
            self.scene_object.addItem(self.compounds_rhs[cid_string])

        # layer 2 for structure_rhs
        pos2_y = self.window_height / 2
        relevant_structures_rhs = []
        for i in range(len(self.total_number_structures_rhs)):
            if self.total_number_structures_rhs[i]['$oid'] in all_structure_ids:
                relevant_structures_rhs.append(self.total_number_structures_rhs[i])

        for i, relevant_structure in enumerate(relevant_structures_rhs):
            if i % 2 == 0 or i == 0:
                pos2_y -= i * 50
            else:
                pos2_y += i * 50

            structure_in = db.Structure(db.ID(relevant_structure['$oid']), structure_collection)
            structure_in_item = Structure(
                pos_structures_rhs_x, pos2_y, pen=self.structure_pen, brush=self.structure_brush
            )
            structure_in_item.db_representation = structure_in

            self.__bind_functions_to_object(structure_in_item)
            rhs_string = structure_in.id().string()
            self.structure_rhs[rhs_string] = structure_in_item
            self.scene_object.addItem(self.structure_rhs[rhs_string])

            # add lines layer 12
            ids = [value["id"]['$oid'] for value in self.total_number_compound_rhs]
            side_point = QPoint(structure_in_item.center())
            rid_str = structure_in_item.db_representation.id().string()
            for k, c in enumerate(ids):
                if c == list_add_rhs[0]['$oid']:
                    for j in range(len(list_add_rhs[1])):
                        if rid_str in list_add_rhs[1][j]['$oid']:
                            path = QPainterPath(self.compounds_rhs[c].center())
                            path.lineTo(side_point)
                            lid = rid_str + "_" + c + "_" + str(k)
                            self.line_items1[lid] = self.scene_object.addPath(path, pen=self.path_pen)

                elif c == list_add_rhs[2]['$oid']:
                    for j in range(len(list_add_rhs[3])):
                        if rid_str in list_add_rhs[3][j]['$oid']:
                            path = QPainterPath(self.compounds_rhs[c].center())
                            path.lineTo(side_point)
                            lid = rid_str + "_" + c + "_" + str(k)
                            self.line_items1[lid] = self.scene_object.addPath(path, pen=self.path_pen)

        # layer 5 for compound_lhs
        self.list_compound_out_item = []
        for i in range(len(self.total_number_compound_lhs)):
            pos5_y = self.window_height / 2
            if i % 2 == 0 or i == 0:
                pos5_y += 150
            else:
                pos5_y -= 150

            a_id = db.ID(self.total_number_compound_lhs[i]["id"]["$oid"])
            type_str = self.total_number_compound_lhs[i]["type"]
            a_type = db.CompoundOrFlask.COMPOUND if type_str == "compound" else db.CompoundOrFlask.FLASK
            compound_out = get_compound_or_flask(a_id, a_type, compound_collection, flask_collection)
            compound_out_item = Compound(
                pos_compounds_lhs_x, pos5_y, pen=self.compound_pen, brush=self.compound_brush
            )

            # list of compounds for layer 45 in next loop
            self.list_compound_out_item.append(compound_out_item)

            compound_out_item.db_representation = compound_out

            self.__bind_functions_to_object(compound_out_item)
            comin_string = compound_out.id().string()
            self.compounds_lhs[comin_string] = compound_out_item
            self.scene_object.addItem(self.compounds_lhs[comin_string])

        # structure lhs
        list_add_lhs = []
        for lhs_element in self.selected_reaction["lhs"]:
            list_add_lhs.append(lhs_element["id"])
            self.lhs_node_types.append(lhs_element["type"])

            lhs_id = db.ID(lhs_element["id"]["$oid"])
            if lhs_element["type"] == "compound":
                ag = db.Compound(lhs_id, compound_collection)
                lhs_aggregate = json.loads(str(ag))
            elif lhs_element["type"] == "flask":
                ag = db.Flask(lhs_id, flask_collection)
                lhs_aggregate = json.loads(str(ag))
            else:
                raise RuntimeError("Unknown aggregate type in database.")
            self.total_number_structures_lhs.extend(lhs_aggregate["structures"])
            list_add_lhs.append(lhs_aggregate["structures"])

        self.total_number_structures_lhs = [dict(tupleized) for tupleized in set(
            tuple(item.items()) for item in self.total_number_structures_lhs)]  # reduce dublicated structure

        # layer 4 for structure_lhs
        pos4_y = self.window_height / 2
        relevant_structures_lhs = []
        for i in range(len(self.total_number_structures_lhs)):
            if self.total_number_structures_lhs[i]['$oid'] in all_structure_ids:
                relevant_structures_lhs.append(self.total_number_structures_lhs[i])

        for i, relevant_structure in enumerate(relevant_structures_lhs):
            if i % 2 == 0 or i == 0:
                pos4_y -= i * 50
            else:
                pos4_y += i * 50

            structure_out = db.Structure(db.ID(relevant_structure['$oid']), structure_collection)
            self.structure_out_item = Structure(
                pos_structures_lhs_x, pos4_y, pen=self.structure_pen, brush=self.structure_brush
            )
            self.structure_out_item.db_representation = structure_out

            self.__bind_functions_to_object(self.structure_out_item)
            lhs_string = structure_out.id().string()
            self.structure_lhs[lhs_string] = self.structure_out_item
            self.scene_object.addItem(self.structure_lhs[lhs_string])

            # add lines layer 45
            ids = [value["id"]['$oid'] for value in self.total_number_compound_lhs]
            side_point = QPoint(self.structure_out_item.center())
            rid_str = self.structure_out_item.db_representation.id().string()
            for k, c in enumerate(ids):
                if c == list_add_lhs[0]['$oid']:
                    for j in range(len(list_add_lhs[1])):
                        if rid_str in list_add_lhs[1][j]['$oid']:
                            path = QPainterPath(self.compounds_lhs[c].center())
                            path.lineTo(side_point)
                            lid = rid_str + "_" + c + "_" + str(k)
                            self.line_items5[lid] = self.scene_object.addPath(path, pen=self.path_pen)

                elif c == list_add_lhs[2]['$oid']:
                    for j in range(len(list_add_lhs[3])):
                        if rid_str in list_add_lhs[3][j]['$oid']:
                            path = QPainterPath(self.compounds_lhs[c].center())
                            path.lineTo(side_point)
                            lid = rid_str + "_" + c + "_" + str(k)
                            self.line_items5[lid] = self.scene_object.addPath(path, pen=self.path_pen)

        pos3_y = self.window_height / 2
        for i in range(len(self.total_number_elementary_steps)):
            if i % 2 == 0 or i == 0:
                pos3_y = pos3_y - i * 30
            else:
                pos3_y = pos3_y + i * 30

            elementary_reaction_step = db.ElementaryStep(db.ID(self.total_number_elementary_steps[i]["$oid"]),
                                                         elementary_step_collection)
            self.elementary_reaction_step_item = Reaction(
                pos_elementary_steps_x, pos3_y, pen=self.elementary_step_pen, brush=self.elementary_step_brush
            )
            self.elementary_reaction_step_item.db_representation = elementary_reaction_step
            reactant_structures = elementary_reaction_step.get_reactants(db.Side.BOTH)
            self.elementary_reaction_step_item.lhs_ids = [db_id.string() for db_id in reactant_structures[0]]
            self.elementary_reaction_step_item.rhs_ids = [db_id.string() for db_id in reactant_structures[1]]

            self.__bind_functions_to_object(self.elementary_reaction_step_item)
            elemen_string = elementary_reaction_step.id().string()
            self.elementary[elemen_string] = self.elementary_reaction_step_item
            self.elementary[elemen_string].setAcceptHoverEvents(True)
            self.elementary[elemen_string].bind_hover_enter_function(
                self.hover_enter_function
            )
            self.elementary[elemen_string].bind_hover_leave_function(
                self.hover_leave_function
            )
            self.scene_object.addItem(self.elementary[elemen_string])

        for i, key in enumerate(self.elementary):
            elementary_step_item = self.elementary[key]
            # add lines layer 34
            for lhs_id_str in elementary_step_item.lhs_ids:
                if lhs_id_str in self.structure_lhs:
                    side_point = QPoint(elementary_step_item.rhs())
                    path = QPainterPath(self.structure_lhs[lhs_id_str].center())
                    path.lineTo(side_point)
                    lid = key + "_" + lhs_id_str + "_" + str(i)
                    self.line_items4[lid] = self.scene_object.addPath(path, pen=self.path_pen)

            # add lines layer 23
            for rhs_id_str in elementary_step_item.rhs_ids:
                if rhs_id_str in self.structure_rhs:
                    side_point = QPoint(elementary_step_item.lhs())
                    path = QPainterPath(self.structure_rhs[rhs_id_str].center())
                    path.lineTo(side_point)
                    lid = key + "_" + rhs_id_str + "_" + str(i)
                    self.line_items2[lid] = self.scene_object.addPath(path, pen=self.path_pen)

        # move nodes above lines
        self.__move_to_foreground(self.compounds_rhs)
        self.__move_to_foreground(self.structure_rhs)
        self.__move_to_foreground(self.elementary)
        self.__move_to_foreground(self.structure_lhs)
        self.__move_to_foreground(self.compounds_lhs)

        self.timer.start()

        self.scene_object.update()
        self.view = QGraphicsView(self.scene_object)

    def __move_to_foreground(self, dictionary: Dict[str, QGraphicsItem]) -> None:
        for k in dictionary:
            self.scene_object.removeItem(dictionary[k])
            self.scene_object.addItem(dictionary[k])

    def __bind_functions_to_object(self, object: Any) -> None:
        object.bind_mouse_press_function(self.mouse_press_function)
        object.setAcceptHoverEvents(True)
        object.bind_hover_enter_function(self.hover_enter_function)
        object.bind_hover_leave_function(self.hover_leave_function)
        object.bind_menu_function(self.menu_function)

    def menu_function(self, event, item: QGraphicsItem) -> None:
        menu = QMenu()
        copyid_action = menu.addAction('Copy ID')
        if isinstance(item, Structure) or isinstance(item, Compound):
            copy_masm_graph_action = menu.addAction('Copy Molassembler Graph')
        if isinstance(item, Structure):
            move_action = menu.addAction('Move to Molecular Viewer')
        if isinstance(item, Reaction):
            if item.db_representation.has_transition_state():
                move_ts_action = menu.addAction('Move TS to Molecular Viewer')
        _ = menu.addAction('Close Menu')
        action = menu.exec_(event.screenPos())  # type: ignore

        if action == copyid_action:
            current_id = item.db_representation.id().string()
            copy_text_to_clipboard(current_id)
        if isinstance(item, Structure) or isinstance(item, Compound):
            if action == copy_masm_graph_action:
                if isinstance(item, Compound):
                    s = db.Structure(item.db_representation.get_centroid())
                    structures = self.db_manager.get_collection("structures")
                    s.link(structures)
                if isinstance(item, Structure):
                    s = item.db_representation
                if not s.has_graph("masm_cbor_graph"):
                    return
                masm_graph = s.get_graph("masm_cbor_graph")
                copy_text_to_clipboard(masm_graph)
        if isinstance(item, Structure):
            if action == move_action:
                tab = get_core_tab('molecule_viewer')
                if tab is not None:
                    s = item.db_representation
                    tab.update_molecule(atoms=s.get_atoms())
        if isinstance(item, Reaction):
            if item.db_representation.has_transition_state():
                if action == move_ts_action:
                    tab = get_core_tab('molecule_viewer')
                    if tab is not None:
                        es = item.db_representation
                        tsid = es.get_transition_state()
                        s = db.Structure(tsid)
                        structures = self.db_manager.get_collection("structures")
                        s.link(structures)
                        tab.update_molecule(atoms=s.get_atoms())

    def __reset_item_colors(self):
        for i in self.recolored_items[0]:
            i.setPen(self.structure_pen)  # type: ignore
            i.reset_brush()
        for i in self.recolored_items[1]:
            i.setPen(self.compound_pen)  # type: ignore
            i.reset_brush()
        for i in self.recolored_items[2]:
            i.setPen(self.elementary_step_pen)  # type: ignore
            i.reset_brush()
        for i in self.recolored_items[3]:
            i.setPen(self.path_pen)  # type: ignore
        self.recolored_items = [[] for _ in self.recolored_items]

    def mouse_press_function(self, _, item: QGraphicsItem) -> None:
        if self.__current_focus == item.db_representation.id().string():
            return
        self.__current_focus = item.db_representation.id().string()
        self.parent().update_selection_dependent_widgets(self.__current_focus, self.__current_hover)
        self.__reset_item_colors()
        item.setPen(self.hover_pen)
        item.setBrush(self.hover_brush)
        item.update()
        if isinstance(item, Compound):
            self.recolored_items[1].append(item)
        elif isinstance(item, Reaction):
            self.recolored_items[2].append(item)
        elif isinstance(item, Structure):
            self.recolored_items[0].append(item)
        for line_list in self.line_lists:
            for key in line_list.keys():
                if self.__current_focus in key:  # type: ignore
                    line_list[key].setPen(self.hover_pen)  # type: ignore
                    self.recolored_items[3].append(line_list[key])

    def hover_enter_function(self, _, item: QGraphicsItem) -> None:
        self.__current_hover = item.db_representation.id().string()
        self.parent().update_selection_dependent_widgets(self.__current_focus, self.__current_hover)
        item_db_id_h = item.db_representation.id().string()

        if item_db_id_h != self.__current_focus:
            item.setPen(self.hover_pen)
            item.setBrush(self.hover_brush)
            item.update()
            if isinstance(item, Compound):
                for j in range(len(self.line_lists[:2])):
                    for k in self.line_lists[:2][j].keys():
                        if item_db_id_h in k:
                            self.line_lists[:2][j][k].setPen(self.hover_pen)
            elif isinstance(item, Reaction):
                # Key of selected elementary_reaction_step
                key_item = [key for key, value in self.elementary.items() if value == item]
                for j in range(len(self.line_lists[2:])):
                    for k in self.line_lists[2:][j].keys():
                        if (key_item[0]) in k:
                            self.line_lists[2:][j][k].setPen(self.hover_pen)
            elif isinstance(item, Structure):
                for j in range(len(self.line_lists)):
                    for k in self.line_lists[j].keys():
                        if item_db_id_h in k:
                            self.line_lists[j][k].setPen(self.hover_pen)

    def hover_leave_function(self, _, item: QGraphicsItem) -> None:
        self.__current_hover = None
        self.parent().update_selection_dependent_widgets(self.__current_focus, self.__current_hover)
        item_db_id = item.db_representation.id().string()

        if item_db_id != self.__current_focus:
            if isinstance(item, Compound):
                item.setPen(self.compound_pen)
                item.setBrush(self.compound_brush)
            elif isinstance(item, Reaction):
                item.setPen(self.elementary_step_pen)
                item.setBrush(self.elementary_step_brush)
            elif isinstance(item, Structure):
                item.setPen(self.structure_pen)
                item.setBrush(self.structure_brush)

            for j in range(len(self.line_lists)):
                for k in self.line_lists[j].keys():
                    if item_db_id in k:
                        self.line_lists[j][k].setPen(self.path_pen)
            item.update()

    def keyPressEvent(self, event):
        if (event.type() == QEvent.KeyPress and event == QKeySequence.Copy):
            if self.__current_focus is not None:
                copy_text_to_clipboard(self.__current_focus)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            if not self.itemAt(self.mapToScene(ev.pos()).toPoint()) and self.__current_focus:
                self.__current_focus = None
                self.parent().update_selection_dependent_widgets(self.__current_focus, self.__current_hover)
                self.__reset_item_colors()
        super().mousePressEvent(ev)

    def wheelEvent(self, event):
        modifiers = QGuiApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            zoomInFactor = 1.25
            zoomOutFactor = 1 / zoomInFactor

            # Save the scene pos
            oldPos = self.mapToScene(event.pos())

            # Zoom
            if event.angleDelta().y() > 0:
                zoomFactor = zoomInFactor
            else:
                zoomFactor = zoomOutFactor
            self.scale(zoomFactor, zoomFactor)

            # Get the new position
            newPos = self.mapToScene(event.pos())

            # Move scene to old position
            delta = newPos - oldPos
            self.translate(delta.x(), delta.y())
        elif event.modifiers() == Qt.ShiftModifier:
            self.horizontalScrollBar().wheelEvent(event)
        else:
            self.verticalScrollBar().wheelEvent(event)
