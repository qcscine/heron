#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
import json
import numpy as np
from typing import Any, Optional, List, Dict, Tuple, Union

import scine_utilities as utils
import scine_database as db
from scine_database.energy_query_functions import (
    get_barriers_for_elementary_step_by_type,
    get_elementary_step_with_min_ts_energy
)
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
    QGraphicsPathItem,
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
        self.p_layout.replaceWidget(self.mol_widget, new_widget)
        if isinstance(self.mol_widget, MoleculeVideo):
            self.mol_widget.close()
        self.mol_widget = new_widget
        self.mol_widget.show()


class ReactionAndCompoundView(QGraphicsView):
    def __init__(self, parent: QWidget, width: Optional[int] = None, height: Optional[int] = None):

        if width and height:
            self.scene_object = QGraphicsScene(0, 0, width, height)
        else:
            self.scene_object = QGraphicsScene()

        super(ReactionAndCompoundView, self).__init__(self.scene_object, parent=parent)
        self.settings: ReactionAndCompoundViewSettings

        # settings regarding presentation
        self.compound_color = qcolor_by_key('compoundColor')
        self.gray_out_color = qcolor_by_key('grayOutColor')
        self.reaction_color = qcolor_by_key('reactionColor')
        self.highlight_color = qcolor_by_key('highlightColor')
        self.border_color = qcolor_by_key('borderColor')
        self.border_gray_color = qcolor_by_key('borderGrayColor')
        self.edge_color = qcolor_by_key('edgeColor')
        self.association_color = qcolor_by_key('associationColor')
        self.flask_color = qcolor_by_key('flaskColor')

        # rendering smoother lines and edges of nodes
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        self.reaction_brush = build_brush(self.reaction_color)
        self.reaction_pen = build_pen(self.border_color)
        self.compound_brush = build_brush(self.compound_color)
        self.compound_pen = build_pen(self.border_color)
        self.gray_border_pen = build_pen(self.border_gray_color)
        self.flask_brush = build_brush(self.flask_color)
        self.association_brush = build_brush(self.association_color)
        self.hover_brush = build_brush(self.highlight_color)
        self.hover_pen = build_pen(self.highlight_color, width=2)
        self.gray_out_pen = build_pen(self.gray_out_color)
        self.path_pen = build_pen(self.edge_color)

        self.focused_item_db_id: Optional[str] = None
        self.focused_item: Optional[QGraphicsItem] = None
        self.focused_connected_items: List[str] = []
        self.focused_connected_lines: List[str] = []

        self.view_highlighted = False

        self.compounds: Dict[str, List[Compound]] = dict()
        self.reactions: Dict[str, List[Reaction]] = dict()
        self.line_items: Dict[str, QGraphicsPathItem] = dict()

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

    def replace_in_compound_list(self, item: Compound):
        str_id = item.db_representation.id().string()
        self.compounds[str_id] = [item]

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
            if not isinstance(self.itemAt(ev.pos()), Compound) and not isinstance(self.itemAt(ev.pos()), Reaction):
                self.reset_node_focus()
        super().mousePressEvent(ev)

    def reset_node_focus(self):
        self.reset_item_colors()
        # NOTE: Guess this is somewhat causing the weird blink
        self.settings.es_mep_widget.clear_canvas()

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
        # # # Reset all compounds
        for c_list in self.compounds.values():
            for entry in c_list:
                entry.reset_brush()
        # # # Reset all reactions
        for r_list in self.reactions.values():
            for entry in r_list:
                entry.reset_brush()
        # # # Reset all lines
        for line in self.line_items.values():
            line.setPen(self.path_pen)

        self.view_highlighted = False

    # NOTE: Ideally, this should be derived from the subgraph of a centroid; would require the cache to be attribute of
    # this class.
    def set_brush_pen_for_connected_items(self, str_id: str):
        # # # Derive connected items and lines, would be better with graph
        self.focused_connected_items = [str_id]
        self.focused_connected_lines = []
        for edge_key in self.line_items.keys():
            if str_id in edge_key:
                self.focused_connected_items += [c_item[0:24] for c_item in edge_key.split("_")[0:2]
                                                 if str_id != c_item[0:24]]
                self.focused_connected_lines.append(edge_key)

        for item_key in self.compounds.keys():
            if item_key in self.focused_connected_items:
                self.scene_object.removeItem(self.compounds[item_key][0])
                self.scene_object.addItem(self.compounds[item_key][0])
                continue
            else:
                entry = self.compounds[item_key]
                for item in entry:
                    item.set_current_brush(self.gray_out_color)
                    item.set_current_pen(self.gray_border_pen)

        for item_key in self.reactions.keys():
            if item_key in self.focused_connected_items:
                self.scene_object.removeItem(self.reactions[item_key][0])
                self.scene_object.addItem(self.reactions[item_key][0])
                continue
            else:
                entry = self.reactions[item_key]
                for item in entry:
                    item.set_current_brush(self.gray_out_color)
                    item.set_current_pen(self.gray_border_pen)

        for line_key in self.line_items.keys():
            if line_key in self.focused_connected_lines:
                continue
            else:
                self.line_items[line_key].setPen(self.gray_out_pen)

        self.view_highlighted = True

    def set_hover(self, item: QGraphicsItem) -> None:
        item_db_id_h = item.db_representation.id().string()
        item.setPen(self.hover_pen)
        item.setBrush(self.hover_brush)

        for k in self.line_items.keys():
            if item_db_id_h in k:
                self.line_items[k].setPen(self.hover_pen)

    def reset_hover(self, item: QGraphicsItem) -> None:
        item_db_id = item.db_representation.id().string()
        # # # Choose correct brush during hover
        if self.view_highlighted and item_db_id not in self.focused_connected_items:
            line_pen = self.gray_out_pen
            border_pen = self.gray_border_pen
            item.set_current_brush(self.gray_out_color)
            item.set_current_pen(self.gray_border_pen)
        else:
            line_pen = self.path_pen
            border_pen = self.compound_pen if isinstance(item, Compound) else self.reaction_pen
            item.reset_brush()

        if item_db_id == self.focused_item_db_id:
            border_pen = self.hover_pen
        item.set_current_pen(border_pen)
        for k in self.line_items.keys():
            if item_db_id in k:
                self.line_items[k].setPen(line_pen)

    def mouse_press_function(self, _, item: QGraphicsItem) -> None:
        if not self.settings:
            raise RuntimeError('Settings were never added to the reaction compound widget.')
        # update widget
        self.focused_item = item
        if item.db_representation is not None:
            self.focused_item_db_id = str(item.db_representation.id())
        trajectory: Any = utils.MolecularTrajectory()

        mol_widget = self.settings.mol_widget_cache
        mol_index = self.settings.p_layout.indexOf(self.settings.mol_widget)
        charge = None
        mult = None
        if isinstance(item, Reaction):
            if item.spline is not None:
                trajectory = self.__spline_to_trajectory(item.spline)
                # invert trajectory if required
                if item.invert_direction:
                    trajectory = trajectory[::-1]
                # TODO: Avoid database call here!
                step = db.ElementaryStep(item.assigned_es_id, self._elementary_step_collection)
                ts = db.Structure(step.get_transition_state(), self._structure_collection)
                charge = ts.get_charge()
                mult = ts.get_multiplicity()
            else:
                # barrierless reaction currently no trajectory info and no static structure to display
                s = utils.AtomCollection()
                trajectory.elements = s.elements
                trajectory.push_back(s.positions)

            new_widget = MoleculeVideo(parent=self, trajectory=trajectory, mol_widget=mol_widget)
            self.settings.es_mep_widget.update_canvas(item.spline,
                                                      item.barriers,
                                                      new_widget.changed_frame,
                                                      item.invert_direction,
                                                      not item.barrierless_type)

        elif isinstance(item, Compound):
            # update widget
            # get PES info
            centroid = db.Structure(item.db_representation.get_centroid(), self._structure_collection)
            charge = centroid.get_charge()
            mult = centroid.get_multiplicity()
            # get atoms
            centroid_atoms = centroid.get_atoms()
            trajectory.elements = centroid_atoms.elements
            trajectory.push_back(centroid_atoms.positions)
            self.settings.es_mep_widget.clear_canvas()
            new_widget = MoleculeVideo(parent=self, trajectory=trajectory, mol_widget=mol_widget)

        # Construct widget
        self.reset_item_colors()
        self.set_brush_pen_for_connected_items(item.db_representation.id().string())
        self.settings.update_molecule_widget(new_widget)
        # # # Highlight outline of focused item
        self.focused_item.setPen(self.hover_pen)

        # # # Insert mol_widget at correct position of layout
        self.settings.p_layout.insertWidget(mol_index, new_widget)

        if charge is not None and mult is not None:
            new_widget.setToolTip(f"Charge {charge}; Multiplicity {mult}")

    def hover_enter_function(self, _, item: QGraphicsItem) -> None:
        item_db_id_h = item.db_representation.id().string()
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
            activate_action = menu.addAction('Activate compound for exploration')
            deactivate_action = menu.addAction('Deactivate compound for exploration')
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
            elif action == activate_action:
                item.db_representation.enable_exploration()
            elif action == deactivate_action:
                item.db_representation.disable_exploration()
        elif isinstance(item, Reaction):
            if has_ts:
                if action == move_ts_action:
                    self.__move_structure_to_main_viewer(item)

    def __expand_in_new_window(self, item: QGraphicsItem):
        if isinstance(item, Compound):
            from scine_heron.database.expand_widget import ExpandCompound
            selected_compound_dict = json.loads(item.db_representation.json())
            self.__expanded_views.append(ExpandCompound(None, self.db_manager, selected_compound_dict))
            self.__expanded_views[-1].setWindowTitle("Unique Conformers in Aggregate")
            self.__expanded_views[-1].show()
        elif isinstance(item, Reaction):
            from scine_heron.database.expand_widget import ExpandReaction
            selected_reaction_dict = json.loads(item.db_representation.json())
            self.__expanded_views.append(ExpandReaction(None, self.db_manager, selected_reaction_dict))
            self.__expanded_views[-1].setWindowTitle("Elementary steps in Reaction")
            self.__expanded_views[-1].show()

    def __move_structure_to_main_viewer(self, item: QGraphicsItem):
        from scine_heron import get_core_tab
        tab = get_core_tab('molecule_viewer')
        if tab is not None:
            if isinstance(item, Compound):
                db_compound = item.db_representation
                tmp_structure = db.Structure(db_compound.get_centroid(), self._structure_collection)
                tab.update_molecule(atoms=tmp_structure.get_atoms())
            elif isinstance(item, Reaction):
                db_es = db.ElementaryStep(item.assigned_es_id, self._elementary_step_collection)
                if db_es.has_transition_state():
                    tmp_structure = db.Structure(db_es.get_transition_state(), self._structure_collection)
                    tab.update_molecule(atoms=tmp_structure.get_atoms())

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

    def _get_elementary_step_of_reaction_from_db(self,
                                                 reaction: db.Reaction,
                                                 energy_model: db.Model,
                                                 structure_model: Union[None, db.Model] = None
                                                 ) -> Tuple[Union[db.ElementaryStep, None],
                                                            Union[Tuple[float, float], Tuple[None, None]]]:
        # NOTE: Only electronic energies for now
        elementary_step = None
        elementary_step = get_elementary_step_with_min_ts_energy(
            reaction,
            "electronic_energy",
            energy_model,
            self._elementary_step_collection,
            self._structure_collection,
            self._property_collection,
            max_barrier=np.inf,
            min_barrier=- np.inf,
            structure_model=structure_model
        )
        e_type = "electronic_energy"

        # Only query for barrier if es is not None
        if elementary_step is not None:
            barriers = get_barriers_for_elementary_step_by_type(elementary_step, e_type, energy_model,
                                                                self._structure_collection, self._property_collection)
        else:
            barriers = (None, None)

        return elementary_step, barriers
