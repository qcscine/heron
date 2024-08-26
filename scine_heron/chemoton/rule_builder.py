#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional, Dict
import pickle

from PySide2.QtCore import QObject
from PySide2.QtWidgets import (
    QDialog,
    QLabel,
    QWidget,
    QLineEdit,
    QCompleter,
    QPushButton,
    QTextEdit,
    QCheckBox
)

from scine_utilities import ElementInfo

from scine_chemoton.reaction_rules import (
    valid_element,
    RuleSet,
    BaseRule
)

# we are using star imports here, because we allow for straight text save/load, which requires to know all classes
# in these submodules
from scine_chemoton.reaction_rules.\
     element_rules import *  # pylint: disable=(wildcard-import,unused-wildcard-import)  # noqa
from scine_chemoton.reaction_rules.\
    distance_rules import *  # pylint: disable=(wildcard-import,unused-wildcard-import)  # noqa
from scine_chemoton.reaction_rules.\
    polarization_rules import *  # pylint: disable=(wildcard-import,unused-wildcard-import)  # noqa
from scine_chemoton.reaction_rules.\
    reaction_rule_library import *  # pylint: disable=(wildcard-import,unused-wildcard-import)  # noqa

# explicitly import the classes we specify as types in the code to avoid pylint errors
from scine_chemoton.reaction_rules.distance_rules import (
    DistanceRuleSet,
    DistanceBaseRule,
)
from scine_chemoton.reaction_rules.element_rules import (
    ElementRuleSet,
    ElementBaseRule,
)
from scine_chemoton.reaction_rules.polarization_rules import (
    PolarizationRuleSet,
    PolarizationBaseRule,
)
from scine_chemoton.reaction_rules.reaction_rule_library import DefaultOrganicChemistry

from scine_heron.chemoton.class_selection_widget import ClassSelectionWidget
from scine_heron.containers.layouts import VerticalLayout, HorizontalLayout
from scine_heron.containers.buttons import TextPushButton
from scine_heron.io.text_box import yes_or_no_question
from scine_heron.io.file_browser_popup import get_save_file_name, get_load_file_name
from scine_heron.utilities import write_error_message, write_info_message
import scine_heron.io.json_pickle_wrap as json_wrap


class RuleBuilder(QDialog):
    """
    A pop-up that allows to build a Chemoton reaction rule.

    Notes
    -----
    This is mainly a wrapper around the ClassSelection widget
    """

    def __init__(self, rule_type: type, parent: Optional[QObject] = None):
        """
        Construct the widget with the allowed rule type.

        Parameters
        ----------
        rule_type : type
            The rule type we want to build
        parent : Optional[QObject], optional
            The parent widget, by default None

        Raises
        ------
        NotImplementedError
            Unknown rule type provided
        """
        super().__init__(parent=parent)
        if rule_type not in RuleSetBuilder.mapping_set_to_rule_type.values():
            raise NotImplementedError(f"Rule type {rule_type} not implemented")
        # widgets
        self._select_widget = ClassSelectionWidget(rule_type, "rule", parent=self)
        button = TextPushButton("Confirm", self.reject)
        # layout
        layout = VerticalLayout([self._select_widget, button])
        self.setLayout(layout)
        self.setWindowTitle("Rule Builder")

    def get_rule(self) -> BaseRule:
        """
        Get the rule instance that was built.

        Returns
        -------
        BaseRule
            The built rule

        Raises
        ------
        ValueError
            When the rule could not be constructed
        """
        rule = self._select_widget.get_instance()
        if rule is None:
            write_error_message("Could not construct a rule")
            raise ValueError("Could not construct a rule")
        return rule

    def get_current_rule_text(self) -> str:
        """
        Relies on `repr` on the current instance, empty string if no currently valid
        built text.

        Returns
        -------
        str
            The current rule text
        """
        rule = self._select_widget.get_instance()
        if rule is None:
            return ""
        return repr(rule)


class RuleSetBuilder(QDialog):
    """
    A pop-up that allows to build a set of Chemoton reaction rule

    Notes
    -----
    This is mainly a wrapper around the ClassSelection widget
    """

    # defines the connection between the RuleSet and Rule types
    mapping_set_to_rule_type: Dict[type, type] = {
        DistanceRuleSet: DistanceBaseRule,
        ElementRuleSet: ElementBaseRule,
        PolarizationRuleSet: PolarizationBaseRule,
    }

    def __init__(self, options: RuleSet, parent: Optional[QObject] = None):
        """
        Construct the widget with a set of rules that should be expanded

        Parameters
        ----------
        options : RuleSet
            The set to be expanded
        parent : Optional[QObject], optional
            The parent widget, by default None

        Raises
        ------
        NotImplementedError
            Unknown rule set type
        """
        rule_set_type = type(options)
        if rule_set_type not in self.mapping_set_to_rule_type:
            raise NotImplementedError(f"Unknown rule set type {rule_set_type}")
        super().__init__(parent=parent)
        self._options = options

        # rule builder
        self._rule_type = self.mapping_set_to_rule_type[rule_set_type]
        self._select_widget = ClassSelectionWidget(self._rule_type, "rule", parent=self)

        # load
        load_button = TextPushButton("Load existing rule set", self._load)
        if self._rule_type == DistanceBaseRule:
            default_button = TextPushButton("Load default organic chemistry", self._load_default_organic_chemistry)
        else:
            default_button = None

        # element line
        label = QLabel("Set rule for element:")
        self._element_edit = QLineEdit("C")
        completer = QCompleter([str(e) for e in ElementInfo.all_implemented_elements()])
        self._element_edit.setCompleter(completer)
        self._check_box = QCheckBox("move rule, when set")
        self._check_box.setChecked(True)
        button = TextPushButton("Set", self._add_rule, shortcut="Return")
        remove_button = TextPushButton("Remove", self._remove_rule)
        element_layout = HorizontalLayout([label, self._element_edit, self._check_box, button, remove_button])

        # display of all rules
        display_label = QLabel("Current rules:")
        self._display = QTextEdit()
        self._display.setReadOnly(True)
        details_button = TextPushButton("Show current rules in detail", self._detail_display, shortcut="Ctrl+S")

        # confirm
        close_button = TextPushButton("Confirm", self.reject)

        # total layout
        element_container = QWidget()
        element_container.setLayout(element_layout)
        order = [self._select_widget, load_button, default_button, element_container,
                 display_label, self._display, details_button, close_button]
        layout = VerticalLayout([widget for widget in order if widget is not None])
        self.setLayout(layout)
        self.setWindowTitle("Rule Set Builder")

    def get_current_rule_text(self) -> str:
        """
        Combines all rules in the current rule set into a text

        Returns
        -------
        str
            The text describing the set
        """
        text = ""
        for k, v in self._options.items():
            text += f"Rule for {k}: {repr(v)}\n"
        return text

    def _add_rule(self):
        """
        Add a single rule based on the input of the selection widget and the current element.
        """
        element = self._element_edit.text().strip()
        if not valid_element(element):
            write_error_message(f"Invalid element {element}, no rule added")
            return
        rule = self._select_widget.get_instance()
        if rule is None:
            write_error_message("Provided invalid rule, no rule added")
            return
        if element in self._options:
            answer = yes_or_no_question(self, f"Rule for element {element} already exists, overwrite")
            if not answer:
                write_info_message("No rule added")
                self._element_edit.setText("")
                return
        self._options[element] = rule
        if self._check_box.isChecked():
            self._select_widget.restart()  # remove written rule
        self._update_display()

    def _remove_rule(self):
        """
        Remove the current rule of the current element in the rule set
        """
        element = self._element_edit.text().strip()
        if element not in self._options:
            write_error_message(f"Haven't specified any rule for element {element}")
            return
        del self._options[element]
        self._update_display()

    def _update_display(self) -> None:
        """
        Updates our text display based on the current rule set
        """
        text = ""
        for k, v in self._options.items():
            text += f"Rule for {k}: {v.name}\n"
        self._display.setText(text)

    def _detail_display(self) -> None:
        """
        Constructs a pop-up widget with the full details of the current rules and
        includes a save button to write the rule set to disk.
        """
        popup = QDialog(self)
        # generate widgets
        label = QLabel("Detailed rule set")
        text = self.get_current_rule_text()
        text_box = QTextEdit()
        text_box.setText(text)  # two lines init to keep line breaks
        save = TextPushButton("Save rule set to disk", self._save)
        close = TextPushButton("Close", popup.reject)
        # fill layout
        layout = VerticalLayout([label, text_box, save, close])
        popup.setLayout(layout)
        popup.exec_()

    def _save(self) -> None:
        filename = get_save_file_name(self, f"{self._rule_type.__name__}_set",
                                      ["txt", "pkl", "pickle", "json"])
        if filename is None:
            return
        if filename.suffix == ".json":
            with open(filename, "w") as f:
                f.write(json_wrap.encode(self._options))
        elif filename.suffix == ".txt":
            # relies on that every rule set and rule has a proper __repr__
            with open(filename, "w") as f:
                f.write(repr(self._options))
        elif filename.suffix in [".pkl", "pickle"]:
            with open(filename, "wb") as f:
                pickle.dump(self._options, f)
        else:
            # DevNote: Forgot to implement type or file dialog not working
            write_error_message(f"Saving '{filename}' failed")

    def _load(self) -> None:
        filename = get_load_file_name(self, f"{self._rule_type.__name__}_set",
                                      ["txt", "pkl", "pickle", "json"])
        if filename is None:
            return
        if filename.suffix == ".json":
            with open(filename, "r") as f:
                data = f.read()
            loaded_options = json_wrap.decode(data)
        elif filename.suffix == ".txt":
            # relies on that every rule set and rule has a proper __repr__
            with open(filename, "r") as f:
                data = f.read()
            loaded_options = eval(data)  # pylint: disable=eval-used
        elif filename.suffix in [".pkl", "pickle"]:
            with open(filename, "rb") as f:
                loaded_options = pickle.load(f)
        else:
            # DevNote: Forgot to implement type or file dialog not working
            write_error_message(f"Loading '{filename}' failed")
            return
        for k, v in loaded_options.items():
            self._options[k] = v
        self._update_display()

    def _load_default_organic_chemistry(self) -> None:
        ruleset = DefaultOrganicChemistry()
        for k, v in ruleset.items():
            self._options[k] = v
        self._update_display()


class RuleSetBuilderButtonWrapper(QPushButton):

    def __init__(self, options: RuleSet, parent: Optional[QObject] = None):
        super().__init__(parent=parent)
        self.setText("Generate rule set")
        self._options = options
        self._builder = RuleSetBuilder(self._options, parent=self)
        self.clicked.connect(self.execute)  # pylint: disable=no-member
        self.setToolTip(self._builder.get_current_rule_text())

    def execute(self) -> None:
        self._builder.exec_()
        self.setToolTip(self._builder.get_current_rule_text())

    def get_options(self) -> RuleSet:
        return self._options


class RuleBuilderButtonWrapper(QPushButton):

    def __init__(self, rule_type: type, parent: Optional[QObject] = None):
        super().__init__(parent=parent)
        self.setText("Generate rule")
        self._builder = RuleBuilder(rule_type, parent=self)
        self.clicked.connect(self.execute)  # pylint: disable=no-member
        self.setToolTip(self._builder.get_current_rule_text())

    def execute(self) -> None:
        self._builder.exec_()
        self.setToolTip(self._builder.get_current_rule_text())

    def get_rule(self) -> BaseRule:
        return self._builder.get_rule()
