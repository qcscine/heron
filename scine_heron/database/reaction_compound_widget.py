#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from PySide2.QtCore import Qt, QTimer, QPoint, QThreadPool, SignalInstance, QDate  # QTimeLine
from PySide2.QtGui import QPainterPath, QGuiApplication
from PySide2.QtWidgets import (
    QWidget,
    QPushButton,
    QLabel,
    QDateTimeEdit,
    QLineEdit,
    QGraphicsPathItem,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QCheckBox,
    QScrollArea
)
from datetime import datetime
from scine_heron import find_main_window
from scine_heron.settings.class_options_widget import ModelOptionsWidget
from scine_heron.database.reaction_compound_view import ReactionAndCompoundView, ReactionAndCompoundViewSettings
from scine_heron.database.graphics_items import Compound, Reaction
from scine_heron.containers.layouts import VerticalLayout, HorizontalLayout
from scine_heron.containers.buttons import TextPushButton
from scine_heron.io.file_browser_popup import get_load_file_name
from scine_heron.multithread import Worker
from scine_chemoton.gears.pathfinder import Pathfinder as pf

from scine_database.concentration_query_functions import (
    query_concentration,
    query_reaction_flux
)
from scine_database.energy_query_functions import (
    get_energy_change,
    get_barriers_for_elementary_step_by_type,
)
import scine_database as db
import copy
import networkx as nx
import numpy as np
from json import dumps
from typing import Dict, Optional, Any, List, Union, Tuple, TYPE_CHECKING


if TYPE_CHECKING:
    Slot = Any
else:
    from PySide2.QtCore import Slot


class AdvancedSettingsWidget(QWidget):
    def __init__(self, network, db_manager, parent=None) -> None:
        super(AdvancedSettingsWidget, self).__init__(parent)
        self._max_barrier = 2650.5
        self._min_barrier = - 1000.0
        self._always_show_barrierless = True
        self._model: Optional[db.Model] = None
        self._model_button = QPushButton("Set Model")
        self._model_button.clicked.connect(self._call_model_dialog)  # pylint: disable=no-member
        self._enforce_structure_model = False
        self._scale_with_concentrations = False
        self._min_flux = 1e-5
        self._network = network
        self._db_manager = db_manager

        self.__layout = QVBoxLayout()

        self._set_up_barrier_widgets(self.__layout)

        self.__layout.addWidget(self._model_button)

        self.enforce_structure_model_cbox = QCheckBox("Enforce Structure Model", parent=self)
        self.enforce_structure_model_cbox.setChecked(self._enforce_structure_model)
        self.__layout.addWidget(self.enforce_structure_model_cbox)

        self._set_up_concentration_widgets(self.__layout)

        self.setLayout(self.__layout)

    def get_max_barrier(self) -> float:
        return float(self.current_max_barrier_text.text())

    def get_min_barrier(self) -> float:
        return float(self.current_min_barrier_text.text())

    def always_show_barrierless(self) -> bool:
        return self.always_show_barrierless_reactions_cbox.isChecked()

    def get_min_flux(self) -> float:
        return float(self.current_min_flux_text.text())

    def get_model(self) -> db.Model:
        if self._model is None:
            self._query_for_general_model()
        if self._model is None:
            self._call_model_dialog()
        assert self._model is not None
        return self._model

    def scale_with_concentrations(self):
        return self.concentration_scaling_cbox.isChecked()

    def enforce_structure_model(self):
        return self.enforce_structure_model_cbox.isChecked()

    def _call_model_dialog(self):
        dialog = ModelOptionsWidget(self, self._model)
        # Note: Ideally, the option widget should still be movable
        dialog.exec_()
        # Overwrite model from dialog after exec if the initial is None
        if self._model is None:
            self._model = copy.deepcopy(dialog._options)

    def _set_up_barrier_widgets(self, layout):
        qhbox_labels = QHBoxLayout()
        qhbox_texts = QHBoxLayout()
        self.current_max_barrier_label = QLabel(self)
        self.current_max_barrier_label.resize(280, 40)
        self.current_max_barrier_label.setText("Max. Barrier Height [kJ/mol]")
        qhbox_labels.addWidget(self.current_max_barrier_label)
        self.current_max_barrier_text = QLineEdit(self)
        self.current_max_barrier_text.resize(280, 40)
        self.current_max_barrier_text.setText(str(self._max_barrier))
        qhbox_texts.addWidget(self.current_max_barrier_text)

        self.current_min_barrier_label = QLabel(self)
        self.current_min_barrier_label.resize(280, 40)
        self.current_min_barrier_label.setText("Min. Barrier Height [kJ/mol]")
        qhbox_labels.addWidget(self.current_min_barrier_label)
        self.current_min_barrier_text = QLineEdit(self)
        self.current_min_barrier_text.resize(280, 40)
        self.current_min_barrier_text.setText(str(self._min_barrier))
        qhbox_texts.addWidget(self.current_min_barrier_text)

        layout.addLayout(qhbox_labels)
        layout.addLayout(qhbox_texts)
        self.always_show_barrierless_reactions_cbox = QCheckBox("Always show barrier-less reactions", parent=self)
        self.always_show_barrierless_reactions_cbox.setChecked(self._always_show_barrierless)
        layout.addWidget(self.always_show_barrierless_reactions_cbox)

    def _set_up_concentration_widgets(self, layout):
        self.concentration_scaling_cbox = QCheckBox("Truncate by Concentration")
        self.concentration_scaling_cbox.setChecked(self._scale_with_concentrations)
        layout.addWidget(self.concentration_scaling_cbox)
        self.current_min_flux_label = QLabel(self)
        self.current_min_flux_label.resize(280, 40)
        self.current_min_flux_label.setText("Min. Concentration Flux")
        layout.addWidget(self.current_min_flux_label)
        self.current_min_flux_text = QLineEdit(self)
        self.current_min_flux_text.resize(280, 40)
        self.current_min_flux_text.setText(str(self._min_flux))
        layout.addWidget(self.current_min_flux_text)

    def _query_for_general_model(self):
        selection = {
            "$and": [
                {"status": {"$eq": "complete"}},
                {"results.elementary_steps.0": {"$exists": True}},
            ]
        }
        calculation = (
            self._db_manager.get_collection("calculations").get_one_calculation(dumps(selection))
        )
        if calculation is None:
            selection = {"label": {"$in": ["user_optimized", "user_surface_optimized"]}}
            structure = self._db_manager.get_collection("structures").get_one_structure(dumps(selection))
            if structure is None:
                return
            model = structure.model
        else:
            model = calculation.model
        # # # Generalize initial model
        for model_attribute in ["electronic_temperature", "pressure", "spin_mode", "temperature", "version"]:
            setattr(model, model_attribute, "any")
        self._model = model

    def update_settings(self):
        """
        Read the model definition and maximum barrier from the input boxes. If "None" is given in the method family
        input box. Get some model from the database.
        """
        self._enforce_structure_model = self.enforce_structure_model()
        # Maximum/Minimum barrier and flux.
        self._max_barrier = self.get_max_barrier()
        self._min_barrier = self.get_min_barrier()
        self._always_show_barrierless = self.always_show_barrierless()
        self._min_flux = self.get_min_flux()
        self._scale_with_concentrations = self.scale_with_concentrations()


class CRNetwork(ReactionAndCompoundView):
    def __init__(self, parent: QWidget, db_manager: db.Manager) -> None:
        super().__init__(parent=parent)
        self.setMouseTracking(True)
        self.setInteractive(True)
        self.setMinimumWidth(100)
        self.setMinimumHeight(100)

        self.structure_of_compound = None

        self._graph: Union[nx.DiGraph, None] = None
        self._graph_model = db.Model("any", "any", "any")
        self._graph_with_structure_model = False
        self._currently_plotting = False
        self.new_network = False
        # Cache of subgraphs with graph and positions
        # NOTE: Don't know how memory intensive
        self.subgraph_cache: Dict[str, Dict[str, Any]] = dict()

        # Add all data
        self.db_manager: db.Manager = db_manager
        self.centroid_item: Optional[Compound] = None
        self.current_centroid_id: str = ""
        self.__history: List[str] = []
        self.__current_history_position: int = -1

        # db-info of selected compound
        self._compound_collection = self.db_manager.get_collection("compounds")
        self._reaction_collection = self.db_manager.get_collection("reactions")
        self._flask_collection = self.db_manager.get_collection("flasks")
        self._elementary_step_collection = self.db_manager.get_collection("elementary_steps")
        self._property_collection = self.db_manager.get_collection("properties")
        self._structure_collection = self.db_manager.get_collection("structures")

    @staticmethod
    def _print_progress(signal):

        main_window = find_main_window()
        if main_window is not None:
            status_bar = main_window.get_status_bar()
            if signal[0]:
                status_bar.clear_message()
                status_bar.update_status(signal[1], timer=None)
            # When signal is false, error status
            else:
                status_bar.clear_message()
                status_bar.update_error_status(signal[1], timer=5 * 1000)

    @staticmethod
    def trigger_thread_function(func, info_func, *args, **kwargs):
        worker = Worker(func, *args, **kwargs)
        worker.signals.running.connect(info_func)

        pool = QThreadPool.globalInstance()
        pool.start(worker)

    def focus_function(self, _, item: Union[Compound, Reaction]) -> None:
        # Store current connected items
        self.subgraph_cache[self.current_centroid_id]["focused_connected_items"] = self.focused_connected_items
        self.subgraph_cache[self.current_centroid_id]["focused_connected_lines"] = self.focused_connected_lines
        id_string = item.db_representation.id().string()
        assert self.settings
        cr_settings = self.settings
        cr_settings.update_current_centroid_text(id_string)
        cr_settings.advanced_settings_widget.update_settings()
        self.trigger_thread_function(
            self.update_network,
            self._print_progress,
            cr_settings.advanced_settings_widget.get_model(),
            cr_settings.advanced_settings_widget.enforce_structure_model(),
            trigger_plot=True,
            requested_centroid=id_string,
            triggered_from_focus_click=True,
        )

    def redo_move(self):
        if (self.__current_history_position + 2) > len(self.__history) or self.__current_history_position < 0:
            return
        self.__current_history_position += 1
        centroid_id = self.__history[self.__current_history_position]
        self.update_network(self._graph_model, self._graph_with_structure_model,
                            trigger_plot=True,
                            requested_centroid=centroid_id,
                            track_update=False)
        # Update text field
        self.settings.update_current_centroid_text(
            str(self.current_centroid_id)
        )

    def undo_move(self):
        if self.__current_history_position > len(self.__history) or self.__current_history_position < 1:
            return
        self.__current_history_position -= 1
        centroid_id = self.__history[self.__current_history_position]
        self.update_network(self._graph_model, self._graph_with_structure_model,
                            trigger_plot=True,
                            requested_centroid=centroid_id,
                            track_update=False)
        # Update text field
        self.settings.update_current_centroid_text(
            str(self.current_centroid_id)
        )

    def load_graph(self):
        pathfinder = pf(self.db_manager)
        graph_filenname = get_load_file_name(self, "graph", ['json'])
        if graph_filenname is None:
            return
        # Load new graph
        pathfinder.load_graph(graph_filenname)
        self._graph = copy.deepcopy(pathfinder.graph_handler.graph)
        self.settings.advanced_settings_widget._call_model_dialog()
        self._graph_model = self.settings.advanced_settings_widget.get_model()
        # NOTE: Assume structure model for loaded graph
        self.settings.advanced_settings_widget._enforce_structure_model = True
        self.settings.advanced_settings_widget.enforce_structure_model_cbox.setChecked(True)
        self._graph_with_structure_model = True

    def reset_graph(self):
        self._graph = None
        self._graph_model = db.Model("any", "any", "any")

    def reset_subgraph_cache(self):
        self.subgraph_cache = {}

    def remove_all_items(self):
        # # # Remove old items from current scene
        items = self.scene_object.items()
        for item in items:
            self.scene_object.removeItem(item)

    def plot_network(self):
        if self._currently_plotting:
            return
        self._currently_plotting = True
        self.remove_all_items()
        # # # Add new items
        for k in self.line_items.keys():
            self.scene_object.addItem(self.line_items[k])
        for c in self.compounds.keys():
            self.scene_object.addItem(self.compounds[c][0])
        for r in self.reactions.keys():
            self.scene_object.addItem(self.reactions[r][0])
        self.__center_view()

        self._currently_plotting = False

    def update_network(
        self,
        model: db.Model,
        enforce_structure_model: bool,
        progress_callback: Optional[SignalInstance] = None,
        trigger_plot=False,
        requested_centroid: Optional[str] = None,
        track_update: bool = True,
        triggered_from_focus_click: bool = False
    ) -> None:
        if progress_callback is not None:
            progress_callback.emit((True, "Status:" + 4 * " " + "Loading Network"))
        # If graph not present, build basic graph
        if self._graph is None or \
           model != self._graph_model or \
           enforce_structure_model != self._graph_with_structure_model:
            # NOTE: possible to introduce subgraph cache per model
            self.reset_subgraph_cache()
            # NOTE: Add loading screen
            self.__build_graph()
            assert self._graph
            if len(self._graph.nodes()) == 0:
                assert progress_callback
                progress_callback.emit((False, 'Status:' + 4 * " " + "No graph available!"))
                return

            assert self._graph

        if requested_centroid is None:
            tmp_compound = self._compound_collection.get_one_compound(dumps({}))
            if tmp_compound:
                requested_centroid = tmp_compound.id().string()
            else:
                assert progress_callback
                progress_callback.emit((False, 'Status:' + 4 * " " + "No compounds available!"))
                return

        # Check that requested centroid is in graph
        if requested_centroid not in self._graph.nodes():
            assert progress_callback
            progress_callback.emit((False, 'Status:' + 4 * " " + "Centroid not available!"))
            return
        else:
            self.current_centroid_id = requested_centroid

        # Reset storage
        self.compounds = {}
        self.reactions = {}
        self.line_items = {}

        if track_update:
            if len(self.__history) == 0:
                self.__current_history_position += 1
                self.__history = self.__history[0:(self.__current_history_position)]
                self.__history.append(self.current_centroid_id)
            elif self.__history[-1] != self.current_centroid_id:
                self.__current_history_position += 1
                self.__history = self.__history[0:self.__current_history_position]
                self.__history.append(self.current_centroid_id)

        # # # Start building subgraph
        centroid_sub_graph, reaction_nodes, aggregate_nodes = self.__get_subgraph_of_centroid(
            self.current_centroid_id)
        # NOTE: Start building subgraph of all aggregate nodes as subthread (process?),
        #       just list of nodes required as input

        dist_value = 0.2
        max_dimensions = (420, 420)
        if len(centroid_sub_graph.nodes) > 400:
            dist_value = 0.1
            max_dimensions = (int(1000 * 1.5), 1000)

        # # # Retrieve positions
        if "positions" not in self.subgraph_cache[self.current_centroid_id].keys():

            positions = self.__get_node_positions_for_subgraph(self.current_centroid_id, centroid_sub_graph,
                                                               reaction_nodes, aggregate_nodes, dist_value)
            scaled_positions = self.__scale_positions(positions, max_dimensions)

            # Store scaled positions in cache
            self.subgraph_cache[self.current_centroid_id]["positions"] = scaled_positions
            # Init Cache for compounds and reactions
            self.subgraph_cache[self.current_centroid_id]["compounds"] = dict()
            self.subgraph_cache[self.current_centroid_id]["reactions"] = dict()
            self.subgraph_cache[self.current_centroid_id]["lines"] = dict()
            self.subgraph_cache[self.current_centroid_id]["focused_connected_items"] = list()
            self.subgraph_cache[self.current_centroid_id]["focused_connected_lines"] = list()
        else:
            # Load positions from cache:
            scaled_positions = copy.deepcopy(self.subgraph_cache[self.current_centroid_id]["positions"])
            # Load connected items from previous scene
            self.focused_connected_items = copy.deepcopy(self.subgraph_cache[self.current_centroid_id]
                                                         ["focused_connected_items"])
            self.focused_connected_lines = copy.deepcopy(self.subgraph_cache[self.current_centroid_id]
                                                         ["focused_connected_lines"])
            if len(self.focused_connected_items) > 0:
                self.view_highlighted = True

        # # # Build centroid item
        aggregate, a_type = self.__get_aggregate_and_type_from_graph(requested_centroid)
        self.centroid_item, _ = self.__build_compound_item(0, 0, aggregate, a_type, allow_focus=False)

        # # # Build all items
        self.__build_subgraph_items(centroid_sub_graph, scaled_positions, reaction_nodes)
        # # # Reset colors of items if coming from a focus function call
        if triggered_from_focus_click:
            self.reset_item_colors()

        # Update with current centroid id, if empty
        if self.settings.current_id_text.text() == "":
            self.settings.update_current_centroid_text(str(self.current_centroid_id))

        if trigger_plot:
            self.new_network = True

        if progress_callback is not None:
            progress_callback.emit((True, 'Status:' + 4 * " " + "Network Ready"))

    def __build_compound_item(self, x: int, y: int, db_compound: Union[db.Compound, db.Flask],
                              a_type: db.CompoundOrFlask, allow_focus=True) -> Tuple[Compound, str]:
        cid_string = db_compound.id().string()
        # Look up in cache first
        if self.current_centroid_id in self.subgraph_cache.keys() and\
           cid_string in self.subgraph_cache[self.current_centroid_id]['compounds'].keys():
            old_compound_item = self.subgraph_cache[self.current_centroid_id]['compounds'][cid_string]
            # # # Copy stored compound item - necessary for scaling in this thread
            compound_item = Compound(old_compound_item.x_coord, old_compound_item.y_coord,
                                     pen=old_compound_item.get_pen(), brush=old_compound_item.get_brush(),
                                     concentration=old_compound_item.concentration)
            compound_item.set_current_brush(old_compound_item.get_current_brush())
            compound_item.set_current_pen(old_compound_item.get_current_pen())
            compound_item.db_representation = old_compound_item.db_representation
            compound_item.set_created(old_compound_item.get_created())
            compound_item.final_concentration = old_compound_item.final_concentration
            compound_item.concentration_flux = old_compound_item.concentration_flux
            # delete old_compound_item
            del old_compound_item
        else:
            centroid_structure = db.Structure(db_compound.get_centroid(), self._structure_collection)
            c_max = query_concentration("max_concentration", centroid_structure, self._property_collection)
            compound_item = Compound(x, y, pen=self.compound_pen, brush=self.get_aggregate_brush(a_type),
                                     concentration=c_max)
            compound_item.db_representation = db_compound
            compound_item.set_created(db_compound.created())

            compound_item.final_concentration = query_concentration("final_concentration",
                                                                    centroid_structure, self._property_collection)
            compound_item.concentration_flux = query_concentration("concentration_flux",
                                                                   centroid_structure, self._property_collection)

        # Allow to focus is different from graph travel
        self.__bind_functions_to_object(compound_item, allow_focus)

        # Decide upon scaling
        if self.settings.advanced_settings_widget.scale_with_concentrations():
            compound_item.allow_scaling = True
            compound_item.add_concentration_tooltip()
        else:
            compound_item.allow_scaling = False
        # Update size of compound item
        compound_item.update_size()
        # Add to cache
        self.subgraph_cache[self.current_centroid_id]['compounds'][cid_string] = compound_item
        self.replace_in_compound_list(compound_item)

        return compound_item, cid_string

    def __build_reaction_item(self, x: int, y: int, reaction: db.Reaction, side: int):
        assert self._graph
        assert self.settings
        plot_item = True
        # Look up in cache first
        if reaction.id().string() in self.subgraph_cache[self.current_centroid_id]['reactions'].keys():
            old_reaction_item = self.subgraph_cache[self.current_centroid_id]['reactions'][reaction.id().string()]
            # # # Copy stored reaction item - necessary for scaling in this thread
            reaction_item = Reaction(old_reaction_item.x_coord, old_reaction_item.y_coord,
                                     pen=old_reaction_item.get_pen(), brush=old_reaction_item.get_brush(),
                                     flux=old_reaction_item.get_flux(),
                                     invert_direction=old_reaction_item.invert_direction)
            reaction_item.set_current_brush(old_reaction_item.get_current_brush())
            reaction_item.set_current_pen(old_reaction_item.get_current_pen())
            # Copy all attributes
            reaction_item.barriers = old_reaction_item.barriers
            reaction_item.db_representation = old_reaction_item.db_representation
            reaction_item.set_created(old_reaction_item.get_created())
            reaction_item.assigned_es_id = old_reaction_item.assigned_es_id
            reaction_item.energy_difference = old_reaction_item.energy_difference
            reaction_item.spline = old_reaction_item.spline
            reaction_item.barrierless_type = old_reaction_item.barrierless_type
            # delete old_reaction_item
            del old_reaction_item
        else:
            # Get elementary step from graph or database
            es_from_graph = None
            node_id = reaction.id().string() + ";" + str(side) + ";"
            if "elementary_step_id" in self._graph.nodes(data=True)[node_id]:
                es_id = db.ID(
                    self._graph.nodes(data=True)[node_id]["elementary_step_id"])
                es_from_graph = db.ElementaryStep(es_id, self._elementary_step_collection)

            if es_from_graph is None:
                if self._graph_with_structure_model:
                    tmp_structure_model = self._graph_model
                else:
                    tmp_structure_model = None
                es, barriers = self._get_elementary_step_of_reaction_from_db(
                    reaction,
                    self._graph_model,
                    tmp_structure_model)
            else:
                es = es_from_graph
                barriers = get_barriers_for_elementary_step_by_type(es, "electronic_energy", self._graph_model,
                                                                    self._structure_collection,
                                                                    self._property_collection)

            if es is None:
                return None
            # Add reaction flux to reaction item
            # NOTE: Absolute flux, i guess
            flux = query_reaction_flux("_reaction_edge_flux", reaction,
                                       self._compound_collection, self._flask_collection,
                                       self._structure_collection, self._property_collection)
            # Creating reaction item
            reaction_item = Reaction(
                x, y, flux=flux,
                pen=self.reaction_pen,
                brush=self.get_reaction_brush(es.get_type()),
                # invert direction if side is 1
                invert_direction=bool(side)
            )
            reaction_item.set_barriers(barriers)

            if es.get_type() == db.ElementaryStepType.BARRIERLESS:
                reaction_item.barrierless_type = True

            reaction_item.db_representation = reaction
            reaction_item.set_created(reaction.created())
            reaction_item.assigned_es_id = es.id()
            struct = db.Structure(es.get_reactants()[0][0], self._structure_collection)
            # NOTE: Energy difference might be redundant
            reaction_item.energy_difference = get_energy_change(
                es, "electronic_energy", struct.get_model(), self._structure_collection, self._property_collection)

            if es.has_spline():
                reaction_item.spline = es.get_spline()

        self.__bind_functions_to_object(reaction_item)
        # Decide upon scaling
        if self.settings.advanced_settings_widget.scale_with_concentrations():
            reaction_item.allow_scaling = True
        else:
            reaction_item.allow_scaling = False

        # Decide, if plotted or not
        plot_item = False
        if reaction_item.barriers is not None:
            plot_item = self.__barrier_within_plot_window(reaction_item.barriers, side) and \
                self.__created_after_time_limit(reaction_item.get_created()) and \
                self.__reaction_flux_above_threshold(reaction_item.get_flux())
        # Check, if barrierless should be shown
        if reaction_item.barrierless_type and not\
           self.settings.advanced_settings_widget.always_show_barrierless():
            plot_item = False
        # Add to cache
        self.subgraph_cache[self.current_centroid_id]['reactions'][reaction.id().string()] = reaction_item
        if plot_item:
            self.add_to_reaction_list(reaction_item)
            return reaction_item
        else:
            return None

    def __build_edge(self, start: QPoint, end: QPoint, line_id: str):
        # Look edge up in cache first
        if line_id in self.subgraph_cache[self.current_centroid_id]['lines'].keys():
            edge_item = self.subgraph_cache[self.current_centroid_id]['lines'][line_id]
        else:
            path = QPainterPath(start)
            path.lineTo(end)
            # ID must be unique for scene!
            edge_item = QGraphicsPathItem(path)
            edge_item.setPen(self.path_pen)
            self.subgraph_cache[self.current_centroid_id]['lines'][line_id] = edge_item
        return edge_item

    def __barrier_within_plot_window(self, barriers: Union[Tuple[float, float], Tuple[None, None]],
                                     side: int):
        acceptable_barrier = True
        # Safety Check to avoid None comparison
        if not any(barrier is None for barrier in barriers) and self.settings is not None:
            if self.settings.advanced_settings_widget.get_max_barrier() < barriers[side] or \
               self.settings.advanced_settings_widget.get_min_barrier() > barriers[side]:
                acceptable_barrier = False

        return acceptable_barrier

    def __created_after_time_limit(self, created: Union[datetime, None]) -> bool:
        if created is None or created > datetime.fromtimestamp(self.settings.time_edit.dateTime().toSecsSinceEpoch()):
            return True
        else:
            return False

    def __reaction_flux_above_threshold(self, flux: Union[float, None]) -> bool:
        if self.settings.advanced_settings_widget.scale_with_concentrations() and \
           flux <= self.settings.advanced_settings_widget.get_min_flux():
            return False
        else:
            return True

    def __build_graph(self):
        # Init basic finder
        pathfinder = pf(self.db_manager)
        pathfinder.options.barrierless_weight = 1.0
        # Set model for graph from widget
        self._graph_model = copy.deepcopy(self.settings.advanced_settings_widget.get_model())
        pathfinder.options.model = self._graph_model
        pathfinder.options.graph_handler = "basic"

        pathfinder.options.use_structure_model = False
        if self.settings.advanced_settings_widget.enforce_structure_model():
            pathfinder.options.use_structure_model = True
            pathfinder.options.structure_model = self._graph_model
            self._graph_with_structure_model = True
        else:
            self._graph_with_structure_model = False
        # Build graph
        pathfinder.build_graph()
        self._graph = copy.deepcopy(pathfinder.graph_handler.graph)

    def __get_subgraph_of_centroid(self, centroid_id: str) -> Tuple[nx.DiGraph, List[str], List[str]]:
        assert self._graph
        reaction_nodes = []
        aggregate_nodes = []
        # Attempt reset
        centroid_subgraph = None
        undirected_graph = self._graph.to_undirected()
        if centroid_id not in self.subgraph_cache.keys():
            # # # Reactions outgoing from current centroid only!
            for centroid_edge in self._graph.out_edges(centroid_id):
                reaction_nodes.append(centroid_edge[1])
                for reaction_edge in undirected_graph.edges(centroid_edge[1]):
                    if reaction_edge[1] != centroid_id:
                        aggregate_nodes.append(reaction_edge[1])
            # Extract from subgraph from graph
            centroid_subgraph = self._graph.subgraph([centroid_id] + reaction_nodes + aggregate_nodes).copy()
            # Reset weights to one
            # NOTE: If not basic, with barrier info, one could attempt incorporating this information
            for edge in centroid_subgraph.edges:
                centroid_subgraph.edges[edge]['weight'] = 1.0  # old reset
            # Store subgraph in cache
            self.subgraph_cache[centroid_id] = {"graph": centroid_subgraph}
        # # # End building Subgraph
        else:
            centroid_subgraph = copy.deepcopy(self.subgraph_cache[centroid_id]["graph"])
            # Sort to list of nodes
            for node in centroid_subgraph.nodes():
                if ";" in node:
                    reaction_nodes.append(node)
                else:
                    if node != centroid_id:
                        aggregate_nodes.append(node)

        return centroid_subgraph, reaction_nodes, aggregate_nodes

    @staticmethod
    def __get_node_positions_for_subgraph(centroid_id: str, subgraph: nx.DiGraph,
                                          reaction_node_ids: List[str], aggregate_node_ids: List[str],
                                          min_node_distance=0.2) -> Dict[str, Tuple[float, float]]:
        # # # Start Positioning
        # Initial shell, with two rings
        # Loop over aggregates just to get all positions
        shell_position = nx.shell_layout(subgraph, [[centroid_id], reaction_node_ids, aggregate_node_ids],
                                         center=(0, 0), scale=1.0, rotate=0.0)

        # Determine subshell positioning
        for node in reaction_node_ids:
            # Products of reaction outside of rxn node
            outer_sub_shell_rxn = [r_edge[1] for r_edge in subgraph.out_edges(node) if r_edge[1] != centroid_id]
            if len(outer_sub_shell_rxn) > 1:
                outer_center = shell_position[node] + 0.3 * shell_position[node]
            else:
                outer_center = shell_position[node] + 0.25 * shell_position[node]
            outer_sub_shell_pos = nx.shell_layout(subgraph, [outer_sub_shell_rxn],
                                                  center=outer_center, scale=0.05)
            # Overwrite shell positions of outer sub shells
            for key, value in outer_sub_shell_pos.items():
                shell_position[key] = value

            # Reagents or reaction inside of rxn node
            inner_sub_shell_rxn = [r_edge[0] for r_edge in subgraph.in_edges(node) if r_edge[0] != centroid_id]
            if len(inner_sub_shell_rxn) > 1:
                inner_center = shell_position[node] - 0.3 * shell_position[node]
            else:
                inner_center = shell_position[node] - 0.25 * shell_position[node]
            inner_sub_shell_pos = nx.shell_layout(subgraph, [inner_sub_shell_rxn],
                                                  center=inner_center, scale=0.05)
            # Overwrite shell positions of inner sub shells
            for key, value in inner_sub_shell_pos.items():
                shell_position[key] = value

        # Determine position

        spring_position = nx.spring_layout(
            subgraph.to_undirected(),
            pos=shell_position,
            k=min_node_distance,  # node distance
            fixed=[centroid_id],
        )

        return copy.deepcopy(spring_position)

    @staticmethod
    def __scale_positions(positions: Dict[str, Any],
                          max_dimensions: Tuple[int, int]) -> Dict[str, Tuple[int, int]]:
        pos_matrix_list = []
        pos_key = []
        for key, value in positions.items():
            pos_key.append(key)
            pos_matrix_list.append(value)

        pos_matrix = np.asarray(pos_matrix_list)
        # Save normalization
        norm_x = np.max(np.abs(pos_matrix[:, 0])) if np.max(np.abs(pos_matrix[:, 0])) > 1e-9 else 1.0
        norm_y = np.max(np.abs(pos_matrix[:, 1])) if np.max(np.abs(pos_matrix[:, 1])) > 1e-9 else 1.0
        pos_matrix[:, 0] = pos_matrix[:, 0] / norm_x * max_dimensions[0]
        pos_matrix[:, 1] = pos_matrix[:, 1] / norm_y * max_dimensions[1]

        scaled_position = {}
        for key, value in zip(pos_key, pos_matrix):
            scaled_position[key] = value.astype(int)

        return scaled_position

    def __get_aggregate_and_type_from_graph(self,
                                            node_id: str) -> Tuple[Union[db.Compound, db.Flask], db.CompoundOrFlask]:
        assert self._graph
        aggregate: Union[db.Compound, db.Flask]
        if self._graph.nodes(data=True)[node_id]['type'] == db.CompoundOrFlask.COMPOUND.name:
            a_type = db.CompoundOrFlask.COMPOUND
            aggregate = db.Compound(db.ID(node_id), self._compound_collection)
        else:
            a_type = db.CompoundOrFlask.FLASK
            aggregate = db.Flask(db.ID(node_id), self._flask_collection)

        return aggregate, a_type

    def __build_subgraph_items(self, subgraph: nx.DiGraph,
                               positions: Dict[str, Tuple[int, int]], reaction_nodes: List[str]):
        # NOTE: parallelize this!
        for node in reaction_nodes:
            # Draw Rxn Nodes and edges
            rxn = db.Reaction(db.ID(node.split(";")[0]), self._reaction_collection)
            side = int(node.split(";")[1])
            # Filter are in building the reaction item
            rxn_item = self.__build_reaction_item(positions[node][0], positions[node][1], rxn, side)
            if rxn_item is None:
                continue
            # # # Rotate rxn item such that the rhs side points to the average outgoing position
            out_positions = np.array([np.array(positions[edge[1]]) for edge in subgraph.out_edges(node)])
            # Obtain relative vector of all outgoing positions
            rel_out_positions = np.sum(out_positions - np.array(positions[node]), axis=0)
            # Calculate angle to match the outgoing of the rxn item
            # with the average relative vector of the products
            # range from 0 to 2*pi, arctan(cross.norm, dot)
            rot_angle = np.arctan2(-rel_out_positions[1], np.dot(rel_out_positions, np.array([1, 0])))
            rot_angle += 2 * np.pi if rot_angle < 0 else 0
            rxn_item.update_angle(rot_angle)
            # # # Draw incoming edges of rxn node
            for e_count, edge in enumerate(subgraph.in_edges(node)):
                # Draw edge from aggregate to lhs of rxn
                line_id = "_".join(list(edge)) + "_" + str(e_count)
                edge_item = self.__build_edge(QPoint(positions[edge[0]][0],
                                                     positions[edge[0]][1]),
                                              rxn_item.incoming(), line_id)
                self.line_items[line_id] = edge_item

                # Check if compound is drawn already
                if edge[0] not in self.compounds.keys():
                    # Retrieve information of aggregate
                    aggregate, a_type = self.__get_aggregate_and_type_from_graph(edge[0])
                    a_position = positions[edge[0]]
                    self.__build_compound_item(a_position[0], a_position[1], aggregate, a_type)

            # # # Draw outgoing edges of rxn node
            for e_count, edge in enumerate(subgraph.out_edges(node)):
                # Draw edge from rhs of rxn to aggregate
                line_id = "_".join(list(edge)) + "_" + str(e_count)
                edge_item = self.__build_edge(rxn_item.outgoing(),
                                              QPoint(positions[edge[1]][0],
                                                     positions[edge[1]][1]),
                                              line_id)
                self.line_items[line_id] = edge_item
                # Check if compound is drawn already, else draw
                if edge[1] not in self.compounds.keys():
                    # Retrieve information of aggregate
                    aggregate, a_type = self.__get_aggregate_and_type_from_graph(edge[1])
                    a_position = positions[edge[1]]
                    self.__build_compound_item(a_position[0], a_position[1], aggregate, a_type)

    def __center_view(self):
        # self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        self.centerOn(QPoint(0, 0))

    def __bind_functions_to_object(self, object: Any, allow_focus: bool = False) -> None:
        object.bind_mouse_press_function(self.mouse_press_function)
        if allow_focus:
            object.bind_mouse_double_click_function(self.focus_function)
        object.setAcceptHoverEvents(True)
        object.bind_hover_enter_function(self.hover_enter_function)
        object.bind_hover_leave_function(self.hover_leave_function)
        object.bind_menu_function(self.menu_function)

    def __getitem__(self, i):
        # get information of database to make subscriptable
        return f"{i}"


class CRSettings(ReactionAndCompoundViewSettings):

    def __init__(self, parent: QWidget, network: CRNetwork) -> None:
        super().__init__(parent, VerticalLayout())
        self.network = network
        self.new_network = False
        self.button_query = TextPushButton("Query Database", self._query_database_function)
        self.button_update = TextPushButton("Update View", self._update_function, shortcut="F5")
        self.button_load = TextPushButton("Load Graph", self._load_graph_function, shortcut="Ctrl+L")
        self.button_undo = TextPushButton("Undo", self.network.undo_move, shortcut="Ctrl+Z")
        self.button_redo = TextPushButton("Redo", self.network.redo_move, shortcut="Ctrl+R")

        self.time_label = QLabel(self)
        self.time_label.resize(100, 20)
        self.time_label.setFixedHeight(20)
        self.time_label.setText("Only Show Modified Reactions Since")

        self.time_edit = QDateTimeEdit(QDate())
        self.time_edit.setDisplayFormat("HH:mm dd.MM.yyyy")

        self.current_id_label = QLabel(self)
        self.current_id_label.resize(100, 20)
        self.current_id_label.setFixedHeight(20)
        self.current_id_label.setText("Current Center Aggregate")

        self.current_id_text = QLineEdit(self)
        self.current_id_text.resize(100, 40)
        self.current_id_text.setText(str(self.network.current_centroid_id))

        self.save_to_svg_button = TextPushButton("Save SVG", self.network.save_svg, shortcut="Ctrl+S")
        self.button_traveling = TextPushButton("Start Path Analysis", self.__start_path_analysis_function)

        # Timer for reploting
        self.check_new_network_timer = QTimer(self)
        self.check_new_network_timer.setInterval(50)
        self.check_new_network_timer.timeout.connect(self.__plot_new_network)  # pylint: disable=no-member
        if not self.check_new_network_timer.isActive():
            self.check_new_network_timer.start()

        self.mol_widget.setMinimumWidth(200)
        self.mol_widget.setMaximumWidth(1000)
        self.mol_widget.setMinimumHeight(300)
        self.mol_widget.setMaximumWidth(1000)

        self.es_mep_widget.setMinimumHeight(300)
        self.es_mep_widget.setMinimumWidth(200)
        self.es_mep_widget.setMaximumWidth(1000)

        self._settings_visible = False

        # set layout
        self.p_layout.addWidget(self.button_query)
        self.p_layout.addWidget(self.button_load)
        self.p_layout.addWidget(self.button_update)
        self.p_layout.addLayout(HorizontalLayout([self.button_undo, self.button_redo]))
        self.p_layout.add_widgets([
            self.time_label,
            self.time_edit,
            self.current_id_label,
            self.current_id_text
        ])
        self.p_layout.addLayout(HorizontalLayout([self.save_to_svg_button, self.button_traveling]))
        self.p_layout.add_widgets([
            self.mol_widget,
            self.es_mep_widget
        ])
        self._set_up_advanced_settings_widgets(self.p_layout)

        self._scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.p_layout)
        self._scroll_area.setWidget(scroll_widget)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.vscrollbar = self._scroll_area.verticalScrollBar()
        self.vscrollbar.rangeChanged.connect(self.scroll)
        self.set_advanced_settings_visible()
        layout = QVBoxLayout()
        layout.addWidget(self._scroll_area)

        self.setLayout(layout)

        self.button_deactivate_all = QPushButton("Deactivate All Aggregates")
        self.p_layout.addWidget(self.button_deactivate_all)
        self.button_deactivate_all.clicked.connect(self.__deactivate_all_aggregates)  # pylint: disable=no-member
        self.button_deactivate_all.setToolTip("Deactivates the exploration of all aggregates.\n"
                                              "Note that a running KineticsGear may activate their exploration again.")

        self.button_activate_all_user = QPushButton("Activate All USER_OPTIMIZED")
        self.p_layout.addWidget(self.button_activate_all_user)
        self.button_activate_all_user.clicked.connect(self.__activate_all_user_optimized)  # pylint: disable=no-member
        self.button_activate_all_user.setToolTip("WARNING: Activates all aggregates for exploration for which the\n"
                                                 "first structures (centroid) is labeled as USER_OPTIMIZED and NOT\n"
                                                 "all structures that have a structure with the label USER_OPTIMIZED.")
        self.show()

    @Slot(int, int)
    def scroll(self, minimum, maximum):
        value = maximum if self._settings_visible else minimum
        self.vscrollbar.setValue(value)

        self.show()

    def set_advanced_settings_visible(self) -> None:
        self._settings_visible = self.advanced_settings_cbox.isChecked()
        if self._settings_visible:
            self.advanced_settings_widget.setVisible(True)
        else:
            self.advanced_settings_widget.setVisible(False)

    def _set_up_advanced_settings_widgets(self, layout):
        self.advanced_settings_cbox = QCheckBox("ADVANCED SETTINGS")
        self.advanced_settings_cbox.setChecked(self._settings_visible)
        self.advanced_settings_cbox.toggled.connect(  # pylint: disable=no-member
            self.set_advanced_settings_visible
        )

        self.advanced_settings_widget = AdvancedSettingsWidget(
            self.network,
            self.network.db_manager
        )
        layout.addWidget(self.advanced_settings_cbox)
        layout.addWidget(self.advanced_settings_widget)

    def __deactivate_all_aggregates(self):
        compounds = self.network.db_manager.get_collection('compounds')
        flasks = self.network.db_manager.get_collection('flasks')
        for compound in compounds.iterate_all_compounds():
            compound.link(compounds)
            compound.disable_exploration()
        for flask in flasks.iterate_all_flasks():
            flask.link(flasks)
            flask.disable_exploration()

    def __activate_all_user_optimized(self):
        compounds = self.network.db_manager.get_collection('compounds')
        structures = self.network.db_manager.get_collection('structures')
        flasks = self.network.db_manager.get_collection('flasks')
        for compound in compounds.iterate_all_compounds():
            compound.link(compounds)
            centroid_id = compound.get_centroid()
            centroid = db.Structure(centroid_id, structures)
            if centroid.get_label() == db.Label.USER_OPTIMIZED:
                compound.enable_exploration()
        for flask in flasks.iterate_all_flasks():
            flask.link(flasks)
            centroid_id = flask.get_centroid()
            centroid = db.Structure(centroid_id, structures)
            if centroid.get_label() == db.Label.USER_OPTIMIZED:
                flask.enable_exploration()

    def update_current_centroid_text(self, new_text: str) -> None:
        self.current_id_text.setText(new_text)

    def _query_database_function(self) -> None:
        self.network.remove_all_items()
        self.network.reset_graph()
        self.network.reset_subgraph_cache()
        self._update_function()

    def _update_function(self) -> None:
        self.advanced_settings_widget.update_settings()
        requested_string: Union[None, str] = self.current_id_text.text()
        requested_string = requested_string if requested_string else None
        self.network.trigger_thread_function(
            self.network.update_network,
            self.network._print_progress,
            self.advanced_settings_widget.get_model(),
            self.advanced_settings_widget.enforce_structure_model(),
            trigger_plot=True,
            requested_centroid=requested_string,
        )

    def __start_path_analysis_function(self) -> None:
        from scine_heron.database.graph_traversal import GraphTravelWidget
        GraphTravelWidget(self.parent(), self.network.db_manager, self.network._graph_model)

    def _load_graph_function(self) -> None:
        self.network.remove_all_items()
        self.network.reset_graph()
        self.network.reset_subgraph_cache()
        self.network.load_graph()

    def __plot_new_network(self):
        if self.network.new_network:
            self.network.plot_network()
        self.network.new_network = False


class CustomQScrollArea(QScrollArea):
    def wheelEvent(self, event):
        modifiers = QGuiApplication.keyboardModifiers()
        if self.widget().mol_widget.underMouse() and modifiers == Qt.ControlModifier:
            self.widget().mol_widget.wheelEvent(event)
        elif self.widget().mol_widget.underMouse():
            super(CustomQScrollArea, self).wheelEvent(event)
        else:
            super(CustomQScrollArea, self).wheelEvent(event)


class CompoundReactionWidget(QWidget):
    def __init__(self, parent: QWidget, db_manager: db.Manager) -> None:
        super(CompoundReactionWidget, self).__init__(parent=parent)
        self.db_manager = db_manager

        # Create layout and add widgets
        layout = QHBoxLayout()
        self.network = CRNetwork(self, self.db_manager)
        self.settings = CRSettings(self, self.network)
        self.network.set_settings_widget(self.settings)
        self.splitter = QSplitter(self)
        self.splitter.addWidget(self.network)
        self.splitter.addWidget(self.settings)
        self.splitter.setSizes([320, 150])
        layout.addWidget(self.splitter)

        # Set dialog layout
        self.setLayout(layout)

    def center_on_aggregate(self, aggregate_id: str):
        self.settings.update_current_centroid_text(aggregate_id)
        self.settings._update_function()
