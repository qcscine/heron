#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
import json
from typing import Any, Optional, List, Dict, Union

import scine_utilities as utils
import scine_database as db

from scine_heron.database.graphics_items import Compound, Reaction
from scine_heron.molecule.molecule_video import MoleculeVideo
from scine_heron.molecule.molecule_widget import MoleculeWidget
from scine_heron.molecule.reaction_profile import ReactionProfileWidget
from scine_heron.utilities import (
    copy_text_to_clipboard,
    qcolor_by_key,
    build_brush,
    build_pen,
)

from PySide2.QtWidgets import (
    QGraphicsItem,
    QGraphicsView,
    QWidget,
    QGraphicsScene,
    QLayout,
    QMenu,
    QFileDialog
)
from PySide2.QtGui import (
    QKeySequence,
    QGuiApplication,
    QPainter,
)
from PySide2.QtSvg import (
    QSvgGenerator,
)
from PySide2.QtCore import (
    Qt,
    QEvent,
    QSize
)


class ReactionAndCompoundViewSettings(QWidget):
    def __init__(self, parent: QWidget, parsed_layout: QLayout):
        super(ReactionAndCompoundViewSettings, self).__init__(parent)
        self.p_layout = parsed_layout
        self.mol_widget_cache = MoleculeWidget(
            parent=self,
            alternative_zoom_controls=True,
            disable_modification=True
        )
        self.mol_widget = self.mol_widget_cache
        self.es_mep_widget = ReactionProfileWidget(parent=self)

    def update_molecule_widget(self, new_widget):
        self.p_layout.removeWidget(self.mol_widget)
        if isinstance(self.mol_widget, MoleculeVideo):
            self.mol_widget.close()
        self.p_layout.addWidget(new_widget)
        self.mol_widget = new_widget


class ReactionAndCompoundView(QGraphicsView):
    def __init__(self, parent: QWidget, width: Optional[int] = None, height: Optional[int] = None):

        if width and height:
            self.scene_object = QGraphicsScene(0, 0, width, height)
        else:
            self.scene_object = QGraphicsScene()

        super(ReactionAndCompoundView, self).__init__(self.scene_object, parent=parent)
        self.settings: Union[None, ReactionAndCompoundViewSettings] = None

        # settings regarding presentation
        self.compound_color = qcolor_by_key('compoundColor')
        self.reaction_color = qcolor_by_key('reactionColor')
        self.highlight_color = qcolor_by_key('highlightColor')
        self.border_color = qcolor_by_key('borderColor')
        self.edge_color = qcolor_by_key('edgeColor')
        self.association_color = qcolor_by_key('associationColor')
        self.flask_color = qcolor_by_key('flaskColor')

        self.reaction_brush = build_brush(self.reaction_color)
        self.reaction_pen = build_pen(self.border_color)
        self.compound_brush = build_brush(self.compound_color)
        self.compound_pen = build_pen(self.border_color)
        self.flask_brush = build_brush(self.flask_color)
        self.association_brush = build_brush(self.association_color)
        self.hover_brush = build_brush(self.highlight_color)
        self.hover_pen = build_pen(self.highlight_color, width=2)
        self.path_pen = build_pen(self.edge_color)

        self.compound_db_id_cache: List[QGraphicsItem] = []
        self.compound_db_line_cache: List[QGraphicsItem] = []
        self.reaction_db_id_cache: List[QGraphicsItem] = []
        self.reaction_db_line_cache: List[QGraphicsItem] = []
        self.item_list = [(self.compound_db_id_cache, self.compound_db_line_cache),
                          (self.reaction_db_id_cache, self.reaction_db_line_cache)]
        self.focused_item_db_id: Optional[str] = None
        self.focused_item: Optional[QGraphicsItem] = None

        self.compounds: Dict[str, List[Compound]] = dict()
        self.reactions: Dict[str, List[Reaction]] = dict()
        self.line_items: Dict[str, Any] = {}

        self.__expanded_views: List[QWidget] = []

    def save_svg(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save File"),  # type: ignore[arg-type]
            "network.svg",
            self.tr("Vector Graphics (*.svg)"),  # type: ignore[arg-type]
        )
        generator = QSvgGenerator()
        generator.setFileName(filename)
        generator.setSize(QSize(self.sceneRect().width(), self.sceneRect().height()))
        painter = QPainter()
        painter.begin(generator)
        self.scene_object.render(painter)
        painter.end()

    def move_to_foreground(self, dictionary: Dict[str, List[QGraphicsItem]]) -> None:
        for k in dictionary.values():
            for item in k:
                self.scene_object.removeItem(item)
                self.scene_object.addItem(item)

    def add_to_compound_list(self, item: Compound):
        str_id = item.db_representation.id().string()
        if str_id in self.compounds:
            self.compounds[str_id].append(item)
        else:
            self.compounds[str_id] = [item]

    def add_to_reaction_list(self, item: Reaction):
        str_id = item.db_representation.id().string()
        if str_id in self.reactions:
            self.reactions[str_id].append(item)
        else:
            self.reactions[str_id] = [item]

    def set_settings_widget(self, settings_widget: ReactionAndCompoundViewSettings):
        self.settings = settings_widget

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

    def get_aggregate_brush(self, a_type: db.CompoundOrFlask):
        if a_type == db.CompoundOrFlask.FLASK:
            return self.flask_brush
        return self.compound_brush

    def get_reaction_brush(self, elementary_step_type: db.ElementaryStepType):
        if elementary_step_type == db.ElementaryStepType.BARRIERLESS:
            return self.association_brush
        return self.reaction_brush

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

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            if not self.itemAt(self.mapToScene(ev.pos()).toPoint()) and self.focused_item:
                self.reset_node_focus()
        super().mousePressEvent(ev)

    def reset_node_focus(self):
        self.reset_item_colors()
        n = self.settings.p_layout.indexOf(self.settings.mol_widget)
        trajectory: Any = utils.MolecularTrajectory()
        s = utils.AtomCollection()
        trajectory.elements = s.elements
        trajectory.push_back(s.positions)
        new_widget = MoleculeVideo(
            parent=self,
            trajectory=trajectory,
            mol_widget=self.settings.mol_widget_cache
        )
        self.settings.update_molecule_widget(new_widget)
        self.settings.es_mep_widget.update_canvas()
        self.settings.p_layout.insertWidget(n, new_widget)
        self.settings.p_layout.update()

    def keyPressEvent(self, event):
        if (event.type() == QEvent.KeyPress and event == QKeySequence.Copy):
            clipboard = QGuiApplication.clipboard()
            if self.focused_item_db_id is not None and \
                    self.focused_item_db_id not in list(self.reactions.keys()):
                text = self.focused_item_db_id
            elif len(self.compounds) != 0:
                text = list(self.compounds.keys())[0]
            else:
                text = ""
            clipboard.setText(text)

    def reset_item_colors(self):
        for i, tup in enumerate(self.item_list):
            pen = self.compound_pen if i == 0 else self.reaction_pen
            for reaction_or_compound in tup[0]:
                reaction_or_compound.setPen(pen)
                reaction_or_compound.reset_brush()
            for line in tup[1]:
                line.setPen(self.path_pen)
            tup[0].clear()
            tup[1].clear()

    def set_brush_pen_for_all_identical_items(self, str_id: str, is_compound: bool):
        if is_compound:
            id_list = self.reaction_db_id_cache
            line_list = self.reaction_db_line_cache
            item_list = self.compounds
        else:
            id_list = self.compound_db_id_cache
            line_list = self.compound_db_line_cache
            item_list = self.reactions
        for item in item_list[str_id]:
            item.setPen(self.hover_pen)
            item.setBrush(self.hover_brush)
            id_list.append(item)
            if self.focused_item_db_id is not None:
                for k in self.line_items.keys():
                    if self.focused_item_db_id in k:
                        self.line_items[k].setPen(self.hover_pen)
                        line_list.append(self.line_items[k])
            item.update()

    def set_hover(self, item: QGraphicsItem) -> None:
        item_db_id_h = item.db_representation.id().string()
        item.setPen(self.hover_pen)
        item.setBrush(self.hover_brush)
        for k in self.line_items.keys():
            if item_db_id_h in k:
                self.line_items[k].setPen(self.hover_pen)
        item.update()

    def reset_hover(self, item: QGraphicsItem) -> None:
        item_db_id = item.db_representation.id().string()

        if isinstance(item, Compound):
            item.setPen(self.compound_pen)
            item.reset_brush()
        else:
            item.setPen(self.reaction_pen)
            item.reset_brush()

        for k in self.line_items.keys():
            if self.focused_item_db_id is not None:
                if item_db_id in k and self.focused_item_db_id not in k:
                    self.line_items[k].setPen(self.path_pen)
            else:
                if item_db_id in k:
                    self.line_items[k].setPen(self.path_pen)
        item.update()

    def mouse_press_function(self, _, item: QGraphicsItem) -> None:
        if not self.settings:
            raise RuntimeError('Settings were never added to the reaction compound widget.')
        # update widget
        self.focused_item = item
        if item.db_representation is not None:
            self.focused_item_db_id = str(item.db_representation.id())
        trajectory: Any = utils.MolecularTrajectory()

        mol_widget = self.settings.mol_widget_cache
        n = self.settings.p_layout.indexOf(self.settings.mol_widget)
        if isinstance(item, Reaction):
            if item.spline is not None:
                trajectory = self.__spline_to_trajectory(item.spline)
            else:
                # barrierless reaction currently no trajectory info and no static structure to display
                s = utils.AtomCollection()
                if item.structure is not None:
                    s = item.structure
                trajectory.elements = s.elements
                trajectory.push_back(s.positions)
            new_widget = MoleculeVideo(parent=self, trajectory=trajectory, mol_widget=mol_widget)
            self.settings.update_molecule_widget(new_widget)
            self.settings.es_mep_widget.update_canvas(item.spline, item.get_energy_difference())
            self.reset_item_colors()

            # color selection
            self.set_brush_pen_for_all_identical_items(item.db_representation.id().string(), False)

        elif isinstance(item, Compound):
            # update widget
            if item.structure is not None:
                trajectory.elements = item.structure.elements
                trajectory.push_back(item.structure.positions)
            new_widget = MoleculeVideo(parent=self, trajectory=trajectory, mol_widget=mol_widget)
            self.settings.update_molecule_widget(new_widget)
            self.settings.es_mep_widget.update_canvas()
            self.reset_item_colors()

            # color selection
            self.set_brush_pen_for_all_identical_items(item.db_representation.id().string(), True)

        # set new widget
        self.settings.p_layout.insertWidget(n, new_widget)
        self.settings.p_layout.update()

    def hover_enter_function(self, _, item: QGraphicsItem) -> None:
        item_db_id_h = item.db_representation.id().string()
        if item_db_id_h != self.focused_item_db_id:
            if isinstance(item, Compound):
                if item_db_id_h in self.compounds:
                    for same_item in self.compounds[item_db_id_h]:
                        self.set_hover(same_item)
            else:
                if item_db_id_h in self.reactions:
                    for same_item in self.reactions[item_db_id_h]:
                        self.set_hover(same_item)

    def hover_leave_function(self, _, item: QGraphicsItem) -> None:
        item_db_id = item.db_representation.id().string()

        if item_db_id != self.focused_item_db_id:
            if isinstance(item, Compound):
                if item_db_id in self.compounds:
                    for same_item in self.compounds[item_db_id]:
                        self.reset_hover(same_item)
            else:
                if item_db_id in self.reactions:
                    for same_item in self.reactions[item_db_id]:
                        self.reset_hover(same_item)

    def menu_function(self, event, item: QGraphicsItem) -> None:
        menu = QMenu()
        popup_action = menu.addAction('Expand in Pop-Up')
        copyid_action = menu.addAction('Copy ID')
        if isinstance(item, Compound):
            copy_masm_graph_action = menu.addAction('Copy Molassembler Graph')
            move_action = menu.addAction('Move to Molecular Viewer')
        if isinstance(item, Reaction):
            has_ts = bool(item.spline is not None)
            if has_ts:
                move_ts_action = menu.addAction('Move TS to Molecular Viewer')
        _ = menu.addAction('Close Menu')
        action = menu.exec_(event.screenPos())  # type: ignore
        if action == popup_action:
            self.__expand_in_new_window(item)
        elif action == copyid_action:
            current_id = self.__get_id_of_current_item(item)
            copy_text_to_clipboard(current_id)
        elif isinstance(item, Compound):
            if action == copy_masm_graph_action:
                current_graph = self.__get_masm_graph_of_current_compound(item)
                copy_text_to_clipboard(current_graph)
            elif action == move_action:
                self.__move_structure_to_main_viewer(item)
        elif isinstance(item, Reaction):
            if has_ts:
                if action == move_ts_action:
                    self.__move_structure_to_main_viewer(item)

    def __expand_in_new_window(self, item: QGraphicsItem):
        if isinstance(item, Compound):
            from scine_heron.database.expand_widget import ExpandCompound
            selected_compound = item.db_representation
            # from str to dict transformation
            selected_compound_dict = json.loads(f"{selected_compound}")
            self.__expanded_views.append(ExpandCompound(None, self.db_manager, selected_compound_dict))
            self.__expanded_views[-1].setWindowTitle("Unique Conformers in Aggregate")
            self.__expanded_views[-1].show()
        elif isinstance(item, Reaction):
            from scine_heron.database.expand_widget import ExpandReaction
            selected_reaction = item.db_representation
            selected_reaction_dict = json.loads(f"{selected_reaction}")
            self.__expanded_views.append(ExpandReaction(None, self.db_manager, selected_reaction_dict))
            self.__expanded_views[-1].setWindowTitle("Unique Conformers in Aggregate")
            self.__expanded_views[-1].show()

    def __move_structure_to_main_viewer(self, item: QGraphicsItem):
        from scine_heron import get_core_tab
        tab = get_core_tab('molecule_viewer')
        if tab is not None:
            tab.update_molecule(atoms=item.structure)

    def __get_id_of_current_item(self, item: QGraphicsItem):
        if isinstance(item, Compound) or isinstance(item, Reaction):
            item_id = item.db_representation.id().string()
            return item_id

    def __get_masm_graph_of_current_compound(self, item: QGraphicsItem) -> str:
        if isinstance(item, Compound):
            structures = self.db_manager.get_collection("structures")
            s = db.Structure(item.db_representation.get_centroid())
            s.link(structures)
            if not s.has_graph("masm_cbor_graph"):
                return "No graph available"
            masm_graph = s.get_graph("masm_cbor_graph")
            return masm_graph
        else:
            return "No graph available"
