#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QMenu,
                               QTreeWidget, QTreeWidgetItem, QLabel, QLineEdit, QPushButton, QDateTimeEdit)
from PySide2.QtCore import Qt, QObject, QDate
from PySide2.QtGui import QFont
from datetime import datetime
from typing import Any, Optional, Union, Tuple, List, Dict
from json import dumps

from scine_database import Manager, ID, Structure, ElementaryStep, ElementaryStepType, Label
import scine_database as db
from scine_utilities import AtomCollection

from scine_heron.utilities import datetime_to_query
from scine_heron.molecule.molecule_widget import MoleculeWidget
from scine_heron.database.reaction_compound_widget import AdvancedSettingsWidget
from scine_heron.database.energy_query_functions import check_barrier_height
from scine_heron.database.concentration_query_functions import query_reaction_flux
from scine_heron.database.compound_and_flasks_helper import get_compound_or_flask
from scine_heron.utilities import copy_text_to_clipboard
from scine_heron import get_core_tab

from PySide2.QtWidgets import QCheckBox


class TreeWidget(QTreeWidget):
    def __init__(self, parent: QObject):
        QTreeWidget.__init__(self, parent)

    def contextMenuEvent(self, event):
        self.currentItem().contextMenuEvent(event)


class TreeWidgetItem(QTreeWidgetItem):

    def __init__(self, parent: QObject, info: List[str]):
        QTreeWidgetItem.__init__(self, parent, info, type=QTreeWidgetItem.UserType)
        self.id_string_list = [label.split('(')[1][:-1] for label in info]
        self.item_type = info[0].split('(')[0].strip()

    def contextMenuEvent(self, event):
        menu = QMenu()
        copyid_action = menu.addAction('Copy ID')
        show_in_mol_view = menu.addAction('Move to Molecular Viewer')

        cfs_type: bool = self.item_type in ['Compound', 'Flask', 'Structure']
        er_type: bool = self.item_type in ['Elementary Step', 'Reaction']

        if cfs_type:
            copy_masm_cbor_action = menu.addAction('Copy Molassembler Graph')
            center_in_network = menu.addAction('Center in Network View')
        if er_type:
            submenu = menu.addMenu("Copy Reactants")
            reactants = self.get_reactants()
            reactant_copy_actions = [submenu.addAction(r) for r in reactants]
        _ = menu.addAction('Close Menu')
        action = menu.exec_(event.globalPos())  # type: ignore
        if action == copyid_action:
            current_id = self.id_string_list[0]
            copy_text_to_clipboard(current_id)
        if action == show_in_mol_view:
            self.display_in_molecule_viewer()
        if cfs_type:
            if action == copy_masm_cbor_action:
                self.copy_cbor_to_clipboard()
            if action == center_in_network:
                self.center_network_view_on_aggregate()
        if er_type:
            for i, copy_action in enumerate(reactant_copy_actions):
                if action == copy_action:
                    copy_text_to_clipboard(reactants[i])

    def copy_cbor_to_clipboard(self):
        if self.item_type == 'Structure':
            self.parent().copy_cbor_to_clipboard()
        else:
            self.treeWidget().parent().copy_cbor_to_clipboard(self.id_string_list[0], self.item_type)

    def center_network_view_on_aggregate(self):
        if self.item_type == 'Structure':
            self.parent().center_network_view_on_aggregate()
        else:
            self.treeWidget().parent().center_network_view_on_aggregate(self.id_string_list[0])

    def display_in_molecule_viewer(self):
        if self.item_type in ['Structure', 'Elementary Step']:
            self.treeWidget().parent().display_in_molecule_viewer(self.id_string_list[0])
        else:
            self.child(0).display_in_molecule_viewer()

    def get_reactants(self) -> List[str]:
        if self.item_type in ['Elementary Step']:
            return self.treeWidget().parent().get_reactants(self.id_string_list[0])
        else:
            return self.child(0).get_reactants()


class AggregateTreeWidget(QWidget):
    def __init__(self, parent: Optional[QWidget], db_manager: Manager):
        super(AggregateTreeWidget, self).__init__(parent)

        layout = QVBoxLayout()

        self.current_agg_id_label = QLabel(self)
        self.current_agg_id_label.resize(560, 40)
        self.current_agg_id_label.setText("Current Aggregate ID")
        layout.addWidget(self.current_agg_id_label)

        agg_widget = QWidget()
        agg_h_box = QHBoxLayout()
        self.current_agg_id_text = QLineEdit(self)
        self.current_agg_id_text.resize(400, 40)
        self.current_agg_id_text.setText("")
        agg_h_box.addWidget(self.current_agg_id_text)
        self.button_jump_to_agg_id = QPushButton("Jump To ID")
        agg_h_box.addWidget(self.button_jump_to_agg_id)
        self.button_jump_to_agg_id.clicked.connect(self.__focus_aggregate_id)  # pylint: disable=no-member
        agg_widget.setLayout(agg_h_box)
        layout.addWidget(agg_widget)

        self.current_id_label = QLabel(self)
        self.current_id_label.resize(560, 40)
        self.current_id_label.setText("Current Structure ID")
        layout.addWidget(self.current_id_label)

        str_widget = QWidget()
        str_h_box = QHBoxLayout()
        self.current_id_text = QLineEdit(self)
        self.current_id_text.resize(400, 40)
        self.current_id_text.setText("")
        str_h_box.addWidget(self.current_id_text)
        self.button_jump_to_str_id = QPushButton("Jump To ID")
        str_h_box.addWidget(self.button_jump_to_str_id)
        self.button_jump_to_str_id.clicked.connect(self.__focus_structure_id)  # pylint: disable=no-member
        str_widget.setLayout(str_h_box)
        layout.addWidget(str_widget)

        self.current_cbor_label = QLabel(self)
        self.current_cbor_label.resize(560, 40)
        self.current_cbor_label.setText("Current Aggregate MASM-CBOR String")
        layout.addWidget(self.current_cbor_label)

        cbor_widget = QWidget()
        cbor_h_box = QHBoxLayout()
        self.current_cbor_text = QLineEdit(self)
        self.current_cbor_text.resize(400, 40)
        self.current_cbor_text.setText("")
        cbor_h_box.addWidget(self.current_cbor_text)
        self.button_jump_to_cbor = QPushButton("Jump To CBOR-String")
        cbor_h_box.addWidget(self.button_jump_to_cbor)
        self.button_jump_to_cbor.clicked.connect(self.jump_to_cbor)  # pylint: disable=no-member
        cbor_widget.setLayout(cbor_h_box)
        layout.addWidget(cbor_widget)

        update_h_box = QHBoxLayout()
        update_widget = QWidget()
        self.button_update = QPushButton("Update")
        update_h_box.addWidget(self.button_update)
        self.button_update.clicked.connect(self.update)  # pylint: disable=no-member
        self._query_compounds = True
        self.query_compounds_cbox = QCheckBox("Show Compounds", parent=self)
        self.query_compounds_cbox.setChecked(self._query_compounds)
        self.query_compounds_cbox.clicked.connect(self._check_query_compounds)  # pylint: disable=no-member
        update_h_box.addWidget(self.query_compounds_cbox)
        self.query_flasks_cbox = QCheckBox("Show Flasks", parent=self)
        self.query_flasks_cbox.setChecked(False)
        self.query_flasks_cbox.clicked.connect(self._check_query_flasks)  # pylint: disable=no-member
        update_h_box.addWidget(self.query_flasks_cbox)
        update_widget.setLayout(update_h_box)
        layout.addWidget(update_widget)

        self.db_manager = db_manager

        self.tree = TreeWidget(self)
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self.focus)  # pylint: disable=no-member
        self.tree.itemActivated.connect(self.focus)  # pylint: disable=no-member
        layout.addWidget(self.tree)
        self.setLayout(layout)

        self.structures = self.db_manager.get_collection("structures")

        self.compounds = self.db_manager.get_collection("compounds")
        self.flasks = self.db_manager.get_collection("flasks")
        self._is_updating = False

    def _check_query_compounds(self):
        if self.query_compounds_cbox.isChecked():
            self.query_flasks_cbox.setChecked(False)
        else:
            self.query_flasks_cbox.setChecked(True)

    def _check_query_flasks(self):
        if self.query_flasks_cbox.isChecked():
            self.query_compounds_cbox.setChecked(False)
        else:
            self.query_compounds_cbox.setChecked(True)

    def _check_masm_graph(self, aggregate: Union[db.Compound, db.Flask]) -> bool:
        graph = db.Structure(aggregate.get_centroid(), self.structures).get_graph("masm_cbor_graph")
        return graph == self.current_cbor_text.text()

    def jump_to_cbor(self):
        if self._is_updating:
            return
        self._is_updating = True
        items = []
        query_compounds = self.query_compounds_cbox.isChecked()
        if query_compounds:
            aggregates = "compounds"
            collection = self.compounds
            it = collection.iterate_all_compounds()
            allowed_labels = [Label.MINIMUM_OPTIMIZED, Label.USER_OPTIMIZED, Label.SURFACE_OPTIMIZED]
        else:
            aggregates = "flasks"
            collection = self.flasks
            it = collection.iterate_all_flasks()
            allowed_labels = [Label.COMPLEX_OPTIMIZED, Label.USER_OPTIMIZED]
        for i in it:
            i.link(collection)
            if self._check_masm_graph(i):
                main = TreeWidgetItem(self.tree, [f"{aggregates.capitalize()} ({str(i.get_id())})"])
                items.append(main)
                for sid in i.get_structures():
                    structure = db.Structure(sid, self.structures)
                    if structure.get_label() in allowed_labels:
                        TreeWidgetItem(main, [f"Structure ({str(sid)})"])
                break
        self.tree.insertTopLevelItems(0, items)
        if items:
            self.focus(items[0], None)
        self._is_updating = False

    def update(self):
        if self._is_updating:
            return
        self._is_updating = True
        self.tree.clear()
        items = []
        query_compounds = self.query_compounds_cbox.isChecked()
        if query_compounds:
            aggregates = "compounds"
            collection = self.compounds
            it = collection.iterate_all_compounds()
            allowed_labels = [Label.MINIMUM_OPTIMIZED, Label.USER_OPTIMIZED, Label.SURFACE_OPTIMIZED]
        else:
            aggregates = "flasks"
            collection = self.flasks
            it = collection.iterate_all_flasks()
            allowed_labels = [Label.COMPLEX_OPTIMIZED, Label.USER_OPTIMIZED]
        for i in it:
            i.link(collection)
            main = TreeWidgetItem(self.tree, [f"{aggregates.capitalize()[0:-1]} ({str(i.get_id())})"])
            items.append(main)
            for sid in i.get_structures():
                structure = db.Structure(sid, self.structures)
                if structure.get_label() in allowed_labels:
                    TreeWidgetItem(main, [f"Structure ({str(sid)})"])
        self.tree.insertTopLevelItems(0, items)
        self._is_updating = False

    def focus(self, item: TreeWidgetItem, _):
        if item.childCount() > 0:
            self.current_agg_id_text.setText(item.id_string_list[0])
            item = item.child(0)
        else:
            self.current_agg_id_text.setText(item.parent().id_string_list[0])
        structure_id = item.id_string_list[0]
        structure = db.Structure(db.ID(structure_id), self.structures)
        cbor_string = ""
        if structure.has_graph("masm_cbor_graph"):
            cbor_string = structure.get_graph("masm_cbor_graph")
        self.current_cbor_text.setText(cbor_string)
        self.current_id_text.setText(structure_id)
        self.__focus_structure_id(structure_id)

    def __focus_structure_id(self, str_id: Optional[str] = None) -> None:
        if str_id is None or not str_id:
            str_id = self.current_id_text.text().strip()
            item_search: Tuple[Union[str, None], Union[str, None]] = (None, None)
            if not str_id:
                return
            item_search = None, str_id
            self._activate_item(item_search)
        s = Structure(ID(str_id), self.structures)
        self.parent().display_molecule(s.get_atoms())

    def __focus_aggregate_id(self, agg_id: Optional[str] = None) -> None:
        if agg_id is None or not agg_id:
            agg_id = self.current_agg_id_text.text().strip()
            item_search: Tuple[Union[str, None], Union[str, None]] = (None, None)
            if not agg_id:
                return
            if self.query_compounds_cbox.isChecked():
                aggregates = "compounds"
                a_type = db.CompoundOrFlask.COMPOUND
            else:
                aggregates = "flasks"
                a_type = db.CompoundOrFlask.FLASK
            agg = get_compound_or_flask(db.ID(agg_id), a_type, self.compounds, self.flasks)
            if not agg.exists():
                print(f"No {aggregates.capitalize()[:-1]} exists with ID {agg_id}")
                return
            str_id = str(agg.get_centroid())
            item_search = agg_id, None
            self._activate_item(item_search)
        s = Structure(ID(str_id), self.structures)
        self.parent().display_molecule(s.get_atoms())

    def _activate_item(self, item_search: Tuple[Union[str, None], Union[str, None]]) -> None:
        if item_search[0] is None and item_search[1] is None:
            return
        aggregates = "compounds" if self.query_compounds_cbox.isChecked() else "flasks"
        if item_search[0] is not None:
            search_str = f"{aggregates.capitalize()} ({item_search[0]})"
            items = self.tree.findItems(search_str, Qt.MatchFlag.MatchCaseSensitive)  # type: ignore
            if not items:
                return
        if item_search[1] is not None:
            search_str = f"Structure ({item_search[1]})"
            items = self.tree.findItems(search_str, Qt.MatchFlag.MatchCaseSensitive)  # type: ignore
        if not items:
            return
        current = self.tree.currentItem()
        if current is not None:
            current.setSelected(False)
            current.setExpanded(False)
        self.tree.setCurrentItem(items[0])
        items[0].setExpanded(True)
        self.focus(items[0], None)

    def copy_cbor_to_clipboard(self, aggregate_id: str, aggregate_type: str):
        if aggregate_type.lower() == "compound":
            a_type = db.CompoundOrFlask.COMPOUND
        else:
            a_type = db.CompoundOrFlask.FLASK
        aggregate = get_compound_or_flask(db.ID(aggregate_id), a_type, self.compounds, self.flasks)
        centroid = db.Structure(aggregate.get_centroid(), self.structures)
        cbor = centroid.get_graph("masm_cbor_graph")
        copy_text_to_clipboard(cbor)

    def center_network_view_on_aggregate(self, aggregate_id: str):
        tab = get_core_tab('network_viewer')
        if tab is not None:
            tab.jump_to_aggregate_id(aggregate_id)

    def display_in_molecule_viewer(self, structure_id: str):
        structure = db.Structure(db.ID(structure_id), self.structures)
        atoms = structure.get_atoms()
        tab = get_core_tab('molecule_viewer')
        if tab is not None:
            tab.update_molecule(atoms=atoms)


class ReactionTreeWidget(QWidget):
    def __init__(self, parent: Optional[QWidget], db_manager: Manager):
        super(ReactionTreeWidget, self).__init__(parent)
        self.db_manager = db_manager

        self.collection = self.db_manager.get_collection("reactions")
        self.elementary_steps = self.db_manager.get_collection("elementary_steps")
        self.structures = self.db_manager.get_collection("structures")
        self.properties = self.db_manager.get_collection("properties")
        self.compounds = self.db_manager.get_collection("compounds")
        self.flasks = self.db_manager.get_collection("flasks")
        self.reactions = self.db_manager.get_collection("reactions")

        layout = QVBoxLayout()
        self.button_update = QPushButton("Update")
        layout.addWidget(self.button_update)
        self.button_update.clicked.connect(self.update)  # pylint: disable=no-member

        # Selection label and line edit box
        self.reaction_selection_label = QLabel(self)
        self.reaction_selection_label.setText('Reaction Selection')
        self.reaction_selection_label.resize(560, 40)
        layout.addWidget(self.reaction_selection_label)

        self.reaction_selection_text = QLineEdit(self)
        self.reaction_selection_text.setText("")
        self.reaction_selection_text.setToolTip('Any valid pymongo query\n'
                                                ' e.g.: {"_id": {"$oid": "627ad4ef38b7073df406d2ab"}}\n'
                                                'or a file name if <Reaction Ids from file> is toggled.\n'
                                                'Note that the file must only contain reaction IDs with one ID per '
                                                'line.')
        self.reaction_selection_text.resize(560, 40)
        layout.addWidget(self.reaction_selection_text)

        qh_box_layout_labeles = QHBoxLayout()
        self.lhs_selection_label = QLabel(self)
        self.lhs_selection_label.setText("LHS")
        self.lhs_selection_label.resize(int(560 / 2.1), 40)
        qh_box_layout_labeles.addWidget(self.lhs_selection_label)

        self.rhs_selection_label = QLabel(self)
        self.rhs_selection_label.setText("RHS")
        self.rhs_selection_label.resize(int(560 / 2.1), 40)
        qh_box_layout_labeles.addWidget(self.rhs_selection_label)
        layout.addLayout(qh_box_layout_labeles)

        qh_box_layout_texts = QHBoxLayout()
        self.lhs_selection_text = QLineEdit(self)
        self.lhs_selection_text.setText("")
        self.lhs_selection_text.setToolTip("The LHS/RHS constraint may be combined with the selection field if\n"
                                           "it contains a <$and> operator or reads reaction IDs from file.\n"
                                           "Multiple aggregate IDs/MASM graphs should be separated by spaces:\n"
                                           "    627a75f938b7073df306c7c3 62aa892438b70728a545f6e0")
        qh_box_layout_texts.addWidget(self.lhs_selection_text)

        self.rhs_selection_text = QLineEdit(self)
        self.rhs_selection_text.setText("")
        qh_box_layout_texts.addWidget(self.rhs_selection_text)
        layout.addLayout(qh_box_layout_texts)

        qh_box_layout_toggles = QHBoxLayout()
        # optional toggle to read the reaction ids from some file
        self.read_from_file_cbox = QCheckBox("Reaction IDs from file", parent=self)
        self.read_from_file_cbox.setChecked(False)
        qh_box_layout_toggles.addWidget(self.read_from_file_cbox)

        self.use_lhs_rhs_selection_cbox = QCheckBox("Use LHS/RHS selection", parent=self)
        self.use_lhs_rhs_selection_cbox.setChecked(False)
        qh_box_layout_toggles.addWidget(self.use_lhs_rhs_selection_cbox)

        self.take_as_masm_string_cbox = QCheckBox("LHS and RHS are MASM strings", parent=self)
        self.take_as_masm_string_cbox.setChecked(False)
        qh_box_layout_toggles.addWidget(self.take_as_masm_string_cbox)

        self.time_label = QLabel(self)
        self.time_label.resize(100, 40)
        self.time_label.setText("Only Show Modified Reactions Since")
        self.time_edit = QDateTimeEdit(QDate())
        self.time_edit.setDisplayFormat("HH:mm dd.MM.yyyy")
        qh_box_layout_toggles.addWidget(self.time_label)
        qh_box_layout_toggles.addWidget(self.time_edit)
        self.earliest_reaction_creation: Optional[datetime] = None

        layout.addLayout(qh_box_layout_toggles)

        self._advanced_settings_visible = False
        self._set_up_advanced_settings_widgets(layout)

        self.tree = TreeWidget(self)
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self.focus)  # pylint: disable=no-member
        self.tree.itemActivated.connect(self.focus)  # pylint: disable=no-member
        layout.addWidget(self.tree)
        self.setLayout(layout)

        self._is_updating = False

    def set_advanced_settings_visible(self) -> None:
        self._advanced_settings_visible = self.advanced_settings_cbox.isChecked()
        if self._advanced_settings_visible:
            self.advanced_settings_widget.setVisible(True)
        else:
            self.advanced_settings_widget.setVisible(False)

    def _set_up_advanced_settings_widgets(self, layout):
        self.advanced_settings_cbox = QCheckBox("ADVANCED SETTINGS")
        self.advanced_settings_cbox.setChecked(self._advanced_settings_visible)
        self.advanced_settings_cbox.toggled.connect(  # pylint: disable=no-member
            self.set_advanced_settings_visible
        )

        self.advanced_settings_widget = AdvancedSettingsWidget(
            None,
            self.db_manager
        )
        layout.addWidget(self.advanced_settings_cbox)
        layout.addWidget(self.advanced_settings_widget)
        self.set_advanced_settings_visible()

    def _get_reaction_selection(self) -> Dict[str, Any]:
        from json import loads, JSONDecodeError
        selection: Dict = {"$and": []}
        custom_selection: Optional[Dict] = None

        if self.read_from_file_cbox.isChecked():
            try:
                f = open(self.reaction_selection_text.text(), "r")
                lines = f.readlines()
                f.close()
                reaction_str_ids = [{"$oid": line.replace("\n", "")} for line in lines]
                custom_selection = {"_id": {"$in": reaction_str_ids}}
            except OSError:
                print("Could not open/read file " + self.reaction_selection_text.text())
        else:
            if self.reaction_selection_text.text():
                try:
                    custom_selection = loads(self.reaction_selection_text.text())
                except JSONDecodeError as error:
                    print("Invalid input string. The string must be convertable to a python dictionary!")
                    print(error.msg)
        if custom_selection is not None:
            selection["$and"].append(custom_selection)

        # time handling
        time = datetime.fromtimestamp(self.time_edit.dateTime().toSecsSinceEpoch())
        if self.earliest_reaction_creation is None:
            reaction = self.reactions.get_one_reaction(dumps({}))
            if reaction is None:
                # we don't even have a reaction, so just return empty dict
                return dict()
            self.earliest_reaction_creation = reaction.created()
        if self.earliest_reaction_creation < time:
            # only query if even relevant for network
            selection["$and"].append(datetime_to_query(time))

        # Use LHS/RHS definition as an additional constraint
        if self.use_lhs_rhs_selection_cbox.isChecked() and not self.take_as_masm_string_cbox.isChecked():
            lhs_selection_ids = self.lhs_selection_text.text().split()
            rhs_selection_ids = self.rhs_selection_text.text().split()
            if lhs_selection_ids:
                lhs_condition = {"$and": [{"lhs.id": {"$oid": str_id}} for str_id in lhs_selection_ids]}
                selection["$and"].append(lhs_condition)  # type: ignore
            if rhs_selection_ids:
                rhs_condition = {"$and": [{"rhs.id": {"$oid": str_id}} for str_id in rhs_selection_ids]}
                selection["$and"].append(rhs_condition)  # type: ignore

        if selection["$and"]:
            return selection
        return dict()

    def update(self):
        if self._is_updating:
            return
        self._is_updating = True
        items = []
        selection = self._get_reaction_selection()
        self.advanced_settings_widget.update_settings()
        self.tree.clear()
        for i in self.collection.iterate_reactions(dumps(selection)):
            i.link(self.collection)
            if not self._filter_reaction(i):
                continue
            main = TreeWidgetItem(self.tree, [f"Reaction ({str(i.get_id())})"])
            items.append(main)
            for c in i.get_elementary_steps():
                TreeWidgetItem(main, [f"Elementary Step ({str(c)})"])
        self.tree.insertTopLevelItems(0, items)
        self._is_updating = False

    def _filter_reaction(self, reaction: db.Reaction) -> bool:
        if not self._check_reaction_barrier(reaction):
            return False
        if self.advanced_settings_widget.scale_with_concentrations():
            if not self._check_concentration_flux(reaction):
                return False
        if self.take_as_masm_string_cbox.isChecked() and self.use_lhs_rhs_selection_cbox.isChecked():
            if not self._check_masm_graph(reaction):
                return False
        return True

    def _check_reaction_barrier(self, reaction: db.Reaction) -> bool:
        return check_barrier_height(reaction, self.db_manager, self.advanced_settings_widget.get_model(),
                                    self.structures, self.properties, self.advanced_settings_widget.get_max_barrier(),
                                    self.advanced_settings_widget.get_min_barrier(),
                                    self.advanced_settings_widget.always_show_barrierless()) is not None

    def _check_concentration_flux(self, reaction: db.Reaction) -> bool:
        flux = query_reaction_flux("_reaction_edge_flux", reaction, self.compounds, self.flasks, self.structures,
                                   self.properties)
        return flux > self.advanced_settings_widget.get_min_flux()

    def _valid_graphs(self, reference: List[str], reactant_graphs: List[str]) -> bool:
        # Make sure that there are no graphs but the reference ones.
        for graph in reactant_graphs:
            if graph not in reference:
                return False
        # Make sure that we have all reference graphs.
        for ref in reference:
            if ref not in reactant_graphs:
                return False
        return True

    def _get_reactant_masm_strings(self, reactants: List[db.ID], reactant_types: List[db.CompoundOrFlask]) -> List[str]:
        masm_strings = list()
        for a_id, a_type in zip(reactants, reactant_types):
            aggregate = get_compound_or_flask(a_id, a_type, self.compounds, self.flasks)
            centroid = db.Structure(aggregate.get_centroid(), self.structures)
            graph = centroid.get_graph("masm_cbor_graph")
            masm_strings.append(graph)
        return masm_strings

    def _check_masm_graph(self, reaction: db.Reaction) -> bool:
        reactants = reaction.get_reactants(db.Side.BOTH)
        reactant_types = reaction.get_reactant_types(db.Side.BOTH)
        lhs_references = self.lhs_selection_text.text().split()
        rhs_references = self.rhs_selection_text.text().split()
        reaction_lhs_masm_strings = self._get_reactant_masm_strings(reactants[0], reactant_types[0])
        reaction_rhs_masm_strings = self._get_reactant_masm_strings(reactants[1], reactant_types[1])
        valid_lhs_strings = True
        valid_rhs_strings = True
        if lhs_references:
            valid_lhs_strings = self._valid_graphs(lhs_references, reaction_lhs_masm_strings)
        if rhs_references:
            valid_rhs_strings = self._valid_graphs(rhs_references, reaction_rhs_masm_strings)

        if valid_rhs_strings and valid_lhs_strings:
            return True
        return valid_rhs_strings and valid_lhs_strings

    def focus(self, item, _):
        if item.childCount() > 0:
            item = item.child(0)
        step = ElementaryStep(ID(item.text(0).split('(')[1][:-1]))
        step.link(self.elementary_steps)
        if step.get_type() == ElementaryStepType.BARRIERLESS:
            ts_atoms = AtomCollection()
        else:
            ts = Structure(step.get_transition_state())
            ts.link(self.structures)
            ts_atoms = ts.get_atoms()
        lhs, rhs = step.get_reactants(db.Side.BOTH)
        lhs_atoms = []
        for lid in lhs:
            s = Structure(lid)
            s.link(self.structures)
            lhs_atoms.append(s.get_atoms())
        rhs_atoms = []
        for rid in rhs:
            s = Structure(rid)
            s.link(self.structures)
            rhs_atoms.append(s.get_atoms())
        self.parent().display_molecules(lhs_atoms, ts_atoms, rhs_atoms)

    def display_in_molecule_viewer(self, step_id: str):
        step = db.ElementaryStep(db.ID(step_id), self.elementary_steps)
        if not step.has_transition_state():
            return
        else:
            ts_id = step.get_transition_state()
            structure = db.Structure(ts_id, self.structures)
            atoms = structure.get_atoms()
            tab = get_core_tab('molecule_viewer')
            if tab is not None:
                tab.update_molecule(atoms=atoms)

    def get_reactants(self, step_id: str) -> List[str]:
        step = db.ElementaryStep(db.ID(step_id), self.elementary_steps)
        reaction = db.Reaction(step.get_reaction(), self.reactions)
        reactants = reaction.get_reactants(db.Side.BOTH)
        # return flattened list
        return [str(r_id) for side in reactants for r_id in side]


class MolecularReactionView(QTabWidget):
    def __init__(self, parent: Optional[QWidget], lhs, ts, rhs, mol_widget_cache):
        super(MolecularReactionView, self).__init__(parent)
        self.__layout = None
        self.__deleteables: List[QWidget] = []
        self.update(lhs, ts, rhs, mol_widget_cache)

    def update(self, lhs, ts, rhs, mol_widget_cache):
        if self.__layout is None:
            self.__layout = QHBoxLayout()
            self.setLayout(self.__layout)
        else:
            for i in reversed(range(self.__layout.count())):
                widget = self.__layout.itemAt(i).widget()
                widget.setParent(None)  # actually remove the widget from the gui
                self.__layout.removeWidget(widget)
            for d in self.__deleteables:
                d.close()

        def plus():
            plus = QLabel(self)
            plus.setText("+")
            plus.setFont(QFont('Arial', 20))
            return plus

        arrow_lhs = QLabel(self)
        arrow_lhs.setText("---")
        arrow_lhs.setFont(QFont('Arial', 20))
        arrow_rhs = QLabel(self)
        arrow_rhs.setFont(QFont('Arial', 20))
        arrow_rhs.setText("-->")

        mol_view_count = 0
        for i, atoms in enumerate(lhs):
            mol_widget = mol_widget_cache[mol_view_count]
            mol_widget.update_molecule(atoms=atoms)
            self.__layout.addWidget(mol_widget)
            if i < len(lhs) - 1:
                plus_widget = plus()
                self.__layout.addWidget(plus_widget)
                self.__deleteables.append(plus_widget)
            mol_view_count += 1
        self.__layout.addWidget(arrow_lhs)
        self.__deleteables.append(arrow_lhs)
        mol_widget = mol_widget_cache[mol_view_count]
        mol_widget.update_molecule(atoms=ts)
        mol_view_count += 1
        self.__layout.addWidget(mol_widget)
        self.__layout.addWidget(arrow_rhs)
        self.__deleteables.append(arrow_rhs)
        for i, atoms in enumerate(rhs):
            mol_widget = mol_widget_cache[mol_view_count]
            mol_widget.update_molecule(atoms=atoms)
            self.__layout.addWidget(mol_widget)
            if i < len(rhs) - 1:
                plus_widget = plus()
                self.__layout.addWidget(plus_widget)
                self.__deleteables.append(plus_widget)
            mol_view_count += 1

        while mol_view_count < len(mol_widget_cache):
            mol_widget = mol_widget_cache[mol_view_count]
            mol_widget.update_molecule(atoms=lhs[0])
            mol_view_count += 1


class ContentWidget(QWidget):
    def __init__(self, parent: Optional[QWidget], db_manager: Manager, aggregates: str):
        super(ContentWidget, self).__init__(parent)
        self.db_manager = db_manager
        self.__layout = QVBoxLayout()

        if aggregates == "reactions":
            self.tree = ReactionTreeWidget(self, db_manager)
        else:
            self.tree = AggregateTreeWidget(self, db_manager)
        self.__layout.addWidget(self.tree)
        self.__mol_widget_cache: List[MoleculeWidget] = [
            MoleculeWidget(
                parent=self, atoms=AtomCollection()
            )
        ]
        self.mol_widget = self.__mol_widget_cache[0]
        self.__layout.addWidget(self.mol_widget)
        self.setLayout(self.__layout)

    def display_molecule(self, structure):
        old_widget = self.mol_widget
        if len(self.__mol_widget_cache) == 0:
            self.__mol_widget_cache.append(MoleculeWidget(
                parent=self, atoms=AtomCollection()
            ))
        new_widget = self.__mol_widget_cache[0]
        new_widget.update_molecule(atoms=structure)
        self.mol_widget = new_widget
        self.__layout.replaceWidget(old_widget, new_widget)

    def display_molecules(self, lhs, ts, rhs):
        n_views = len(lhs) + 1 + len(rhs)
        for _ in range(n_views - len(self.__mol_widget_cache)):
            self.__mol_widget_cache.append(MoleculeWidget(
                parent=self, atoms=AtomCollection()
            ))
        if isinstance(self.mol_widget, MoleculeWidget):
            self.__layout.removeWidget(self.mol_widget)
            self.mol_widget = MolecularReactionView(self, lhs, ts, rhs, self.__mol_widget_cache)
            self.__layout.addWidget(self.mol_widget)
        elif isinstance(self.mol_widget, MolecularReactionView):
            self.mol_widget.update(lhs, ts, rhs, self.__mol_widget_cache)


class DatabaseViewerWidget(QWidget):
    def __init__(self, parent: Optional[QWidget], db_manager: Manager):
        super(DatabaseViewerWidget, self).__init__(parent)
        self.db_manager = db_manager

        self.__layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.aggregates_tab = ContentWidget(self, self.db_manager, "compounds")
        self.reactions_tab = ContentWidget(self, self.db_manager, "reactions")
        # Add tabs
        self.tabs.addTab(self.aggregates_tab, "Aggregates")
        self.tabs.addTab(self.reactions_tab, "Reactions")
        # Add tabs to widget
        self.__layout.addWidget(self.tabs)
        self.setLayout(self.__layout)
