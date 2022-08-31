#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from typing import Dict, Any, List, Union, Tuple

import scine_database as db
from scine_heron.multithread import Worker
from scine_heron.database.energy_query_functions import get_energy_change
from scine_heron.database.graphics_items import Compound, Pathinfo, Reaction
from scine_heron.database.graph_build_pathfinder import Pathfinder as pf
from scine_heron.database.reaction_compound_view import ReactionAndCompoundView, ReactionAndCompoundViewSettings
from scine_heron.database.compound_flask_helpers import get_compound_or_flask, aggregate_type_from_string

from PySide2.QtWidgets import (
    QWidget,
    QCheckBox,
    QGraphicsView,
    QVBoxLayout,
    QHBoxLayout,
    QGraphicsScene,
    QComboBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QScrollArea
)
from PySide2.QtGui import QPainterPath, QGuiApplication
from PySide2.QtCore import Qt, QPoint, QTimer, QTimeLine, QThreadPool, SignalInstance


class CustomQScrollArea(QScrollArea):
    def wheelEvent(self, event):
        modifiers = QGuiApplication.keyboardModifiers()
        if self.widget().mol_widget.underMouse() and modifiers == Qt.ControlModifier:
            self.widget().mol_widget.wheelEvent(event)
        elif self.widget().mol_widget.underMouse():
            super(CustomQScrollArea, self).wheelEvent(event)
        else:
            super(CustomQScrollArea, self).wheelEvent(event)


class GraphTravelWidget(QWidget):
    def __init__(self, parent: QWidget, db_manager: db.Manager) -> None:
        self.window_width = 1440
        self.window_height = 810
        self.scene_object = QGraphicsScene(0, 0, self.window_width, self.window_height)
        super(GraphTravelWidget, self).__init__(parent=parent)
        self.db_manager = db_manager

        layout_main = QVBoxLayout()

        layout = QHBoxLayout()
        self.graph_travel_view = GraphTravelView(self, self.db_manager)
        self.settings = TraversalSettings(self, self.graph_travel_view)
        self.graph_travel_view.set_settings_widget(self.settings)

        self.settings_scroll_area = CustomQScrollArea()
        self.settings_scroll_area.setWidget(self.settings)
        self.settings_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.settings_scroll_area.setFixedWidth(self.settings._widget_width + 10)

        layout.addWidget(self.graph_travel_view)
        layout.addWidget(self.settings_scroll_area)

        layout_main.addLayout(layout)

        # Attempt of a loading bar ...
        layout_bottom = QHBoxLayout()
        status_label = QLabel(self)
        status_label.setText("Status:")
        status_label.setFixedSize(80, 20)
        layout_bottom.addWidget(status_label)

        self.status_indicator = QLabel(self)
        self.status_indicator.setText("Ready")
        self.status_indicator.resize(240, 20)
        self.settings.set_status_widget(self.status_indicator)
        layout_bottom.addWidget(self.status_indicator)

        spacefill = QLabel(self)
        spacefill.resize(900, 20)
        layout_bottom.addWidget(spacefill)

        layout_main.addLayout(layout_bottom)

        self.setLayout(layout_main)

        # self.scene_object.update()
        self.view = QGraphicsView(self.scene_object)
        self.view.setLayout(layout_main)
        self.view.setWindowTitle("Graph Traversal")
        self.view.show()


class GraphTravelView(ReactionAndCompoundView):
    def __init__(self, parent: QWidget, db_manager: db.Manager) -> None:
        super(GraphTravelView, self).__init__(parent=parent)
        self.setMouseTracking(True)
        self.setInteractive(True)

        # Add all data
        self.db_manager: db.Manager = db_manager
        self.line_items: Dict[str, Any] = {}

        self._curve_width, self._curve_height, self._curve_angle, self._curve_arc_length = 20, 20, 30, 60
        self._currently_plotting = False

        self.timer: Union[QTimeLine, None] = None
        self.frames: Union[int, None] = None
        self.compound_start: str = ""
        self.compound_stop: str = ""

        self.pathinfo_list: List[Pathinfo] = []

        # db-info of selected compound
        self._compound_collection = self.db_manager.get_collection("compounds")
        self._reaction_collection = self.db_manager.get_collection("reactions")
        self._flask_collection = self.db_manager.get_collection("flasks")
        self._elementary_step_collection = self.db_manager.get_collection("elementary_steps")
        self._property_collection = self.db_manager.get_collection("properties")
        self._structure_collection = self.db_manager.get_collection("structures")

    def __getitem__(self, i):
        # get information of database
        # to make subscriptable
        return f"{i}"

    def remove_line_items(self):
        for line in self.line_items.values():
            self.scene_object.removeItem(line)
        # Reset line storage
        self.line_items = {}

    def remove_compound_items(self):
        for n_list in self.compounds.values():
            for n in n_list:
                self.scene_object.removeItem(n)
        # Reset node storage
        self.compounds = {}

    def remove_reaction_items(self):
        for n_list in self.reactions.values():
            for n in n_list:
                self.scene_object.removeItem(n)
        # Reset node storage
        self.reactions = {}

    def remove_pathinfo_items(self):
        for info in self.pathinfo_list:
            self.scene_object.removeItem(info)
        # Reset storage
        self.pathinfo_list = []

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
            # Center on mouse position
            self.centerOn(oldPos.x(), oldPos.y())
        elif event.modifiers() == Qt.ShiftModifier:
            self.horizontalScrollBar().wheelEvent(event)
        else:
            self.verticalScrollBar().wheelEvent(event)

    def plot_graph_travel(self, source: str, target: str, paths_data: List[Tuple[List[str], List[int], float]]):
        if self._currently_plotting:
            return
        self._currently_plotting = True
        # Create singular timer for all added animated items
        self.timer = QTimeLine(1000)
        self.frames = 40
        self.timer.setFrameRange(0, self.frames)
        # Clear scene
        self.remove_line_items()
        self.remove_compound_items()
        self.remove_reaction_items()
        self.remove_pathinfo_items()
        self.scene_object.update()

        # given input information
        self.compound_stop = target

        # number of possible path
        number_paths = len(paths_data)
        cid_type = ""
        # loop over paths
        for path_data_index in range(number_paths):
            reaction_before = 0
            if path_data_index == 0:
                self.__build_pathinfo_item(
                    reaction_before - 3 * 70,
                    (path_data_index - number_paths) * 140 - 50,
                    text="Number\nLength")
            # loop over reactions in path
            for rxn_index in range(len(paths_data[path_data_index][0])):
                if rxn_index == 0:
                    self.compound_start = source
                    compound_collection = self.db_manager.get_collection("compounds")
                    source_type = "compound" if compound_collection.has_compound(db.ID(source)) else "flask"
                    cid_string, cid_type = self.graph_travel(
                        self.compound_start, source_type, paths_data[path_data_index],
                        rxn_index, path_data_index + 1, number_paths, reaction_before)
                else:
                    cid_string, cid_type = self.graph_travel(
                        cid_string, cid_type, paths_data[path_data_index],
                        rxn_index, path_data_index + 1, number_paths, reaction_before)

                reaction_before += 1

        # move nodes above lines
        self.move_to_foreground(self.compounds)
        self.move_to_foreground(self.reactions)

        self.timer.start()
        self._currently_plotting = False
        # Bounding rectangle around current scene
        rect = self.scene().itemsBoundingRect()
        self.scene().setSceneRect(rect)
        # Fit scene rectangle in view and center on rectangle center
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        self.centerOn(self.sceneRect().center().x(), self.sceneRect().center().y() - 20)

    def graph_travel(self,
                     cid_string: str,
                     cid_type: str,
                     path_data: Tuple[List[str],
                                      List[int],
                                      float],
                     rxn_index: int,
                     path_count: int,
                     total_path_number: int,
                     reaction_before: int):

        # Split path data into reaction_list, reaction_side_list and path_length
        reaction_list = path_data[0]
        reaction_side_list = path_data[1]
        path_length = path_data[2]

        reactions_id = []
        length_reaction_list = len(reaction_list)

        # **********
        # Compound A
        # **********
        compound_a_type = aggregate_type_from_string(cid_type)
        compound_a = get_compound_or_flask(db.ID(cid_string), compound_a_type,
                                           self._compound_collection, self._flask_collection)

        # 100px per graph (vertical) + 40 padding
        # 140px compound to compound per reaction (horizontal)
        pos_y_comp_a = (path_count - total_path_number) * 140 - 50  # center in own 100px, global center around 0
        pos_x_comp_a = reaction_before * 140

        if cid_string == self.compound_start:
            assert self.settings
            text_info = '#' + str(self.settings._first_path_index + path_count) + "\n" + str(round(path_length, 2))
            self.__build_pathinfo_item(pos_x_comp_a - 3 * 70, pos_y_comp_a, text=text_info)
            _, _ = self.__build_compound_item(pos_x_comp_a, pos_y_comp_a, compound_a, compound_a_type)

        reaction_k = db.Reaction(db.ID(reaction_list[rxn_index]), self._reaction_collection)
        reaction_incoming_side_k = reaction_side_list[rxn_index]
        # Check, is selected compound on rhs/lhs of which reaction and take this reaction
        reactions_id.append(reaction_k.id().string())
        # Side of compound A for reaction is given by reaction_incoming_side_k
        xhs = db.Side.RHS if reaction_incoming_side_k == 1 else db.Side.LHS
        # *********
        # Reaction
        # *********
        # draw associated reaction
        pos_x_reaction = pos_x_comp_a + 70
        pos_y_reaction = pos_y_comp_a

        # reaction = db.Reaction(db.ID(reactions_id[0]), reaction_collection)
        reaction_type = db.ElementaryStep(reaction_k.get_elementary_steps()[
                                          0], self._elementary_step_collection).get_type()
        if xhs == db.Side.RHS:
            reaction_item = Reaction(
                pos_x_reaction, pos_y_reaction, rot=1, pen=self.reaction_pen,
                brush=self.get_reaction_brush(reaction_type)
            )
            side = reaction_item.rhs()
        elif xhs == db.Side.LHS:
            reaction_item = Reaction(
                pos_x_reaction, pos_y_reaction, pen=self.reaction_pen, brush=self.get_reaction_brush(reaction_type)
            )
            side = reaction_item.lhs()
        else:
            raise RuntimeError("The reaction side must be LHS or RHS.")
        reaction_item.db_representation = reaction_k
        es = db.ElementaryStep(reaction_k.get_elementary_steps()[0], self._elementary_step_collection)
        struct = db.Structure(es.get_reactants()[0][0], self._structure_collection)
        reaction_item.energy_difference = get_energy_change(
            es, "electronic_energy", struct.get_model(), self._structure_collection, self._property_collection)
        if es.has_spline():
            reaction_item.spline = es.get_spline()

        self.__bind_functions_to_object(reaction_item)
        self.add_to_reaction_list(reaction_item)
        self.scene_object.addItem(reaction_item)

        # drawing path from reaction to compound A
        self.__draw_lines(reaction_k, xhs, cid_string, side)

        # ********************
        # Compound A hanging
        # ********************
        # determine further hanging compounds beside compound A
        reactants = reaction_k.get_reactants(xhs)[0] if xhs == db.Side.LHS else reaction_k.get_reactants(xhs)[1]
        reactant_types = reaction_k.get_reactant_types(xhs)[0] if xhs == db.Side.LHS\
            else reaction_k.get_reactant_types(xhs)[1]

        # drawing hanging compounds
        n_on_a_side: int = len(reactants) - 1
        current_index_on_a_side: int = 0
        for a_id, a_type in zip(reactants, reactant_types):
            if a_id != compound_a.id():
                compound_h = get_compound_or_flask(a_id, a_type, self._compound_collection,
                                                   self._flask_collection)

                pos_x_compound_a_beside = pos_x_comp_a + 20
                pos_y_compound_a_beside = pos_y_comp_a + (30 + 60 * int((current_index_on_a_side / n_on_a_side)))

                _, cid_string_hang = self.__build_compound_item(
                    pos_x_compound_a_beside, pos_y_compound_a_beside, compound_h, a_type
                )

                # drawing path from reaction to compound hanging
                self.__draw_curves(reaction_k, len(reactants), cid_string_hang, side)
                current_index_on_a_side += 1

        # ***********************
        # Compound Z and Compound Z hanging
        # ***********************
        # switch xhs for drawing edge at other side of reaction
        if xhs == db.Side.RHS:
            xhs = db.Side.LHS
            side = reaction_item.lhs()
        elif xhs == db.Side.LHS:
            xhs = db.Side.RHS
            side = reaction_item.rhs()

        # determine further hanging compounds beside compound Z
        reactants = reaction_k.get_reactants(xhs)[0] if xhs == db.Side.LHS else reaction_k.get_reactants(xhs)[1]
        reactant_types = reaction_k.get_reactant_types(xhs)[0] if xhs == db.Side.LHS\
            else reaction_k.get_reactant_types(xhs)[1]

        # Position the compound on the RHS of the previous reaction.
        # We must place one compound in the center between the previous and the next reaction,
        # and all other compounds on the sides.
        central_compound_id = db.ID(self.compound_stop)
        final_target_on_rhs = central_compound_id in reactants
        if rxn_index < (length_reaction_list - 1):
            # not the last reaction. At least one more to go!
            reaction_kp1 = db.Reaction(db.ID(reaction_list[rxn_index + 1]), self._reaction_collection)
            reaction_kp1_side = reaction_side_list[rxn_index + 1]
            central_compound_id = self.__get_next_central_compound(reactants, reaction_kp1, reaction_kp1_side)
        elif rxn_index >= (length_reaction_list - 1) and not final_target_on_rhs:
            raise RuntimeError("Invalid reaction path! Reaction path does not end in the target species.")
        central_compound_type = reactant_types[reactants.index(central_compound_id)]
        central_compound_type_str = "compound" if central_compound_type == db.CompoundOrFlask.COMPOUND else "flask"
        n_on_z_side: int = len(reactants) - 1
        current_index_on_z_side: int = 0
        for a_id, a_type in zip(reactants, reactant_types):
            if a_id != central_compound_id:
                compound_h_after = get_compound_or_flask(
                    a_id, a_type, self._compound_collection, self._flask_collection)

                pos_x_comp_z = pos_x_comp_a + 120
                pos_y_comp_z = pos_y_comp_a - (30 + 60 * int(current_index_on_z_side / n_on_z_side))

                _, cid_string = self.__build_compound_item(
                    pos_x_comp_z, pos_y_comp_z, compound_h_after, a_type
                )

                # drawing path from reaction to compound Z hanging
                self.__draw_curves_after(reaction_k, len(reactants), cid_string, side)
                current_index_on_z_side += 1
            else:
                # We arrived at the target/central compound. Set it to the center.
                compound_h_after = get_compound_or_flask(
                    a_id, a_type, self._compound_collection, self._flask_collection)

                _, cid_string = self.__build_compound_item(
                    pos_x_comp_a + 140, pos_y_comp_a, compound_h_after, a_type
                )
                # drawing path from reaction to compound Z
                self.__draw_lines(reaction_k, xhs, cid_string, side)
        return central_compound_id.string(), central_compound_type_str

    @staticmethod
    def __get_next_central_compound(rhs_reactants: List[db.ID],
                                    next_reaction: db.Reaction,
                                    reaction_kp1_side: int) -> db.ID:
        next_reactants = next_reaction.get_reactants(db.Side.BOTH)
        for a_id in rhs_reactants:
            if a_id in next_reactants[reaction_kp1_side]:
                return a_id
        raise RuntimeError(
            next_reaction.id().string() +
            ": Invalid reaction path detected. The reaction path does not connect a consecutive set of"
            " compounds.")

    def __build_compound_item(self, x: int, y: int, db_compound: Union[db.Compound, db.Flask],
                              a_type: db.CompoundOrFlask) -> Tuple[Compound, str]:
        compound_item = Compound(x, y, pen=self.compound_pen, brush=self.get_aggregate_brush(a_type))
        s = db.Structure(db_compound.get_centroid(), self._structure_collection)
        compound_item.db_representation = db_compound
        compound_item.structure = s.get_atoms()
        cid_string = db_compound.id().string()
        self.__bind_functions_to_object(compound_item)
        self.add_to_compound_list(compound_item)
        # self.compounds[cid_string] = compound_item
        self.scene_object.addItem(compound_item)
        return compound_item, cid_string

    def __build_pathinfo_item(self, x: int, y: int, text: str):
        pathinfo_item = Pathinfo(x, y, text)
        self.scene_object.addItem(pathinfo_item)
        self.pathinfo_list.append(pathinfo_item)

    def __draw_lines(self, reaction, xhs, cid, side) -> None:
        a = len(self.line_items)
        reactants = reaction.get_reactants(xhs)[0] if xhs == db.Side.LHS else reaction.get_reactants(xhs)[1]
        for j in range(len(reactants)):
            oid = reaction.id().string()
            side_point_a = QPoint(self.compounds[cid][-1].center())
            path = QPainterPath(side)
            path.lineTo(side_point_a)
            lid = cid + "_" + oid + "_" + str(j) + "_" + str(a)
            self.line_items[lid] = self.scene_object.addPath(path, pen=self.path_pen)

    def __draw_curves(self, reaction, n_besides: int, cid, side) -> None:
        a = len(self.line_items)
        for j in range(n_besides):
            oid = reaction.id().string()
            side_point_hang = QPoint(self.compounds[cid][-1].center())
            path = QPainterPath(side)
            path.arcTo(side.x() - 12, side.y(), self._curve_width, self._curve_height, 4 * self._curve_angle,
                       self._curve_arc_length)
            path.arcTo(side_point_hang.x(), side_point_hang.y(), self._curve_width, -self._curve_height,
                       self._curve_angle, self._curve_arc_length)
            lid = cid + "_" + oid + "_" + str(j) + "_" + str(a)
            self.line_items[lid] = self.scene_object.addPath(path, pen=self.path_pen)

    def __draw_curves_after(self, reaction, n_compound_beside_after, cid, side) -> None:
        a = len(self.line_items)
        for j in range(n_compound_beside_after):
            oid = reaction.id().string()
            side_point_hang = QPoint(self.compounds[cid][-1].center())
            path = QPainterPath(side)
            path.arcTo(side.x(), side.y(), self._curve_width / 1.7, -self._curve_height, 2 * self._curve_angle,
                       -self._curve_arc_length)
            path.arcTo(side_point_hang.x(), side_point_hang.y(), -self._curve_width, self._curve_height,
                       self._curve_angle, self._curve_arc_length)
            lid = cid + "_" + oid + "_" + str(j) + "_" + str(a)
            self.line_items[lid] = self.scene_object.addPath(path, pen=self.path_pen)

    def __bind_functions_to_object(self, object: Any) -> None:
        object.bind_mouse_press_function(self.mouse_press_function)
        object.setAcceptHoverEvents(True)
        object.bind_hover_enter_function(self.hover_enter_function)
        object.bind_hover_leave_function(self.hover_leave_function)
        object.bind_menu_function(self.menu_function)


class TraversalSettings(ReactionAndCompoundViewSettings):
    def __init__(self, parent: QWidget, graph_travel_view: GraphTravelView) -> None:
        super(TraversalSettings, self).__init__(parent=parent, parsed_layout=QVBoxLayout())

        # Elements of widget relative to width of ReactionProfile Canvas
        self._widget_width = 480
        # Fixed width for widget
        self.setMinimumWidth(self._widget_width)
        self.setMaximumWidth(self._widget_width)

        self.graph_travel_view = graph_travel_view
        self.status_widget: Union[None, QWidget] = None

        self.start_box_label = QLabel(self)
        self.start_box_label.setText("Start ID")
        self.start_box_label.resize(int(self._widget_width * 0.95), 40)
        self.p_layout.addWidget(self.start_box_label)

        self.start_id_text = QLineEdit(self)
        self.start_id_text.resize(int(self._widget_width * 0.95), 40)
        self.start_id_text.setText("")
        self.p_layout.addWidget(self.start_id_text)

        self.target_box_label = QLabel(self)
        self.target_box_label.setText("Target ID")
        self.target_box_label.resize(int(self._widget_width * 0.95), 40)
        self.p_layout.addWidget(self.target_box_label)

        self.target_id_text = QLineEdit(self)
        self.target_id_text.resize(int(self._widget_width * 0.95), 40)
        self.target_id_text.setText("")
        self.p_layout.addWidget(self.target_id_text)
        # Search layout box
        hbox1layout = QHBoxLayout()
        button_search = QPushButton("Search")
        button_search.setFixedSize(int(self._widget_width * 0.33), 40)
        button_search.clicked.connect(  # pylint: disable=no-member
            lambda: self.trigger_thread_function(
                self.__search_function))
        hbox1layout.addWidget(button_search)

        self.button_prev = QPushButton("Prev 15")
        self.button_prev.clicked.connect(self.__prev_function)  # pylint: disable=no-member
        self.button_prev.setFixedSize(int(self._widget_width * 0.3), 40)
        self.button_prev.setDisabled(True)
        hbox1layout.addWidget(self.button_prev)

        self.button_next = QPushButton("Next 15")
        self.button_next.setFixedSize(int(self._widget_width * 0.3), 40)
        self.button_next.setDisabled(True)
        self.button_next.clicked.connect(  # pylint: disable=no-member
            lambda: self.trigger_thread_function(
                self.__next_function))
        hbox1layout.addWidget(self.button_next)

        self.p_layout.addLayout(hbox1layout)
        # List of currently found paths and bool to indicate if new paths have been found
        self.found_paths: List[Tuple[List[str], List[int], float]] = []
        self.new_paths = False
        self._first_path_index = 0
        self._searched_unique_paths = False
        self._skipped_paths_counter = 0

        # Timer for plotting newly found paths
        self.check_new_paths_timer = QTimer(self)
        self.check_new_paths_timer.setInterval(50)
        self.check_new_paths_timer.timeout.connect(self.__plot_new_paths)  # pylint: disable=no-member
        self.check_new_paths_timer.start()

        self.cb_box_label = QLabel(self)
        self.cb_box_label.setText("Graph Weighting Options")
        self.cb_box_label.resize(int(self._widget_width * 0.95), 40)
        self.p_layout.addWidget(self.cb_box_label)

        self.path_weight_options = pf.get_valid_graph_handler_options()
        self.pathfinder: Union[pf, None] = None

        self._path_weight_cb = QComboBox()
        for weighting_scheme in self.path_weight_options:
            self._path_weight_cb.addItem(weighting_scheme)
        self._path_weight_cb.currentIndexChanged.connect(self.update_path_weighting)  # pylint: disable=no-member
        self.p_layout.addWidget(self._path_weight_cb)

        self.button_update = QPushButton("Update")
        self.p_layout.addWidget(self.button_update)
        self.button_update.clicked.connect(self._update_function)  # pylint: disable=no-member

        self.save_to_svg_button = QPushButton("Save SVG")
        self.save_to_svg_button.clicked.connect(  # pylint: disable=no-member
            self.graph_travel_view.save_svg
        )
        self.p_layout.addWidget(self.save_to_svg_button)

        self.unique_paths_cbox = QCheckBox("Show unique paths only")
        self.p_layout.addWidget(self.unique_paths_cbox)

        # Add molecule viewer and trajectory widgets to layout
        self.p_layout.addWidget(self.mol_widget)
        self.mol_widget.setMinimumWidth(self._widget_width)
        self.mol_widget.setMaximumWidth(self._widget_width)
        self.mol_widget.setMinimumHeight(350)

        self.p_layout.addWidget(self.es_mep_widget)
        self.es_mep_widget.setMinimumHeight(250)
        self.es_mep_widget.setMaximumHeight(300)
        self.es_mep_widget.setMinimumWidth(self._widget_width)
        self.es_mep_widget.setMaximumWidth(self._widget_width)

        self.path_weighting: str = self.path_weight_options[0]

        # Setup compound costs settings and make them invisible per default
        self._compound_costs_settings_visible = False
        self._set_up_compound_costs_settings_widgets(self.p_layout)
        self.setLayout(self.p_layout)
        self.show()
        self.set_compound_costs_settings_visible()

    def set_compound_costs_settings_visible(self) -> None:
        self._compound_costs_settings_visible = self.compound_costs_cbox.isChecked()
        if self._compound_costs_settings_visible:
            self.compound_costs_settings_widget.setVisible(True)
        else:
            self.compound_costs_settings_widget.setVisible(False)

    def _set_up_compound_costs_settings_widgets(self, layout):
        self.compound_costs_cbox = QCheckBox("COMPOUND COSTS SETTINGS")
        self.compound_costs_cbox.setChecked(self._compound_costs_settings_visible)
        self.compound_costs_cbox.toggled.connect(  # pylint: disable=no-member
            self.set_compound_costs_settings_visible
        )

        self.compound_costs_settings_widget = CompoundCostsSettingsWidget(self, self)
        layout.addWidget(self.compound_costs_cbox)
        layout.addWidget(self.compound_costs_settings_widget)

    def set_status_widget(self, status_widget: QWidget):
        self.status_widget = status_widget

    def __print_progress(self, n):
        if n:
            self.status_widget.setText("Calculating routes")
        else:
            self.status_widget.setText("Ready")

    def trigger_thread_function(self, func):
        worker = Worker(func)
        worker.signals.running.connect(self.__print_progress)

        pool = QThreadPool.globalInstance()
        pool.start(worker)

    def update_path_weighting(self, new_weighting_index: int):
        self.path_weighting = self.path_weight_options[new_weighting_index]

    def __valid_path_to_plot(self, pathfinder_path_nodes: List[str]):
        # Extract ID of reaction nodes of pathfinder path
        tmp_rxn_list = [node.split(";")[0] for node in pathfinder_path_nodes if ";" in node]
        # True if every reaction only appears once, else False
        return len(tmp_rxn_list) == len(list(set(tmp_rxn_list)))

    def __add_path_to_found_paths(self, pathfinder_path: Tuple[List[str], float]):
        # Extract ID of reaction nodes of pathfinder path
        tmp_rxn_list = [node.split(";")[0] for node in pathfinder_path[0] if ";" in node]
        # Extract side from which the reaction is approached; 0 corresponds to db.Side.LHS, 1 to db.Side.RHS
        tmp_rxn_side_list = [int(node.split(";")[1][0]) for node in pathfinder_path[0] if ";" in node]
        # Add path to self.found_paths
        self.found_paths.append((tmp_rxn_list, tmp_rxn_side_list, pathfinder_path[1]))

    def __clear_found_paths(self):
        self.found_paths = []

    def _update_function(self):
        self.pathfinder = pf(self.graph_travel_view.db_manager)
        self.pathfinder.options.graph_handler = self.graph_travel_view.settings.path_weighting
        self.pathfinder.build_graph()

    def __search_function(self, progress_callback: SignalInstance):
        progress_callback.emit(True)
        if self.start_id_text.text() == "" or self.target_id_text.text() == "":
            raise RuntimeError("Please add a start ID and a target ID for your search.")
        if self.pathfinder is None:
            self._update_function()
            assert self.pathfinder
        else:
            assert self.pathfinder
            assert self.pathfinder.graph_handler
        # Reset iterator in pathfinder
        self.pathfinder._use_old_iterator = False
        self._skipped_paths_counter = 0
        # Clear self.found_paths
        self.__clear_found_paths()
        path_counter = 0
        if self.unique_paths_cbox.isChecked():
            # Loop until 15 paths are found
            while (path_counter < 15):
                tmp_paths = self.pathfinder.find_unique_paths(
                    self.start_id_text.text(), self.target_id_text.text(), 1)
                if len(tmp_paths) == 0:
                    break
                if self.__valid_path_to_plot(tmp_paths[0][0]):
                    self.__add_path_to_found_paths(tmp_paths[0])
                    path_counter += 1
                if not self.pathfinder._use_old_iterator:
                    self.pathfinder._use_old_iterator = True
            # Activate next Button
            self.button_next.setEnabled(True)
            # Set search type memory
            self._searched_unique_paths = True
        else:
            # Loop until 15 paths are found
            while (path_counter < 15):
                tmp_paths = self.pathfinder.find_paths(self.start_id_text.text(), self.target_id_text.text(), 1,
                                                       n_skipped_paths=self._skipped_paths_counter)
                if len(tmp_paths) == 0:
                    break
                self._skipped_paths_counter += 1
                if self.__valid_path_to_plot(tmp_paths[0][0]):
                    self.__add_path_to_found_paths(tmp_paths[0])
                    path_counter += 1
            self.button_next.setEnabled(True)
            self._searched_unique_paths = False

        # Reset found paths and first path index
        self.pathfinder._use_old_iterator = True
        self._first_path_index = 0
        self.new_paths = True
        self.button_prev.setDisabled(True)

        progress_callback.emit(False)

    def __next_function(self, progress_callback: SignalInstance):
        progress_callback.emit(True)
        assert self.pathfinder
        # Check, if previous search was unique or not
        if self.unique_paths_cbox.isChecked() is self._searched_unique_paths:
            if len(self.found_paths) - self._first_path_index == 15:
                path_counter = 0
                if self.unique_paths_cbox.isChecked():
                    # Loop until 15 paths are found
                    while (path_counter < 15):
                        tmp_paths = self.pathfinder.find_unique_paths(
                            self.start_id_text.text(), self.target_id_text.text(), 1)
                        if len(tmp_paths) == 0:
                            break
                        if self.__valid_path_to_plot(tmp_paths[0][0]):
                            self.__add_path_to_found_paths(tmp_paths[0])
                            path_counter += 1
                else:
                    # Loop until 15 paths are found
                    while (path_counter < 15):
                        tmp_paths = self.pathfinder.find_paths(
                            self.start_id_text.text(),
                            self.target_id_text.text(),
                            15,
                            n_skipped_paths=self._skipped_paths_counter)
                        if len(tmp_paths) == 0:
                            break
                        self._skipped_paths_counter += 1
                        if self.__valid_path_to_plot(tmp_paths[0][0]):
                            self.__add_path_to_found_paths(tmp_paths[0])
                            path_counter += 1

            self._first_path_index += 15
            self.button_prev.setEnabled(True)
        # # # Reset if entry of check box changed
        else:
            self.__search_function(progress_callback)

        progress_callback.emit(False)
        self.new_paths = True

    def __prev_function(self):
        if self.unique_paths_cbox.isChecked() is self._searched_unique_paths:
            # Reduce start index by 15
            self._first_path_index -= 15
            self.new_paths = True
            if self._first_path_index == 0:
                self.button_prev.setDisabled(True)
        else:
            self.trigger_thread_function(self.__search_function)

    def __plot_new_paths(self):
        if self.new_paths:
            self.graph_travel_view.plot_graph_travel(
                self.start_id_text.text(), self.target_id_text.text(),
                # List of list of visited reaction nodes
                [path_data for path_data in self.found_paths[self._first_path_index:self._first_path_index + 15]]
            )
            # Reset trigger for plotting
            self.new_paths = False


class CompoundCostsSettingsWidget(QWidget):
    def __init__(self, parent: QWidget, traversal_settings: TraversalSettings):
        super(CompoundCostsSettingsWidget, self).__init__(parent=parent)

        self.traversal_settings = traversal_settings
        self._widget_width = self.traversal_settings._widget_width * 0.9

        self.start_compound_fields = 1
        self.__layout = QVBoxLayout()

        self.__set_up_start_conditions_widgets()
        self.__add_buttons()

        self.setLayout(self.__layout)

    def __print_progress(self, n):
        if n:
            self.traversal_settings.status_widget.setText("Determining compound costs")
        else:
            self.traversal_settings.status_widget.setText("Ready")

    def trigger_thread_function(self, func):
        worker = Worker(func)
        worker.signals.running.connect(self.__print_progress)

        pool = QThreadPool.globalInstance()
        pool.start(worker)

    def __set_up_start_conditions_widgets(self):
        # Compound ID and Compound Cost
        compound_id_label = QLabel(self)
        compound_id_label.setFixedSize(self._widget_width * 0.6, 40)
        compound_id_label.setText("Compound ID")
        compound_cost_label = QLabel(self)
        compound_cost_label.setFixedSize(self._widget_width * 0.3, 40)
        compound_cost_label.setText("C. Cost")
        hbox1Layout = QHBoxLayout()
        hbox1Layout.addWidget(compound_id_label)
        hbox1Layout.addWidget(compound_cost_label)
        self.__layout.addLayout(hbox1Layout)
        self.__add_input_widgets()

    def __add_input_widgets(self):
        compound_id_text = QLineEdit(self)
        compound_id_text.setFixedSize(self._widget_width * 0.6, 40)
        compound_id_text.setText("")
        compound_cost_text = QLineEdit(self)
        compound_cost_text.setFixedSize(self._widget_width * 0.35, 40)
        compound_cost_text.setText("")
        hbox2Layout = QHBoxLayout()
        hbox2Layout.addWidget(compound_id_text)
        hbox2Layout.addWidget(compound_cost_text)
        self.__layout.addLayout(hbox2Layout)

    def __add_buttons(self):
        button_add_start_compounds = QPushButton("+")
        button_add_start_compounds.setFixedSize(self._widget_width * 0.2, 40)
        button_add_start_compounds.clicked.connect(  # pylint: disable=no-member
            self.__add_start_compounds_function)
        button_remove_start_compounds = QPushButton("-")
        button_remove_start_compounds.setFixedSize(self._widget_width * 0.2, 40)
        button_remove_start_compounds.clicked.connect(  # pylint: disable=no-member
            self.__remove_start_compounds_function)

        button_reset_start_compounds = QPushButton("Reset")
        button_reset_start_compounds.resize(self._widget_width * 0.6, 40)
        button_reset_start_compounds.clicked.connect(  # pylint: disable=no-member
            self.__reset_start_compounds_function)

        hbox1Layout = QHBoxLayout()
        hbox1Layout.addWidget(button_add_start_compounds)
        hbox1Layout.addWidget(button_remove_start_compounds)
        hbox1Layout.addWidget(button_reset_start_compounds)
        self.__layout.addLayout(hbox1Layout)

        button_calculate_compound_costs = QPushButton("Calculate Compound Costs")
        button_calculate_compound_costs.resize(self._widget_width, 40)
        button_calculate_compound_costs.clicked.connect(  # pylint: disable=no-member
            lambda: self.trigger_thread_function(self.__calculate_compound_costs_function))
        self.__layout.addWidget(button_calculate_compound_costs)

    def __add_start_compounds_function(self):
        self.parent().setMinimumHeight(self.parent().height() + 60)
        self.start_compound_fields += 1
        # Remove calc compound costs button
        button_calc_compound_costs = self.__layout.itemAt(self.__layout.count() - 1)
        button_calc_compound_costs.widget().deleteLater()
        # Remove +, -, reset button
        button_layout = self.__layout.itemAt(self.__layout.count() - 2).layout()
        self.__clear_layout(button_layout)
        self.__layout.removeItem(button_layout)

        # Add new input widgets
        self.__add_input_widgets()
        # Add buttons at bottom
        self.__add_buttons()

    def __remove_start_compounds_function(self):
        if self.start_compound_fields == 1:
            # Reset text in first input widget
            self.__layout.itemAt(1).layout().itemAt(0).widget().setText("")
            self.__layout.itemAt(1).layout().itemAt(1).widget().setText("")
        else:
            self.start_compound_fields -= 1
            last_input_layout = self.__layout.itemAt(self.__layout.count() - 3).layout()
            self.__clear_layout(last_input_layout)
            self.__layout.removeItem(last_input_layout)
            self.parent().setMinimumHeight(self.parent().height() - 60)

    @staticmethod
    def __clear_layout(layout):
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            widget.deleteLater()

    def __reset_start_compounds_function(self):
        deleteLayout = []
        # Clear all input widgets
        for i in range(2, self.start_compound_fields + 1):
            item = self.__layout.itemAt(i)
            if item is not None:
                layout = item.layout()
                if layout is not None:
                    self.__clear_layout(layout)
                    deleteLayout.append(layout)
        # Clear all input widgets layout
        for k in deleteLayout:
            self.__layout.removeItem(k)
        self.parent().setMinimumHeight(self.parent().height() - 60 * self.start_compound_fields)
        self.start_compound_fields = 1
        # Reset text in first input widget
        self.__layout.itemAt(1).layout().itemAt(0).widget().setText("")
        self.__layout.itemAt(1).layout().itemAt(1).widget().setText("")

    def __calculate_compound_costs_function(self, progress_callback: SignalInstance):
        if self.traversal_settings.pathfinder is None:
            self.traversal_settings._update_function()
            assert self.traversal_settings.pathfinder
        else:
            assert self.traversal_settings.pathfinder
        progress_callback.emit(True)
        start_conditions = {}
        # Create input dictionary
        for input_widgets in [self.__layout.itemAt(i).layout() for i in range(1, self.start_compound_fields + 1)]:
            key = input_widgets.itemAt(0).widget().text()
            value = input_widgets.itemAt(1).widget().text()
            if key == "" or value == "":
                raise RuntimeError("Please complete input.")
            if float(value) < 0:
                raise RuntimeError("Only weights > 0 are allowed.")
            start_conditions[key] = float(value)

        self.traversal_settings.pathfinder.set_start_conditions(start_conditions)
        # # # Determine the compound costs
        self.traversal_settings.pathfinder.calculate_compound_costs()
        # # # Update the graph with the information of the compound costs
        self.traversal_settings.pathfinder.update_graph_compound_costs()
        progress_callback.emit(False)
