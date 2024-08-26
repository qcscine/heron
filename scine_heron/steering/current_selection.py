#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from collections import deque
from copy import deepcopy
from datetime import datetime, timedelta
from json import dumps
from threading import Event
from typing import Deque, Optional, List, Any, Tuple

from PySide2.QtWidgets import (
    QLineEdit,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QTabWidget,
    QSizePolicy,
    QTreeWidget,
)

from scine_database import Manager, Structure, ID
from scine_utilities import AtomCollection
from scine_chemoton.steering_wheel.datastructures import SelectionResult, ProtocolEntry
from scine_chemoton.steering_wheel.network_expansions import NetworkExpansion
from scine_chemoton.gears.elementary_steps import ElementaryStepGear
from scine_chemoton.gears.elementary_steps.trial_generator.fragment_based import FragmentBased
from scine_chemoton.gears.elementary_steps.trial_generator.bond_based import BondBased
from scine_chemoton.utilities.reactive_complexes.inter_reactive_complexes import assemble_reactive_complex
from scine_chemoton.utilities.datastructure_transfer import make_picklable

from scine_heron.chemoton.chemoton_widget import generate_gear_name_settings_suggestions
from scine_heron.chemoton.class_searcher import ChemotonClassSearcher
from scine_heron.chemoton.filter_builder import FilterBuilder
from scine_heron.chemoton.grouped_combo_box import GroupedComboBox
from scine_heron.settings.class_options_widget import generate_instance_based_on_potential_widget_input

from scine_heron.containers.progress_bar import HeronProgressBar
from scine_heron.containers.start_stop_widget import StartStopWidget
from scine_heron.containers.wrapped_label import WrappedLabel
from scine_heron.containers.buttons import TextPushButton
from scine_heron.containers.layouts import VerticalLayout
from scine_heron.utilities import (
    write_error_message,
    vertical_scroll_area_wrap,
    write_info_message,
    timedelta_string
)

from .display_widget import SteeringDisplay
from .structure_display import StructureWithReactiveSites
from .tree_items import TreeWidget, TreeWidgetItem
from .selection_threads import UnimolecularThread, BimolecularThread, UnimolecularCoordinates, BimolecularCoordinates


class CurrentSelectionDisplay(StartStopWidget):
    """
    The widget displaying the current selection.

    Notes
    -----
    It inherits from StartStopWidget, because we want to pass it to the ChemotonWidgetContainer,
    but it does not really implement any abstract methods, because these are not meant to be called
    for this widget.
    """

    def __init__(self, parent: SteeringDisplay, db_manager: Optional[Manager] = None,
                 selection: Optional[SelectionResult] = None, name: Optional[str] = None):
        super().__init__(parent=parent)
        label = QLabel("Display of current selection")
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(label)
        if name is not None:
            name_label = WrappedLabel(name)
            self._layout.addWidget(name_label)

        self._selection = selection
        self._manager = db_manager
        if self._selection is None or self._manager is None:
            return
        self._selection.aggregate_filter.initialize_collections(self._manager)
        self._selection.reactive_site_filter.initialize_collections(self._manager)
        self._selection.further_exploration_filter.initialize_collections(self._manager)
        self._set_filter_info()
        self._content = vertical_scroll_area_wrap(SelectionContentWidget(self, self._manager, self._selection, parent))
        self._content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._layout.addWidget(self._content)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    @classmethod
    def with_loading_info(cls, parent: SteeringDisplay):
        """
        Constructs a dummy widget that tells the user that we are currently constructing the widget.

        Notes
        -----
        Since the introduction of the update button, the load time is very short and this is not required
        any more. Can be removed when refactoring the update logic to avoid too many molecular widgets.
        (See SteeringDisplay.construct_new_current_selection_widget docs)

        Parameters
        ----------
        parent : SteeringDisplay
            The parent widget holding this widget

        Returns
        -------
        CurrentSelectionDisplay
            The dummy widget
        """
        inst = cls(parent=parent)
        query_info = QLineEdit("Loading current selection...")
        query_info.setReadOnly(True)
        inst.layout().addWidget(query_info)
        return inst

    def _set_filter_info(self):
        """
        Writes the filter information
        """
        filter_defaults = FilterBuilder.default_filters()
        for default, set_filter in zip(filter_defaults, [self._selection.aggregate_filter,
                                                         self._selection.reactive_site_filter,
                                                         self._selection.further_exploration_filter]):
            # ensure that comparison is made by explicit type equals and not 'isinstance' due to inheritance
            default_type = type(default)
            filter_type = type(default)
            if filter_type != default_type:
                self._add_filter_at_layout(set_filter.name)

    def join(self, force_join: bool = False) -> None:
        """
        Dummy abstract method overload, not meant to be called
        """

    def start_stop(self, start_all: bool = False, stop_all: bool = False) -> None:
        """
        Dummy abstract method overload, not meant to be called
        """

    def set_docstring_dict(self, doc_string_parser: Any) -> None:
        """
        Dummy abstract method overload, not meant to be called
        """

    def stop_class_if_working(self) -> None:
        """
        Dummy abstract method overload, not meant to be called
        """


class SelectionContentWidget(QWidget):
    """
    This widget displays and handles most of the current selection display.
    It is meant to be held by the CurrentSelectionWidget and wrapped by a vertical scrollbar.
    """

    def __init__(self, parent: CurrentSelectionDisplay, db_manager: Manager, selection_result: SelectionResult,
                 total_display: SteeringDisplay):
        """
        Construct the widget with parent, database, and selection information.
        The database is required because we query it to find out what possible network expansion would set up.

        Parameters
        ----------
        parent : CurrentSelectionDisplay
            The CurrentSelectionWidget that holds us
        db_manager : Manager
            The manager of the Scine Database
        selection_result : SelectionResult
            The selection result this widget represents
        total_display : SteeringDisplay
            The steering tab widget, currently only required for the model.
        """
        super().__init__(parent)
        self.setMaximumHeight(750)
        self._total_display = total_display
        # propagate db information
        self._manager = db_manager
        self._credentials = db_manager.get_credentials()
        self._structure_collection = db_manager.get_collection("structures")
        self._compound_collection = db_manager.get_collection("compounds")
        self._flask_collection = db_manager.get_collection("flasks")
        self._selection_result = selection_result
        self._selection_result.aggregate_filter.initialize_collections(db_manager)
        self._selection_result.reactive_site_filter.initialize_collections(db_manager)
        self._selection_result.further_exploration_filter.initialize_collections(db_manager)

        # set up tabs
        self._uni_tab = SelectionTab(self)
        self._bi_tab = SelectionTab(self)
        self._structure_tab = SelectionTab(self)
        self._uni_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._bi_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._structure_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._tabs = QTabWidget(self)
        self._tabs.addTab(self._uni_tab, "Unimolecular")
        self._tabs.addTab(self._bi_tab, "Bimolecular")
        self._tabs.addTab(self._structure_tab, "Lone Structures")
        self._tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # get DB data
        self._lone_structures = self._gather_lone_structures()

        # set up potential next steps interface
        self._potential_next_step: Optional[NetworkExpansion] = None
        self._step_searcher = ChemotonClassSearcher(NetworkExpansion)
        self._chemical_step_box = GroupedComboBox(self, self._step_searcher)
        self._progress_bar = HeronProgressBar(self)
        self._site_settings_button = TextPushButton("Update", self.update_content, self)
        self._runtime_of_update = datetime.now()
        self._runtime_memory: Deque[timedelta] = deque([], maxlen=5)

        # update handling
        self._uni_update_thread: Optional[UnimolecularThread] = None
        self._bi_update_thread: Optional[BimolecularThread] = None
        self._finished_uni_update = Event()
        self._finished_bi_update = Event()
        self._uni_items: List[TreeWidgetItem] = []
        self._is_updating = False

        # put everything into a layout
        self._layout = VerticalLayout([
            self._chemical_step_box,
            self._progress_bar,
            self._site_settings_button,
            self._tabs
        ])
        self.setLayout(self._layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def closeEvent(self, event):
        """
        Overload of the close event to ensure that the update threads are stopped.
        """
        self._cleanup_threads(active_stop=True)
        super().closeEvent(event)

    def _cleanup_threads(self, active_stop: bool = False) -> None:
        """
        Wait for update threads and join them.
        """
        # clear events for next run
        self._finished_uni_update.clear()
        self._finished_bi_update.clear()
        self._uni_items = []
        self._runtime_of_update = datetime.now()
        self._runtime_memory.clear()
        if self._uni_update_thread is not None:
            if active_stop:
                self._uni_update_thread.stop()
            self._uni_update_thread.wait()
            self._uni_update_thread = None
        if self._bi_update_thread is not None:
            if active_stop:
                self._bi_update_thread.stop()
            self._bi_update_thread.wait()
            self._bi_update_thread = None

    def _start_threads(self, potential_next_step: NetworkExpansion, selection: SelectionResult) -> None:
        """
        Starts the threads that gather the information about all uni- and bimolecular complexes set up with the
        given potential next exploration step.

        Parameters
        ----------
        potential_next_step : NetworkExpansion
            The potential next exploration step for which the complexes are gathered.
        selection : SelectionResult
            The selection result onto which the potential expansion should work on
        """
        self._cleanup_threads()

        # prepare transfer
        safe_step = make_picklable(potential_next_step)
        safe_selection = make_picklable(selection)
        if not isinstance(safe_step, NetworkExpansion):
            raise RuntimeError("Could not pickle potential next step")
        if not isinstance(safe_selection, SelectionResult):
            raise RuntimeError("Could not pickle selection result")
        assert deepcopy(safe_step)
        assert deepcopy(safe_selection)

        # construct threads
        self._uni_update_thread = UnimolecularThread(self, self._credentials, deepcopy(safe_step),
                                                     deepcopy(safe_selection))
        self._bi_update_thread = BimolecularThread(self, self._credentials, deepcopy(safe_step),
                                                   deepcopy(safe_selection))

        # signals that both have
        self._uni_update_thread.final_count_signal.connect(lambda count:  # pylint: disable=no-member
                                                           self._finish_update(0, count))
        self._uni_update_thread.info_message_signal.connect(write_info_message)  # pylint: disable=no-member
        self._uni_update_thread.error_message_signal.connect(write_error_message)  # pylint: disable=no-member
        self._uni_update_thread.loop_signal.connect(self._increase_progress_bar)  # pylint: disable=no-member

        self._bi_update_thread.final_count_signal.connect(lambda count:  # pylint: disable=no-member
                                                          self._finish_update(1, count))
        self._bi_update_thread.info_message_signal.connect(write_info_message)  # pylint: disable=no-member
        self._bi_update_thread.error_message_signal.connect(write_error_message)  # pylint: disable=no-member
        self._bi_update_thread.loop_signal.connect(self._increase_progress_bar)  # pylint: disable=no-member

        # uni signals
        self._uni_update_thread.single_structure_no_sites_signal.connect(  # pylint: disable=no-member
            self._add_uni_item
        )
        self._uni_update_thread.coordinates_signal.connect(self._fill_unimolecular)  # pylint: disable=no-member

        # bi signals
        self._bi_update_thread.coordinates_signal.connect(self._fill_bimolecular)  # pylint: disable=no-member

        # start
        self._uni_update_thread.start()
        self._bi_update_thread.start()

    def _add_uni_item(self, name: str, atoms: AtomCollection) -> None:
        """
        Builds a TreeWidgetItem with the given name and atoms and adds it to our container, which
        we add at once when we receive the finish signal.

        Parameters
        ----------
        name : str
            The name of the item.
        atoms : AtomCollection
            The atoms shown in the item
        """
        self._uni_items.append(TreeWidgetItem(self._uni_tab.tree, [name], atoms, []))

    def _fill_unimolecular(self, coordinates: UnimolecularCoordinates) -> None:
        total_count = 0
        for cid, sub_dict in coordinates.data.items():
            for sid, coords in sub_dict.items():
                if self._selection_result.structures and ID(sid) not in self._selection_result.structures:
                    continue
                total_count += self._single_structure_add(sid, self._uni_tab, cid, coords)
        self._finish_update(0, total_count)

    def _fill_bimolecular(self, coordinates_holder: BimolecularCoordinates) -> None:
        # we have to set up the protocol here, because the setup for the coordinates was done in a different process
        if self._potential_next_step is None:
            raise RuntimeError("No potential next expansion step set up")
        self._potential_next_step.dry_setup_protocol(self._credentials, self._selection_result)
        items = []
        total_count = 0
        for cid, sub_dict in coordinates_holder.data.items():
            compound_a, compound_b = cid.split("-")
            individual_indices: List[List[int]] = []
            individual_complexes: List[AtomCollection] = []
            individual_structure_pairs: List[List[str]] = []
            for sid, coords in sub_dict.items():
                structure_list = [Structure(ID(s), self._structure_collection) for s in sid.split("-")]
                if self._selection_result.structures and not all(ID(s) in self._selection_result.structures
                                                                 for s in sid.split("-")):
                    continue
                structure_a = structure_list[0]
                structure_b = structure_list[1]
                atoms_a = structure_a.get_atoms()
                atoms_b = structure_b.get_atoms()
                n_atoms_lhs = len(atoms_a)
                complex_index = 0
                for (coordinates, _), complexes in coords.items():
                    lhs: List[int] = []
                    rhs: List[int] = []
                    intra_total: List[int] = []
                    for pair in coordinates:
                        self._map_indices(lhs, rhs, intra_total, pair, n_atoms_lhs)
                    if complexes:
                        for complex in complexes:
                            complex_index = complex_index + 1
                            atoms, lhs, shifted_rhs = assemble_reactive_complex(atoms_a, atoms_b, lhs, rhs, *complex)
                            this_indices = lhs + shifted_rhs + intra_total
                            individual_indices.append(this_indices)
                            individual_complexes.append(atoms)
                            individual_structure_pairs.append([str(structure_a.id()), str(structure_b.id())])
                            assert all(s < len(atoms) for s in this_indices)
            if individual_indices and individual_complexes:
                total_indices = self.flatten_and_deduplicate_list(individual_indices)
                total_atoms = individual_complexes[0]
                top_item = TreeWidgetItem(self._bi_tab.tree, [f"Compounds ({compound_a}-{compound_b})"],
                                          total_atoms, total_indices)
                for i, (indices, complex_atoms, structure_pair) in \
                        enumerate(zip(individual_indices, individual_complexes, individual_structure_pairs)):
                    total_count += 1
                    TreeWidgetItem(top_item, ["Structures (\n\t" + '-\n\t'.join(s for s in structure_pair) +
                                              "\n\t_coordinate_" + str(i) + "\n)"],
                                   complex_atoms, indices)
                items.append(top_item)
        self._bi_tab.tree.insertTopLevelItems(0, items)
        self._finish_update(1, total_count)

    def _fill_structures(self) -> None:
        """
        Fills the tab with structures without an aggregate.
        Pretty fast and easy, because we gather the structures already in the constructor,
        because they don't change between different network expansion steps.
        """
        total_count = 0
        for sid in self._lone_structures:
            total_count += 1
            total_count += self._single_structure_add(sid, self._structure_tab)
        self._structure_tab.set_count(total_count)

    def _finish_update(self, index: int, count: int, active_stop: bool = False) -> None:
        """
        Handles the finishing of an update thread.
        """
        if index == 0:
            self._finished_uni_update.set()
            self._uni_tab.set_count(count)
            if self._uni_items:
                self._uni_tab.tree.insertTopLevelItems(0, self._uni_items)
                self._uni_items = []
                self._tabs.setCurrentIndex(0)
        elif index == 1:
            self._finished_bi_update.set()
            self._bi_tab.set_count(count)
            if count:
                self._tabs.setCurrentIndex(1)
        else:
            raise RuntimeError(f"Invalid index {index}")
        if self._finished_uni_update.is_set() and self._finished_bi_update.is_set():
            self._cleanup_threads(active_stop=active_stop)
            self._fill_progress_bar()
            self._site_settings_button.setText("Update")
            self._site_settings_button.setEnabled(True)
            self._is_updating = False
            self.updateGeometry()

    def update_content(self) -> None:
        """
        Update function that queries the database to build the reactive complexes and fills our tabs.
        This function may take some time.
        """
        if self._is_updating:
            write_info_message("Aborted preview")
            self._clear_and_terminate()
            return
        self._is_updating = True
        self._site_settings_button.setText("Abort")
        name = self._chemical_step_box.currentText().strip()

        model = self._total_display.get_model()
        predefined_kwargs = {
            "model": model,
        }
        # first create a dummy expansion from which we get the gears it will put in its protocol, so we can
        # give proper suggestions for the gear options
        dummy_step = self._step_searcher[name](**predefined_kwargs)
        dummy_step.dry_setup_protocol(self._credentials, self._selection_result)
        suggestions = generate_gear_name_settings_suggestions(dummy_step.current_gears())
        self._potential_next_step = \
            generate_instance_based_on_potential_widget_input(self, self._step_searcher[name], predefined_kwargs,
                                                              suggestions)
        dummy_step.protocol = []  # make sure we delete forked objects
        try:
            self._potential_next_step.dry_setup_protocol(self._credentials, self._selection_result)
            selection = {"exploration_disabled": {"$ne": True}}
            if hasattr(self._potential_next_step, "options") \
                    and getattr(self._potential_next_step.options, "react_flasks", False):
                self._progress_bar.setMaximum(max(2 * self._flask_collection.count(dumps(selection)), 1))
            else:
                self._progress_bar.setMaximum(max(2 * self._compound_collection.count(dumps(selection)), 1))
            self._progress_bar.setValue(0)
            self._progress_bar.setTextVisible(True)
            self._fill_tabs()
        except BaseException as e:
            import traceback
            traceback.print_exc()
            write_error_message(str(e))
            self._clear_and_terminate()

    def _clear_and_terminate(self) -> None:
        self._clear_tabs()
        self._progress_bar.setToolTip("Aborted")
        if not self._finished_uni_update.is_set():
            self._finished_uni_update.set()
            self._finish_update(0, 0, active_stop=True)
        if not self._finished_bi_update.is_set():
            self._finished_bi_update.set()
            self._finish_update(1, 0, active_stop=True)

    def _increase_progress_bar(self) -> None:
        current_value = self._progress_bar.value()
        max_value = self._progress_bar.maximum()
        self._progress_bar.setValue(current_value + 1)
        self._progress_bar.setToolTip(f"{int((current_value + 1) * 100 / max_value)} % finished")
        interval = 10
        if (current_value % interval) == 0:
            if current_value > (max_value / 2):
                self._runtime_memory.append(datetime.now() - self._runtime_of_update)
                if len(self._runtime_memory) == self._runtime_memory.maxlen:
                    # calculate remaining time
                    average_time = sum([t.total_seconds() for t in self._runtime_memory]) / self._runtime_memory.maxlen
                    remaining_time_steps = (max_value - current_value) / interval
                    remaining_time = average_time * remaining_time_steps
                    self._site_settings_button.setText(f"Abort (est. time left "
                                                       f"{timedelta_string(timedelta(seconds=remaining_time))})")
            self._runtime_of_update = datetime.now()

    def _fill_progress_bar(self) -> None:
        self._progress_bar.setValue(self._progress_bar.maximum())

    def _fill_tabs(self) -> None:
        """
        The main updating function that takes the most time, but the two time intensive tabs are threaded away.
        """
        self._clear_tabs()
        if self._potential_next_step is None:
            raise RuntimeError("No potential next expansion step set up")
        self._potential_next_step.protocol.clear()  # we clear here, because we have to transfer across
        self._start_threads(self._potential_next_step, self._selection_result)
        self._fill_structures()

    def _clear_tabs(self) -> None:
        """
        Clears all sub tabs
        """
        self._uni_tab.clear()
        self._bi_tab.clear()
        self._structure_tab.clear()

    def _map_indices(self, lhs_to_add_to: List[int], rhs_to_add_to: List[int], intra_to_add_to: List[int],
                     pair: Tuple[int, int], n_atoms_lhs: int) -> None:
        """
        This is a utility method that ensures indexing consistency that is required,
        because Chemoton has a varying API logic for its indices for bimolecular cases.

        Parameters
        ----------
        lhs_to_add_to : List[int]
            The list of left-hand-side indices we add indices to
        rhs_to_add_to : List[int]
            The list of right-hand-side indices we add indices to
        intra_to_add_to : List[int]
            The list of intramolecular indices we add indices to
        pair : Tuple[int, int]
            The reactive indices
        n_atoms_lhs : int
            The number of atoms of the left-hand-side structure

        Raises
        ------
        NotImplementedError
            Multiple elementary step gears with different TrialGenerators
        NotImplementedError
            An unknown TrialGenerator
        RuntimeError
            No gear with a TrialGenerator present
        """
        # find out TrialGenerator
        trial_generator = None
        assert self._potential_next_step is not None
        for entry in self._potential_next_step.protocol:
            if not isinstance(entry, ProtocolEntry):
                continue
            if isinstance(entry.gear, ElementaryStepGear):
                if entry.gear.options.enable_bimolecular_trials:
                    if trial_generator is None:
                        trial_generator = entry.gear.trial_generator
                    elif not issubclass(type(trial_generator), type(entry.gear.trial_generator)) \
                            and not issubclass(type(entry.gear.trial_generator), type(trial_generator)):
                        raise NotImplementedError("Varying Trial Generator currently not supported")
        if trial_generator is None:
            raise RuntimeError("Could not determine Trial Generator")

        # fill in lists depending on TrialGenerator
        if isinstance(trial_generator, FragmentBased):
            assert not any(p >= n_atoms_lhs for p in pair)
            lhs_to_add_to.append(pair[0])
            rhs_to_add_to.append(pair[1])
        elif isinstance(trial_generator, BondBased):
            p1 = pair[0]
            p2 = pair[1]
            if p1 >= n_atoms_lhs > p2:
                lhs_to_add_to.append(p2)
                rhs_to_add_to.append(p1 - n_atoms_lhs)
            elif p2 >= n_atoms_lhs > p1:
                lhs_to_add_to.append(p1)
                rhs_to_add_to.append(p2 - n_atoms_lhs)
            else:
                intra_to_add_to.append(p1)
                intra_to_add_to.append(p2)
        else:
            raise NotImplementedError(f"Trial Generator {type(trial_generator)} currently not supported")

    def _single_structure_add(self, structure_id: str, tab_to_add_to: QTreeWidget, compound_id: Optional[str] = None,
                              coordinates: Optional[List[Tuple[List[List[Tuple[int, int]]], int]]] = None) -> int:
        """
        Adds a single structure to a tab.

        Parameters
        ----------
        structure_id : str
            The ID of the structure as a string
        tab_to_add_to : TreeWidget
            The tab we want to add to, type hint in code is not explicit due to circular dependency
        compound_id : Optional[str], optional
            The compound ID the structure belongs to as a string, by default None
        coordinates : Optional[List[Tuple[List[List[Tuple[int, int]]], int]]], optional
            Reactive coordinates already cleaned by index mapping, by default None.
            If not given, only a top level item is added and no reactive complexes with reactive indices are shown.

        Returns
        -------
        int
            The number of structures (i.e. individual subitems)
        """
        total_count = 0
        structure = Structure(ID(structure_id), self._structure_collection)
        if coordinates is None or not structure.has_graph("masm_cbor_graph") \
                or not structure.has_graph("masm_idx_map"):
            top_item = TreeWidgetItem(tab_to_add_to.tree, [f"Structure ({structure_id})"], structure.get_atoms(), [])
        else:
            individual_indices: List[List[int]] = []
            for coords, _ in coordinates:
                for pairs in coords:
                    this_indices: List[int] = []
                    for pair in pairs:
                        this_indices.append(pair[0])
                        this_indices.append(pair[1])
                    individual_indices.append(this_indices)
            total_indices = self.flatten_and_deduplicate_list(individual_indices)
            if not total_indices:
                # no reaction possible with this, so we don't show it
                return 0
            atoms = structure.get_atoms()
            top_item = TreeWidgetItem(tab_to_add_to.tree, [f"Compound ({compound_id})"],
                                      atoms, total_indices)
            for count, indices in enumerate(individual_indices):
                total_count += 1
                TreeWidgetItem(top_item, [f"Structure ({structure_id}_coordinate_{count}"],
                               atoms, indices)
        tab_to_add_to.tree.insertTopLevelItems(0, [top_item])
        return total_count

    def _gather_lone_structures(self) -> List[str]:
        """
        Identifies all the individual structures in the given selection result, that don't have an aggregate.

        Returns
        -------
        List[str]
            The IDs of the structures as strings
        """
        lone_structures: List[str] = []
        if self._selection_result.structures:
            for sid in self._selection_result.structures:
                structure = Structure(sid, self._structure_collection)
                if not structure.has_aggregate():
                    lone_structures.append(str(sid))
        return lone_structures

    @staticmethod
    def flatten_and_deduplicate_list(list_of_lists: List[List[int]]) -> List[int]:
        """
        Utility function to flatten list of lists and deduplicate the resulting list.
        """
        return list(set([index for sublist in list_of_lists for index in sublist]))


class SelectionTab(QWidget):
    """
    The widget that represents a tab and contains the selection tree and the molecule viewer.
    """

    def __init__(self, parent: Optional[QWidget]) -> None:
        super().__init__(parent)
        count_layout = QHBoxLayout()
        count_label = QLabel("Total job count:")
        self._count_edit = QLineEdit("0")
        self._count_edit.setReadOnly(True)
        count_layout.addWidget(count_label)
        count_layout.addWidget(self._count_edit)
        self.tree = TreeWidget(parent=self)
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self._mol_widget = StructureWithReactiveSites(parent=self)

        self._layout = QVBoxLayout()
        self._layout.addLayout(count_layout)
        self._layout.addWidget(self.tree)
        self._layout.addWidget(self._mol_widget)
        self.setLayout(self._layout)

    def set_count(self, count: int) -> None:
        """
        Set the count display
        """
        self._count_edit.setText(str(count))

    def display_atoms_with_sites(self, atoms: AtomCollection, indices: List[int]) -> None:
        """
        Plug in new structure and reactive sites.

        Parameters
        ----------
        atoms : AtomCollection
            The new structure
        indices : List[int]
            The new reactive indices
        """
        self._mol_widget.update_structure(atoms, indices)

    def reset_camera(self):
        """
        Reset the camera in the molecular viewer
        """
        self._mol_widget.reset_camera()

    def clear(self) -> None:
        """
        Clear everything the tab is holding
        """
        self.tree.clear()
        self._count_edit.setText("0")
        self._mol_widget.clear()
