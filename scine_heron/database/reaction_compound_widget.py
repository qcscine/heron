#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from typing import Dict, Optional, Any, List, Union, Tuple
from json import dumps
import json

import numpy as np

import scine_database as db
import scine_utilities as utils

from scine_heron.utilities import datetime_to_query
from scine_heron.database.graphics_items import Compound, Reaction
from scine_heron.database.energy_query_functions import check_barrier_height, get_energy_change
from scine_heron.database.concentration_query_functions import query_concentration, query_reaction_flux
from scine_heron.database.reaction_compound_view import ReactionAndCompoundView, ReactionAndCompoundViewSettings
from scine_heron.database.compound_and_flasks_helper import get_compound_or_flask
from scine_heron import find_main_window
from datetime import datetime

from PySide2.QtWidgets import (
    QWidget,
    QPushButton,
    QLabel,
    QDateTimeEdit,
    QLineEdit,
    QGraphicsItemAnimation,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QGraphicsItem,
    QCheckBox,
    QScrollArea
)
from PySide2.QtGui import QPainterPath, QGuiApplication
from PySide2.QtCore import Qt, QTimer, QPoint, QTimeLine, QDate


def reaction_is_parallel(reaction: db.Reaction, step: db.ElementaryStep, structures: db.Collection):
    reaction_lhs = reaction.get_reactants(db.Side.LHS)[0]
    step_lhs = step.get_reactants(db.Side.LHS)[0]
    step_lhs_aggregate_ids = [db.Structure(s_id, structures).get_aggregate() for s_id in step_lhs]
    if len(step_lhs_aggregate_ids) == len(reaction_lhs):
        for a_id in step_lhs_aggregate_ids:
            if a_id not in reaction_lhs:
                return False
        return True
    return False


def reaction_is_outgoing(reaction: db.Reaction, centroid_id: db.ID):
    return centroid_id in reaction.get_reactants(db.Side.LHS)[0]


class AdvancedSettingsWidget(QWidget):
    def __init__(self, network, db_manager, parent=None):
        super(AdvancedSettingsWidget, self).__init__(parent)
        self._max_barrier = 265.5
        self._min_barrier = - 100.0
        self._always_show_barrierless = True
        self._model = db.Model("DFT", "", "")
        self._scale_with_concentrations = False
        self._min_flux = 1e-5
        self._network = network
        self._db_manager = db_manager

        self.__layout = QVBoxLayout()

        self._set_up_barrier_widgets(self.__layout)
        self.current_method_family_text, self.current_method_text, self.current_basis_set_text,\
            self.current_solvation_text, self.current_solvent_text = self._set_up_electronic_structure_model_widgets(
                self.__layout)
        self._set_up_concentration_widgets(self.__layout)
        self.setLayout(self.__layout)

    def reset_compounds(self):
        if self._network:
            self._network.reset_compounds = True

    def get_max_barrier(self) -> float:
        return float(self.current_max_barrier_text.text())

    def get_min_barrier(self) -> float:
        return float(self.current_min_barrier_text.text())

    def always_show_barrierless(self) -> bool:
        return self.always_show_barrierless_reactions_cbox.isChecked()

    def get_min_flux(self) -> float:
        return float(self.current_min_flux_text.text())

    def get_model(self) -> db.Model:
        return self._model

    def scale_with_concentrations(self):
        return self.concentration_scaling_cbox.isChecked()

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
        self.concentration_scaling_cbox.toggled.connect(self.reset_compounds)  # pylint: disable=no-member
        layout.addWidget(self.concentration_scaling_cbox)

        self.current_min_flux_label = QLabel(self)
        self.current_min_flux_label.resize(280, 40)
        self.current_min_flux_label.setText("Min. Concentration Flux")
        layout.addWidget(self.current_min_flux_label)
        self.current_min_flux_text = QLineEdit(self)
        self.current_min_flux_text.resize(280, 40)
        self.current_min_flux_text.setText(str(self._min_flux))
        layout.addWidget(self.current_min_flux_text)

    def _set_up_electronic_structure_model_widgets(self, layout) -> Tuple[QWidget, QWidget, QWidget, QWidget, QWidget]:
        """
        Add the widgets for the electronic structure definition to the layout.
        """
        # Header
        current_model_label = QLabel(self)
        current_model_label.resize(280, 40)
        current_model_label.setText("Electronic Structure Model")
        # First line of boxes: Method family, method, and basis set
        layout.addWidget(current_model_label)
        current_method_family_label = QLabel(self)
        current_method_family_label.resize(70, 40)
        current_method_family_label.setText("Family")
        current_method_label = QLabel(self)
        current_method_label.resize(70, 40)
        current_method_label.setText("Method")
        current_basis_set_label = QLabel(self)
        current_basis_set_label.resize(70, 40)
        current_basis_set_label.setText("Basis Set")
        hbox1Layout = QHBoxLayout()
        hbox1Layout.addWidget(current_method_family_label)
        hbox1Layout.addWidget(current_method_label)
        hbox1Layout.addWidget(current_basis_set_label)
        layout.addLayout(hbox1Layout)

        current_method_family_text = QLineEdit(self)
        current_method_family_text.resize(70, 40)
        current_method_family_text.setText("None")
        current_method_text = QLineEdit(self)
        current_method_text.resize(70, 40)
        current_method_text.setText("")
        current_basis_set_text = QLineEdit(self)
        current_basis_set_text.resize(70, 40)
        current_basis_set_text.setText("")
        hbox2Layout = QHBoxLayout()
        hbox2Layout.addWidget(current_method_family_text)
        hbox2Layout.addWidget(current_method_text)
        hbox2Layout.addWidget(current_basis_set_text)
        layout.addLayout(hbox2Layout)

        # Second line of boxes: Solvation and solvent
        current_solvation_label = QLabel(self)
        current_solvation_label.resize(70, 40)
        current_solvation_label.setText("Solvation")
        current_solvent_label = QLabel(self)
        current_solvent_label.resize(70, 40)
        current_solvent_label.setText("Solvent")
        hbox3Layout = QHBoxLayout()
        hbox3Layout.addWidget(current_solvation_label)
        hbox3Layout.addWidget(current_solvent_label)
        layout.addLayout(hbox3Layout)

        current_solvation_text = QLineEdit(self)
        current_solvation_text.resize(70, 40)
        current_solvation_text.setText("")
        current_solvent_text = QLineEdit(self)
        current_solvent_text.resize(70, 40)
        current_solvent_text.setText("")
        hbox4Layout = QHBoxLayout()
        hbox4Layout.addWidget(current_solvation_text)
        hbox4Layout.addWidget(current_solvent_text)
        layout.addLayout(hbox4Layout)
        return current_method_family_text, current_method_text, current_basis_set_text, current_solvation_text,\
            current_solvent_text

    def update_settings(self):
        """
        Read the model definition and maximum barrier from the input boxes. If "None" is given in the method family
        input box. Get some model from the database.
        """
        requested_method_family = self.current_method_family_text.text()
        if "None" in requested_method_family:
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
                selection = {"label": "user_optimized"}
                structure = self._db_manager.get_collection("structures").get_one_structure(dumps(selection))
                if structure is None:
                    return
                model = structure.model
            else:
                model = calculation.model
            self._model = model
            self.update_electronic_structure_model_text(model)
        else:
            requested_method = self.current_method_text.text()
            requested_basis_set = self.current_basis_set_text.text()
            self._model = db.Model(
                requested_method_family, requested_method, requested_basis_set
            )
            self._model.solvent = self.current_solvent_text.text()
            self._model.solvation = self.current_solvation_text.text()
        # Maximum/Minimum barrier and flux.
        self._max_barrier = self.get_max_barrier()
        self._min_barrier = self.get_min_barrier()
        self._always_show_barrierless = self.always_show_barrierless()
        self._min_flux = self.get_min_flux()
        self._scale_with_concentrations = self.scale_with_concentrations()

    def update_electronic_structure_model_text(self, model: db.Model) -> None:
        """
        Update the text boxes for the electronic structure model with the settings given in the model.
        """
        self.current_method_family_text.setText(model.method_family)
        self.current_method_text.setText(model.method)
        self.current_basis_set_text.setText(model.basis_set)
        self.current_solvation_text.setText(model.solvation)
        self.current_solvent_text.setText(model.solvent)


class CRNetwork(ReactionAndCompoundView):
    def __init__(self, parent: QWidget, db_manager: db.Manager) -> None:
        import math
        super().__init__(parent=parent)
        self.setMouseTracking(True)
        self.setInteractive(True)
        self.setMinimumWidth(100)
        self.setMinimumHeight(100)

        self.structure_of_compound = None

        # Expand reactions in pop-up window
        self.total_number_elementary_steps = None
        self.total_number_compound_rhs: Optional[List[dict]] = None
        self.total_number_compound_lhs: Optional[List[dict]] = None
        self.select_item: dict = {}

        # Add all data
        self.db_manager: db.Manager = db_manager
        self.old_compounds: Dict[str, Compound] = {}
        self.old_reactions: Dict[str, Reaction] = {}
        self.centroid_item: Optional[Compound] = None
        self.current_centroid_id: str = ""
        self.animations: List[QGraphicsItemAnimation] = []
        self.reaction_query: Dict[Any, Any] = {}
        self.earliest_compound_creation: Optional[datetime] = None
        self.__currently_updating: bool = False
        self.__history: List[str] = []
        self.__current_history_position: int = -1
        self.__last_max_barrier: float = -math.inf
        self.__last_min_barrier: float = -math.inf
        self.__last_model: db.Model = db.Model('any', 'any', 'any')
        self.reset_compounds: bool = False

        self.__last_min_flux: Union[float, None] = None
        self.__last_scale_with_concentrations: Union[bool, None] = None
        self.__last_always_show_barrierless: Union[bool, None] = None

    def focus_function(self, _, item: Union[Compound, Reaction]) -> None:
        self.centroid_item = item
        string = self.centroid_item.db_representation.id().string()
        assert self.settings
        cr_settings = self.settings
        cr_settings.update_current_centroid_text(string)
        cr_settings.advanced_settings_widget.update_settings()
        self.update_network(cr_settings.advanced_settings_widget.get_max_barrier(),
                            cr_settings.advanced_settings_widget.get_min_barrier(),
                            cr_settings.advanced_settings_widget.always_show_barrierless(),
                            cr_settings.advanced_settings_widget.get_model(),
                            cr_settings.advanced_settings_widget.scale_with_concentrations(),
                            cr_settings.advanced_settings_widget.get_min_flux())

    def __animate_move(self, item: QGraphicsItem, x: float, y: float) -> None:
        move = QGraphicsItemAnimation(self)
        move.setItem(item)
        move.setTimeLine(self.timer)
        current_center = item.boundingRect().center().toPoint()
        new_center = QPoint(int(x), int(y))
        movement_dynamic = new_center - current_center
        for i in range(self.frames):
            move.setScaleAt(i / self.frames, 1, 1)
            move.setPosAt(i / self.frames, movement_dynamic)
            # TODO This make the points jump at the end of the fade in, but it should be smooth
            #  This should could be debugged, the line above make the jump happen at the start
            # move.setPosAt(i / self.frames, ((i+1) / self.frames) * movement_dynamic)
        self.animations.append(move)

    def __animate_fade_out(self, item: QGraphicsItem) -> None:
        fade_out = QGraphicsItemAnimation(self)
        fade_out.setItem(item)
        fade_out.setTimeLine(self.timer)
        current_pos = item.pos().toPoint()
        current_center = item.boundingRect().center().toPoint()
        movement_dynamic = current_center - current_pos
        for i in range(self.frames):
            fade_out.setScaleAt(
                i / self.frames, 1 - (i + 1) / self.frames, 1 - (i + 1) / self.frames
            )
            fade_out.setPosAt(
                i / self.frames,
                (current_pos + movement_dynamic) * ((i + 1) / self.frames),
            )
        self.animations.append(fade_out)

    def __animate_fade_in(self, item: QGraphicsItem) -> None:
        fade_in = QGraphicsItemAnimation(self)
        fade_in.setItem(item)
        fade_in.setTimeLine(self.timer)
        current_pos = item.pos().toPoint()
        current_center = item.boundingRect().center().toPoint()
        movement_dynamic = current_center - current_pos
        for i in range(self.frames):
            fade_in.setScaleAt(
                i / self.frames, (i + 1) / self.frames, (i + 1) / self.frames
            )
            fade_in.setPosAt(
                i / self.frames,
                (current_pos + movement_dynamic) * (1 - (i + 1) / self.frames),
            )
        fade_in.setStep(0.0)
        self.animations.append(fade_in)

    def redo_move(self):
        if (self.__current_history_position + 2) > len(self.__history) or self.__current_history_position < 0:
            return
        self.__current_history_position += 1
        centroid_id = self.__history[self.__current_history_position]
        self.update_network(self.__last_max_barrier, self.__last_min_barrier,
                            self.__last_always_show_barrierless, self.__last_model,
                            self.__last_scale_with_concentrations, self.__last_min_flux, centroid_id, False)

    def undo_move(self):
        if self.__current_history_position > len(self.__history) or self.__current_history_position < 1:
            return
        self.__current_history_position -= 1
        centroid_id = self.__history[self.__current_history_position]
        self.update_network(self.__last_max_barrier, self.__last_min_barrier,
                            self.__last_always_show_barrierless, self.__last_model,
                            self.__last_scale_with_concentrations, self.__last_min_flux, centroid_id, False)

    def update_network(
        self,
        max_barrier: float,
        min_barrier: float,
        always_show_barrierless: bool,
        model: db.Model,
        scale_with_concentrations,
        min_flux: float,
        requested_centroid: Optional[str] = None,
        track_update: bool = True,
    ) -> None:

        if self.__currently_updating:
            return
        self.__currently_updating = True
        # Create singular timer for all added animated items
        #  Segfaults if done in the __init__ function
        self.timer = QTimeLine(1000)  # pylint: disable=attribute-defined-outside-init
        self.frames = 40  # pylint: disable=attribute-defined-outside-init
        self.timer.setFrameRange(0, self.frames)

        # Better network view
        reaction_multiple_compounds_index: List[Any] = []
        list_of_reactions: List[Any] = []
        list_of_angles: List[Any] = []
        reaction_cache_sorted: List[Any] = []
        compound_pairs_in_reaction: List[Any] = []

        if self.__last_model and self.__last_min_flux and self.__last_scale_with_concentrations\
                and self.__last_always_show_barrierless:
            if model != self.__last_model or abs(self.__last_max_barrier - max_barrier) > 1e-9 \
                    or abs(self.__last_min_barrier - min_barrier) > 1e-9\
                    or self.__last_scale_with_concentrations != scale_with_concentrations \
                    or self.__last_always_show_barrierless != always_show_barrierless \
                    or abs(self.__last_min_flux - min_flux) > 1e-9:
                # delete stuff
                for c_str_id in self.compounds:
                    self.__animate_fade_out(self.compounds[c_str_id][0])
                for r_str_id in self.reactions:
                    self.__animate_fade_out(self.reactions[r_str_id][0])
                self.compounds = dict()
                self.reactions = dict()

        self.__last_max_barrier = max_barrier
        self.__last_min_barrier = min_barrier
        self.__last_always_show_barrierless = always_show_barrierless
        self.__last_model = model
        self.__last_min_flux = min_flux
        self.__last_scale_with_concentrations = scale_with_concentrations

        for k in self.compounds:
            self.old_compounds[k] = self.compounds[k][0]
        for k in self.reactions:
            self.old_reactions[k] = self.reactions[k][0]
        # Instantly remove all lines
        for k in self.line_items:
            self.scene_object.removeItem(self.line_items[k])

        structure_collection = self.db_manager.get_collection("structures")
        reaction_collection = self.db_manager.get_collection("reactions")
        compound_collection = self.db_manager.get_collection("compounds")
        flask_collection = self.db_manager.get_collection("flasks")
        property_collection = self.db_manager.get_collection("properties")

        # Reset storage
        self.compounds = {}
        self.reactions = {}
        self.animations = []
        if self.centroid_item is None or requested_centroid is not None:
            if requested_centroid is None:
                tmp_compound = compound_collection.get_one_compound(dumps({}))
                if tmp_compound:
                    a_id = tmp_compound.id()
                else:
                    print("No compounds available!")
                    return
            else:
                a_id = db.ID(requested_centroid)

            centroid: Union[db.Compound, db.Flask] = db.Compound(a_id, compound_collection)
            if not centroid.exists():
                centroid = db.Flask(a_id, flask_collection)
            if not centroid.exists():
                centroid = self.centroid_item  # type: ignore
            if not centroid.exists():
                tmp_compound = compound_collection.get_one_compound(dumps({}))
                if tmp_compound:
                    a_id = tmp_compound.id()
                    centroid = db.Compound(a_id, compound_collection)
                else:
                    print("No compounds available!")
                    return

            concentration = None
            s = db.Structure(centroid.get_centroid(), structure_collection)
            if scale_with_concentrations:
                concentration = query_concentration("max_concentration", s, property_collection)
            self.centroid_item = Compound(
                0, 0, concentration=concentration
            )
            self.centroid_item.db_representation = centroid
            self.centroid_item.structure = s.get_atoms()
            if isinstance(centroid, db.Compound):
                self.centroid_item.set_brush(self.compound_brush)
                self.centroid_item.setPen(self.compound_pen)
            else:
                self.centroid_item.set_brush(self.flask_brush)
                self.centroid_item.setPen(self.compound_pen)
            self.__bind_functions_to_object(self.centroid_item, True)
            cid_string = centroid.id().string()
            self.add_to_compound_list(self.centroid_item)
            self.scene_object.addItem(self.centroid_item)
        else:
            centroid = self.centroid_item.db_representation

            if centroid.id().string() in self.old_compounds:
                del self.old_compounds[centroid.id().string()]
            # Reset color to be sure
            self.reset_item_colors()
            self.focused_item_db_id = None
            self.focused_item = None
            self.centroid_item.x_coord = 0
            self.centroid_item.y_coord = 0
            self.__animate_move(self.centroid_item, 0, 0)
            cid_string = centroid.id().string()
            self.add_to_compound_list(self.centroid_item)
        self.current_centroid_id = cid_string

        if track_update:
            self.__last_max_barrier = max_barrier
            self.__last_min_barrier = min_barrier
            self.__last_always_show_barrierless = always_show_barrierless
            self.__last_model = model
            if len(self.__history) == 0:
                self.__current_history_position += 1
                self.__history = self.__history[0:(self.__current_history_position)]
                self.__history.append(self.current_centroid_id)
            elif self.__history[-1] != self.current_centroid_id:
                self.__current_history_position += 1
                self.__history = self.__history[0:self.__current_history_position]
                self.__history.append(self.current_centroid_id)

        centroid_id_string = self.centroid_item.db_representation.id().string()
        selection = {
            "$and": [{
                "$or": [
                    {"lhs.id": {"$oid": centroid_id_string}},
                    {"rhs.id": {"$oid": centroid_id_string}},
                ]},
                self.reaction_query
            ]
        }

        reaction_cache = []
        elementary_step_cache = []
        reaction_flux = []
        for r in reaction_collection.iterate_reactions(dumps(selection)):
            r.link(reaction_collection)

            if scale_with_concentrations:
                flux = query_reaction_flux("_reaction_edge_flux", r, compound_collection, flask_collection,
                                           structure_collection, property_collection)
                if flux < min_flux:
                    continue
                reaction_flux.append(flux)
            else:
                reaction_flux.append(None)

            elementary_step = check_barrier_height(
                r,
                self.db_manager,
                model,
                structure_collection,
                property_collection,
                max_barrier,
                min_barrier,
                always_show_barrierless
            )
            if elementary_step is not None:
                reaction_cache.append(r)
                elementary_step_cache.append(elementary_step)

        # Part I - Clustering of the Reactions
        # fill new list by reaction items
        reaction_cache_items: List[Any] = []
        for reaction in reaction_cache:
            reaction_id = reaction.id().string()
            selected_reaction = {'_id': {'$oid': reaction_id}}
            reaction_info = json.loads(self.__getitem__(reaction_collection.find(dumps(selected_reaction))))
            reaction_cache_items.append(reaction_info)

        centroid_id = {'id': {'$oid': centroid_id_string}, 'type': 'compound'}

        # cluster reactions with multiple compounds
        for i in range(len(reaction_cache_items)):
            for j in range(i + 1, len(reaction_cache_items)):
                for k in reaction_cache_items[i]["rhs"]:
                    for m in reaction_cache_items[j]["rhs"]:
                        if k != centroid_id and k == m:
                            self.__reformat_reaction(compound_pairs_in_reaction, i, j)

                    for m in reaction_cache_items[j]["lhs"]:
                        if k != centroid_id and k == m:
                            self.__reformat_reaction(compound_pairs_in_reaction, i, j)

                for k in reaction_cache_items[i]["lhs"]:
                    for m in reaction_cache_items[j]["lhs"]:
                        if k != centroid_id and k == m:
                            self.__reformat_reaction(compound_pairs_in_reaction, i, j)

                    for m in reaction_cache_items[j]["rhs"]:
                        if k != centroid_id and k == m:
                            self.__reformat_reaction(compound_pairs_in_reaction, i, j)

        # resolve sublist in list
        reaction_multiple_compounds_index = [item for sublist in compound_pairs_in_reaction for item in sublist]

        # remove dublicates elements
        reaction_multiple_compounds_index = list(dict.fromkeys(reaction_multiple_compounds_index))

        elementary_step_cache_sorted = []
        reaction_flux_sorted = []

        # add clustered reactions in the new list
        for index in reaction_multiple_compounds_index:
            reaction_cache_sorted.append(reaction_cache[index])
            elementary_step_cache_sorted.append(elementary_step_cache[index])
            reaction_flux_sorted.append(reaction_flux[index])

        reaction_multiple_compounds_index.sort(reverse=True)
        for index in reaction_multiple_compounds_index:
            reaction_cache.pop(index)
            elementary_step_cache.pop(index)
            reaction_flux.pop(index)

        # add missing reactions in the new sorted list
        reaction_cache_sorted += reaction_cache
        elementary_step_cache_sorted += elementary_step_cache
        reaction_flux_sorted += reaction_flux
        reaction_cache = []
        elementary_step_cache = []
        reaction_flux = []

        # Part II - Rotation and Formation of Reactions
        # presentation of reactions
        total_number_of_reactions = len(reaction_cache_sorted)
        for counter, r in enumerate(reaction_cache_sorted):
            rid_string = r.id().string()
            selected_rid = {'_id': {'$oid': rid_string}}
            current_reaction = json.loads(self.__getitem__(reaction_collection.find(dumps(selected_rid))))
            flux = reaction_flux_sorted[counter]

            # new radius for reactions and flasks
            radius = 220
            if total_number_of_reactions <= 40:
                # circle for number of reaction < 41, each 9° one reaction
                major_axis = 1
                minor_axis = 1
            else:
                # ellips for number of reaction > 40
                major_axis = 1.27   # type: ignore
                minor_axis = 0.78   # type: ignore

            angle_reaction = ((counter / total_number_of_reactions) * 360.0) * (np.pi / 180)
            list_of_angles.append(angle_reaction)
            x = radius * major_axis * np.cos(angle_reaction)
            y = radius * minor_axis * np.sin(angle_reaction)

            if rid_string in self.old_reactions:
                self.reactions[rid_string] = [self.old_reactions[rid_string]]
                del self.old_reactions[rid_string]
                self.reactions[rid_string][0].flux = flux
                self.reactions[rid_string][0].reset_brush()
                self.reactions[rid_string][0].setPen(self.reaction_pen)

                # correct rotation of reactions
                if self.reactions[rid_string][0].rot == 0:
                    for key in range(len(current_reaction['lhs'])):
                        if centroid_id["id"] == current_reaction['lhs'][key]["id"]:
                            self.reactions[rid_string][0].x_coord = x
                            self.reactions[rid_string][0].y_coord = y

                    for key in range(len(current_reaction['rhs'])):
                        if centroid_id["id"] == current_reaction['rhs'][key]["id"]:
                            self.reactions[rid_string][0].x_coord = x
                            self.reactions[rid_string][0].y_coord = y
                            self.reactions[rid_string][0].rot = 1

                elif self.reactions[rid_string][0].rot == 1:
                    for key in range(len(current_reaction['rhs'])):
                        if centroid_id["id"] == current_reaction['rhs'][key]["id"]:
                            self.reactions[rid_string][0].x_coord = x
                            self.reactions[rid_string][0].y_coord = y

                    for key in range(len(current_reaction['lhs'])):
                        if centroid_id["id"] == current_reaction['lhs'][key]["id"]:
                            self.reactions[rid_string][0].x_coord = x
                            self.reactions[rid_string][0].y_coord = y
                            self.reactions[rid_string][0].rot = 0

                self.reactions[rid_string][0].update_angle(angle_reaction)
                # Check again on which side the centroid is relative to the direction of the elementary step and the
                # reaction itself.
                es = elementary_step_cache_sorted[counter]
                step_parallel_to_reaction = reaction_is_parallel(r, es, structure_collection)
                outgoing_reaction = reaction_is_outgoing(r, centroid.id())
                keep_sign = (outgoing_reaction and step_parallel_to_reaction) or (not outgoing_reaction
                                                                                  and not step_parallel_to_reaction)
                self.reactions[rid_string][0].invert_sign_of_difference = not keep_sign
                self.__animate_move(self.reactions[rid_string][0], x, y)
            else:
                # check, is centroid connected to lhs or rhs
                for key in range(len(current_reaction['lhs'])):
                    if centroid_id["id"] == current_reaction['lhs'][key]["id"]:
                        self.reactions[rid_string] = [Reaction(
                            x, y, flux=flux, ang=angle_reaction, pen=self.reaction_pen,
                            brush=self.reaction_brush
                        )]
                for key in range(len(current_reaction['rhs'])):
                    if centroid_id["id"] == current_reaction['rhs'][key]["id"]:
                        self.reactions[rid_string] = [Reaction(
                            x, y, flux=flux, ang=angle_reaction, rot=1, pen=self.reaction_pen,
                            brush=self.reaction_brush
                        )]
                self.reactions[rid_string][0].db_representation = r
                reagents = r.get_reactants(db.Side.BOTH)
                reagents_types = r.get_reactant_types(db.Side.BOTH)
                self.reactions[rid_string][0].lhs_ids = [c.string() for c in reagents[0]]
                self.reactions[rid_string][0].rhs_ids = [c.string() for c in reagents[1]]
                self.reactions[rid_string][0].lhs_types = reagents_types[0]
                self.reactions[rid_string][0].rhs_types = reagents_types[1]
                es = elementary_step_cache_sorted[counter]
                step_parallel_to_reaction = reaction_is_parallel(r, es, structure_collection)
                outgoing_reaction = reaction_is_outgoing(r, centroid.id())
                keep_sign = (outgoing_reaction and step_parallel_to_reaction) or (not outgoing_reaction
                                                                                  and not step_parallel_to_reaction)
                self.reactions[rid_string][0].energy_difference = get_energy_change(
                    es, "electronic_energy", model, structure_collection, property_collection)
                self.reactions[rid_string][0].invert_sign_of_difference = not keep_sign
                if es.get_type() != db.ElementaryStepType.BARRIERLESS:
                    ts = db.Structure(es.get_transition_state())
                    ts.link(structure_collection)
                    self.reactions[rid_string][0].structure = ts.get_atoms()
                else:
                    self.reactions[rid_string][0].structure = utils.AtomCollection()
                    self.reactions[rid_string][0].set_brush(self.association_brush)

                if es.has_spline():
                    self.reactions[rid_string][0].spline = es.get_spline()
                self.__bind_functions_to_object(self.reactions[rid_string][0], False)
                self.scene_object.addItem(self.reactions[rid_string][0])
                self.__animate_fade_in(self.reactions[rid_string][0])

        # Part III - Swapping and Formation of the Compounds
        # list existing reaction with element as dict
        # switch position of compounds if there is a relation between two
        for i in range(len(list(self.reactions.keys()))):
            select_R = list(self.reactions.keys())[i]
            axt = json.loads(self.__getitem__(reaction_collection.find(dumps({'_id': {'$oid': select_R}}))))
            list_of_reactions.append(axt)

        for entry in range(len(self.reactions.values())):
            z = 1
            if entry == len(self.reactions.values()) - 1:
                z = 0

            # check each compound in rhs
            for compound in list(self.reactions.values())[entry][0].rhs_ids:
                if compound == centroid_id_string:
                    continue

                # take index of the current compound
                index_compound = list(self.reactions.values())[entry][0].rhs_ids.index(compound)

                # check, if compound is already existing in next reaction. For the case "yes", then swap index of rhs
                if compound in list(self.reactions.values())[entry + z][0].rhs_ids:
                    index_compound_rhs = list(self.reactions.values())[entry + z][0].rhs_ids.index(compound)
                    if len(list(self.reactions.values())[entry + z][0].rhs_ids) > 1:
                        if index_compound_rhs == 1:
                            a = list(self.reactions.values())[entry + z][0].rhs_ids[1]
                            b = list(self.reactions.values())[entry + z][0].rhs_ids[0]
                            a, b = b, a

                    if len(list(self.reactions.values())[entry][0].rhs_ids) > 1:
                        if index_compound == 0:
                            a = list(self.reactions.values())[entry][0].rhs_ids[1]
                            b = list(self.reactions.values())[entry][0].rhs_ids[0]
                            a, b = b, a

                # check, if compound is already existing in next reaction. For the case "yes", then swap index of lhs
                if compound in list(self.reactions.values())[entry + z][0].lhs_ids:
                    index_compound_lhs = list(self.reactions.values())[entry + z][0].lhs_ids.index(compound)
                    if len(list(self.reactions.values())[entry + z][0].lhs_ids) > 1:
                        if index_compound_lhs == 1:
                            a = list(self.reactions.values())[entry + z][0].lhs_ids[1]
                            b = list(self.reactions.values())[entry + z][0].lhs_ids[0]
                            a, b = b, a

                    if len(list(self.reactions.values())[entry][0].rhs_ids) > 1:
                        if index_compound == 0:
                            a = list(self.reactions.values())[entry][0].rhs_ids[1]
                            b = list(self.reactions.values())[entry][0].rhs_ids[0]
                            a, b = b, a

            # check each compound in lhs
            for compound in list(self.reactions.values())[entry][0].lhs_ids:
                if compound == centroid_id_string:
                    continue

                # take index of the current compound
                index_compound = list(self.reactions.values())[entry][0].lhs_ids.index(compound)

                # check, if compound is already existing in next reaction. For the case "yes", then swap index of rhs
                if compound in list(self.reactions.values())[entry + z][0].rhs_ids:
                    index_compound_rhs = list(self.reactions.values())[entry + z][0].rhs_ids.index(compound)
                    if len(list(self.reactions.values())[entry + z][0].rhs_ids) > 1:
                        if index_compound_rhs == 1:
                            a = list(self.reactions.values())[entry + z][0].rhs_ids[1]
                            b = list(self.reactions.values())[entry + z][0].rhs_ids[0]
                            a, b = b, a

                    if len(list(self.reactions.values())[entry][0].lhs_ids) > 1:
                        if index_compound == 0:
                            a = list(self.reactions.values())[entry][0].lhs_ids[1]
                            b = list(self.reactions.values())[entry][0].lhs_ids[0]
                            a, b = b, a

                # check, if compound is already existing in next reaction. For the case "yes", then swap index of lhs
                if compound in list(self.reactions.values())[entry + z][0].lhs_ids:
                    index_compound_lhs = list(self.reactions.values())[entry + z][0].lhs_ids.index(compound)
                    if len(list(self.reactions.values())[entry + z][0].lhs_ids) > 1:
                        if index_compound_lhs == 1:
                            a = list(self.reactions.values())[entry + z][0].lhs_ids[1]
                            b = list(self.reactions.values())[entry + z][0].lhs_ids[0]
                            a, b = b, a

                    if len(list(self.reactions.values())[entry][0].lhs_ids) > 1:
                        if index_compound == 0:
                            a = list(self.reactions.values())[entry][0].lhs_ids[1]
                            b = list(self.reactions.values())[entry][0].lhs_ids[0]
                            a, b = b, a

        # Formation of compounds
        for count, r_list in enumerate(self.reactions.values()):
            r = r_list[0]
            deviation_change = False

            for cid_string, ctype in zip(r.lhs_ids + r.rhs_ids, r.lhs_types + r.rhs_types):
                if cid_string in self.compounds:
                    continue
                c = get_compound_or_flask(db.ID(cid_string), ctype, compound_collection, flask_collection)

                # is compound on side of centroid --> inside
                inside = False
                if centroid_id_string in r.lhs_ids and cid_string in r.lhs_ids:
                    inside = True
                if centroid_id_string in r.rhs_ids and cid_string in r.rhs_ids:
                    inside = True

                # check, if the frequency of compound in one or more reactions
                compounds_in_lhs = []
                compounds_in_rhs = []

                # generate dictionary of 2 elements of c
                id_c = json.loads(self.__getitem__(c))['_id']
                objecttype_c = json.loads(self.__getitem__(c))['_objecttype']
                check_c = {'id': id_c, 'type': objecttype_c}

                # check the frequency of same compound_rhs in reactions
                for reaction in range(len(list_of_reactions)):
                    if check_c in list_of_reactions[reaction]['rhs']:
                        compounds_in_rhs.append(reaction)

                # check the frequency of same compound_lhs in reactions
                for reaction in range(len(list_of_reactions)):
                    if check_c in list_of_reactions[reaction]['lhs']:
                        compounds_in_lhs.append(reaction)

                len_rhs = len(compounds_in_rhs)
                len_lhs = len(compounds_in_lhs)
                # formation of the compound depending on inside/outside
                if inside:
                    # radius compound inside - depending on number of reactions
                    if (len_lhs == 1) ^ (len_rhs == 1):
                        # if compound consist to one reaction
                        radius = 120
                        # angle of compound depending on angle_reaction plus deviation of 0.07
                        deviation = 0.07
                        angle_compound = list_of_angles[count] + deviation

                    elif (len_lhs == 1 and len_rhs == 1):
                        # if compound consists to two reactions:
                        if total_number_of_reactions <= 40:
                            # radius = 280
                            radius = 160
                        else:
                            # radius = 280
                            radius = 160

                        angle_compound_lhs, angle_compound_rhs = 0, 0
                        for i in range(len_lhs):
                            angle_compound_lhs += list_of_angles[compounds_in_lhs[i]]
                        for i in range(len_rhs):
                            angle_compound_rhs += list_of_angles[compounds_in_rhs[i]]

                        # in the middle of the angle of i reactions
                        if (len_rhs > 1 and len_lhs == 0) or (len_lhs > 1 and len_rhs == 0):
                            angle_compound = max(angle_compound_rhs, angle_compound_lhs) / (len_lhs + len_rhs)
                        else:
                            angle_compound = (angle_compound_rhs + angle_compound_lhs) / (len_lhs + len_rhs)

                        if total_number_of_reactions > 40:
                            angle_compound = angle_compound + 0.02

                    if len_lhs > 1 or len_rhs > 1:
                        # if compound consists to multiple reactions:
                        if total_number_of_reactions <= 40:
                            # radius = 280
                            radius = 160
                        else:
                            # radius = 280
                            radius = 160

                        angle_compound_lhs, angle_compound_rhs = 0, 0
                        for i in range(len_lhs):
                            angle_compound_lhs += list_of_angles[compounds_in_lhs[i]]
                        for i in range(len_rhs):
                            angle_compound_rhs += list_of_angles[compounds_in_rhs[i]]

                        # in the middle of the angle of i reactions
                        if (len_rhs > 1 and len_lhs == 0) or (len_lhs > 1 and len_rhs == 0):
                            angle_compound = max(angle_compound_rhs, angle_compound_lhs) / (len_lhs + len_rhs)
                        else:
                            angle_compound = (angle_compound_rhs + angle_compound_lhs) / (len_lhs + len_rhs)

                        if total_number_of_reactions > 40:
                            angle_compound = angle_compound + 0.02
                else:
                    # radius of circle: compound outside - depending on number of reactions
                    if len_lhs > 1 or len_rhs > 1:
                        # if compound consists to more reactions at same side (lhs/rhs)
                        if total_number_of_reactions <= 40:
                            # radius = 350
                            radius = 280
                        else:
                            # radius = 340
                            radius = 280

                        angle_compound_lhs, angle_compound_rhs = 0, 0
                        for i in range(len_lhs):
                            angle_compound_lhs += list_of_angles[compounds_in_lhs[i]]
                        for i in range(len_rhs):
                            angle_compound_rhs += list_of_angles[compounds_in_rhs[i]]

                        # in the middle of the angle of i reactions
                        if (len_rhs > 1 and len_lhs == 0) or (len_lhs > 1 and len_rhs == 0):
                            angle_compound = max(angle_compound_rhs, angle_compound_lhs) / (len_lhs + len_rhs)
                        else:
                            angle_compound = (angle_compound_rhs + angle_compound_lhs) / (len_lhs + len_rhs)

                    elif ((cid_string in r.rhs_ids) and len(r.rhs_ids) == 2) \
                            or ((cid_string in r.lhs_ids) and len(r.lhs_ids) == 2):
                        if total_number_of_reactions <= 40:
                            radius = 350
                            if deviation_change is False:
                                deviation = -0.05
                            elif deviation_change:
                                deviation = 0.05
                        else:
                            radius = 340
                            if deviation_change is False:
                                deviation = -0.03
                            elif deviation_change:
                                deviation = 0.03

                        angle_compound = list_of_angles[count] + deviation
                        deviation_change = True
                    else:
                        # if compound on outside consists to one reactions:
                        if total_number_of_reactions <= 40:
                            radius = 350
                        else:
                            radius = 340

                        angle_compound = list_of_angles[count]

                if total_number_of_reactions <= 40:
                    major_axis = 1
                    minor_axis = 1
                else:
                    major_axis = 1.27   # type: ignore
                    minor_axis = 0.78   # type: ignore

                x = radius * major_axis * np.cos(angle_compound)
                y = radius * minor_axis * np.sin(angle_compound)

                # Update if it is already present
                concentration = None
                if scale_with_concentrations:
                    s = db.Structure(c.get_centroid(), structure_collection)
                    concentration = query_concentration("max_concentration", s, property_collection)
                brush = self.get_aggregate_brush(ctype)
                if cid_string in self.old_compounds and not self.reset_compounds:
                    self.compounds[cid_string] = [self.old_compounds[cid_string]]
                    del self.old_compounds[cid_string]
                    self.compounds[cid_string][0].setBrush(brush)
                    self.compounds[cid_string][0].setPen(self.compound_pen)
                    self.compounds[cid_string][0].x_coord = x
                    self.compounds[cid_string][0].y_coord = y
                    self.compounds[cid_string][0].concentration = concentration
                    # scaling = self.compounds[cid_string].get_scaling()
                    self.__animate_move(self.compounds[cid_string][0], x, y)
                else:
                    s = db.Structure(c.get_centroid(), structure_collection)
                    self.compounds[cid_string] = [Compound(
                        x, y, pen=self.compound_pen, brush=brush, concentration=concentration
                    )]
                    self.compounds[cid_string][0].db_representation = c
                    self.compounds[cid_string][0].structure = s.get_atoms()
                    self.__bind_functions_to_object(self.compounds[cid_string][0], True)
                    self.scene_object.addItem(self.compounds[cid_string][0])
                    self.__animate_fade_in(self.compounds[cid_string][0])

        # Add lines
        self.line_items = {}
        for r in self.reactions.values():
            self.__draw_lines_per_reaction_side(r[0], "lhs")
            self.__draw_lines_per_reaction_side(r[0], "rhs")

        # Move nodes above lines
        self.move_to_foreground(self.compounds)
        self.move_to_foreground(self.reactions)

        # Fade out old items
        for k in self.old_compounds.keys():
            self.__animate_fade_out(self.old_compounds[k])
        for k in self.old_reactions.keys():
            self.__animate_fade_out(self.old_reactions[k])

        # Start/run animations and wait for them to finish before deleting old items
        self.timer.start()
        QTimer.singleShot(1100, self.__delete_old_items)
        QTimer.singleShot(1150, self.__center_view)
        QTimer.singleShot(1200, self.__unlock_update)
        self.reset_compounds = False

    def __center_view(self):
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def __draw_lines_per_reaction_side(self, reaction: Reaction, side: str) -> None:
        ids = reaction.lhs_ids if side == "lhs" else reaction.rhs_ids
        side_point = QPoint(reaction.lhs()) if side == "lhs" else QPoint(reaction.rhs())
        rid = reaction.db_representation.id().string()
        for i, c in enumerate(ids):
            lid = rid + "_" + c + "_" + str(i)
            if lid in self.line_items:
                continue
            path = QPainterPath(self.compounds[c][0].center())
            path.lineTo(side_point)
            self.line_items[lid] = self.scene_object.addPath(path, pen=self.path_pen)
            self.__animate_fade_in(self.line_items[lid])

    def __bind_functions_to_object(self, object: Any, allow_focus: bool = False) -> None:
        object.bind_mouse_press_function(self.mouse_press_function)
        if allow_focus:
            object.bind_mouse_double_click_function(self.focus_function)
        object.setAcceptHoverEvents(True)
        object.bind_hover_enter_function(self.hover_enter_function)
        object.bind_hover_leave_function(self.hover_leave_function)
        object.bind_menu_function(self.menu_function)

    def __delete_old_items(self) -> None:
        # Remove old items
        for i in self.old_compounds.values():
            self.scene_object.removeItem(i)
        for i in self.old_reactions.values():
            self.scene_object.removeItem(i)
        self.old_compounds = {}
        self.old_reactions = {}
        self.scene_object.update()

    def __unlock_update(self) -> None:
        self.__currently_updating = False
        main_window = find_main_window()
        if main_window is not None:
            main_window.get_status_bar().clear_message()

    def __getitem__(self, i):
        # get information of database to make subscriptable
        return f"{i}"

    def __reformat_reaction(self, input_list, i, j):
        index_of_i = []
        index_of_j = []

        if [i, j] not in input_list:
            input_list.append([i, j])

        for idx, pair in zip(reversed(range(len(input_list))), input_list[:-1]):
            if i in pair:
                index_of_i.append(idx)
            elif j in pair:
                index_of_j.append(idx)

        if len(index_of_i) > 0 and len(index_of_j) == 0:
            if i == input_list[index_of_i[0]][0]:
                i, j = j, i
                input_list.insert(index_of_i[0], [i, j])
            elif i == input_list[index_of_i[0]][1]:
                input_list.insert(index_of_i[0] + 1, [i, j])

            del input_list[-1]

        if len(index_of_j) > 0 and len(index_of_i) == 0:
            if j == input_list[index_of_j[0]][0]:
                input_list.insert(index_of_j[0], [i, j])
            elif j == input_list[index_of_j[0]][1]:
                i, j = j, i
                input_list.insert(index_of_j[0] + 1, [i, j])

            del input_list[-1]

        if len(index_of_i) == 1 and len(index_of_j) == 1:
            if index_of_i[0] + 1 == index_of_j[0]:
                if i == input_list[index_of_i[0]][1] and j == input_list[index_of_j[0]][1]:
                    a = input_list[index_of_j[0]][0]
                    b = input_list[index_of_j[0]][1]
                    a, b = b, a
                    input_list.insert(index_of_j[0], [i, j])

        if len(index_of_i) > 0 and len(index_of_j) > 0:
            for first in index_of_i:
                for second in index_of_j:
                    if first + 1 == second:
                        if input_list[first][1] == input_list[second][0] and input_list[first][1] != j:
                            del input_list[-1]
                            continue


class CRSettings(ReactionAndCompoundViewSettings):

    def __init__(self, parent: QWidget, network: CRNetwork) -> None:
        super().__init__(parent, QVBoxLayout())
        self.network = network
        self.button_update = QPushButton("Update")
        self.p_layout.addWidget(self.button_update)
        self.button_update.clicked.connect(self.__update_function)  # pylint: disable=no-member

        self.button_undo = QPushButton("Undo")
        self.p_layout.addWidget(self.button_undo)
        self.button_undo.clicked.connect(self.network.undo_move)  # pylint: disable=no-member

        self.button_redo = QPushButton("Redo")
        self.p_layout.addWidget(self.button_redo)
        self.button_redo.clicked.connect(self.network.redo_move)  # pylint: disable=no-member

        self.time_label = QLabel(self)
        self.time_label.resize(100, 40)
        self.time_label.setText("Only Show Modified Reactions Since")
        self.time_edit = QDateTimeEdit(QDate())
        self.time_edit.setDisplayFormat("HH:mm dd.MM.yyyy")
        self.p_layout.addWidget(self.time_label)
        self.p_layout.addWidget(self.time_edit)

        self.current_id_label = QLabel(self)
        self.current_id_label.resize(100, 40)
        self.current_id_label.setText("Current Center Aggregate")
        self.p_layout.addWidget(self.current_id_label)
        self.current_id_text = QLineEdit(self)
        self.current_id_text.resize(100, 40)
        self.current_id_text.setText(str(self.network.current_centroid_id))
        self.p_layout.addWidget(self.current_id_text)
        self.button_jump_to_id = QPushButton("Jump to ID")
        self.p_layout.addWidget(self.button_jump_to_id)
        self.button_jump_to_id.clicked.connect(self.__jump_to_function)  # pylint: disable=no-member

        self.save_to_svg_button = QPushButton("Save SVG")
        self.p_layout.addWidget(self.save_to_svg_button)
        self.save_to_svg_button.clicked.connect(self.network.save_svg)  # pylint: disable=no-member

        self.button_traveling = QPushButton("Start Path Analysis")
        self.p_layout.addWidget(self.button_traveling)
        self.button_traveling.clicked.connect(self.__start_path_analysis_function)  # pylint: disable=no-member

        self.p_layout.addWidget(self.mol_widget)
        self.mol_widget.setMinimumWidth(200)
        self.mol_widget.setMaximumWidth(1000)
        self.mol_widget.setMinimumHeight(300)
        self.mol_widget.setMaximumWidth(1000)

        self.p_layout.addWidget(self.es_mep_widget)
        self.es_mep_widget.setMinimumHeight(300)
        self.es_mep_widget.setMinimumWidth(200)
        self.es_mep_widget.setMaximumWidth(1000)

        self._settings_visible = False
        self._set_up_advanced_settings_widgets(self.p_layout)
        self.setLayout(self.p_layout)
        self.show()
        self.set_advanced_settings_visible()

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

    def update_current_centroid_text(self, new_text: str) -> None:
        self.current_id_text.setText(new_text)

    def jump_to_aggregate_id(self, aggregate_id: str):
        self.current_id_text.setText(aggregate_id)
        self.__jump_to_function()

    def __jump_to_function(self) -> None:
        self.advanced_settings_widget.update_settings()
        requested_string: Union[None, str] = self.current_id_text.text()
        requested_string = requested_string if requested_string else None
        self.network.update_network(
            self.advanced_settings_widget.get_max_barrier(), self.advanced_settings_widget.get_min_barrier(),
            self.advanced_settings_widget.always_show_barrierless(), self.advanced_settings_widget.get_model(),
            self.advanced_settings_widget.scale_with_concentrations(), self.advanced_settings_widget.get_min_flux(),
            requested_string
        )
        self.update_current_centroid_text(
            str(self.network.current_centroid_id)
        )

    def __update_function(self) -> None:
        main_window = find_main_window()
        if main_window is not None:
            status_bar = main_window.get_status_bar()
            status_bar.update_status('Updating Network ...', timer=None)
        time = datetime.fromtimestamp(self.time_edit.dateTime().toSecsSinceEpoch())
        if self.network.earliest_compound_creation is None:
            compounds = self.network.db_manager.get_collection('compounds')
            compound = compounds.get_one_compound(dumps({}))
            if compound is None:
                return
            self.network.earliest_compound_creation = compound.created()
        if self.network.earliest_compound_creation < time:
            # only query if even relevant for network
            self.network.reaction_query = datetime_to_query(time)
        else:
            self.network.reaction_query = {}
        self.advanced_settings_widget.update_settings()
        requested_string: Union[None, str] = self.current_id_text.text()
        requested_string = requested_string if requested_string else None
        self.network.update_network(self.advanced_settings_widget.get_max_barrier(),
                                    self.advanced_settings_widget.get_min_barrier(),
                                    self.advanced_settings_widget.always_show_barrierless(),
                                    self.advanced_settings_widget.get_model(),
                                    self.advanced_settings_widget.scale_with_concentrations(),
                                    self.advanced_settings_widget.get_min_flux(),
                                    requested_string)
        self.update_current_centroid_text(
            str(self.network.current_centroid_id)
        )

    def __start_path_analysis_function(self) -> None:
        from scine_heron.database.graph_traversal import GraphTravelWidget
        GraphTravelWidget(self.parent(), self.network.db_manager)


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
        self.settings_scroll_area = CustomQScrollArea()
        self.settings_scroll_area.setWidget(self.settings)
        self.settings_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.splitter = QSplitter(self)
        self.splitter.addWidget(self.network)
        self.splitter.addWidget(self.settings_scroll_area)
        self.splitter.setSizes([320, 280])
        layout.addWidget(self.splitter)

        # Set dialog layout
        self.setLayout(layout)

    def jump_to_aggregate_id(self, aggregate_id: str):
        self.settings.jump_to_aggregate_id(aggregate_id)
