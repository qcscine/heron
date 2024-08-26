#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

"""
Provides the DictOptionWidget class.
"""
import inspect
import pickle
import yaml
from collections import UserDict, UserList
from copy import deepcopy
from enum import Enum
from itertools import product
from os import path
from typing import Optional, Dict, Any, Union, List, Tuple, Set, Type, Callable, Iterable, TYPE_CHECKING

from scine_utilities import ValueCollection, Settings, OptionListDescriptor

from PySide2.QtCore import Qt
from PySide2.QtGui import QCloseEvent
from PySide2.QtWidgets import (
    QVBoxLayout,
    QDialog,
    QWidget,
    QFrame,
    QLabel,
    QSpinBox,
    QLineEdit,
    QDoubleSpinBox,
    QCheckBox,
    QGridLayout,
    QPushButton,
    QStyle,
    QCompleter,
    QHBoxLayout
)

from scine_heron.containers.wrapped_label import WrappedLabel
from scine_heron.containers.buttons import TextPushButton
from scine_heron.containers.layouts import VerticalLayout
from scine_heron.containers.without_wheel_event import NoWheelSpinBox, NoWheelDoubleSpinBox, NoWheelComboBox
from scine_heron.io.file_browser_popup import get_save_file_name, get_load_file_name
from scine_heron.io.json_pickle_wrap import encode, decode
from scine_heron.io.text_box import text_input_box
from scine_heron.settings.enum_selection import EnumSelectionBox
from scine_heron.toolbar.io_toolbar import ToolBarWithSaveLoad
from scine_heron.utilities import write_error_message, write_info_message
from scine_heron.dependencies.optional_import import importer, is_imported
from scine_heron.settings.docstring_parser import DocStringParser

if TYPE_CHECKING:
    from scine_database import Model, Job, Side, Label, ID
    from scine_chemoton.utilities.options import BaseOptions
    from scine_chemoton.reaction_rules import RuleSet, BaseRule
    from scine_chemoton.steering_wheel.datastructures import GearOptions, LogicCoupling
    from scine_heron.chemoton.rule_builder import RuleBuilderButtonWrapper, RuleSetBuilderButtonWrapper
    from scine_chemoton.utilities.model_combinations import ModelCombination
    from scine_chemoton.utilities.db_object_wrappers.thermodynamic_properties import ReferenceState
    from scine_heron.chemoton.reference_state_builder import ReferenceStateBuilder
    from scine_heron.chemoton.gear_options_widget import GearOptionsBuilderButtonWrapper
    from scine_heron.chemoton.side_builder import SideBuilder
    from scine_chemoton.gears.kinetic_modeling.atomization import (
        MultiModelEnergyReferences, PlaceHolderMultiModelEnergyReferences
    )
    from scine_chemoton.utilities.uncertainties import UncertaintyEstimator, ZeroUncertainty
    from scine_chemoton.utilities.place_holder_model import construct_place_holder_model
    from scine_heron.chemoton.energy_reference_builder import EnergyReferenceBuilder
    from scine_heron.chemoton.uncertainty_tuple import UncertaintyTuple
    from scine_chemoton.utilities.reactive_complexes.inter_reactive_complexes import InterReactiveComplexes
else:
    Model = importer("scine_database", "Model")
    Side = importer("scine_database", "Side")
    Job = importer("scine_database", "Job")
    Label = importer("scine_database", "Label")
    ID = importer("scine_database", "ID")
    BaseOptions = importer("scine_chemoton.utilities.options", "BaseOptions")
    ModelCombination = importer("scine_chemoton.utilities.model_combinations", "ModelCombination")
    RuleSet = importer("scine_chemoton.reaction_rules", "RuleSet")
    BaseRule = importer("scine_chemoton.reaction_rules", "BaseRule")
    RuleBuilderButtonWrapper = importer("scine_heron.chemoton.rule_builder", "RuleBuilderButtonWrapper")
    RuleSetBuilderButtonWrapper = importer("scine_heron.chemoton.rule_builder", "RuleSetBuilderButtonWrapper")
    ReferenceState = importer("scine_chemoton.utilities.db_object_wrappers.thermodynamic_properties", "ReferenceState")
    MultiModelEnergyReferences = importer("scine_chemoton.gears.kinetic_modeling.atomization",
                                          "MultiModelEnergyReferences")
    PlaceHolderMultiModelEnergyReferences = importer("scine_chemoton.gears.kinetic_modeling.atomization",
                                                     "PlaceHolderMultiModelEnergyReferences")
    ZeroUncertainty = importer("scine_chemoton.utilities.uncertainties", "ZeroUncertainty")
    construct_place_holder_model = importer("scine_chemoton.utilities.place_holder_model",
                                            "construct_place_holder_model")
    UncertaintyEstimator = importer("scine_chemoton.utilities.uncertainties", "UncertaintyEstimator")
    ReferenceStateBuilder = importer("scine_heron.chemoton.reference_state_builder", "ReferenceStateBuilder")
    SideBuilder = importer("scine_heron.chemoton.side_builder", "SideBuilder")
    GearOptions = importer("scine_chemoton.steering_wheel.datastructures", "GearOptions")
    LogicCoupling = importer("scine_chemoton.steering_wheel.datastructures",
                             "LogicCoupling")  # pylint: disable=unused-wildcard-import
    GearOptionsBuilderButtonWrapper = importer("scine_heron.chemoton.gear_options_widget",
                                               "GearOptionsBuilderButtonWrapper")
    EnergyReferenceBuilder = importer("scine_heron.chemoton.energy_reference_builder", "EnergyReferenceBuilder")
    UncertaintyTuple = importer("scine_heron.chemoton.uncertainty_tuple", "UncertaintyTuple")
    InterReactiveComplexes = importer("scine_chemoton.utilities.reactive_complexes.inter_reactive_complexes",
                                      "InterReactiveComplexes")


class DefaultMapping:
    """
    Defines defaults for each type
    """

    def __init__(self) -> None:
        self._mapping: Dict[Type, Any] = {
            int: 0,
            bool: False,
            float: 0.0,
            str: "",
            dict: {},
            Dict: {},
            list: [],
            List: [],
            set: set(),
            Set: set(),
            tuple: tuple(),
            Tuple: tuple(),  # type: ignore
            UserDict: {},
            RuleSet: RuleSet({}),
            GearOptions: GearOptions(),
            UserList: [],
            ValueCollection: ValueCollection({}),
            Model: Model("PM6", "PM6", ""),
            Job: Job("job_order"),
            Label: Label.MINIMUM_OPTIMIZED,
            ID: ID(),
            Any: "",  # type: ignore
            type(None): None,
            Side: Side.BOTH,
        }
        if is_imported(Model):
            self._mapping[ReferenceState] = ReferenceState(float(Model("PM6", "PM6", "").temperature),
                                                           float(Model("PM6", "PM6", "").pressure))
            self._mapping[ModelCombination] = ModelCombination(construct_place_holder_model())
            self._mapping[MultiModelEnergyReferences] = PlaceHolderMultiModelEnergyReferences()
            self._mapping[UncertaintyEstimator] = ZeroUncertainty()
        if is_imported(UncertaintyTuple):
            self._mapping[UncertaintyTuple] = UncertaintyTuple.get_default()
        standard_types = self.standard_types()
        for t in standard_types:
            self._mapping[List[t]] = []  # type: ignore
        self._mapping[List[Any]] = []  # type: ignore
        for s in standard_types:
            for t in standard_types:
                self._mapping[Dict[s, t]] = {}  # type: ignore
                self._mapping[Dict[s, Any]] = {}  # type: ignore
                self._mapping[Dict[Any, t]] = {}  # type: ignore
        self._mapping[Dict[Any, Any]] = {}  # type: ignore

    def __getitem__(self, item: Optional[Type]):
        # TODO maybe cycle through keys and check for subclasses if class not explicitly present in map
        if item is None:
            return deepcopy(self._mapping[type(item)])
        return deepcopy(self._mapping[item])  # deepcopy ensures safety of mutable default types

    @staticmethod
    def standard_types() -> List[Type]:
        return [bool, int, float, str]

    @staticmethod
    def enhanced_standard_types() -> List[Type]:
        return DefaultMapping.standard_types() + [dict, list, set, tuple, ValueCollection, Model, Job, RuleSet,
                                                  Dict[Any, Any], List[Any], Set[Any], Tuple[Any, ...]]  # type: ignore

    def keys(self):
        return self._mapping.keys()


class DictOptionWidget(QFrame):
    """
    DictOptionWidget create a container of widgets based on options types.
    """

    def __init__(
            self,
            options: Dict[str, Any],
            parent: Optional[QWidget],
            show_border: Optional[bool] = False,
            docstring_dict: Optional[Dict[str, str]] = None,
            add_close_button: bool = True,
            allow_additions: bool = False,
            allow_removal: bool = True,
            value_type: Optional[Type] = None,
            addition_suggestions: Optional[List[str]] = None,
            suggestions_by_name: Optional[Dict[str, Dict[str, Callable]]] = None,
            suggestions_with_values: Optional[Dict[str, Callable]] = None,
            keys_excluded_from_io: Optional[List[str]] = None,
    ) -> None:
        super(DictOptionWidget, self).__init__(parent)
        self._ignore_list = ["self", "args", "kwargs", "_"]
        self.__io_extensions = ['yaml', 'json', 'pkl', 'pickle']
        self._options = options
        self._option_widgets: Dict[str, QWidget] = {}
        self._option_getters: Dict[str, Callable[[], Any]] = {}
        self._docstring_dict = docstring_dict
        self._value_type = value_type
        self._allow_removal = allow_removal
        self._addition_suggestions = addition_suggestions
        self._suggestions_by_name = suggestions_by_name
        self._suggestions_with_values = suggestions_with_values
        self._keys_excluded_from_io = keys_excluded_from_io

        self.__default_min_value = -1000000000
        self.__default_max_value = 1000000000
        self.__double_spin_step = 0.1
        self.__double_spin_decimals = 10

        self.__standard_types = DefaultMapping.standard_types()
        self.__enhanced_standard_types = DefaultMapping.enhanced_standard_types()
        self.__default_mapping = DefaultMapping()

        if show_border:
            self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)

        self.__super_layout = QGridLayout()
        if allow_removal:
            self.__super_layout.addWidget(ToolBarWithSaveLoad(self._save, self._load, self))
        self.__layout = QGridLayout()
        for option_name, option in self._options.items():
            self.add_key_value(option_name, option)
        self.__options_holder_widget = QWidget()
        self.__options_holder_widget.setLayout(self.__layout)
        self.__super_layout.addWidget(self.__options_holder_widget)

        if allow_additions:
            self.__super_layout.addWidget(TextPushButton("Add new field", self.__add_option, self))
        if parent is not None and add_close_button:
            self.__super_layout.addWidget(
                TextPushButton("Ok", parent.close, self, shortcut="Return")  # type: ignore
            )

        self.setLayout(self.__super_layout)

    def add_key_value(self, option_name: str, option: Any, allow_removal_for_dict: bool = True) -> None:
        if option_name in self._ignore_list:
            return
        self._options[option_name] = option
        if isinstance(self._options, Settings) \
                and isinstance(self._options.descriptor_collection[option_name], OptionListDescriptor):
            assert option in self._options.descriptor_collection[option_name].options
            widget = self.__generate_selection_box(self._options.descriptor_collection[option_name].options)
            widget.setCurrentText(option)

            def getter():
                return widget.currentText()
        else:
            widget, getter = self.construct_widget_based_on_type(option, option_name, allow_removal_for_dict)
        self._option_widgets[option_name] = widget
        self._option_getters[option_name] = getter

        name_widget = WrappedLabel(option_name)
        if self._docstring_dict and option_name in self._docstring_dict:
            name_widget.setToolTip(self._docstring_dict[option_name])

        index = len(self._option_widgets)
        self.__layout.addWidget(name_widget, index, 0)
        self.__layout.addWidget(widget, index, 1)
        if self._allow_removal:
            self.__layout.addWidget(self.__generate_removal_widget(index), index, 2)

    def construct_widget_based_on_type(self, option: Any, option_name: Optional[str] = None,
                                       allow_removal_for_dict: bool = True) \
            -> Tuple[QWidget, Callable[[], Any]]:
        # base types
        # bool must be checked before int!
        if self.__option_check(option, [bool])[0]:
            option = self.__sanitize_option(option)
            widget = self.__generate_checkbox_widget(option)
            return widget, widget.isChecked
        if self.__option_check(option, [int])[0]:
            option = self.__sanitize_option(option)
            widget = self.__generate_spin_widget(option)
            return widget, widget.value
        if self.__option_check(option, [float])[0]:
            option = self.__sanitize_option(option)
            widget = self.__generate_double_spin_widget(option)
            return widget, widget.value
        if self.__option_check(option, [str])[0]:
            option = self.__sanitize_option(option)
            widget = self.__generate_line_editor_widget(option)
            if self._suggestions_by_name is not None and option_name is not None \
                    and option_name in self._suggestions_by_name:
                widget.setCompleter(QCompleter(list(self._suggestions_by_name[option_name].keys())))
            return widget, widget.text

        # Scine types
        if self.__option_check(option, [ID])[0]:
            option = self.__sanitize_option(option)
            widget = self.__generate_line_editor_widget(str(option))

            def id_getter() -> ID:
                return ID(widget.text())

            return widget, id_getter
        if self.__option_check(option, [RuleSet])[0]:
            option = self.__sanitize_option(option)
            widget = RuleSetBuilderButtonWrapper(option, self)
            return widget, widget.get_options
        if self.__option_check(option, [BaseRule])[0]:
            option_type = self.__option_check(option, [BaseRule])[1]
            if option_type is not None:
                widget = RuleBuilderButtonWrapper(option_type, self)
                return widget, widget.get_rule
        if self.__option_check(option, [Enum])[0]:
            option_type = self.__option_check(option, [Enum])[1]
            if option_type is not None and issubclass(option_type, Enum):
                widget = EnumSelectionBox(self, option_type)
                return widget, widget.get_value
        if self.__option_check(option, [Label])[0]:
            option_type = self.__option_check(option, [Label])[1]
            if option_type is not None and issubclass(option_type, Label):
                widget = EnumSelectionBox(self, option_type)  # type: ignore
                return widget, widget.get_value
        if self.__option_check(option, [GearOptions])[0]:
            option = self.__sanitize_option(option)
            gears = None
            if self._suggestions_by_name is not None and option_name is not None:
                suggestions = self._suggestions_by_name.get(option_name)
                if suggestions is not None and len(suggestions) == 1:
                    # only one option, we rely on implicit coupling that this single function gives us all gears
                    # TODO maybe make this more explicit
                    gears = list(suggestions.values())[0]()
            if not is_imported(GearOptionsBuilderButtonWrapper):
                raise ImportError("GearOptionsBuilderButtonWrapper could not be imported.")
            widget = GearOptionsBuilderButtonWrapper(option, gears, self)
            return widget, widget.get_options
        if self.__option_check(option, [ValueCollection])[0]:
            option = self.__sanitize_option(option)
            if option is None:
                option = self.__default_mapping[ValueCollection]
            if self._suggestions_by_name is not None and option_name is not None:
                suggest_dict = self._suggestions_by_name.get(option_name)
            else:
                suggest_dict = None
            widget = DictOptionWidget(
                option.as_dict(), parent=self, show_border=True, add_close_button=False, allow_additions=True,
                suggestions_with_values=suggest_dict, allow_removal=allow_removal_for_dict
            )

            def vc_getter():
                return ValueCollection(widget.get_widget_data())

            return widget, vc_getter
        if self.__option_check(option, [ModelCombination])[0]:
            # This class uses something from the dict_options_widget. Therefore, we cannot
            # import it on the top of the file because this would lead to circular imports.
            from scine_heron.chemoton.model_combination_builder import ModelCombinationBuilder
            option = self.__sanitize_option(option)
            widget = ModelCombinationBuilder(option, self)
            return widget, widget.get_model_combination

        if self.__option_check(option, [MultiModelEnergyReferences])[0]:
            option = self.__sanitize_option(option)
            widget = EnergyReferenceBuilder(option, self)
            return widget, widget.get_energy_reference

        if self.__option_check(option, [UncertaintyTuple])[0]:
            # This class uses something from the dict_options_widget. Therefore, we cannot
            # import it on the top of the file because this would lead to circular imports.
            from scine_heron.chemoton.uncertainty_estimator_builder import UncertaintyBuilder
            option = self.__sanitize_option(option)
            widget = UncertaintyBuilder(option, self)
            return widget, widget.get_uncertainty_tuple
        if self.__option_check(option, [UncertaintyEstimator])[0]:
            # This class uses something from the dict_options_widget. Therefore, we cannot
            # import it on the top of the file because this would lead to circular imports.
            from scine_heron.chemoton.uncertainty_estimator_builder import UncertaintyEstimatorBuilder
            option = self.__sanitize_option(option)
            widget = UncertaintyEstimatorBuilder(option, self)
            return widget, widget.get_uncertainty_estimator

        if self.__option_check(option, [Side])[0]:
            option = self.__sanitize_option(option)
            widget = SideBuilder(self)
            return widget, widget.get_side

        if self.__option_check(option, [ReferenceState])[0]:
            option = self.__sanitize_option(option)
            widget = ReferenceStateBuilder(option, self)
            return widget, widget.get_reference_state

        if self.__option_check(option, [Model, Job])[0]:
            san_option = self.__sanitize_option(option)
            if san_option is None:
                san_option = self.__default_mapping[self.__option_check(option, [Model, Job])[1]]
            widget = DictOptionWidget(
                self.get_attributes_of_object(san_option), parent=self, show_border=True, add_close_button=False,
                allow_removal=False
            )

            def mj_getter():
                self.set_attributes_to_object(san_option, widget.get_widget_data())
                return san_option

            return widget, mj_getter
        if self.__option_check(option, [BaseOptions])[0]:
            widget = DictOptionWidget(
                self.get_attributes_of_object(option), parent=self, show_border=True, add_close_button=False,
                allow_removal=False
            )

            def option_getter():
                self.set_attributes_to_object(option, widget.get_widget_data())
                return option

            return widget, option_getter

        if self.__option_check(option, [InterReactiveComplexes])[0]:
            san_option = self.__sanitize_option(option)
            if hasattr(san_option, "options"):
                widget_options = san_option.options
                obj = san_option
            elif hasattr(option, "options"):
                widget_options = option.options
                obj = option
            else:
                write_error_message("Received InterReactiveComplexes but could not find options")
                return QLabel("Error"), lambda: None
            parser = DocStringParser()
            doc_name = option_name if option_name is not None else InterReactiveComplexes.__name__
            doc_strings = parser.get_docstring_for_object_attrs(doc_name, obj)
            widget = DictOptionWidget(self.get_attributes_of_object(widget_options),
                                      parent=self, docstring_dict=doc_strings, add_close_button=False,
                                      show_border=True, allow_additions=False, allow_removal=False)

            def irc_getter():
                self.set_attributes_to_object(widget_options, widget.get_widget_data())
                obj.options = widget_options
                return obj

            return widget, irc_getter

        # iterable types
        if self.__option_check(option, [tuple, Tuple])[0]:  # type: ignore
            san_option = self.__sanitize_option(option)
            option_type = self.__first_non_union_type(option)
            widget = self.__generate_iterable_edit_widget(san_option, option_type, allow_additions=False)
            return widget, widget.get_values
        if self.__option_check(option, [list, List, UserList])[0]:
            san_option = self.__sanitize_option(option)
            # in the case of the annotation
            # Union[List[SomeType], None] we want to get the SomeType
            # in the case of the annotation
            # List[SomeType] we want to get the SomeType
            if isinstance(option, inspect.Parameter) and option.annotation != inspect.Parameter.empty \
                    and getattr(option.annotation, "__origin__", None) is Union:
                # we got a Union
                option_type = self.__first_non_union_type(self.__first_non_union_type(option))
            else:
                # we got a List directly
                option_type = self.__first_non_union_type(option)
            widget = self.__generate_iterable_edit_widget(san_option, option_type, allow_additions=True)
            return widget, widget.get_values
        if self.__option_check(option, [dict, Dict, UserDict])[0]:
            option_type = self.__option_check(option, [dict, Dict, UserDict])[1]
            if hasattr(option_type, "__args__") and len(getattr(option_type, "__args__")) == 2:
                value_type = getattr(option_type, "__args__")[1]
            else:
                value_type = None
            option = self.__sanitize_option(option)
            if option is None:
                option = self.__default_mapping[dict]
            if self._suggestions_by_name is not None and option_name is not None:
                suggestions = self._suggestions_by_name.get(option_name)
            else:
                suggestions = None
            widget = DictOptionWidget(option, parent=self, show_border=True, add_close_button=False,
                                      allow_additions=True, value_type=value_type, suggestions_with_values=suggestions,
                                      allow_removal=allow_removal_for_dict
                                      )
            return widget, widget.get_widget_data
        if self.__option_check(option, [Iterable])[0]:
            option_type = self.__first_non_union_type(option)
            widget = self.__generate_iterable_edit_widget([], option_type, allow_additions=True)
            return widget, widget.get_values

        # assume we have a non-default class that provides default constructor with options
        try:
            print(f"Warning: Could not deduce type of {option}, the widget might be incorrect.")
            attr = self.get_attributes_of_object(option)
            if hasattr(option, "options"):
                attr = {**attr, **self.get_attributes_of_object(option.options)}
            if self._suggestions_by_name is not None and option_name is not None:
                suggestions = self._suggestions_by_name.get(option_name)
            else:
                suggestions = None
            widget = DictOptionWidget(
                attr, parent=self, show_border=True, add_close_button=False, allow_removal=False,
                suggestions_with_values=suggestions
            )
            return widget, widget.get_widget_data
        except BaseException as e:  # TODO maybe remove exception info for release
            option_info = option if option is type else type(option)
            widget = QLabel(f"Type '{str(option_info)}' is not implemented: {str(e)}")
            return widget, lambda: None

    def __option_check(self, parameter: Any, types_to_check: List[Type]) \
            -> Tuple[bool, Optional[Type]]:
        """
        Also modifies parameter in case it is an inspect.Parameter to obtain a real type
        """
        for type_to_check in types_to_check:
            if isinstance(parameter, type_to_check):
                return True, type(parameter)
            # if received directly a type:
            if parameter == type_to_check:
                return True, parameter
        # add subscriptions to typing classes
        if List in types_to_check:
            types_to_check += [List[t] for t in self.__enhanced_standard_types]  # type: ignore
            types_to_check.append(List[Any])
        if Dict in types_to_check:
            for s in self.__standard_types:
                for t in self.__standard_types:
                    types_to_check.append(Dict[s, t])  # type: ignore
                    types_to_check.append(Dict[s, Any])  # type: ignore
                    types_to_check.append(Dict[Any, t])  # type: ignore
            types_to_check.append(Dict[Any, Any])  # type: ignore
        if Tuple in types_to_check and hasattr(parameter, "__args__"):
            n_args = len(getattr(parameter, "__args__"))
            for perm in product(list(self.__default_mapping.keys()), repeat=n_args):
                # for perm in product(list(self.__default_mapping.keys()), repeat=2):
                types_to_check.append(Tuple[perm])  # type: ignore
        # add Optional to all types
        types_to_check += [Optional[t] for t in types_to_check]  # type: ignore

        def types_equal(a: type, b: type) -> bool:
            if b == Iterable:
                a_origin = getattr(a, "__origin__", None)
                if a_origin is not None:
                    return issubclass(a_origin, Iterable)
            try:
                if issubclass(a, b):
                    return True
            except TypeError:
                pass
            return a == b

        for type_to_check in types_to_check:
            if parameter == type_to_check:
                return True, parameter
            if hasattr(parameter, "__origin__") and getattr(parameter, "__origin__") is Union:
                for arg in getattr(parameter, "__args__"):
                    if types_equal(arg, type_to_check):
                        return True, type_to_check
        # now it has to be an inspect.Parameter to still work
        if not isinstance(parameter, inspect.Parameter):
            return False, None

        def from_default(_parameter: inspect.Parameter, _types_to_check):
            # try to get the type from the assigned default
            default = _parameter.default
            if default == inspect.Parameter.empty:
                return False, None
            for _type_to_check in _types_to_check:
                if not hasattr(_type_to_check, "__origin__"):
                    # typing classes cannot be used in 'isinstance'
                    if isinstance(default, _type_to_check):
                        return True, type(default)
            return False, None

        annot = parameter.annotation
        # if there is a "from __future__ import annotations" call somewhere in our import tree
        # then the inspect.Parameter.annotation will not return the actual type, e.g., db.Model,
        # but the string of the type, e.g., "db.Model"
        # so, if we get a string, we try to reverse this with an eval call
        if isinstance(annot, str):
            try:
                annot = eval(annot)  # pylint: disable=eval-used
            except NameError as e:
                print(f"Error in evaluation of type annotation: {str(e)}")
                # cannot use annotation, try default
                return from_default(parameter, types_to_check)

        if Tuple in types_to_check and hasattr(annot, "__args__"):
            n_args = len(getattr(annot, "__args__"))
            for perm in product(list(self.__default_mapping.keys()), repeat=n_args):
                # for perm in product(list(self.__default_mapping.keys()), repeat=2):
                types_to_check.append(Tuple[perm])  # type: ignore

        if annot != inspect.Parameter.empty:

            # check if we have a Union
            if hasattr(annot, "__origin__") and getattr(annot, "__origin__") is Union:
                args = getattr(annot, "__args__")
                for type_to_check in types_to_check:
                    for arg in args:
                        if types_equal(arg, type_to_check):
                            return True, arg
            else:
                for type_to_check in types_to_check:
                    if types_equal(annot, type_to_check):
                        return True, annot
        # maybe no annotation but a default
        return from_default(parameter, types_to_check)

    def __sanitize_option(self, option: Any) -> Any:

        # if there is a "from __future__ import annotations" call somewhere in our import tree
        # then the inspect.Parameter.annotation will not return the actual type, e.g., db.Model,
        # but the string of the type, e.g., "db.Model"
        # so, if we get a string, we try to reverse this with an eval call
        def destringify_annot(annotation: Union[str, Type]) -> Type:
            if isinstance(annotation, str):
                try:
                    return eval(annotation)  # pylint: disable=eval-used
                except NameError as e:
                    # cannot use annotation, try default
                    raise RuntimeError("Cannot transform string annotation to type") from e
            return annotation

        if isinstance(option, inspect.Parameter):
            default = option.default
            if default != inspect.Parameter.empty:
                if default is None:
                    annot = destringify_annot(option.annotation)
                    if annot != inspect.Parameter.empty:
                        if hasattr(annot, "__origin__") and getattr(annot, "__origin__") is Union:
                            args = getattr(annot, "__args__")
                            for arg in args:
                                try:
                                    return self.__default_mapping[arg]
                                except KeyError:
                                    pass
                        return self.__default_mapping[annot]
                return default
            annot = destringify_annot(option.annotation)
        else:
            annot = option
        # check if we have a Union
        if hasattr(annot, "__origin__") and getattr(annot, "__origin__") is Union:
            args = getattr(annot, "__args__")
            # special case for rule building
            for arg in args:
                if hasattr(arg, "__origin__") or arg == Any:
                    continue
                if issubclass(arg, RuleSet) or issubclass(arg, BaseRule):
                    return arg({})
            # default case
            for arg in args:
                # roundabout way, because we only overwrite __getitem__ in DefaultMapping
                try:
                    return self.__default_mapping[arg]
                except KeyError:
                    pass
        # check if we have a Tuple
        if hasattr(annot, "__origin__") and getattr(annot, "__origin__") is tuple:
            args = getattr(annot, "__args__")
            return tuple(self.__default_mapping[arg] for arg in args)
        try:
            return self.__default_mapping[annot]
        except (KeyError, TypeError):
            return annot

    @staticmethod
    def __first_non_union_type(option: Any) -> type:
        if isinstance(option, inspect.Parameter):
            val = option.annotation
            if val == inspect.Parameter.empty:
                val = option.default
                if val == inspect.Parameter.empty:
                    return Any  # type: ignore
        else:
            val = option
        args = getattr(val, "__args__", None)
        if args is None:
            if isinstance(val, type):
                return val
            # check if we got a value instead of a type annotation and can get the type from its member
            if len(val):
                return type(val[0])
            return Any  # type: ignore
        # make sure we don't have a union
        while getattr(args[0], "__origin__", None) is Union:
            args = getattr(args[0], "__args__")
        return args[0]

    def __add_option(self) -> None:
        if self._value_type == Any:
            self._value_type = None
        require_value_type = self._value_type is None and self._suggestions_with_values is None
        if self._addition_suggestions is not None:
            suggestions = self._addition_suggestions
        elif self._suggestions_with_values is not None:
            suggestions = list(self._suggestions_with_values.keys())
        else:
            suggestions = None
        edit = OptionsAdditionDialog(add_value_field=require_value_type, parent=self, suggestions=suggestions)
        edit.exec_()
        name = edit.name.strip()
        if name:
            if self._suggestions_with_values is not None:
                value = self._suggestions_with_values.get(name)
                if value is None:
                    write_error_message(f"Entered invalid key {name}")
                else:
                    try:
                        self.add_key_value(name, value(), allow_removal_for_dict=False)
                    except (NameError, TypeError):
                        write_error_message(f"Could not construct {value} for key {name}")
            elif self._value_type is None:
                if edit.type.strip():
                    try:
                        cls = eval(edit.type.strip())  # pylint: disable=eval-used
                        self.add_key_value(name, cls())
                    except NameError:
                        write_error_message(f"Given type {edit.type} is not a valid type")
                    except TypeError:
                        write_info_message(f"Trying to infer type from {edit.type}")
                        self.add_key_value(name, cls)
                else:
                    self.add_key_value(name, "")
            else:
                self.add_key_value(name, self._value_type())  # type: ignore
        else:
            write_error_message("Did not enter an option name")

    def __generate_spin_widget(self, option: int) -> QSpinBox:
        spin_edit = NoWheelSpinBox()
        spin_edit.setMinimum(int(self.__default_min_value))
        spin_edit.setMaximum(int(self.__default_max_value))
        spin_edit.setValue(option)
        return spin_edit

    def __generate_double_spin_widget(self, option: float) -> QDoubleSpinBox:
        spin_edit = NoWheelDoubleSpinBox()
        spin_edit.setMinimum(float(self.__default_min_value))
        spin_edit.setMaximum(float(self.__default_max_value))
        spin_edit.setSingleStep(self.__double_spin_step)
        spin_edit.setDecimals(self.__double_spin_decimals)
        spin_edit.setValue(option)
        return spin_edit

    def __generate_iterable_edit_widget(self, option: Iterable, sub_type: Optional[type] = None,
                                        allow_additions: bool = True) -> QWidget:
        widget = IterableEditWidget(self, sub_type, allow_additions)
        if option != sub_type:
            for entry in option:
                sub_widget, getter = self.construct_widget_based_on_type(entry)
                widget.add(sub_widget, getter)
        return widget

    @staticmethod
    def __generate_checkbox_widget(option: bool) -> QCheckBox:
        check_box = QCheckBox()
        check_box.setChecked(option)
        return check_box

    @staticmethod
    def __generate_selection_box(options: List[str]) -> NoWheelComboBox:
        box = NoWheelComboBox()
        box.addItems(options)
        return box

    @staticmethod
    def __generate_line_editor_widget(option: Union[str, List]) -> QLineEdit:
        line_edit = QLineEdit()
        line_edit.setText(str(option))
        return line_edit

    def __generate_removal_widget(self, index: int) -> QPushButton:
        check_box = QPushButton(icon=self.style().standardIcon(QStyle.SP_TitleBarCloseButton), text="remove field")
        check_box.setChecked(False)
        check_box.clicked.connect(lambda: self.__remove_option(index))  # pylint: disable=no-member
        return check_box

    def __remove_option(self, row_index: int):
        to_delete = []
        # this method can be reached even if removal is not allowed, because we want to remove things
        # if we are loading the new options and they have duplicate names to existing ones
        # the reason is, because we only hold the widgets and getters, but no setters
        n_cols = 3 if self._allow_removal else 2
        for i in range(n_cols):
            item = self.__layout.itemAtPosition(row_index, i)
            assert item is not None
            to_delete.append(item.widget())
        assert isinstance(to_delete[0], QLabel)
        name = to_delete[0].text()
        del self._options[name]
        del self._option_widgets[name]
        for widget in to_delete:
            widget.setAttribute(Qt.WA_DeleteOnClose)
            self.__layout.removeWidget(widget)
            widget.close()
            widget.setParent(None)  # type: ignore
        self.__layout.update()
        self.updateGeometry()

    @staticmethod
    def get_attributes_of_object(o: object) -> Dict[str, Any]:
        attributes = inspect.getmembers(
            o.__class__, lambda a: not (inspect.isroutine(a))
        )
        return {
            a[0]: getattr(o, a[0])
            for a in attributes
            if a[0] != "step_result" and not a[0].startswith("_") and not inspect.isclass(a[1])
        }

    @staticmethod
    def set_attributes_to_object(o: object, d: Dict[str, Any]) -> None:
        if isinstance(o, dict) or isinstance(o, ValueCollection):
            for option_name, option in d.items():
                o[option_name] = option
        else:
            for option_name, option in d.items():
                setattr(o, option_name, option)

    def get_widget_data(self) -> Dict[str, Any]:
        data: Dict[str, Any] = dict()
        for option_name, option in self._options.items():
            if option_name in self._ignore_list:
                continue
            try:
                getter = self._option_getters[option_name]
                data[option_name] = getter()
            except BaseException as e:
                write_error_message(f"Could not get data for option {option_name}: {e}")
                widget = self._option_widgets[option_name]
                try:
                    sub_data = widget.get_widget_data()
                    attr = self.get_attributes_of_object(option)
                    if attr:
                        set_attr = {data_k: data_v for data_k, data_v in sub_data.items() if data_k in attr}
                        self.set_attributes_to_object(option, set_attr)
                    if hasattr(option, "options"):
                        attr = self.get_attributes_of_object(option.options)
                        set_attr = {data_k: data_v for data_k, data_v in sub_data.items() if data_k in attr}
                        self.set_attributes_to_object(option.options, set_attr)
                    data[option_name] = option
                except BaseException as exc:  # TODO maybe remove exception info for release
                    option_info = option if option is type else type(option)
                    raise NotImplementedError(f"Type '{str(option_info)}' is not implemented: {str(exc)}") from exc
        return data

    def _save(self):
        filename = get_save_file_name(self, "options", self.__io_extensions)
        if filename is None:
            return
        data = self.get_widget_data()
        # delete excluded keys
        if self._keys_excluded_from_io is not None:
            for key in self._keys_excluded_from_io:
                data.pop(key, None)
        try:
            if filename.suffix == ".json":
                with open(filename, "w") as f:
                    f.write(encode(data))
            elif filename.suffix in [".pickle", ".pkl"]:
                with open(filename, "wb") as f:
                    pickle.dump(data, f)
            elif filename.suffix == ".yaml":
                with open(filename, "w") as f:
                    f.write(yaml.dump(data))
            else:
                raise NotImplementedError(f"Extension {filename.suffix} is not implemented")
        except BaseException as e:
            write_error_message(f"Could not save options: {e}")

    def _load(self):
        filename = get_load_file_name(self, "options", self.__io_extensions)
        if filename is None:
            return
        try:
            if filename.suffix == ".json":
                with open(filename, "r") as f:
                    data = decode(f.read())
            elif filename.suffix in [".pickle", ".pkl"]:
                with open(filename, "rb") as f:
                    data = pickle.load(f)
            elif filename.suffix == ".yaml":
                with open(filename, "r") as f:
                    data = yaml.safe_load(f.read().replace("\t", "  ").replace("    ", "  "))
            else:
                raise NotImplementedError(f"Extension {filename.suffix} is not implemented")
        except BaseException as e:
            write_error_message(f"Could not save options: {e}")
            return
        # delete excluded keys
        if self._keys_excluded_from_io is not None:
            for key in self._keys_excluded_from_io:
                data.pop(key, None)
        # delete existing options with the same name
        # we need to first gather the indices and then delete from highest to lowest, because otherwise
        # Qt gives us the wrong indices
        to_delete_rows = []
        for option_name, option in data.items():
            if option_name in self._options:
                index = self.__layout.indexOf(self._option_widgets[option_name])
                # index is the total index of all widgets in the layout, we want to know the row
                # index is always the value position in the row, which has the index 1 with 0 being the label
                # therefore we remove 1 and the divide by the number of columns
                n_cols = 3 if self._allow_removal else 2
                row = (index - 1) // n_cols
                to_delete_rows.append(row + 1)
        to_delete_rows.sort(reverse=True)
        for row in to_delete_rows:
            self.__remove_option(row)
        # now add the new options
        for option_name, option in data.items():
            self.add_key_value(option_name, option)


class OptionsAdditionDialog(QDialog):
    """
    QDialog to add an option
    """

    def __init__(self, add_value_field: bool, parent: Optional[QWidget] = None,
                 suggestions: Optional[List[str]] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Specify new key name")
        self.setMinimumWidth(400)
        self.setMinimumHeight(400)
        self.setMaximumWidth(650)
        self.setMaximumHeight(900)

        self.name = ""
        self.type = ""
        self.__add_value_field = add_value_field

        layout = QVBoxLayout()
        name_label = QLabel("Option name")
        self.__name_edit = QLineEdit()
        self.__name_edit.setText("")
        if suggestions is not None:
            completer = QCompleter(suggestions)
            completer.setFilterMode(Qt.MatchContains)
            self.__name_edit.setCompleter(completer)
        layout.addWidget(name_label)
        layout.addWidget(self.__name_edit)

        if add_value_field:
            type_label = QLabel("Option type (e.g. 'str')")
            type_suggestions = ['str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple']
            type_completer = QCompleter(type_suggestions)
            self.__type_edit = QLineEdit()
            self.__type_edit.setText("")
            self.__type_edit.setCompleter(type_completer)
            layout.addWidget(type_label)
            layout.addWidget(self.__type_edit)

        layout.addWidget(TextPushButton("Ok", self.reject, self))

        self.setLayout(layout)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.name = self.__name_edit.text()
        if self.__add_value_field:
            self.type = self.__type_edit.text()
        super().closeEvent(event)

    def reject(self) -> None:
        self.name = self.__name_edit.text()
        if self.__add_value_field:
            self.type = self.__type_edit.text()
        super().reject()


class IterableEditWidget(QWidget):

    def __init__(self, parent: DictOptionWidget, fixed_sub_types: Union[type, List[type], None] = None,
                 allow_additions: bool = False) -> None:
        super().__init__(parent)
        self._parent = parent
        # buttons
        self._add_button = None
        self._copy_button = None
        self._paste_button = None
        self.remove_last_button = None
        # containers
        self._widgets: List[QWidget] = []
        self._getters: List[Callable[[], Any]] = []
        self._super_layout = VerticalLayout()
        self.single_layout = QHBoxLayout()
        self._super_layout.addLayout(self.single_layout)
        self.setLayout(self._super_layout)
        # find out initial structure
        if fixed_sub_types == Any:
            self._fixed_sub_types = None
        else:
            self._fixed_sub_types = fixed_sub_types
        self._add_wrapper(self._fixed_sub_types, add_one=False)
        self._allow_additions = allow_additions
        self._copy_filename = ".iterable_edit_widget_copy.pkl"
        if allow_additions:
            # add buttons
            max_width = 200
            self._add_button = TextPushButton("Add", self._add_dialog, max_width=max_width)
            self._copy_button = TextPushButton("Copy", self.copy, max_width=max_width)
            self._paste_button = TextPushButton("Paste", self.paste, max_width=max_width)
            self._super_layout.add_widgets([self._add_button, self._copy_button, self._paste_button])
            if not self._widgets or self.single_layout.count():
                self.remove_last_button = TextPushButton("Remove last", self._remove_last_single_entry)
                self.single_layout.addWidget(self.remove_last_button)

    def copy(self):
        """
        write a hidden pickle file
        """
        obj = [self._fixed_sub_types, self._allow_additions, self.get_values()]
        with open(self._copy_filename, "wb") as f:
            pickle.dump(obj, f)

    def paste(self):
        """
        read a hidden pickle file
        """
        if not path.isfile(self._copy_filename):
            write_error_message("Cannot paste, No copy available")
            return
        with open(self._copy_filename, "rb") as f:
            copy = pickle.load(f)
        if not isinstance(copy, list) or len(copy) != 3:
            write_error_message("Cannot paste, copy is not an IterableEditWidget")
            return
        self.clear()
        self._fixed_sub_types = copy[0]
        self._allow_additions = copy[1]
        for value in copy[2]:
            self._add_by_value(value)

    def clear(self):
        """
        clear all widgets
        """
        for widget in self._widgets:
            if any(self.single_layout.itemAt(i).widget() == widget for i in range(self.single_layout.count())):
                self._remove_entries(widget, self.single_layout)
            elif any(self._super_layout.itemAt(i).widget() == widget for i in range(self._super_layout.count())):
                self._remove_entries(widget, self._super_layout)
            else:
                pass

    def _add_by_value(self, value: Any) -> None:
        widget, getter = self._parent.construct_widget_based_on_type(value)
        self.add(widget, getter)

    def add(self, other: QWidget, getter: Callable[[], Any]) -> None:
        self._widgets.append(other)
        self._getters.append(getter)
        if not isinstance(other, IterableEditWidget):
            # single remove button
            offset = 0 if self.remove_last_button is None else 1
            self.single_layout.insertWidget(self.single_layout.count() - offset, other)
        elif self._add_button is None:
            self._super_layout.addWidget(other)
        else:
            remove_button = QPushButton("Remove")
            remove_button.clicked.connect(  # pylint: disable=no-member
                lambda: self._remove_entries(other, self._super_layout)
            )
            # use inserts because of buttons
            offset = 0 if other.remove_last_button is None else 1
            other.single_layout.insertWidget(other.single_layout.count() - offset, remove_button)
            # add, copy, paste buttons
            super_offset = 0 if self._add_button is None else 3
            self._super_layout.insertWidget(self._super_layout.count() - super_offset, other)

    def _remove_last_single_entry(self) -> None:
        if not self._widgets:
            return
        offset = 1 if self._add_button is None else 2  # because of remove button
        item = self.single_layout.itemAt(self.single_layout.count() - offset)
        self._remove_entries(item.widget(), self.single_layout)

    def _remove_entries(self, widget: QWidget, layout) -> None:
        # our data structures
        index = self._widgets.index(widget)
        self._widgets.pop(index)
        self._getters.pop(index)
        # widget visibility
        widget.setAttribute(Qt.WA_DeleteOnClose)
        widget.close()
        widget.setParent(None)  # type: ignore
        layout.removeWidget(widget)

    def get_values(self) -> Iterable:
        return [getter() for getter in self._getters]

    def _add_dialog(self) -> None:
        if self._fixed_sub_types is None and not self._getters:
            # no type specified, ask for type
            text = text_input_box(self, "Add list entry", "Please specify the type of the list entry",
                                  QLineEdit.Normal, "int")
            if not text:
                write_error_message("No type specified, aborting")
                return
            try:
                cls = eval(text)  # pylint: disable=eval-used
            except NameError:
                write_error_message(f"Given type {text} is not a valid type")
                return
            except TypeError:
                write_info_message(f"Trying to infer type from {text}")
                try:
                    cls = type(text)
                except TypeError:
                    write_error_message(f"Could not infer type from {text}")
                    return
            self._fixed_sub_types = cls
        elif self._fixed_sub_types is None:
            self._fixed_sub_types = type(self._getters[-1]())
        self._add_wrapper(self._fixed_sub_types, add_one=True)

    def _add_wrapper(self, sub_types: Union[type, List[type], None], add_one: bool = False) -> None:
        if isinstance(sub_types, list):
            for t in sub_types:
                widget, getter = self._parent.construct_widget_based_on_type(t)
                self.add(widget, getter)
        elif sub_types is not None and hasattr(sub_types, "__origin__") \
                and getattr(sub_types, "__origin__") is not Union:
            widget = IterableEditWidget(self._parent, list(getattr(sub_types, "__args__", True)))  # type: ignore
            self.add(widget, widget.get_values)
        elif add_one:
            widget, getter = self._parent.construct_widget_based_on_type(sub_types)
            self.add(widget, getter)

    def __len__(self) -> int:
        return len(self._widgets)
