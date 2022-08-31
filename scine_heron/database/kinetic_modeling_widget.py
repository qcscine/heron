#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from typing import List, Any, Tuple, Union, Dict, Set, Optional

import scine_database as db
import scine_utilities as utils

from scine_heron.database.concentration_query_functions import query_concentration, query_concentration_list
from scine_heron.molecule.molecule_widget import MoleculeWidget

from PySide2.QtWidgets import (
    QWidget,
    QLabel,
    QComboBox,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QCheckBox,
    QScrollArea,
)

from PySide2.QtCore import Qt


class DirectedExplorationProgressView(QScrollArea):
    def __init__(self, db_manager: db.Manager) -> None:
        super().__init__()

        self.db_manager: db.Manager = db_manager
        self.__currently_updating = False
        self._old_layout: Union[None, QVBoxLayout] = None

        self._element_width = 200
        self._element_height = 200

    def update_view(self, step_to_compound_mapper: Any):
        if self.__currently_updating:
            return
        self.__currently_updating = True
        compound_collection = self.db_manager.get_collection("compounds")
        structure_collection = self.db_manager.get_collection("structures")
        # Remove old stuff
        if self._old_layout:
            QWidget().setLayout(self._old_layout)
        layout = QVBoxLayout()
        step_to_compound_map = step_to_compound_mapper.get_step_to_compound_mapping(
            self.parent().settings.get_comparison_threshold())
        show_only_added_compounds: bool = self.parent().settings.show_only_added_compounds
        already_present_compounds: Set[str] = set()
        for i, compound_id_list in enumerate(step_to_compound_map):
            step_widget = QWidget()
            qhbox = QHBoxLayout()
            self.add_description_box(qhbox, i + 1)
            added_compounds = False
            for c_id, label in compound_id_list:
                if show_only_added_compounds and i > 0:
                    if c_id.string() in already_present_compounds:
                        continue
                added_compounds = True
                compound = db.Compound(c_id, compound_collection)
                centroid = db.Structure(compound.get_centroid(), structure_collection)
                self.add_molecule(centroid, label, c_id, qhbox)
            if i == 0:
                already_present_compounds = set(c_id.string() for c_id, _ in compound_id_list)
            else:
                already_present_compounds = already_present_compounds.union(
                    set(c_id.string() for c_id, _ in compound_id_list))
            if added_compounds:
                step_widget.setLayout(qhbox)
                scroll_area = QScrollArea()
                scroll_area.setFixedWidth(self.width() - 25)
                scroll_area.setWidget(step_widget)
                layout.addWidget(scroll_area)

        self._old_layout = layout
        view_widget = QWidget()
        view_widget.setLayout(layout)
        self.setWidget(view_widget)

        self.__currently_updating = False

    def add_description_box(self, layout: QHBoxLayout, step_index: int):
        qvbox = QVBoxLayout()
        q_label = QLabel()
        q_label.setText("Step " + str(step_index))
        q_label.setFixedSize(int(self._element_width / 2), self._element_height)
        qvbox.addWidget(q_label, Qt.AlignTop)

        q_label1 = QLabel()
        q_label1.setText("c_max\nc_final\nc_flux\nID")
        q_label1.setFixedSize(int(self._element_width / 2), int(self._element_height / 2))
        qvbox.addWidget(q_label1, Qt.AlignTop)
        layout.addLayout(qvbox, Qt.AlignTop)

    def add_molecule(self, structure: db.Structure, label: str, c_id: db.ID, layout: QHBoxLayout):
        qvbox = QVBoxLayout()
        new_widget = MoleculeWidget(
            self, atoms=structure.get_atoms(),
        )
        new_widget.setFixedSize(self._element_width, self._element_height)
        qvbox.addWidget(new_widget, Qt.AlignTop)

        q_label = QLabel()
        q_label.setText(label + "\n" + c_id.string())
        q_label.setFixedSize(self._element_width, int(self._element_height / 2))
        q_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        qvbox.addWidget(q_label, Qt.AlignTop)
        layout.addLayout(qvbox, Qt.AlignTop)


class KineticModelingDrivenExplorationExtractor:
    def __init__(self, db_manager: db.Manager):
        self._kinetic_modeling_job_order: str = "kinetx_kinetic_modeling"
        self._aggregate_id_key: str = "aggregate_ids"
        self._aggregate_type_key: str = "aggregate_types"
        self._start_concentrations_key: str = "start_concentrations"
        self._structures: db.Collection = db_manager.get_collection("structures")
        self._compounds: db.Collection = db_manager.get_collection("compounds")
        self._calculations: db.Collection = db_manager.get_collection("calculations")
        self._properties: db.Collection = db_manager.get_collection("properties")
        self.max_concentration_label: str = "max_concentration"
        self.final_concentration_label: str = "final_concentration"
        self.concentration_flux_label: str = "concentration_flux"
        self._comparison_index: int = 0
        self._concentrations_to_compounds_map: Dict[str, Tuple[List[float], List[float], List[float]]] = dict()
        self._n_calcs_last: int = 0
        self._compound_ids_per_calculations: List[List[Tuple[db.ID, str]]] = list()
        self._old_threshold: Union[None, float] = None
        self._concentrations_to_calculations_map: Dict[str, List[int]] = dict()
        self._starting_compound_ids: Optional[List[Tuple[db.ID, str]]] = None

    def reset_cache(self):
        self._n_calcs_last = 0
        self._concentrations_to_compounds_map = dict()
        self._old_threshold = None

    def set_comparison_index(self, new_index: int):
        self._comparison_index = new_index
        self.reset_cache()

    def get_comparison_options(self):
        return [self.max_concentration_label, self.final_concentration_label, self.concentration_flux_label]

    def get_step_to_compound_mapping(self, comparison_threshold: float) -> List[List[Tuple[db.ID, str]]]:
        return self._get_compounds_in_kinetic_modeling_jobs(comparison_threshold)

    def _get_one_input_structure(self):
        # Check for a compound with a start concentration
        for compound in self._compounds.iterate_all_compounds():
            compound.link(self._compounds)
            centroid = db.Structure(compound.get_centroid(), self._structures)
            start_concentration = query_concentration("start_concentration", centroid, self._properties)
            if start_concentration:
                return centroid

    def _get_initial_compounds_from_calculation_settings(self, settings: utils.ValueCollection)\
            -> List[Tuple[db.ID, str]]:
        if not self._starting_compound_ids:
            if settings[self._start_concentrations_key]:
                assert isinstance(settings[self._start_concentrations_key], list)
            if settings[self._aggregate_id_key]:
                assert isinstance(settings[self._aggregate_id_key], list)
            if settings[self._aggregate_type_key]:
                assert isinstance(settings[self._aggregate_type_key], list)
            start_concentrations: List[float] = settings[self._start_concentrations_key]  # type: ignore
            aggregate_ids: List[str] = settings[self._aggregate_id_key]  # type: ignore
            aggregate_types: List[int] = settings[self._aggregate_type_key]  # type: ignore
            self._starting_compound_ids = list()
            for concentration, a_str_id, a_type in zip(start_concentrations, aggregate_ids, aggregate_types):
                if concentration > 0.0 and db.CompoundOrFlask(a_type) == db.CompoundOrFlask.COMPOUND:
                    self._starting_compound_ids.append((db.ID(a_str_id), "\ninput\n"))
        return self._starting_compound_ids

    def _keep_track_on_concentration_to_calculation_mapping(self, str_id: str, calc_index: int):
        if str_id in self._concentrations_to_calculations_map:
            self._concentrations_to_calculations_map[str_id].append(calc_index)
        else:
            self._concentrations_to_calculations_map[str_id] = [calc_index]

    def _get_concentration_index_for_calculation(self, str_id: str, calc_index: int):
        return self._concentrations_to_calculations_map[str_id].index(calc_index)

    def _get_compounds_in_kinetic_modeling_jobs(self, comparison_threshold: float) -> List[List[Tuple[db.ID, str]]]:
        calculation_ids = self._get_one_input_structure().get_calculations(self._kinetic_modeling_job_order)
        if len(calculation_ids) < 1:
            return list()
        if len(calculation_ids) > self._n_calcs_last:
            self.reset_cache()
        if self._old_threshold:
            if abs(self._old_threshold - comparison_threshold) < 1e-14:
                return self._compound_ids_per_calculations

        self._n_calcs_last = len(calculation_ids)
        settings_0 = db.Calculation(calculation_ids[0], self._calculations).get_settings()
        self._compound_ids_per_calculations = [self._get_initial_compounds_from_calculation_settings(settings_0)]
        self._concentrations_to_compounds_map = dict()
        for i, calc_id in enumerate(calculation_ids):
            calculation = db.Calculation(calc_id, self._calculations)
            settings = calculation.get_settings()
            compound_ids: List[Tuple[db.ID, str]] = list()
            if calculation.get_status() != db.Status.COMPLETE:
                continue
            a_str_ids: List[str] = settings[self._aggregate_id_key]  # type: ignore
            a_int_types: List[int] = settings[self._aggregate_type_key]  # type: ignore
            for a_str_id, a_type in zip(a_str_ids, a_int_types):
                if db.CompoundOrFlask(a_type) == db.CompoundOrFlask.COMPOUND:
                    c_id = db.ID(a_str_id)
                    compound = db.Compound(c_id, self._compounds)
                    centroid = db.Structure(compound.get_centroid(), self._structures)
                    self._keep_track_on_concentration_to_calculation_mapping(a_str_id, i)

                    if a_str_id in self._concentrations_to_compounds_map:
                        max_concentrations = self._concentrations_to_compounds_map[a_str_id][0]
                        final_concentrations = self._concentrations_to_compounds_map[a_str_id][1]
                        concentration_fluxes = self._concentrations_to_compounds_map[a_str_id][2]
                    else:
                        max_concentrations = query_concentration_list(
                            self.max_concentration_label, centroid, self._properties)
                        final_concentrations = query_concentration_list(
                            self.final_concentration_label, centroid, self._properties)
                        concentration_fluxes = query_concentration_list(
                            self.concentration_flux_label, centroid, self._properties)
                        self._concentrations_to_compounds_map[a_str_id] = (max_concentrations, final_concentrations,
                                                                           concentration_fluxes)
                    c_i = self._get_concentration_index_for_calculation(a_str_id, i)
                    concentrations = [max_concentrations[c_i], final_concentrations[c_i], concentration_fluxes[c_i]]
                    if None not in concentrations:
                        if concentrations[self._comparison_index] >= comparison_threshold:
                            label = str(round(concentrations[0], 4)) + "\n" + str(round(concentrations[1], 4))\
                                + "\n" + str(round(concentrations[2], 4))
                            compound_ids.append((c_id, label))
            self._compound_ids_per_calculations.append(compound_ids)
            self._old_threshold = comparison_threshold
        return self._compound_ids_per_calculations


class DirectedExplorationProgressSettings(QWidget):
    def __init__(self, parent: QWidget, db_manager: db.Manager) -> None:
        super(DirectedExplorationProgressSettings, self).__init__(parent)
        self._db_manager = db_manager
        self._comparison_label = "max_concentration"
        self._comparison_threshold = 1e-1
        self.show_only_added_compounds: bool = True
        self._label_options_cb: Union[None, QComboBox] = None
        layout = QVBoxLayout()
        self._width = 240
        self.setFixedWidth(self._width)

        self._button_update = QPushButton("Update")
        layout.addWidget(self._button_update)
        self._button_update.clicked.connect(self.__update_function)  # pylint: disable=no-member
        mapper_options = ["kinetic modeling"]
        self._step_to_compound_mapper = KineticModelingDrivenExplorationExtractor(self._db_manager)

        self._qvbox = QVBoxLayout()
        self._step_mapper_label = QLabel()
        self._step_mapper_label.setText("Exploration Step Mapper")
        self._qvbox.addWidget(self._step_mapper_label)

        self._mapper_cb = QComboBox()
        for mapper in mapper_options:
            self._mapper_cb.addItem(mapper)
        self._mapper_cb.currentIndexChanged.connect(self.update_step_to_compound_mapper)  # pylint: disable=no-member
        self._qvbox.addWidget(self._mapper_cb)

        self._concentration_box_label = QLabel()
        self._concentration_box_label.setText("Comparison Label")
        self._qvbox.addWidget(self._concentration_box_label)
        self.update_label_options(self._qvbox)

        self._concentration_threshold_label = QLabel()
        self._concentration_threshold_label.setText("Concentration Threshold")
        self._qvbox.addWidget(self._concentration_threshold_label)
        self._concentration_threshold_text = QLineEdit(self)
        self._concentration_threshold_text.setText(str(self._comparison_threshold))
        self._qvbox.addWidget(self._concentration_threshold_text)

        self.only_added_cbox = QCheckBox("Show only added compounds")
        self.only_added_cbox.setChecked(self.show_only_added_compounds)
        self.only_added_cbox.toggled.connect(self.update_show_only_added_compounds)  # pylint: disable=no-member
        self._qvbox.addWidget(self.only_added_cbox)

        self._qvbox.addStretch()

        layout.addLayout(self._qvbox)
        self.setLayout(layout)

    def update_show_only_added_compounds(self):
        self.show_only_added_compounds = self.only_added_cbox.isChecked()

    def update_label_options(self, layout: QVBoxLayout):
        label_options = self._step_to_compound_mapper.get_comparison_options()
        old_widget = self._label_options_cb
        self._label_options_cb = QComboBox()
        for o in label_options:
            self._label_options_cb.addItem(o)
        self._label_options_cb.currentIndexChanged.connect(self.update_comparison_index)  # pylint: disable=no-member
        if old_widget:
            layout.replaceWidget(old_widget, self._label_options_cb)
        else:
            layout.addWidget(self._label_options_cb)

    def __update_function(self) -> None:
        self.parent().progress_view.update_view(self._step_to_compound_mapper)

    def update_step_to_compound_mapper(self, new_mapper_index: int):
        if new_mapper_index == 0:
            self._step_to_compound_mapper = KineticModelingDrivenExplorationExtractor(self._db_manager)
            self.update_label_options(self._qvbox)

    def update_comparison_index(self, new_comparison_index):
        self._step_to_compound_mapper.set_comparison_index(new_comparison_index)

    def get_comparison_threshold(self):
        return float(self._concentration_threshold_text.text())


class KineticExplorationProgressWidget(QWidget):
    def __init__(self, parent: QWidget, db_manager: db.Manager) -> None:
        super(KineticExplorationProgressWidget, self).__init__(parent=parent)
        self.db_manager = db_manager

        # Create layout and add widgets
        layout = QHBoxLayout()
        self.progress_view = DirectedExplorationProgressView(self.db_manager)
        self.settings = DirectedExplorationProgressSettings(self, self.db_manager)
        layout.addWidget(self.progress_view)
        layout.addWidget(self.settings)

        # Set dialog layout
        self.setLayout(layout)
