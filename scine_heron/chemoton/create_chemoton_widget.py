#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from abc import abstractmethod
from typing import Any, Optional, Union

from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QLineEdit,
    QPushButton,
    QGridLayout,
)
from PySide2.QtCore import Qt
from scine_database import Manager
from scine_utilities import ValueCollection

from scine_chemoton.engine import Engine
from scine_chemoton.gears.elementary_steps import ElementaryStepGear
from scine_chemoton.steering_wheel.selections.input_selections import ScineGeometryInputSelection

from scine_heron.chemoton.chemoton_widget import (
    EngineWidget,
    SelectionWidget,
    StepWidget,
    generate_gear_name_settings_suggestions
)
from scine_heron.chemoton.chemoton_widget_container import ChemotonWidgetContainer
from scine_heron.chemoton.class_searcher import ChemotonClassSearcher
from scine_heron.chemoton.grouped_combo_box import GroupedComboBox
from scine_heron.containers.buttons import TextPushButton
from scine_heron.io.text_box import yes_or_no_question
from scine_heron.molecular_viewer import get_mol_viewer_tab
from scine_heron.settings.class_options_widget import \
    generate_instance_based_on_potential_widget_input, ClassOptionsWidget
from scine_heron.utilities import write_error_message
from scine_heron.chemoton.filter_builder import FilterBuilder


class CreateChemotonWidget(QWidget):
    """
    An abstract base class for widgets that allow to build a new widget that holds
    a Chemoton class.

    Notes
    -----
    This widget has hard-coded sizes
    """
    label: str = "Add class"
    default_name: str = "default_name"
    chemoton_class_label = QLabel("Gear:")
    chemoton_class: GroupedComboBox

    def __init__(
            self, parent: ChemotonWidgetContainer, db_manager: Manager, class_searcher: ChemotonClassSearcher
    ) -> None:
        """
        Construct the widget with database information and class that holds the possible classes.

        Parameters
        ----------
        parent : ChemotonWidgetContainer
            The parent widget that holds ChemotonWidgets.
        db_manager : Manager
            The Scine DB Manager that holds the database information
        class_searcher : ChemotonClassSearcher
            A class that holds all underlying classes of the widget this widget
            should be able to construct.
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.class_searcher = class_searcher
        self.button_add = TextPushButton(self.label, self._generate_new_widget, self)

        self._layout = QVBoxLayout()
        self._layout.setAlignment(Qt.AlignTop)
        self._layout.addWidget(QLabel(self.label))
        self._layout.addWidget(self.button_add)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit(self.default_name)
        name_layout.addWidget(self.name_edit)
        self._layout.addLayout(name_layout)

        self._add_chemoton_class_at_layout()

        self.filter_check: Optional[QCheckBox] = None
        self.settings_check: Optional[QCheckBox] = None
        self._layout_additions()

        self.setLayout(self._layout)

        self.setMaximumWidth(500)
        self.setMinimumWidth(300)
        self.setMaximumHeight(400)
        self.setMinimumHeight(200)

    def _add_filter_checkbox_to_layout(self):
        """
        Adds a checkbox to our layout with the question if we want to include the
        filter of the builder.
        """
        layout = QHBoxLayout()
        self.filter_check = QCheckBox("Take Filter from Builder")
        self.filter_check.setChecked(False)
        layout.addWidget(self.filter_check)
        self._layout.addLayout(layout)

    def _add_settings_checkbox_to_layout(self):
        """
        Adds a check box to our layout with the question if we want to include the
        settings of the builder.
        """
        layout = QHBoxLayout()
        self.settings_check = QCheckBox("Take Settings from Builder")
        self.settings_check.setChecked(False)
        layout.addWidget(self.settings_check)
        self._layout.addLayout(layout)

    def _add_chemoton_class_at_layout(self) -> None:
        """
        Adds a combox box that allows to select the underlying Chemoton class
        and the surrounding name information and selections.
        """
        layout = QHBoxLayout()

        self.chemoton_class = GroupedComboBox(self, self.class_searcher)

        layout.addWidget(self.chemoton_class_label)
        layout.addWidget(self.chemoton_class)
        self._layout.addLayout(layout)

    def _filters_are_activated(self) -> bool:
        """
        Returns
        -------
        bool
            If the filters checkbox exists and is ticked.
        """
        return self.filter_check is not None and self.filter_check.isChecked()

    def _determine_name(self, cls_name: str) -> str:
        """
        Determines the name of the class based on the given name. If the name is the
        default name, we return the classes name.

        Parameters
        ----------
        cls_name : str
            The entered class name

        Returns
        -------
        str
            The class name to be given to the new widget.
        """
        name = self.name_edit.text()
        if name == self.default_name:
            return cls_name
        return name

    @abstractmethod
    def _layout_additions(self) -> None:
        """
        Possible additional layout additions that can be implemnted by child class
        """

    @abstractmethod
    def _generate_new_widget(self) -> None:
        """
        The generation of a new widget.
        """


class CreateEngineWidget(CreateChemotonWidget):
    """
    Widget that creates and adds a new widget that holds and controls a Chemoton engine.
    """
    label: str = "Add Engine"
    chemoton_class_label = QLabel("Gear:")

    def _layout_additions(self) -> None:
        """
        Adds the filter and settings check boxes to the layout
        """
        self._add_filter_checkbox_to_layout()
        self._add_settings_checkbox_to_layout()

    def _generate_new_widget(self) -> None:
        """
        Construct the engine based on the selected text in the combobox together
        with the built filters and settings, if wanted. Also carries out the complete
        settings mapping for more complex gear option structures.

        Notes
        -----
        Actual construction of the widgets is done by calling the `add_widget`
        method of our parent.
        """
        gear_name = self.chemoton_class.currentText().strip()

        credentials = self.db_manager.get_credentials()
        engine = Engine(credentials)
        gear = self.class_searcher[gear_name]()

        # take care of model
        if hasattr(gear.options, "model"):
            model = self.parent().get_model()
            setattr(gear.options, "model", model)

        # take care of filters
        filter_description = ""
        if self._filters_are_activated():
            filters = self.parent().get_filters()
            filter_names = [
                "aggregate_filter",
                "reactive_site_filter",
                "further_exploration_filter",
                "structure_filter",
                "elementary_step_filter",
                "reaction_filter",
                "aggregate_enabling",
                "aggregate_validation",
                "reaction_enabling",
                "result_enabling",
                "reaction_validation",
                "reaction_disabling",
                "step_disabling"
            ]
            assert len(filters) == len(filter_names)

            for name, filter_inst in zip(filter_names, filters):
                was_set = False
                # All filters are handled in the same way except the reactive site and further exploration filter.
                # These are not a members of the gear itself but of the trial generator of the elementary step gears.
                if name not in ["reactive_site_filter", "further_exploration_filter"]:
                    if hasattr(gear, name):
                        setattr(gear, name, filter_inst)
                        was_set = True
                else:
                    if hasattr(gear, "trial_generator") and hasattr(getattr(gear, "trial_generator"), name):
                        setattr(getattr(gear, "trial_generator"), name, filter_inst)
                        was_set = True
                if was_set:
                    filter_description += f"{filter_inst.name}\n"
        if not filter_description:
            filter_description = "None"

        # take care of settings
        if self.settings_check is not None and self.settings_check.isChecked():
            settings = self.parent().get_settings()

            def evaluate_new_value(old_value: Any) -> Union[ValueCollection, dict, bool]:
                if isinstance(old_value, ValueCollection):
                    return settings if not old_value else ValueCollection({**old_value.as_dict(), **settings.as_dict()})
                elif isinstance(old_value, dict):
                    return settings.as_dict() if not old_value else {**old_value, **settings.as_dict()}
                return False

            attr, mapping = EngineWidget.get_settings(gear)
            for k, v in attr.items():
                if "settings" in k:
                    new_value = evaluate_new_value(v)
                    if not new_value:
                        continue
                    if hasattr(gear.options, k):
                        setattr(gear.options, k, new_value)
                    if isinstance(gear, ElementaryStepGear):
                        if hasattr(gear.trial_generator.options, k):
                            setattr(gear.trial_generator.options, k, new_value)
                        if "." in k:
                            mapping_key = k.split(".")[0]
                            if mapping_key in mapping:
                                for subkey, subvalue in mapping[mapping_key].items():
                                    if "settings" in subkey:
                                        unmod_key = subkey.split(".")[-1]
                                        new_value = evaluate_new_value(subvalue)
                                        if not new_value:
                                            continue
                                        setattr(getattr(gear.trial_generator.options, mapping_key),
                                                unmod_key, new_value)

        engine.set_gear(gear)
        new_widget = EngineWidget(
            self.parent(),
            engine,
            gear,
            self._determine_name(gear_name),
            gear_name,
            filter_description
        )
        self.parent().add_widget(new_widget)


class CreateStep(CreateChemotonWidget):
    """
    Widget that creates and adds a new widget that holds and controls a Network Expansion.
    """
    label: str = "Add Network Expansion"
    chemoton_class_label = QLabel("Network Expansion:")

    def _layout_additions(self) -> None:
        """
        Adds the settings checkbox to the layout
        """
        self._add_settings_checkbox_to_layout()

    def _generate_new_widget(self) -> None:
        """
        Generates the underlying Network Expansion with the set model, optionally
        the built settings and some possible user input via a pop-up.

        Notes
        -----
        Actual construction of the widgets is done by calling the `add_widget`
        method of our parent.
        """
        step_name = self.chemoton_class.currentText().strip()

        model = self.parent().get_model()
        predefined_kwargs = {
            "model": model,
        }
        if self.settings_check is not None and self.settings_check.isChecked():
            settings = self.parent().get_settings()
            predefined_kwargs["general_settings"] = settings

        step_cls = self.class_searcher[step_name]
        suggestions = generate_gear_name_settings_suggestions()
        step = generate_instance_based_on_potential_widget_input(self, step_cls, predefined_kwargs, suggestions)

        new_widget = StepWidget(
            self.parent(),
            step,
            self._determine_name(step_name),
            step_name,
        )
        self.parent().add_widget(new_widget)


class CreateSelection(CreateChemotonWidget):
    """
    Widget that creates and adds a new widget that holds and controls a Selection.
    """
    label: str = "Add Selection Step"
    chemoton_class_label = QLabel("Selection Step:")

    def _layout_additions(self) -> None:
        """
        Adds the filter checkbox and everything related to the global selection logic
        to the layout
        """
        self._add_filter_checkbox_to_layout()
        # global actual widgets
        self._button_add_global = QPushButton("Add as global Selection")
        self._button_add_global.clicked.connect(  # pylint: disable=no-member
            lambda: self._generate_new_widget(as_global=True)
        )
        self._global_first_check = QCheckBox("Apply global selection\nfor first step")
        self._global_first_check.setChecked(False)
        # global widgets layout design
        self._global_container_widget = QWidget()
        global_grid = QGridLayout()
        global_grid.addWidget(self._button_add_global, 0, 0)
        global_grid.addWidget(self._global_first_check, 0, 1)
        self._global_container_widget.setLayout(global_grid)
        self._layout.addWidget(self._global_container_widget)

    def _generate_new_widget(self, as_global: bool = False) -> None:
        """
        Constructs the underlying selection with the set model and built filters.
        Also handles special case of ScineGeometryInputSelection and writes the filter
        description.

        Parameters
        ----------
        as_global : bool, optional
            If the built selection is global, by default False

        Notes
        -----
        Actual construction of the widgets is done by calling the `add_widget`
        method of our parent.
        """

        selection_name = self.chemoton_class.currentText().strip()

        model = self.parent().get_model()
        predefined_kwargs = {
            "model": model
        }
        if self._filters_are_activated():
            filters = self.parent().get_filters()
            predefined_kwargs["additional_aggregate_filters"] = [filters[0]]
            predefined_kwargs["additional_reactive_site_filters"] = [filters[1]]
        else:
            predefined_kwargs["additional_aggregate_filters"] = None
            predefined_kwargs["additional_reactive_site_filters"] = None
        selection_cls = self.class_searcher[selection_name]

        # special case for mol viewer selection
        if selection_cls == ScineGeometryInputSelection:
            """
            this code block requires some updates in other modules
            answer = yes_or_no_question(self, "Do you want to take the current calculator from the molecular viewer")
            if answer:
                tab = get_mol_viewer_tab(want_atoms_there=True)
                if tab is None or tab.mol_widget is None:
                    # error was printed
                    return
                calculator = tab.create_calculator_widget.get_calculator()
                predefined_kwargs["structure_information_input"] = [calculator]
            else:
            """
            answer2 = yes_or_no_question(self,
                                         "Do you want to take the current structure from the molecular viewer")
            if answer2:
                tab = get_mol_viewer_tab(want_atoms_there=True)
                if tab is None or tab.mol_widget is None:
                    # error was printed
                    return
                atoms = tab.mol_widget.get_atom_collection()
                required_input = {
                    "molecular_charge": 0,
                    "spin_multiplicity": 1,
                }
                inp = ClassOptionsWidget(required_input, parent=self, allow_additions=False, allow_removal=False)
                inp.exec_()
                predefined_kwargs["structure_information_input"] = [
                    (atoms, required_input["molecular_charge"], required_input["spin_multiplicity"])
                ]
            else:
                write_error_message(f"Abort {ScineGeometryInputSelection.__name__} creation")
                return

        selection = generate_instance_based_on_potential_widget_input(self, selection_cls, predefined_kwargs)

        default_filters = FilterBuilder.default_filters()
        filter_description = ""
        if self._filters_are_activated():
            for default, filter_inst in zip(default_filters, filters):
                if filter_inst is not default:
                    filter_description += f"{filter_inst.name}\n"
        if not filter_description:
            filter_description = "None"

        new_widget = SelectionWidget(
            self.parent(),
            selection,
            self._determine_name(selection_name),
            selection_name,
            filter_description,
            as_global=as_global,
            global_for_first=self._global_first_check.isChecked()
        )
        self.parent().add_widget(new_widget, predefined_position=as_global)
