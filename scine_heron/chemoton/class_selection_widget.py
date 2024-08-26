#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from dataclasses import dataclass, field
from inspect import isabstract
from typing import Any, List, Optional, Dict, Type, Tuple
from enum import Enum
from PySide2.QtWidgets import (
    QWidget,
    QGridLayout,
    QLabel,
    QVBoxLayout,
)

import numpy as np
# filters
from scine_chemoton.filters.aggregate_filters import (
    AggregateFilter,
    AggregateFilterAndArray,
    AggregateFilterOrArray,
)
from scine_chemoton.filters.reactive_site_filters import (
    ReactiveSiteFilter,
    ReactiveSiteFilterAndArray,
    ReactiveSiteFilterOrArray,
)
from scine_chemoton.filters.further_exploration_filters import (
    FurtherExplorationFilter,
    FurtherExplorationFilterAndArray,
    FurtherExplorationFilterOrArray,
)
from scine_chemoton.filters.elementary_step_filters import (
    ElementaryStepFilter,
    ElementaryStepFilterAndArray,
    ElementaryStepFilterOrArray
)
from scine_chemoton.filters.reaction_filters import (
    ReactionFilter,
    ReactionFilterAndArray,
    ReactionFilterOrArray
)
from scine_chemoton.filters.structure_filters import (
    StructureFilter,
    StructureFilterAndArray,
    StructureFilterOrArray,
)
# rule sets
from scine_chemoton.reaction_rules.distance_rules import (
    DistanceBaseRule,
    DistanceRuleAndArray,
    DistanceRuleOrArray,
)
from scine_chemoton.reaction_rules.polarization_rules import (
    PolarizationBaseRule,
    PolarizationRuleAndArray,
)

from scine_heron.chemoton.class_searcher import ChemotonClassSearcher
from scine_heron.chemoton.grouped_combo_box import GroupedComboBox
from scine_heron.containers.buttons import TextPushButton
from scine_heron.utilities import write_error_message, write_info_message


class _CombinationLogical(Enum):
    """
    Allows to control if the combination is a logical 'and' or 'or'
    """
    AND = "and"
    OR = "or"


@dataclass
class SelectionState:
    build_text: str = field(default="")
    class_instances_without_logicals: List[Any] = field(default_factory=list)
    current_open_logics: List[_CombinationLogical] = field(default_factory=list)
    last_closed_logical: Optional[_CombinationLogical] = field(default=None)


class ClassSelectionWidget(QWidget):
    """
    A class that allows to select classes of a certain type and combine them with
    'and' or 'or' logic, display the building process as a string based on the class
    names and then constructs the built object if requested.

    Notes
    -----
    * Currently assumes that the given class is not wanted to be selected, but only its subclasses.
    * The combination logic corresponding classes need to be added in the constructor
    to work for the corresponding classes (e.g., AggregateFilterAndArray for AggregateFilter),
    otherwise the logical combinations are simply forbidden.
    """

    def __init__(self, class_to_select: Type, class_description: str, parent: Optional[QWidget] = None):
        """
        Construct the widget based on a class type and a description.

        Parameters
        ----------
        class_to_select : Type
            The base class that we want to build
        class_description : str
            A well readable description of the class, mostly used for error messages.
        parent : Optional[QWidget], optional
            The parent widget, by default None
        """
        super().__init__(parent)
        self._class_description = class_description
        self._build_text: str = ""
        self._class_instances_without_logicals: List[Any] = []
        self._current_open_logics: List[_CombinationLogical] = []
        self._last_closed_logical: Optional[_CombinationLogical] = None

        self._logical_class_translation: Dict[Tuple[_CombinationLogical, Type], Type] = {
            (_CombinationLogical.AND, AggregateFilter): AggregateFilterAndArray,
            (_CombinationLogical.OR, AggregateFilter): AggregateFilterOrArray,
            (_CombinationLogical.AND, ReactiveSiteFilter): ReactiveSiteFilterAndArray,
            (_CombinationLogical.OR, ReactiveSiteFilter): ReactiveSiteFilterOrArray,
            (_CombinationLogical.AND, FurtherExplorationFilter): FurtherExplorationFilterAndArray,
            (_CombinationLogical.OR, FurtherExplorationFilter): FurtherExplorationFilterOrArray,
            (_CombinationLogical.AND, ElementaryStepFilter): ElementaryStepFilterAndArray,
            (_CombinationLogical.OR, ElementaryStepFilter): ElementaryStepFilterOrArray,
            (_CombinationLogical.AND, ReactionFilter): ReactionFilterAndArray,
            (_CombinationLogical.OR, ReactionFilter): ReactionFilterOrArray,
            (_CombinationLogical.AND, StructureFilter): StructureFilterAndArray,
            (_CombinationLogical.OR, StructureFilter): StructureFilterOrArray,
            (_CombinationLogical.AND, DistanceBaseRule): DistanceRuleAndArray,
            (_CombinationLogical.OR, DistanceBaseRule): DistanceRuleOrArray,
            (_CombinationLogical.AND, PolarizationBaseRule): PolarizationRuleAndArray,
        }
        skip_logic_buttons = not any(issubclass(class_to_select, k[1]) for k in self._logical_class_translation)

        black_list = []
        # add logical combinations to blacklist if they exist
        for logic in [_CombinationLogical.AND, _CombinationLogical.OR]:
            combination = self._logical_class_translation.get((logic, class_to_select))
            if combination is not None:
                black_list.append(combination)

        if class_to_select is ReactiveSiteFilter:
            black_list.append(FurtherExplorationFilter)  # FurtherFilter inherits from ReactiveSite

        self._searcher = ChemotonClassSearcher(class_to_select, black_list, avoid_exact_match=True)

        self._layout = QVBoxLayout(self)

        # buttons
        if not skip_logic_buttons:
            self._button_begin_and = TextPushButton("Begin logical And",
                                                    lambda: self._start_logical(_CombinationLogical.AND))
            self._button_begin_or = TextPushButton("Begin logical Or",
                                                   lambda: self._start_logical(_CombinationLogical.OR))
            self._button_end_and = TextPushButton("End logical And",
                                                  lambda: self._end_logical(_CombinationLogical.AND))
            self._button_end_or = TextPushButton("End logical Or",
                                                 lambda: self._end_logical(_CombinationLogical.OR))

            button_grid = QGridLayout()
            button_grid.addWidget(self._button_begin_and, 0, 0)
            button_grid.addWidget(self._button_end_and, 0, 1)
            button_grid.addWidget(self._button_begin_or, 1, 0)
            button_grid.addWidget(self._button_end_or, 1, 1)
            self._button_holder_widget = QWidget()
            self._button_holder_widget.setLayout(button_grid)
            self._layout.addWidget(self._button_holder_widget)

            # back button
            self._button_remove = TextPushButton("Remove last addition", self._remove_last)
            self._layout.addWidget(self._button_remove)

        # wipe button
        self._button_wipe = TextPushButton("Restart", self.restart)
        self._layout.addWidget(self._button_wipe)

        # class selection
        self._class_label = QLabel(f"{class_description}:", parent=self)
        self._class_box = GroupedComboBox(self, self._searcher)
        self._button_set_class = TextPushButton(f"Add {class_description}",
                                                lambda: self._add_instance(self._class_box.currentText().strip()),
                                                parent=self)
        self._layout.addWidget(self._class_label)
        self._layout.addWidget(self._class_box)
        self._layout.addWidget(self._button_set_class)

        # display
        self._display_label = QLabel("Current build:", parent=self)
        self._display = QLabel("", parent=self)
        self._display.setWordWrap(True)

        self._layout.addWidget(self._display_label)
        self._layout.addWidget(self._display)

        # verification button
        self._button_check = TextPushButton("Verify input", self.is_valid)  # type: ignore
        self._layout.addWidget(self._button_check)

        self.setLayout(self._layout)

    def _start_logical(self, logic: _CombinationLogical) -> None:
        """
        Start a logical bracket if sanity checks are passed.

        Parameters
        ----------
        logic : _CombinationLogical
            The logical operation that is started
        """
        if not self._current_open_logics and self._build_text:
            # we already have some instance(s), but no current logics to combine something, so it is too late to start
            write_error_message(f"You have already added a {self._class_description.lower()} "
                                f"and cannot start a logic operation only now")
            return
        if (logic, self._searcher.search_type) not in self._logical_class_translation:
            write_error_message(f"Cannot combine {self._searcher.search_type.__name__} with '{logic.value}' operation")
            return
        self._current_open_logics.append(logic)
        self._build_text_addition(f"{logic.value}(")

    def _end_logical(self, logic: _CombinationLogical) -> None:
        """
        End a logical bracket, if sanity checks are passed.

        Parameters
        ----------
        logic : _CombinationLogical
            The logical operation that is ended
        """
        if not self._current_open_logics or self._current_open_logics[-1] != logic:
            write_error_message(f"'{logic.value}' is not the currently open logical bracket.")
            return
        if self.build_text[-1] == "(":
            # we close, but just opened something, remove previous
            write_info_message("Removing opened logical operation")
            self._remove_last()
            self._current_open_logics.pop(-1)
        else:
            self._build_text_addition(")")
            self._last_closed_logical = self._current_open_logics.pop(-1)

    @property
    def build_text(self) -> str:
        """
        The description of the current build

        Returns
        -------
        str
            The build text
        """
        return self._build_text

    @build_text.setter
    def build_text(self, new_text: str):
        """
        Change the text of the current build, both internally and of the displayed box.

        Parameters
        ----------
        new_text : str
            The new build text.
        """
        self._build_text = new_text
        self._display.setText(self._build_text)

    def _build_text_addition(self, add: str):
        """
        Add something to the build text.

        Notes
        -----
        Does some additional padding based on brackets and commata.

        Parameters
        ----------
        add : str
            The added text.
        """
        if not self._build_text or self._build_text[-1] == "(" or add == ")":
            new_text = self._build_text + add
        else:
            new_text = self._build_text + f", {add}"
        self.build_text = new_text

    def _remove_last(self):
        """
        Removes the last logical or class that was added to the build.
        """
        chars = ['(', ')', ',']
        if not self._build_text:
            write_error_message("You have not added anything yet")
        elif self._build_text and self._build_text[-1] == ")":
            # just closed a logical, so simply remove bracket, and no class instances
            self.build_text = self._build_text[:-1]
            if self._last_closed_logical is None:
                write_error_message("Failed to remove last addition, wiping everything")
                self.restart()
            else:
                self._current_open_logics.append(self._last_closed_logical)
                # this can make problems with multiple deletes, but will likely just trigger a restart
                self._last_closed_logical = None
        # test for logical start at the end; -1 because of openeing bracket
        elif self.build_text[-4:-1] == _CombinationLogical.AND.value:
            self.build_text = self.build_text[:-4]
            self._current_open_logics.pop(-1)
        elif self.build_text[-3:-1] == _CombinationLogical.OR.value:
            self.build_text = self.build_text[:-3]
            self._current_open_logics.pop(-1)
        elif not self._class_instances_without_logicals:
            # we got no logical start and we also don't have a class instance, something is weird
            write_error_message("Failed to remove last addition, wiping everything")
            self.restart()
        elif len(self._class_instances_without_logicals) == 1 and not any(c in self._build_text for c in chars):
            # we got exactly one class and no logicals
            self._class_instances_without_logicals.pop(-1)
            self.build_text = ""
        else:
            # we should have a class instance as last thing to delete, delete point is either '(', ')', or ','
            # find the highest index with str.find()
            # str.find() gives first index, so let's reverse the string
            reversed_text = self._build_text[::-1]
            indices = [reversed_text.find(c) for c in chars]
            # find returns -1 if not in string, correct to infinity
            correct_indices = [i if i != -1 else np.inf for i in indices]
            char = chars[int(np.argmin(correct_indices))]
            new_text = char.join(self.build_text.split(char)[:-1])
            if char != ',':
                # keep the split character if it is not the comma
                new_text += char
            self._class_instances_without_logicals.pop(-1)
            self.build_text = new_text

    def restart(self) -> None:
        """
        Reset the building process to a clean built.
        """
        self.build_text = ""
        self._class_instances_without_logicals = []
        self._current_open_logics = []
        self._last_closed_logical = None

    def _add_instance(self, class_name: str):
        """
        Adds a new instance to the built, which might require user input for the
        construction arguments based on a pop-up.

        Parameters
        ----------
        class_name : str
            The name of the new class, that is looked up in the ChemotonClassSearcher.
        """
        from scine_heron.settings.class_options_widget import generate_instance_based_on_potential_widget_input

        if not self._current_open_logics and self._build_text:
            write_error_message(f"Cannot add an additional {self._class_description} without logical operations")
            return
        cls = self._searcher[class_name]
        instance = generate_instance_based_on_potential_widget_input(self, cls)
        if instance is None:
            return
        self._class_instances_without_logicals.append(instance)
        self._build_text_addition(class_name)

    def get_instance(self) -> Optional[Any]:
        """
        Construct the complete object based on the current built.

        Returns
        -------
        Optional[Any]
            The constructed class, None if not valid
        """
        if not self.build_text:
            write_info_message(f"No {self._class_description} has been specified")
            if isabstract(self._searcher.search_type):
                return None
            return self._searcher.search_type()
        if self._current_open_logics:
            write_error_message("We still have an open logic operation")
            return None
        if not any(bracket in self._build_text for bracket in ["(", ")"]):
            if len(self._class_instances_without_logicals) > 1:
                write_error_message("More than one instance was given, without any logical operations")
                return None
            return self._class_instances_without_logicals[0]

        first_logical = self._get_logical_in_3_chars(self._build_text[:3])

        grouping: Dict[_CombinationLogical, List[Any]] = {first_logical: []}  # data container
        current_lists = [grouping[first_logical]]  # structure to always point to currently filling structure

        # 'and' or ' or'
        last_3_chars = ' ' + first_logical.value if first_logical == _CombinationLogical.OR else first_logical.value
        start_index = 4 if first_logical == _CombinationLogical.AND else 3
        instance_index = 0
        for char in self._build_text[start_index:]:
            last_char = last_3_chars[-1]
            if char == ',' and last_char != ')':
                current_lists[-1].append(self._class_instances_without_logicals[instance_index])
                instance_index += 1
            elif char == '(':
                logical = self._get_logical_in_3_chars(last_3_chars)
                current_lists[-1].append({logical: []})
                current_lists.append(current_lists[-1][-1][logical])
            elif char == ')' and last_char != ')':
                current_lists[-1].append(self._class_instances_without_logicals[instance_index])
                instance_index += 1
                current_lists.pop(-1)
            last_3_chars = last_3_chars[1:] + char
        return self._convert_dictionary_to_instance(grouping)

    def _convert_dictionary_to_instance(self, grouping: Dict[_CombinationLogical, List[Any]]) -> Any:
        """
        Converts a dictionary of logicals and list of class instances to the final object.

        Parameters
        ----------
        grouping : Dict[_CombinationLogical, List[Any]]
            A dictionary describing the logical grouping.

        Returns
        -------
        Any
            The built object
        """
        if len(grouping.keys()) > 1:
            raise RuntimeError("internal error")
        key, values = list(grouping.items())[0]
        cls = self._logical_class_translation[(_CombinationLogical(key), self._searcher.search_type)]
        subcls = self._get_subclasses(values)
        return cls(subcls)

    def _get_subclasses(self, values: List[Any]) -> List[Any]:
        """
        A recursive method that allows to traverse the logical combinations to gather
        the complete list of subclasses of a logical combination class.

        Parameters
        ----------
        values : List[Any]
            The list of class instances or dictionaries to be interpreted.
            Dictionaries are evaluated in a recursive fashion.

        Returns
        -------
        List[Any]
            The list of all subclasses for a logical.
        """
        result = []
        for v in values:
            if isinstance(v, dict):
                if len(v.keys()) > 1:
                    raise RuntimeError("internal error")
                key, values = list(v.items())[0]
                cls = self._logical_class_translation[(_CombinationLogical(key), self._searcher.search_type)]
                subcls = self._get_subclasses(list(v.values())[0])
                result.append(cls(subcls))
            else:
                result.append(v)
        return result

    @staticmethod
    def _get_logical_in_3_chars(chars: str) -> _CombinationLogical:
        """
        Translate a string of 3 characters into a Logical Enum.

        Parameters
        ----------
        chars : str
            The string to be parsed

        Returns
        -------
        _CombinationLogical
            The logical described by the string

        Raises
        ------
        RuntimeError
            If string is not of length three or none of the implemented logicals
            are recognized.
        """
        if not len(chars) == 3:
            raise RuntimeError("Internal Error")
        if chars[:2] == _CombinationLogical.OR.value or chars[-2:] == _CombinationLogical.OR.value:
            return _CombinationLogical.OR
        if chars == _CombinationLogical.AND.value:
            return _CombinationLogical.AND
        raise RuntimeError(f"Internal Error: '{chars}'")

    def is_valid(self) -> bool:
        """
        If the current built is valid. This simply tested by trying to construct
        an object from the text with the associated sanity checks, no further test are done.

        Notes
        -----
        The result is also emitted as an info or error message.

        Returns
        -------
        bool
            If the build is valid
        """
        valid = self.get_instance() is not None
        if valid:
            write_info_message(f"Valid {self._class_description} has been specified")
        else:
            write_error_message(f"The {self._class_description} is not valid!")
        return valid

    def get_state(self) -> SelectionState:
        return SelectionState(self.build_text, self._class_instances_without_logicals,
                              self._current_open_logics, self._last_closed_logical)

    def set_state(self, state: SelectionState) -> None:
        self.build_text = state.build_text
        self._class_instances_without_logicals = state.class_instances_without_logicals
        self._current_open_logics = state.current_open_logics
        self._last_closed_logical = state.last_closed_logical
