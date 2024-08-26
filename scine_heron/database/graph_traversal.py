#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

import copy
from typing import Dict, Any, List, Union, Tuple
import datetime
import time
import networkx as nx
from pathlib import Path

import scine_database as db
from scine_database.energy_query_functions import get_energy_change, get_barriers_for_elementary_step_by_type
from scine_heron.multithread import Worker

from scine_heron.containers.buttons import TextPushButton
from scine_heron.containers.wrapped_label import WrappedLabel
from scine_heron.toolbar.io_toolbar import ToolBarWithSaveLoad
from scine_heron.statusbar.status_bar import StatusBar
from scine_heron.io.file_browser_popup import get_save_file_name, get_load_file_name
from scine_heron.settings.class_options_widget import ClassOptionsWidget, CompoundCostOptionsWidget
from scine_heron.containers.without_wheel_event import NoWheelDoubleSpinBox
from scine_heron.settings.dict_option_widget import DictOptionWidget
from scine_heron.settings.docstring_parser import DocStringParser

from scine_heron.database.graphics_items import Compound, Pathinfo, Reaction
from scine_heron.database.reaction_compound_view import ReactionAndCompoundView, ReactionAndCompoundViewSettings
from scine_heron.database.path_energy_levels import PathLevelWidget


from scine_chemoton.gears.pathfinder import Pathfinder as pf

from PySide2.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
    QWidget,
    QCheckBox,
    QGraphicsView,
    QVBoxLayout,
    QHBoxLayout,
    QGraphicsScene,
    QLineEdit,
    QLabel,
    QScrollArea,
)
from PySide2.QtGui import QPainterPath, QGuiApplication, QPainter
from PySide2.QtCore import Qt, QPoint, QTimer, QThreadPool, SignalInstance


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
    def __init__(self, parent: QWidget, db_manager: db.Manager, model: db.Model) -> None:
        self.window_width = 1440
        self.window_height = 810
        self.scene_object = QGraphicsScene(0, 0, self.window_width, self.window_height)
        super(GraphTravelWidget, self).__init__(parent=parent)
        self.db_manager = db_manager

        outer_layout_main = QVBoxLayout()
        inner_layout_main = QVBoxLayout()
        layout = QHBoxLayout()
        self.graph_travel_view = GraphTravelView(self, self.db_manager)
        self.settings = TraversalSettings(self, self.graph_travel_view, model)
        self.graph_travel_view.set_settings_widget(self.settings)

        self.settings_scroll_area = CustomQScrollArea()
        self.settings_scroll_area.setWidget(self.settings)
        self.settings_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.settings_scroll_area.setFixedWidth(self.settings._widget_width + 10)

        layout.addWidget(self.graph_travel_view)
        layout.addWidget(self.settings_scroll_area)

        inner_layout_main.addLayout(layout)
        inner_layout_main.setContentsMargins(9, 9, 9, 9)  # Default padding

        self.status_bar = StatusBar(self)
        self.settings.set_status_bar(self.status_bar)
        self.status_bar.update_status("Status:" + 4 * " " + "Ready", timer=None)

        outer_layout_main.addLayout(inner_layout_main)
        # Status bar
        layout_bottom = QHBoxLayout()
        layout_bottom.addWidget(self.status_bar)

        outer_layout_main.addLayout(layout_bottom)
        outer_layout_main.setContentsMargins(0, 0, 0, 0)  # Remove padding

        self.setLayout(outer_layout_main)

        self.view = QGraphicsView(self.scene_object)
        self.view.setLayout(outer_layout_main)
        self.view.setWindowTitle("Graph Traversal")
        # rendering smoother lines and edges of nodes
        self.view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

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
        self._path_window = 140
        self._currently_plotting = False

        self.compound_start: str = ""
        self.compound_stop: str = ""

        self.pathinfo_list: List[Pathinfo] = []
        self._graph: nx.DiGraph = None

        # db-info of selected compound
        self._compound_collection = self.db_manager.get_collection("compounds")
        self._reaction_collection = self.db_manager.get_collection("reactions")
        self._flask_collection = self.db_manager.get_collection("flasks")
        self._elementary_step_collection = self.db_manager.get_collection("elementary_steps")
        self._property_collection = self.db_manager.get_collection("properties")
        self._structure_collection = self.db_manager.get_collection("structures")

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

    def plot_paths(self,
                   paths_excluding_rxn_double_cross: List[Tuple[List[str], float]],
                   paths_including_rxn_double_cross: List[Tuple[List[str], float]],
                   true_sight: bool):
        if self._currently_plotting:
            return
        self._currently_plotting = True
        # # # Remove old items from current scene
        self.remove_line_items()
        self.remove_compound_items()
        self.remove_reaction_items()
        self.remove_pathinfo_items()
        self.scene_object.update()

        # given input information
        assert paths_including_rxn_double_cross
        assert self.settings
        path_row = 0
        # # # Paths excluding double rxn crossing are easier to interpret for the operator
        if true_sight or len(paths_excluding_rxn_double_cross) == 0:
            for path in paths_including_rxn_double_cross:
                path_rank = self.settings._first_index_double_rxns
                self.construct_single_path_objects(path[0], path_rank, path_row, path[1])
                path_row += 1
        else:
            for path in paths_excluding_rxn_double_cross:
                path_rank = self.settings._first_index_no_double_rxns
                self.construct_single_path_objects(path[0], path_rank, path_row, path[1])
                path_row += 1

        # move nodes above lines
        self.move_to_foreground(self.compounds)
        self.move_to_foreground(self.reactions)

        # Bounding rectangle around current scene
        rect = self.scene().itemsBoundingRect()
        self.scene().setSceneRect(rect)
        # Fit scene rectangle in view and center on rectangle center
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        self.centerOn(self.sceneRect().center().x(), self.sceneRect().center().y() - 20)
        self._currently_plotting = False

    def construct_single_path_objects(self, path, path_rank, path_row_index, path_length):
        widget_y_position = path_row_index * self._path_window
        # Require pathfinder graph, only connectivity
        path_graph = self.__construct_path_graph(path)
        path_graph_positions = self.__determine_node_positions(path, path_graph, widget_y_position)
        # NOTE: Access x pos value better
        # Build path info (rank and length)
        path_rank += path_row_index + 1
        path_length = round(path_length, 2)
        self.__build_pathinfo_item(
            - 6 * 70,
            widget_y_position,
            path, path_rank, path_length,
            text="Number\nLength")
        text_info = '#' + str(path_rank) + "\n" + str(path_length)
        self.__build_pathinfo_item(-3 * 70, widget_y_position, path, path_rank, path_length, text=text_info)

        # loop over positions and draw rxn nodes, edges and aggregates
        for node, position in path_graph_positions.items():
            # Draw Rxn Nodes and edges
            if ";0;" in node or ";1;" in node:
                rxn = db.Reaction(db.ID(node.split(";")[0]), self._reaction_collection)
                side = int(node.split(";")[1])
                rxn_item = self.__build_reaction_item(position[0], position[1], rxn, side)
                # Draw incoming edges of rxn node
                for e_count, edge in enumerate(path_graph.in_edges(node)):
                    line_id = "_".join(list(edge)) + "_" + str(e_count) + "_" + str(path_row_index)
                    edge_item = self.__build_edge(QPoint(path_graph_positions[edge[0]][0],
                                                         path_graph_positions[edge[0]][1]),
                                                  rxn_item.incoming())
                    self.line_items[line_id] = edge_item
                # Draw outgoing edges of rxn node
                for e_count, edge in enumerate(path_graph.out_edges(node)):
                    line_id = "_".join(list(edge)) + "_" + str(e_count) + "_" + str(path_row_index)
                    edge_item = self.__build_edge(rxn_item.outgoing(),
                                                  QPoint(path_graph_positions[edge[1]][0],
                                                         path_graph_positions[edge[1]][1]))
                    self.line_items[line_id] = edge_item
            else:
                # Draw Aggregate Nodes
                node_stripped = node.split(";")[0]
                if self._graph.nodes(data=True)[node_stripped]['type'] == db.CompoundOrFlask.COMPOUND.name:
                    a_type = db.CompoundOrFlask.COMPOUND
                    aggregate = db.Compound(db.ID(node_stripped), self._compound_collection)
                else:
                    a_type = db.CompoundOrFlask.FLASK
                    aggregate = db.Flask(db.ID(node_stripped), self._flask_collection)

                self.__build_compound_item(position[0], position[1], aggregate, a_type)

    def __construct_path_graph(self, path: List[str]) -> nx.DiGraph:
        # Derive edges from path
        path_edges = [(path[i], path[i + 1]) for i in range(0, len(path) - 1)]
        path_graph = nx.DiGraph()
        for node in path:
            path_graph.add_node(node)
        for edge in path_edges:
            path_graph.add_edge(edge[0], edge[1], weight=1.0)

        r_counter = 0
        p_counter = 0
        for rxn_node_index, node in enumerate([filtered_node for filtered_node in path if ";" in filtered_node]):
            # Add incoming reactants to complete path graph
            for edge in self._graph.in_edges(node):
                if edge != path_edges[2 * rxn_node_index]:
                    reactant_node = edge[0] + ";r" + str(r_counter) + ";"
                    path_graph.add_node(reactant_node)
                    path_graph.add_edge(reactant_node, node, weight=1.0)
                    r_counter += 1
            # Add outgoing products to complete path graph
            for edge in self._graph.out_edges(node):
                if edge != path_edges[2 * rxn_node_index + 1]:
                    product_node = edge[1] + ";p" + str(p_counter) + ";"
                    path_graph.add_node(product_node)
                    path_graph.add_edge(node, product_node, weight=1.0)
                    p_counter += 1

        return path_graph

    @staticmethod
    def __construct_model_string(model: db.Model) -> str:
        model_string = model.method
        if model.basis_set and model.basis_set.lower() != "none":
            model_string += "/" + model.basis_set
        if model.solvation and model.solvation.lower() != "none" and model.solvent.lower() != "any":
            model_string += "(" + model.solvent + ")"
        return model_string

    @staticmethod
    def __determine_node_positions(path: List[str],
                                   path_graph: nx.DiGraph, path_y_pos: float) -> Dict[str, Tuple[float, float]]:
        positions = {}
        path_edges = [(path[i], path[i + 1]) for i in range(0, len(path) - 1)]
        # NOTE: maybe set this somewhere better
        x_shift = 35.0
        y_shift = 25.0

        path_node_x_pos = 0.0
        for node in path:
            positions[node] = (path_node_x_pos, path_y_pos)
            path_node_x_pos += x_shift * 2

        reactant_edges = []
        prodcut_edges = []
        for rxn_node_index, node in enumerate([filtered_node for filtered_node in path if ";" in filtered_node]):
            # Position of reactants
            # Count minus one due to path
            for in_count, edge in enumerate(path_graph.in_edges(node)):
                if edge != path_edges[2 * rxn_node_index]:
                    r_node = edge[0]
                    positions[r_node] = (positions[node][0] - x_shift,
                                         positions[node][1] - y_shift * (in_count))
                    reactant_edges.append((r_node, node))

            # Position of products
            for out_count, edge in enumerate(path_graph.out_edges(node)):
                if edge != path_edges[2 * rxn_node_index + 1]:
                    p_node = edge[1]
                    positions[p_node] = (positions[node][0] + x_shift,
                                         positions[node][1] + y_shift * (out_count))
                    prodcut_edges.append((node, p_node))

        return positions

    # # # START BUILD ITEM FUNCTIONS

    def __build_compound_item(self, x: int, y: int, db_compound: Union[db.Compound, db.Flask],
                              a_type: db.CompoundOrFlask) -> Tuple[Compound, str]:
        compound_item = Compound(x, y, pen=self.compound_pen, brush=self.get_aggregate_brush(a_type))
        compound_item.db_representation = db_compound
        cid_string = db_compound.id().string()
        self.__bind_functions_to_object(compound_item)
        self.add_to_compound_list(compound_item)
        self.scene_object.addItem(compound_item)
        return compound_item, cid_string

    def __build_reaction_item(self, x: int, y: int, reaction: db.Reaction, side: int):
        assert self.settings
        assert self.settings.pathfinder  # mypy ...
        # Include structure model
        if self.settings.pathfinder.options.use_structure_model:
            structure_model = self.settings.pathfinder.options.structure_model
            if not isinstance(structure_model, db.Model):
                raise RuntimeError("Structure model not set")
        else:
            structure_model = self.settings.pathfinder.options.model
        # Get elementary step from graph or database
        es_from_graph = None
        node_id = reaction.id().string() + ";" + str(side) + ";"
        if "elementary_step_id" in self._graph.nodes(data=True)[node_id]:
            es_id = db.ID(
                self._graph.nodes(data=True)[node_id]["elementary_step_id"])
            es_from_graph = db.ElementaryStep(es_id, self._elementary_step_collection)

        if es_from_graph is None:
            es, barriers = self._get_elementary_step_of_reaction_from_db(
                reaction,
                self.settings.pathfinder.options.model,
                structure_model)
        else:
            es = es_from_graph
            # Get barrier of ES
            barriers = get_barriers_for_elementary_step_by_type(
                es,
                "electronic_energy",
                self.settings.pathfinder.options.model,
                self._structure_collection,
                self._property_collection)
        assert es
        reaction_item = Reaction(
            x, y, pen=self.reaction_pen,
            brush=self.get_reaction_brush(es.get_type()),
            # invert direction if side is 1
            invert_direction=bool(side)
        )
        reaction_item.db_representation = reaction
        reaction_item.assigned_es_id = es.id()

        struct = db.Structure(es.get_reactants()[0][0], self._structure_collection)
        reaction_item.energy_difference = get_energy_change(
            es, "electronic_energy", struct.get_model(), self._structure_collection, self._property_collection)
        if barriers[0] is not None and barriers[1] is not None:
            reaction_item.set_barriers(barriers)
        if es.has_spline():
            reaction_item.spline = es.get_spline()

        self.__bind_functions_to_object(reaction_item)
        self.add_to_reaction_list(reaction_item)
        self.scene_object.addItem(reaction_item)

        return reaction_item

    def __build_pathinfo_item(self, x: int, y: int, path: List[Any], path_rank: int, path_length: float, text: str):
        pathinfo_item = Pathinfo(x, y, path, path_rank, path_length, text)
        pathinfo_item.bind_mouse_double_click_function(self.path_info_mouse_double_press)

        self.scene_object.addItem(pathinfo_item)
        self.pathinfo_list.append(pathinfo_item)

    def __build_edge(self, start: QPoint, end: QPoint):
        path = QPainterPath(start)
        path.lineTo(end)
        # ID must be unique for scene!
        edge_item = QGraphicsPathItem(path)
        edge_item.setPen(self.path_pen)
        # ID must be unique for scene!
        self.scene_object.addItem(edge_item)
        return edge_item

    # # # END BUILD ITEM FUNCTIONS
    def path_info_mouse_double_press(self, _, item: QGraphicsItem) -> None:
        assert self.settings
        # Include structure model
        if self.settings.pathfinder.options.use_structure_model:
            structure_model = self.settings.pathfinder.options.structure_model
            if not isinstance(structure_model, db.Model):
                raise RuntimeError("Structure model not set")
        else:
            structure_model = self.settings.pathfinder.options.model

        level_list = [0.0]
        is_barrierless_list = []
        type_list = []
        for rxn_id in [rxn_node for rxn_node in item.path if ';' in rxn_node]:

            # Get elementary step from graph or database
            es_from_graph = None
            if "elementary_step_id" in self._graph.nodes(data=True)[rxn_id]:
                es_id = db.ID(
                    self._graph.nodes(data=True)[rxn_id]["elementary_step_id"])
                es_from_graph = db.ElementaryStep(es_id, self._elementary_step_collection)

            if es_from_graph is None:
                rxn = db.Reaction(db.ID(rxn_id.split(';')[0]), self._reaction_collection)
                es, barriers = self._get_elementary_step_of_reaction_from_db(
                    rxn,
                    self.settings.pathfinder.options.model,
                    structure_model)
            else:
                es = es_from_graph
                barriers = get_barriers_for_elementary_step_by_type(
                    es_from_graph,
                    "electronic_energy",
                    self.settings.pathfinder.options.model,
                    self._structure_collection,
                    self._property_collection
                )

            # Check faulty barriers
            if any(barrier is None for barrier in barriers) or es is None:
                raise RuntimeError("Barrier is None")

            es_type = es.get_type()
            if es_type == db.ElementaryStepType.BARRIERLESS:
                is_barrierless_list.append(True)
            else:
                is_barrierless_list.append(False)

            side_of_approach = int(rxn_id.split(';')[1])
            if side_of_approach == 0:
                tmp_up = barriers[0]
                tmp_down = barriers[1]
            else:
                tmp_up = barriers[1]
                tmp_down = barriers[0]
            level_list.append(level_list[-1] + tmp_up)  # type: ignore
            level_list.append(level_list[-1] - tmp_down)  # type: ignore
        # # # Type list
        for node_id in item.path:
            if node_id is None or item.path_rank is None or item.path_length is None:
                continue
            # skip rxn nodes
            if ';' in node_id:
                continue
            if self._graph.nodes(data=True)[node_id]['type'] == db.CompoundOrFlask.COMPOUND.name:
                aggregate_type = db.CompoundOrFlask.COMPOUND
            elif self._graph.nodes(data=True)[node_id]['type'] == db.CompoundOrFlask.FLASK.name:
                aggregate_type = db.CompoundOrFlask.FLASK
            else:
                raise RuntimeError("Unknown aggregate type")
            type_list.append(aggregate_type)
        overall_rxn = self.settings.pathfinder.get_overall_reaction_equation(item.path)

        # Model string construction
        es_method_info = self.__construct_model_string(self.settings.pathfinder.options.model)
        # Structure model string construction
        if self.settings.pathfinder.options.use_structure_model \
           and self.settings.pathfinder.options.structure_model != self.settings.pathfinder.options.model:
            structure_model = self.settings.pathfinder.options.structure_model
            es_method_info += " energies on " +\
                              self.__construct_model_string(self.settings.pathfinder.options.structure_model)
            es_method_info += " structures"

        path_level_widget = PathLevelWidget(parent=self, db_manager=self.db_manager,
                                            levels=level_list, barrierless=is_barrierless_list,
                                            type_list=type_list,
                                            path_info=(item.path_rank, item.path_length, item.path),
                                            rxn_equation=overall_rxn,
                                            es_method_info=es_method_info)

        path_level_widget.show()

    def __bind_functions_to_object(self, object: Any) -> None:
        object.bind_mouse_press_function(self.mouse_press_function)
        object.setAcceptHoverEvents(True)
        object.bind_hover_enter_function(self.hover_enter_function)
        object.bind_hover_leave_function(self.hover_leave_function)
        object.bind_menu_function(self.menu_function)


class TraversalSettings(ReactionAndCompoundViewSettings):
    def __init__(self, parent: QWidget, graph_travel_view: GraphTravelView, model: db.Model) -> None:
        super(TraversalSettings, self).__init__(parent=parent, parsed_layout=QVBoxLayout())

        # Elements of widget relative to width of ReactionProfile Canvas
        self._widget_width = 480
        # Fixed width for widget
        self.setMinimumWidth(self._widget_width)
        self.setMaximumWidth(self._widget_width)

        self.graph_travel_view = graph_travel_view
        self.status_bar: Union[None, QWidget] = None

        self.p_layout.addWidget(ToolBarWithSaveLoad(self._save, self._load, self,
                                                    hover_text_save="Save Graph", hover_text_load="Load Graph"))

        self.start_box_label = QLabel(self)
        self.start_box_label.setText("Start ID")
        self.start_box_label.resize(int(self._widget_width * 0.95), 20)
        self.start_box_label.setFixedHeight(20)
        self.p_layout.addWidget(self.start_box_label)

        self.start_id_text = QLineEdit(self)
        self.start_id_text.resize(int(self._widget_width * 0.95), 40)
        self.start_id_text.setText("")
        self.p_layout.addWidget(self.start_id_text)

        self.target_box_label = QLabel(self)
        self.target_box_label.setText("Target ID")
        self.target_box_label.resize(int(self._widget_width * 0.95), 20)
        self.target_box_label.setFixedHeight(20)
        self.p_layout.addWidget(self.target_box_label)

        self.target_id_text = QLineEdit(self)
        self.target_id_text.resize(int(self._widget_width * 0.95), 40)
        self.target_id_text.setText("")
        self.p_layout.addWidget(self.target_id_text)
        # Search layout box
        hbox1layout = QHBoxLayout()
        self.button_search = TextPushButton(
            "Search",
            lambda: self.trigger_thread_function(
                self._search_function,
                self._print_progress))
        hbox1layout.addWidget(self.button_search)

        self.button_prev = TextPushButton("Previous", self.__prev_function)
        self.button_prev.setDisabled(True)
        hbox1layout.addWidget(self.button_prev)

        self.button_next = TextPushButton("Next", lambda: self.trigger_thread_function(
            self.__next_function, self._print_progress))
        self.button_next.setDisabled(True)
        hbox1layout.addWidget(self.button_next)

        self.p_layout.addLayout(hbox1layout)
        # List of currently found paths and bool to indicate if new paths have been found
        self.paths_excluding_reaction_double_crossing: List[Tuple[List[str], float]] = []
        self.paths_including_reaction_double_crossing: List[Tuple[List[str], float]] = []

        self.new_paths = False
        self._first_index_no_double_rxns = 0
        self._first_index_double_rxns = 0
        self._searched_unique_paths = False
        self._skipped_paths_counter = 0
        self._pathfinder_options_changed = False
        self._pathfinder_graph_from_file = False

        # Timer for plotting newly found paths
        self.check_new_paths_timer = QTimer(self)
        # Timer might be causing segfaults if too short
        self.check_new_paths_timer.setInterval(1)
        self.check_new_paths_timer.timeout.connect(self.__plot_new_paths)  # pylint: disable=no-member
        self.check_new_paths_timer.start()

        self.pathfinder = pf(self.graph_travel_view.db_manager)
        # Model from CRNetworkView
        self.pathfinder.options.model = copy.deepcopy(model)
        self.pathfinder.options.structure_model = copy.deepcopy(model)

        self._start_conditions: Dict[str, float] = {}

        # buttons

        self.button_settings = TextPushButton("Pathfinder Settings", self._show_settings)
        self.p_layout.addWidget(self.button_settings)

        self.button_ccost = TextPushButton("Start conditions", self._show_start_conditions)
        self.p_layout.addWidget(self.button_ccost)

        self.button_calculate_compound_costs = TextPushButton(
            "Calculate Compound Costs", lambda: self.trigger_thread_function(
                self.__calculate_compound_costs_function, self._print_progress))
        self.p_layout.addWidget(self.button_calculate_compound_costs)

        self.buttons_to_deactivate = [self.button_search, self.button_next, self.button_prev,
                                      self.button_settings, self.button_ccost, self.button_calculate_compound_costs]
        self.buttons_to_reactivate: List[Any] = []

        self.save_to_svg_button = TextPushButton("Save SVG", self.graph_travel_view.save_svg)
        self.p_layout.addWidget(self.save_to_svg_button)

        # Search time layout
        search_time_layout = QHBoxLayout()
        search_time_layout.addWidget(WrappedLabel("Max. Search Time"))
        self.max_search_time = NoWheelDoubleSpinBox()
        self.max_search_time.setMinimum(1.0)
        self.max_search_time.setMaximum(3600.0)
        self.max_search_time.setValue(60.0)
        search_time_layout.addWidget(self.max_search_time)
        self.p_layout.addLayout(search_time_layout)

        self.unique_paths_cbox = QCheckBox("Show unique paths only")
        self.unique_paths_cbox.setChecked(True)
        self.p_layout.addWidget(self.unique_paths_cbox)

        self.true_sight_cbox = QCheckBox("Activate true sight")
        self.true_sight_cbox.setToolTip("Allow identical reaction\n to occur twice in shown paths.")
        self.p_layout.addWidget(self.true_sight_cbox)

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

        self.setLayout(self.p_layout)
        self.show()

    def set_status_bar(self, status_widget: QWidget):
        self.status_bar = status_widget

    def _save(self):
        timestamp = datetime.datetime.now().strftime("%m%d-%H%M%S")
        handler = self.pathfinder.options.graph_handler

        filename = get_save_file_name(self, "graph." + handler + "." + timestamp, ['json'])
        if filename is None:
            return
        self.pathfinder.export_graph(filename)

    def _load(self):
        graph_filename = get_load_file_name(self, "graph", ['json'])
        if graph_filename is None:
            return
        compound_cost_filename = get_load_file_name(self, "compound_costs", ["json"])
        if compound_cost_filename is None:
            self.pathfinder.load_graph(graph_filename)
            self._pathfinder_graph_from_file = True
        else:
            self.pathfinder.load_graph(graph_filename, compound_cost_filename)
            self._pathfinder_graph_from_file = True
        # # # Link graph of travel view to graph of graph handler
        self.graph_travel_view._graph = self.pathfinder.graph_handler.graph

    def _print_progress(self, signal):
        if signal[0]:
            self.status_bar.clear_message()
            self.status_bar.update_status("Status:" + 4 * " " + signal[1], timer=None)
        # When signal is false, error status
        else:
            self.status_bar.clear_message()
            self.status_bar.update_error_status("Status:" + 4 * " " + signal[1], timer=5 * 1000)

    @staticmethod
    def trigger_thread_function(func, info_func):
        worker = Worker(func)
        worker.signals.running.connect(info_func)

        pool = QThreadPool.globalInstance()
        pool.start(worker)

    def __path_has_reaction_double_crossing(self, pathfinder_path_nodes: List[str]):
        # Extract ID of reaction nodes of pathfinder path
        tmp_rxn_list = [node.split(";")[0] for node in pathfinder_path_nodes if ";" in node]
        # True if every reaction only appears once, else False
        return len(tmp_rxn_list) != len(list(set(tmp_rxn_list)))

    def __clear_found_paths(self):
        self.paths_excluding_reaction_double_crossing = []
        self.paths_including_reaction_double_crossing = []

    def _build_graph_function(self):
        self.pathfinder.build_graph()

    def _show_settings(self):
        docstring_parser = DocStringParser()
        docstrings = docstring_parser.get_docstring_for_object_attrs(self.pathfinder.__class__.__name__,
                                                                     self.pathfinder.options)
        prev_options = copy.deepcopy(self.pathfinder.options)
        options = DictOptionWidget.get_attributes_of_object(self.pathfinder.options)
        setting_widget = ClassOptionsWidget(
            options, docstrings, parent=self, add_close_button=True,
            allow_removal=False,
        )
        # # # Other Defaults for barrierless weight widget
        barrierless_weight_widget = setting_widget._option_widget._option_widgets['barrierless_weight']
        barrierless_weight_widget.setMaximum(float(1e14))
        barrierless_weight_widget.setValue(1e12)
        # # #
        setting_widget.exec_()
        DictOptionWidget.set_attributes_to_object(self.pathfinder.options, options)
        self._pathfinder_options_changed = bool(prev_options != self.pathfinder.options)

    def _show_start_conditions(self):
        # can load stuff from json
        new_compound_costs = copy.deepcopy(self._start_conditions)
        ccost_widget = CompoundCostOptionsWidget(new_compound_costs, parent=self)
        # exec for looking
        ccost_widget.show()

    def _disable_buttons(self):
        # Disable buttons to avoid overload
        buttons_to_reactivate = []
        for button in self.buttons_to_deactivate:
            if button.isEnabled():
                buttons_to_reactivate.append(button)
                button.setDisabled(True)
        return buttons_to_reactivate

    def _show_path_level_widget(self):
        path_level_widget = PathLevelWidget(parent=self, db_manager=self.graph_travel_view.db_manager)
        path_level_widget.show()

    def _find_unique_paths_and_store_in_cache(self) -> bool:
        """
        Wrapper function for finding unique paths and storing the results in the cache
        for including double crossing of reactions and
        for excluding double crossing of reactions.

        Returns
        -------
        search_timed_out : bool
            Bool indicating if the search was interrupted by a time out.
        """
        # Counter for following loops
        path_counter = 0
        search_timed_out = False
        # Loop until 15 paths are found
        search_start_time = time.time()
        while (path_counter < 15):
            tmp_paths = self.pathfinder.find_unique_paths(
                self.start_id_text.text(), self.target_id_text.text(), 1)
            if len(tmp_paths) == 0:
                break
            # Regardless if valid or not, save the path here
            self.paths_including_reaction_double_crossing.append(tmp_paths[0])
            # Count only, if it is a path without rxn double crossing
            if not self.__path_has_reaction_double_crossing(tmp_paths[0][0]):
                self.paths_excluding_reaction_double_crossing.append(tmp_paths[0])
                path_counter += 1
            if not self.pathfinder._use_old_iterator:
                self.pathfinder._use_old_iterator = True
            if ((time.time() - search_start_time) > float(self.max_search_time.value())):
                search_timed_out = True
                break
        return search_timed_out

    def _find_paths_and_store_in_cache(self) -> bool:
        """
        Wrapper function for finding non-unique paths and storing the results in the cache
        for including double crossing of reactions and
        for excluding double crossing of reactions.

        Returns
        -------
        search_timed_out : bool
            Bool indicating if the search was interrupted by a time out.
        """
        # counter
        path_counter = 0
        search_timed_out = False
        analyzed_paths = 0
        search_start_time = time.time()
        while (path_counter < 15):
            tmp_paths = self.pathfinder.find_paths(self.start_id_text.text(), self.target_id_text.text(), 1,
                                                   n_skipped_paths=self._skipped_paths_counter)
            if len(tmp_paths) == 0:
                break
            self._skipped_paths_counter += 1
            analyzed_paths += 1
            # Regardless if valid or not, save the path here
            self.paths_including_reaction_double_crossing.append(tmp_paths[0])
            # Count only, if it is a valid path
            if not self.__path_has_reaction_double_crossing(tmp_paths[0][0]):
                self.paths_excluding_reaction_double_crossing.append(tmp_paths[0])
                path_counter += 1
            if ((time.time() - search_start_time) > float(self.max_search_time.value())):
                search_timed_out = True
                break
        return search_timed_out

    def _search_function(self, progress_callback: SignalInstance):
        progress_callback.emit((True, "Calculating routes"))
        self.buttons_to_reactivate = self._disable_buttons()

        if self.start_id_text.text() == "" or self.target_id_text.text() == "":
            progress_callback.emit((False, "Add a start ID and a target ID for your search."))
            return

        if self.pathfinder.graph_handler is None or (
                self._pathfinder_options_changed and not self._pathfinder_graph_from_file):
            progress_callback.emit((True, "Building graph"))
            self._build_graph_function()
            self.graph_travel_view._graph = self.pathfinder.graph_handler.graph
            progress_callback.emit((True, "Calculating routes"))
            # Reset bool for changed options
            if self._pathfinder_options_changed:
                self._pathfinder_options_changed = False
            assert self.pathfinder
        else:
            assert self.pathfinder
            assert self.pathfinder.graph_handler
        # Reset iterator in pathfinder
        self.pathfinder._use_old_iterator = False
        self._skipped_paths_counter = 0
        # Clear all paths found so far
        self.__clear_found_paths()

        search_timed_out = False

        if self.unique_paths_cbox.isChecked():
            # Loop until 15 paths are found
            search_timed_out = self._find_unique_paths_and_store_in_cache()
            # Activate next Button
            self.buttons_to_reactivate.append(self.button_next)
            # Set search type memory
            self._searched_unique_paths = True
        else:
            # Loop until 15 paths are found
            search_timed_out = self._find_paths_and_store_in_cache()
            self._searched_unique_paths = False
            self.buttons_to_reactivate.append(self.button_next)

        # Reset found paths and first path index
        self.new_paths = True
        self.pathfinder._use_old_iterator = True
        self._first_index_double_rxns = 0
        self._first_index_no_double_rxns = 0

        # Signal to Status Box
        status_message = "Ready"
        if search_timed_out:
            status_message += " -- with search time out"
        if len(self.paths_excluding_reaction_double_crossing) == 0:
            status_message += " -- True sight mode"
        progress_callback.emit((True, status_message))

    def _paths_in_cache(self) -> bool:
        paths_in_cache = False
        # Check paths including rxn double crossings if box is checked
        if self.true_sight_cbox.isChecked():
            if (len(self.paths_including_reaction_double_crossing) - self._first_index_double_rxns) > 15:
                paths_in_cache = True
        # Check paths excluding rxn double crossings if box is checked
        else:
            if (len(self.paths_excluding_reaction_double_crossing) - self._first_index_no_double_rxns) > 15:
                paths_in_cache = True
        return paths_in_cache

    def __next_function(self, progress_callback: SignalInstance):  # pylint: disable=unused-argument

        if self.start_id_text.text() == "" or self.target_id_text.text() == "":
            progress_callback.emit((False, "Add a start ID and a target ID for your search."))
            return

        progress_callback.emit((True, "Calculating routes"))
        self.buttons_to_reactivate = self._disable_buttons()
        assert self.pathfinder
        increase_indices = False
        search_timed_out = False
        # Check, if previous search was unique or not
        if self.unique_paths_cbox.isChecked() == self._searched_unique_paths:
            if self._paths_in_cache():
                increase_indices = True
            elif self.unique_paths_cbox.isChecked():
                search_timed_out = self._find_unique_paths_and_store_in_cache()
            else:
                # Loop until 15 paths are found
                search_timed_out = self._find_paths_and_store_in_cache()

            # # # Safety check for case no rxn excluding double crossing are found
            if len(self.paths_excluding_reaction_double_crossing) == 0 and\
               (len(self.paths_including_reaction_double_crossing) - self._first_index_double_rxns) > 15:
                increase_indices = True
            # # # Determine on how to increase indices
            if increase_indices:
                self._first_index_no_double_rxns += 15
                self._first_index_double_rxns += 15
            else:
                # # # Set indices
                self._first_index_no_double_rxns = 15 * \
                    int((len(self.paths_excluding_reaction_double_crossing) - 1) / 15)
                self._first_index_double_rxns = 15 * int((len(self.paths_including_reaction_double_crossing) - 1) / 15)
        # # # Redo search if any entry of checked box changed
        else:
            self.trigger_thread_function(self._search_function, self._print_progress)

        # Signal to Status Box
        status_message = "Ready"
        if search_timed_out:
            status_message += " -- with search time out"
        if len(self.paths_excluding_reaction_double_crossing) == 0:
            status_message += " -- True sight mode"
        progress_callback.emit((True, status_message))

        self.new_paths = True

    def __prev_function(self):
        if self.unique_paths_cbox.isChecked() == self._searched_unique_paths:
            self.buttons_to_reactivate = self._disable_buttons()
            # Reduce start index by 15
            self._first_index_no_double_rxns -= 15
            self._first_index_double_rxns -= 15
            self.new_paths = True
        else:
            self.trigger_thread_function(self._search_function, self._print_progress)

    def __plot_new_paths(self):
        if self.new_paths:
            # Get end index based on length of stored reactions
            if len(self.paths_excluding_reaction_double_crossing) - self._first_index_no_double_rxns >= 15:
                no_double_cross_step = 15
            else:
                no_double_cross_step = len(self.paths_excluding_reaction_double_crossing) % 15

            if len(self.paths_including_reaction_double_crossing) - self._first_index_double_rxns >= 15:
                double_cross_step = 15
            else:
                double_cross_step = len(self.paths_including_reaction_double_crossing) % 15

            self.graph_travel_view.plot_paths(
                # List of list of visited reaction nodes
                [path_data for path_data in
                    self.paths_excluding_reaction_double_crossing[
                        self._first_index_no_double_rxns:self._first_index_no_double_rxns + no_double_cross_step]],
                [path_data for path_data in
                    self.paths_including_reaction_double_crossing[
                        self._first_index_double_rxns:self._first_index_double_rxns + double_cross_step]],
                self.true_sight_cbox.isChecked()
            )

            # Add or remove previous button dependent on index
            if self._first_index_no_double_rxns > 0.0 or\
               (self.true_sight_cbox.isChecked() and self._first_index_double_rxns > 0.0):
                self.buttons_to_reactivate.append(self.button_prev)
            elif self.button_prev in self.buttons_to_reactivate:
                self.buttons_to_reactivate.remove(self.button_prev)
                self.button_prev.setDisabled(True)

            # Reactivate all of the required buttons
            for button in self.buttons_to_reactivate:
                button.setDisabled(False)
            self.buttons_to_reactivate = []
            # Reset trigger for plotting
            self.new_paths = False

    def __calculate_compound_costs_function(self, progress_callback: SignalInstance):  # pylint: disable=unused-argument
        if self.pathfinder is None:
            self.trigger_thread_function(self._build_graph_function, self._print_progress)
            assert self.pathfinder
        else:
            assert self.pathfinder
        progress_callback.emit((True, "Calculate Compound Costs"))
        # # # Set start conditions
        self.pathfinder.set_start_conditions(self._start_conditions)
        # # # Determine the compound costs
        self.pathfinder.calculate_compound_costs()
        # # # Save compound costs
        timestamp = datetime.datetime.now().strftime("%m%d-%H%M%S")
        filename = Path("compound_costs." + timestamp + ".json")
        self.pathfinder.export_compound_costs(filename)
        # # # Update the graph with the information of the compound costs
        self.pathfinder.update_graph_compound_costs()

        progress_callback.emit((True, "Ready"))
        if self.start_id_text.text() != "" and self.target_id_text.text() != "":
            self.trigger_thread_function(self._search_function,
                                         self._print_progress)
