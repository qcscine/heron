#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Any, List, Optional, Tuple, TYPE_CHECKING, Dict, Union
import pickle

from PySide2.QtCore import QObject
from PySide2.QtWidgets import QWidget, QDialog, QLineEdit

from scine_chemoton.filters.aggregate_filters import (
    AggregateFilter, PlaceHolderAggregateFilter
)
from scine_chemoton.filters.reactive_site_filters import (
    ReactiveSiteFilter,
)
from scine_chemoton.filters.further_exploration_filters import (
    FurtherExplorationFilter,
)
from scine_chemoton.filters.elementary_step_filters import (
    ElementaryStepFilter, PlaceHolderElementaryStepFilter
)
from scine_chemoton.filters.reaction_filters import (
    ReactionFilter, PlaceHolderReactionFilter
)
from scine_chemoton.gears.network_refinement.enabling import (
    AggregateEnabling, ReactionEnabling, EnableCalculationResults, PlaceHolderAggregateEnabling,
    PlaceHolderReactionEnabling, PlaceHolderCalculationEnabling
)
from scine_chemoton.gears.network_refinement.disabling import (
    ReactionDisabling, StepDisabling
)
from scine_chemoton.filters.structure_filters import StructureFilter
from scine_heron.chemoton.class_selection_widget import ClassSelectionWidget, SelectionState
from scine_heron.containers.combo_box_tab_widget import ComboBoxTabWidget
from scine_heron.containers.buttons import TextPushButton
from scine_heron.containers.layouts import VerticalLayout
from scine_heron.io.json_pickle_wrap import encode, decode
from scine_heron.io.file_browser_popup import get_load_file_name, get_save_file_name
from scine_heron.toolbar.io_toolbar import ToolBarWithSaveLoad
from scine_heron.utilities import write_error_message, write_info_message

if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


class AggregateFilterBuilderDialog(QDialog):

    filter_signal = Signal(AggregateFilter)
    reset_filter_signal = Signal()
    state_signal = Signal(SelectionState)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setWindowTitle("Specify Aggregate Filter")
        self._builder = FilterBuilder(parent=self, aggregate_filter_only=True)
        self._ok_button = TextPushButton("OK", self.accept, parent=self)
        self.setLayout(VerticalLayout([self._builder, self._ok_button]))

    def set_state(self, state: SelectionState) -> None:
        self._builder.set_states([state])

    def reject(self) -> None:
        self._send_signals()
        super().reject()

    def accept(self) -> None:
        self._send_signals()
        super().accept()

    def _send_signals(self) -> None:
        aggregate_filter = self._builder.get_aggregate_filter()
        if aggregate_filter is None:
            self.reset_filter_signal.emit()
        else:
            self.filter_signal.emit(aggregate_filter)
            self.state_signal.emit(self._builder.get_states()[0])


class AggregateFilterBuilderButton(TextPushButton):

    def __init__(self, parent: Optional[QWidget] = None, shortcut: Optional[str] = None) -> None:
        super().__init__("Specify Filters", self._pop_up, parent=parent, shortcut=shortcut)
        self._aggregate_filter = AggregateFilter()
        self._last_state = SelectionState()

    def get_aggregate_filter(self) -> AggregateFilter:
        return self._aggregate_filter

    def reset_filter(self) -> None:
        write_error_message("AggregateFilter could not be built")
        self._aggregate_filter = FilterBuilder.default_filters()[0]
        self._last_state = SelectionState()

    def set_aggregate_filter(self, aggregate_filter: AggregateFilter) -> None:
        self._aggregate_filter = aggregate_filter

    def set_state(self, state: SelectionState) -> None:
        self._last_state = state

    def _pop_up(self) -> None:
        dialog = AggregateFilterBuilderDialog(parent=self)
        dialog.set_state(self._last_state)
        dialog.reset_filter_signal.connect(self.reset_filter)  # pylint: disable=no-member
        dialog.filter_signal.connect(self.set_aggregate_filter)  # pylint: disable=no-member
        dialog.state_signal.connect(self.set_state)  # pylint: disable=no-member
        dialog.exec_()


class FilterBuilder(ComboBoxTabWidget):
    """
    A container widget based on tabs with each tab being a ClassSelectionWidget
    for the individual filter types.
    """

    def __init__(self, parent: Optional[QObject] = None, aggregate_filter_only: bool = False) -> None:
        """
        Construct the filter builder with currently hardcoded tabs.

        Parameters
        ----------
        parent : Optional[QObject], optional
            The parent widget, by default None
        """
        # first call super with None, then set tabs, so we can set ourselves as parent
        super().__init__(tabs=None, parent=parent)
        # save load
        self._layout.addWidget(ToolBarWithSaveLoad(self._save, self._load, parent=self))
        # hard code the tabs to be given to our parent to set them up
        self._agg_widget = ClassSelectionWidget(AggregateFilter, "filter", parent=self)
        self._tabs: Dict[str, Union[ClassSelectionWidget, QLineEdit, None]] = {
            "Aggregate Filter": self._agg_widget,
        }
        if aggregate_filter_only:
            self._site_widget: Optional[ClassSelectionWidget] = None
            self._further_widget: Optional[ClassSelectionWidget] = None
            self._structure_widget: Optional[ClassSelectionWidget] = None
            self._elementary_step_widget: Optional[ClassSelectionWidget] = None
            self._reaction_widget: Optional[ClassSelectionWidget] = None
            self._aggregate_enabling_widget: Optional[ClassSelectionWidget] = None
            self._aggregate_validation_widget: Optional[ClassSelectionWidget] = None
            self._reaction_enabling_widget: Optional[ClassSelectionWidget] = None
            self._reaction_disabling_widget: Optional[ClassSelectionWidget] = None
            self._step_disabling_widget: Optional[ClassSelectionWidget] = None
            self._reaction_validation_widget: Optional[ClassSelectionWidget] = None
            self._results_enabling_widget: Optional[ClassSelectionWidget] = None
        else:
            self._site_widget = ClassSelectionWidget(ReactiveSiteFilter, "filter", parent=self)
            self._further_widget = ClassSelectionWidget(FurtherExplorationFilter, "filter", parent=self)
            self._structure_widget = ClassSelectionWidget(StructureFilter, "filter", parent=self)
            self._elementary_step_widget = ClassSelectionWidget(ElementaryStepFilter, "filter", parent=self)
            self._reaction_widget = ClassSelectionWidget(ReactionFilter, "filter", parent=self)
            # TODO: Hide the enabling/disabling logic in the GUI for the time being
            #  because this requires the implementation of additional widgets to construct
            #  the enabling/disabling objects.
            info = QLineEdit("Not supported yet")
            info.setReadOnly(True)
            self._aggregate_enabling_widget = info
            self._aggregate_validation_widget = info
            self._reaction_enabling_widget = info
            self._reaction_disabling_widget = info
            self._step_disabling_widget = info
            self._reaction_validation_widget = info
            self._results_enabling_widget = info
            self._tabs.update({
                "Reactive Site Filter": self._site_widget,
                "Further Exploration Filter": self._further_widget,
                "Structure Filter": self._structure_widget,
                "Elementary Step Filter": self._elementary_step_widget,
                "Reaction Filter": self._reaction_widget,
                "Aggregate Enabling": self._aggregate_enabling_widget,
                "Aggregate Validation": self._aggregate_validation_widget,
                "Reaction Enabling": self._reaction_enabling_widget,
                "Results Enabling": self._results_enabling_widget,
                "Reaction Validation": self._reaction_validation_widget,
                "Reaction Disabling": self._reaction_disabling_widget,
                "Step Disabling": self._step_disabling_widget
            })
        self._aggregate_filter_only = aggregate_filter_only
        self.set_tabs(self._tabs)

    def get_states(self) -> List[SelectionState]:
        return [widget.get_state() for widget in self._tabs.values() if isinstance(widget, ClassSelectionWidget)]

    def set_states(self, states: List[SelectionState]) -> None:
        if not all(isinstance(s, SelectionState) for s in states):
            write_error_message("Could not load filters")
            return
        widgets = [widget for widget in self._tabs.values() if isinstance(widget, ClassSelectionWidget)]
        # restart
        for widget in widgets:
            widget.restart()
        # set states
        for state, widget in zip(states[:len(widgets)], widgets):
            widget.set_state(state)

    def _save(self) -> None:
        filename = get_save_file_name(self, "filters", ["json", "pkl", "pickle"])
        if filename is None:
            write_info_message("Aborted saving")
            return
        write_info_message("Writing to disk")
        states = self.get_states()
        if filename.suffix == ".json":
            with open(filename, "w") as f:
                f.write(encode(states))
        else:
            with open(filename, "wb") as f:
                pickle.dump(states, f)

    def _load(self) -> None:
        filename = get_load_file_name(self, "filters", ["json", "pkl", "pickle"])
        if filename is None:
            write_info_message("Aborted loading")
            return
        write_info_message("Reading from disk")
        if filename.suffix == ".json":
            with open(filename, "r") as f:
                states = decode(f.read())
        else:
            with open(filename, "rb") as f:
                states = pickle.load(f)
        if not isinstance(states, list) or not all(isinstance(s, SelectionState) for s in states):
            write_error_message("Could not load filters")
            return
        self.set_states(states)

    def get_reaction_filter(self) -> Optional[ReactionFilter]:
        """
        Returns
        -------
        Optional[ReactionFilter]
            The instance of the built reaction filter, None if not built.
        """
        if self._reaction_widget is None:
            return None
        return self._reaction_widget.get_instance()

    def get_elementary_step_filter(self) -> Optional[ElementaryStepFilter]:
        """
        Returns
        -------
        Optional[ElementaryStepFilter]
            The instance of the built elementary step filter, None if not built.
        """
        if self._elementary_step_widget is None:
            return None
        return self._elementary_step_widget.get_instance()

    def get_aggregate_enabling(self) -> Optional[AggregateEnabling]:
        """
        Returns
        -------
        Optional[AggregateEnabling]
            The instance of the built aggregate enabling policy, None if not built.
        """
        if self._aggregate_enabling_widget is None:
            return None
        return self._aggregate_enabling_widget.get_instance()

    def get_reaction_enabling(self) -> Optional[ReactionEnabling]:
        """
        Returns
        -------
        Optional[ReactionEnabling]
            The instance of the built reaction enabling policy, None not if not built.
        """
        if self._reaction_enabling_widget is None:
            return None
        return self._reaction_enabling_widget.get_instance()

    def get_aggregate_validation(self) -> Optional[AggregateFilter]:
        """
        Returns
        -------
        Optional[AggregateFilter]
            The instance of the built aggregate validation filter, None not if not built.
        """
        if self._aggregate_validation_widget is None:
            return None
        return self._aggregate_validation_widget.get_instance()

    def get_reaction_validation(self) -> Optional[ReactionFilter]:
        """
        Returns
        -------
        Optional[ReactionFilter]
            The instance of the built reaction validation filter, None if not built.
        """

        if self._reaction_validation_widget is None:
            return None
        return self._reaction_validation_widget.get_instance()

    def get_results_enabling(self) -> Optional[EnableCalculationResults]:
        """
        Returns
        -------
        Optional[EnableCalculationResults]
            The instance of the built results enabling policy, None not if not built.
        """
        if self._results_enabling_widget is None:
            return None
        return self._results_enabling_widget.get_instance()

    def get_reaction_disabling(self) -> Optional[ReactionDisabling]:
        """
        Returns
        -------
        Optional[ReactionDisabling]
            The reaction disabling policy, None not if not built.
        """
        if self._reaction_disabling_widget is None:
            return None
        return self._reaction_disabling_widget.get_instance()

    def get_step_disabling(self) -> Optional[StepDisabling]:
        """
        Returns
        -------
        Optional[StepDisabling]
            The step disabling policy, None not if not built.
        """
        if self._step_disabling_widget is None:
            return None
        return self._step_disabling_widget.get_instance()

    def get_aggregate_filter(self) -> Optional[AggregateFilter]:
        """
        Returns
        -------
        Optional[AggregateFilter]
            The instance of the built aggregate filter, None if currently not valid built
        """
        return self._agg_widget.get_instance()

    def get_site_filter(self) -> Optional[ReactiveSiteFilter]:
        """
        Returns
        -------
        Optional[ReactiveSiteFilter]
            The instance of the built reactive site filter, None if currently not valid built
        """
        if self._site_widget is None:
            return None
        return self._site_widget.get_instance()

    def get_further_filter(self) -> Optional[ReactiveSiteFilter]:
        """
        Returns
        -------
        Optional[ReactiveSiteFilter]
            The instance of the built further exploration filter, None if currently not valid built
        """
        if self._further_widget is None:
            return None
        return self._further_widget.get_instance()

    def get_structure_filter(self) -> Optional[StructureFilter]:
        """
        Returns
        -------
        Optional[StructureFilter]
            The instance of the built structure filter, None if currently not valid built
        """
        if self._structure_widget is None:
            return None
        return self._structure_widget.get_instance()

    def get_filters(self) -> Tuple[AggregateFilter, ReactiveSiteFilter, FurtherExplorationFilter, StructureFilter,
                                   ElementaryStepFilter, ReactionFilter, AggregateEnabling, AggregateFilter,
                                   ReactionEnabling, EnableCalculationResults, ReactionFilter, ReactionDisabling,
                                   StepDisabling]:
        """
        Returns the filters of all tabs.
        Ensures that no None instances are returned by checking the individual instances,
        writing an error message and replacing failed instances with the default super classes.

        Returns
        -------
        Tuple[AggregateFilter, ReactiveSiteFilter, FurtherExplorationFilter, StructureFilter, ElementaryStepFilter,
                ReactionFilter, AggregateEnabling, AggregateFilter, ReactionEnabling, EnableCalculationResults,
                ReactionFilter, ReactionDisabling, StepDisabling]
            The filters of all subtabs
        """
        defaults = self.default_filters()
        if self._aggregate_filter_only:
            agg_filter = self.get_aggregate_filter()
            if agg_filter is None:
                write_error_message("AggregateFilter could not be built")
            else:
                write_info_message("Only AggregateFilter is available")
            return agg_filter, *defaults[1:]  # type: ignore

        class Sentinel:
            pass

        filters = []
        for w in self._tabs.values():
            if isinstance(w, ClassSelectionWidget):
                filters.append(w.get_instance())
            elif isinstance(w, QLineEdit):
                filters.append(Sentinel)
            else:
                filters.append(None)

        for i, _filter in enumerate(filters):
            if _filter is None:
                write_error_message(f"{defaults[i].__class__.__name__} could not be built")
                filters[i] = defaults[i]
            elif _filter is Sentinel:
                filters[i] = defaults[i]
        assert None not in filters
        filter_types = [type(d) for d in defaults]
        assert len(filters) == len(filter_types)
        # todo commented out because not all base types are implemented at the moment
        # assert all(isinstance(f, t) for f, t in zip(filters, filter_types))
        return tuple(filters)  # type: ignore

    @staticmethod
    def default_filters() -> Tuple[AggregateFilter, ReactiveSiteFilter, FurtherExplorationFilter, StructureFilter,
                                   ElementaryStepFilter, ReactionFilter, AggregateEnabling, AggregateFilter,
                                   ReactionEnabling, EnableCalculationResults, ReactionFilter, ReactionDisabling,
                                   StepDisabling]:
        return AggregateFilter(), ReactiveSiteFilter(), FurtherExplorationFilter(), StructureFilter(), \
            PlaceHolderElementaryStepFilter(), PlaceHolderReactionFilter(), PlaceHolderAggregateEnabling(), \
            PlaceHolderAggregateFilter(), PlaceHolderReactionEnabling(), PlaceHolderCalculationEnabling(), \
            PlaceHolderReactionFilter(), ReactionDisabling(), StepDisabling()
