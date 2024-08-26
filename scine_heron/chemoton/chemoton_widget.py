#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from random import random, randint
from time import sleep
from typing import Dict, Union, Optional, Any, TYPE_CHECKING, List, Tuple, Callable
from threading import Thread

from PySide2.QtGui import QCloseEvent
from PySide2.QtCore import QThread, Qt
from PySide2.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
)
from PySide2.QtCore import QObject
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal

from scine_chemoton.gears import Gear
from scine_chemoton.gears.elementary_steps import ElementaryStepGear
from scine_chemoton.engine import Engine  # pylint: disable=import-error
from scine_chemoton.steering_wheel.network_expansions import NetworkExpansion  # pylint: disable=import-error
from scine_chemoton.steering_wheel.selections import Selection  # pylint: disable=import-error
from scine_chemoton.steering_wheel.datastructures import GearOptions  # pylint: disable=import-error

from scine_heron.containers.start_stop_widget import StartStopWidget
from scine_heron.containers.buttons import TextPushButton
from scine_heron.containers.layouts import HorizontalLayout
from scine_heron.containers.wrapped_label import WrappedLabel
from scine_heron.chemoton.class_searcher import ChemotonClassSearcher
from scine_heron.settings.class_options_widget import ClassOptionsWidget
from scine_heron.settings.dict_option_widget import DictOptionWidget
from scine_heron.settings.docstring_parser import DocStringParser
from scine_heron.utilities import write_info_message, write_error_message, construct_sound


class EngineWidget(StartStopWidget):
    """
    A widget that holds a single Chemoton engine, its gear, and its settings.
    It allows interaction with them via buttons.
    """
    # signal that is emitted when a single run is finished
    # this exists, so that this widget's thread class can communicate with the widget.
    single_run_finished = Signal()

    class SingleRunChecker(QThread):
        """
        A utility class for the engine widget that checks whether a single run is finished.
        This is useful, because then the widget can join the engine.
        """

        def __init__(self, parent: Optional[QWidget], engine: Engine, finished_signal: Signal):
            """
            Construct the Thread.
            Every instance of this class can only work on a single engine.

            Parameters
            ----------
            parent : Optional[QWidget]
                The parent widget.
            engine : Engine
                The engine we should observe
            finished_signal : Signal
                The signal we emit, when the engine has gone through a single run.
            """
            super().__init__(parent)
            self._counter = 0
            self._signal = finished_signal
            self._engine = engine
            self._stop = False
            self._sleep_time = 0.1

        def is_running(self) -> bool:
            """
            Whether this thread is running
            """
            return not self._stop

        def stop(self) -> None:
            """
            Stop the thread (not the engine!)
            """
            self._stop = True
            sleep(2 * self._sleep_time)

        def run(self):
            """
            The main loop of the thread.
            It checks the number of gear loops and emits a signal, when it has changed and then exits.
            """
            self._stop = False
            new_counter = self._counter
            while new_counter == self._counter and not self._stop:
                sleep(self._sleep_time)
                new_counter = self._engine.get_number_of_gear_loops()
            self._signal.emit()
            self.exit(0)

    def __init__(
        self,
        parent: Optional[QObject],
        engine: Engine,
        gear: Gear,
        engine_label: str,
        gear_name: str,
        filter_description: str = "None",
    ) -> None:
        """
        Construct the engine widget with the engine, its gear and additional descriptions.

        Parameters
        ----------
        parent : Optional[QObject]
            The parent widget.
        engine : Engine
            The engine to be run
        gear : Gear
            The gear of the engine
        engine_label : str
            The label of this widget
        gear_name : str
            The name of the gear
        filter_description : str, optional
            A description of the set filters, by default "None"
        """
        super().__init__(parent)
        self._parent = parent

        self.setMaximumWidth(300)

        self.engine = engine
        self.gear = gear
        if isinstance(gear, ElementaryStepGear):
            self._sound_start = construct_sound("engine-2")
        else:
            self._sound_start = construct_sound(f"engine-{randint(0, 1)}")
        self._sound_stop = construct_sound("break")
        self._sound_stop.stop()
        self._sound_start.stop()
        self.__engine_is_working = False
        self.__engine_is_joining = False

        # Create layout and add widgets
        self._layout.addWidget(WrappedLabel(engine_label))

        self.__add_gear_at_layout(gear_name)
        self._add_filter_at_layout(filter_description)

        self.button_start_stop = TextPushButton("Start", self.start_stop)
        self.button_single = TextPushButton("Single Run", self.__single_engine_run)

        self._layout.addWidget(self.button_start_stop)
        self._layout.addWidget(self.button_single)
        self.single_run_finished.connect(self.start_stop)  # pylint: disable=no-member
        self.__single_observer: Optional[Any] = None
        self._join_thread: Optional[Thread] = None

        self._add_settings_and_delete_buttons()

        self.init_arguments += [self.engine, self.gear, engine_label, gear_name, filter_description]

        self.setLayout(self._layout)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Clean up our engine before we close the widget.

        Parameters
        ----------
        event : QCloseEvent
            The close event.
        """
        if self._join_thread is not None:
            self._join_thread.join()
        if self.__single_observer is not None and self.__single_observer.is_running():
            self.__single_observer.stop()
            self.__single_observer.wait()
        super().closeEvent(event)

    def set_docstring_dict(self, doc_string_parser: DocStringParser) -> None:
        """
        Set the docstring dictionary for this widget based on our gear and if it is an elementary step gear,
        the trial generator of the gear.

        Parameters
        ----------
        doc_string_parser : DocStringParser
            The parser that can extract the docstrings.
        """
        self._docstring_dict = doc_string_parser.get_docstring_for_object_attrs(
            self.gear.__class__.__name__, self.gear.options
        )
        if isinstance(self.gear, ElementaryStepGear):
            # additional optional stuff
            additionals: List[Dict[str, str]] = []
            if hasattr(self.gear, "trial_generator"):
                obj = self.gear.trial_generator.options
                additionals.append(doc_string_parser.get_docstring_for_object_attrs(obj.__class__.__name__, obj))
            for add in additionals:
                self._docstring_dict = {**self._docstring_dict, **add}

    def stop_class_if_working(self) -> None:
        """
        Stop our engine.
        """
        if self.__engine_is_working:
            if self.__single_observer is not None and self.__single_observer.is_running():
                self.__single_observer.stop()
            self.engine.stop()

    def is_running(self) -> bool:
        return self.__engine_is_working

    def __single_engine_run(self) -> None:
        """
        Run the engine a single time, unless it is already running.
        """
        if self.__engine_is_working:
            write_info_message("Engine is still running")
            return
        self.__switch_status()
        self.__single_observer = self.SingleRunChecker(self, self.engine, self.single_run_finished)
        self.__single_observer.start()
        self.engine.run(single=True)
        if self.button_settings is not None:
            self.button_settings.setEnabled(False)
        if self.button_delete is not None:
            self.button_delete.setEnabled(False)
        # make sure run is not stopped at break point
        self.gear.stop_at_break_point(False)
        self.engine.set_gear(self.gear)

    def __switch_status(self):
        """
        Switch our own status.
        """
        if self.__engine_is_working:
            self.change_color()
            self.button_start_stop.setText("Start")
            if getattr(self._parent, "sound_allowed", False):
                sleep(random() * 0.5)
                self._sound_start.stop()
                self._sound_stop.play()
        else:
            self.change_color(self.green)
            self.button_start_stop.setText("Stop")
            if getattr(self._parent, "sound_allowed", False):
                sleep(random() * 0.5)
                self._sound_stop.stop()
                self._sound_start.play()
        self.__engine_is_working = not self.__engine_is_working

    def start_stop(self, start_all: bool = False, stop_all: bool = False) -> None:
        """
        Start the engine if it is not running, stop it otherwise.

        Parameters
        ----------
        start_all : bool, optional
            Ensures that our engine is not stopped, if it is already running if set to True, by default False
        stop_all : bool, optional
            Influences the joining behavior, if set to True, because if multiple engines
            are stopped, the joining can be simplified, by default False
        """
        if start_all and stop_all:
            write_error_message("Internal Error")
            return
        if start_all and not self.__engine_is_working:
            self._run_impl()
        elif stop_all and self.__engine_is_working:
            if self.__single_observer is not None and self.__single_observer.is_running():
                self.__single_observer.stop()
            if self.__engine_is_joining:
                # expect separate join() call from caller of this method with stop_all=True
                return
            self.engine.stop()
        elif not start_all and self.__engine_is_working:
            if self.__single_observer is not None and self.__single_observer.is_running():
                self.__single_observer.stop()
            if self.__engine_is_joining:
                write_info_message("Still waiting for previous loop of engine to finish")
                return
            self.engine.stop()
            # do join with thread here
            self._join_thread = Thread(target=self.join)
            self._join_thread.start()
        elif not stop_all and not self.__engine_is_working:
            self._run_impl()

    def _run_impl(self) -> None:
        """
        Run the engine, ensure we have the right status and control settings access.
        """
        self.engine.run()
        self.__switch_status()
        if self.button_settings is not None:
            self.button_settings.setEnabled(False)
        if self.button_delete is not None:
            self.button_delete.setEnabled(False)

    def join(self, force_join: bool = False) -> None:
        """
        Join the engine if we are working or want to enforce join.

        Parameters
        ----------
        force_join : bool, optional
            Join the engine even if we are not working, by default False
        """
        if not self.__engine_is_working and not force_join:
            # no join required if not working
            return
        if self.__engine_is_joining:
            while self.__engine_is_joining:
                # in case joining was initiated before and is in progress, we let the current join finish
                # and don't run another join, but this method is expected to only return once it was joined,
                # so, we imitate join behavior by stalling here
                sleep(0.1)
            # join is concluded, simply return
            return
        self.__engine_is_joining = True
        self.engine.join()
        if not force_join or self.__engine_is_working:
            # change if we don't force join, or if we are force joining a running engine
            self.__switch_status()
        if self.button_settings is not None:
            self.button_settings.setEnabled(True)
        if self.button_delete is not None:
            self.button_delete.setEnabled(True)
        # make sure next run is not stopped at break point
        self.gear.stop_at_break_point(False)
        self.engine.set_gear(self.gear)
        self.__engine_is_joining = False

    def __add_gear_at_layout(self, gear_name: str) -> None:
        """
        Adds the information about the gear to our layout

        Parameters
        ----------
        gear_name : str
            The name of the gear
        """
        layout = HorizontalLayout()
        layout.setAlignment(Qt.AlignLeft)

        self.gear_label = QLabel("Gear:")
        self.gear_widget = WrappedLabel(gear_name)

        layout.add_widgets([self.gear_label, self.gear_widget])

        self._layout.addLayout(layout)

    @staticmethod
    def get_settings(gear: Gear) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        The EngineWidget holds a getter/setter for the settings, because they are more
        complicated to extract due to varying APIs between the different gears.

        Notes
        -----
        The getter/setter are static methods so that our classes can access the settings of some gears.

        Parameters
        ----------
        gear : Gear
            The gear we want the settings from

        Returns
        -------
        Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]
            The settings and an optional mapping that allows to map the settings back to the object
        """
        if not isinstance(gear, ElementaryStepGear):
            return DictOptionWidget.get_attributes_of_object(gear.options), {}
        # gather some more options
        option_attrs = DictOptionWidget.get_attributes_of_object(gear.options)
        trial_attrs = DictOptionWidget.get_attributes_of_object(gear.trial_generator.options)
        final_trial_attrs: Dict[str, Any] = {}
        attr_mapping = {}
        for k, v in trial_attrs.items():
            if k.endswith("options"):
                additional_attr = DictOptionWidget.get_attributes_of_object(v)
                # ensure unique keys
                mod_additional_attr = {f"{k}.{subkey}": subvalue for subkey, subvalue in additional_attr.items()}
                attr_mapping[k] = mod_additional_attr
                final_trial_attrs = {**final_trial_attrs, **mod_additional_attr}
            else:
                final_trial_attrs[k] = v
        return {**option_attrs, **final_trial_attrs}, attr_mapping

    @staticmethod
    def set_settings(gear: Gear, options: Dict[str, Any], attribute_mapping: Dict[str, Dict[str, Any]]) -> None:
        """
        The EngineWidget holds a getter/setter for the settings, because they are more
        complicated to extract due to varying APIs between the different gears.

        Notes
        -----
        The getter/setter are static methods so that our classes can access the settings of some gears.

        Parameters
        ----------
        gear : Gear
            The gear we want the settings from
        options : Dict[str, Any]
            The settings we want to set
        attribute_mapping : Dict[str, Dict[str, Any]]
            The mapping of the settings to the actual object
        """
        if not isinstance(gear, ElementaryStepGear):
            # easy case
            DictOptionWidget.set_attributes_to_object(gear.options, options)
            return
        # gather partial options
        option_attrs = DictOptionWidget.get_attributes_of_object(gear.options)
        trial_attrs = DictOptionWidget.get_attributes_of_object(gear.trial_generator.options)
        # apply options
        for k, v in options.items():
            try:
                if k in option_attrs:
                    setattr(gear.options, k, v)
                if k in trial_attrs:
                    setattr(gear.trial_generator.options, k, v)
                if "." in k:
                    mapping_key = k.split(".")[0]
                    if mapping_key in attribute_mapping:
                        # TODO previously relied on mapping value here, but GearOptions in NetworkExpansion
                        # made it necessary to map back to the original value, so the mapping
                        # datastructure could actually be simplified to a single dictionary
                        for subkey in attribute_mapping[mapping_key].keys():
                            unmod_key = subkey.split(".")[-1]
                            if unmod_key == k:
                                setattr(getattr(gear.trial_generator.options, mapping_key), unmod_key, v)
                                break
            except NotImplementedError:
                pass  # can be caused by trial generator warning that settings are ignored, but doesn't matter here

    def _show_settings(self) -> None:
        """
        Display the gear settings in a pop that allows to edit the settings.
        """
        options, mapping = self.get_settings(self.gear)
        setting_widget = ClassOptionsWidget(
            options, self._docstring_dict, parent=self, add_close_button=True, allow_removal=False
        )
        setting_widget.exec_()
        self.set_settings(self.gear, options, mapping)
        self.engine.set_gear(self.gear)


class ExplorationStepWidget(StartStopWidget):
    """
    An abstract base class for widget in a SteeringWheel exploration protocol.
    Can combine identical methods our information access from holding widgets.
    """
    exploration_step_label = "ExplorationStep:"
    changed_settings_signal = Signal(dict)

    def __init__(self, parent: Optional[QObject], exploration_step: Union[Selection, NetworkExpansion],
                 label: str, name: str, *args, **kwargs) -> None:
        """
        Construct the widget with the underlying exploration step and some name information.

        Parameters
        ----------
        parent : Optional[QObject]
            The parent widget
        exploration_step : Union[Selection, NetworkExpansion]
            The held exploration step that should be run
        label : str
            The label of the widget
        name : str
            The name of the step
        """
        super().__init__(parent)
        self.exploration_step = exploration_step
        self.label = label
        self.name = name

        self._layout.addWidget(WrappedLabel(label))
        self.chemical_step_widget: Optional[QLineEdit] = None
        self.init_arguments += [self.exploration_step, self.label, self.name]

    def _create_step_sub_layout(self):
        """
        Add the information about the exploration step to our widget.
        """
        sub_layout = QHBoxLayout()
        sub_layout.setAlignment(Qt.AlignLeft)
        sub_layout.addWidget(WrappedLabel(self.exploration_step_label))

        self.chemical_step_widget = WrappedLabel(self.name)
        sub_layout.addWidget(self.chemical_step_widget)

        self._layout.addLayout(sub_layout)

    def set_docstring_dict(self, doc_string_parser: DocStringParser) -> None:
        """
        Set our docstring information based on a parser that can extract it from the step.

        Parameters
        ----------
        doc_string_parser : DocStringParser
            The parser to extract with
        """
        self._docstring_dict = doc_string_parser.get_docstring_for_instance_init(
            self.exploration_step.__class__.__name__, self.exploration_step.options
        )

    def stop_class_if_working(self) -> None:
        """
        To be implemented by child class
        """

    def start_stop(self, start_all: bool = False, stop_all: bool = False) -> None:
        """
        To be implemented by child class
        """

    def join(self, force_join: bool = False) -> None:
        """
        To be implemented by child class
        """


class SelectionWidget(ExplorationStepWidget):
    """
    The widget that holds a Selection in a steering exploration protocol.
    """
    exploration_step_label_text = "Selection:"

    def __init__(self, parent: QObject, selection: Selection, label: str, selection_name: str,
                 additional_filter_description: str = "None", as_global: bool = False,
                 with_delete: bool = True, global_for_first: bool = False) -> None:
        """
        Constructs the widget with the selection, some name information, and if it is a global selection.

        Parameters
        ----------
        parent : QObject
            The parent widget
        selection : Selection
            The underlying selection
        label : str
            The name of this widget
        selection_name : str
            The name of the selection
        additional_filter_description : str, optional
            Description of any additional filters, by default "None"
        as_global : bool, optional
            If this selection is a global selection, by default False
        with_delete : bool, optional
            If a delete button should be added to our layout, by default True
        global_for_first : bool, optional
            If this global selection should be applied to the first step
            in an exploration protocol, by default False

        Raises
        ------
        RuntimeError
            If conflicting arguments concerning the global selection are given.
        """
        if global_for_first and not as_global:
            raise RuntimeError("Internal error")
        if as_global:
            this_label = f"Global: {label}"
        else:
            this_label = label
        super().__init__(parent, selection, this_label, selection_name)
        self._parent = parent
        self.additional_filter_description = additional_filter_description
        self.as_global = as_global
        self.global_for_first = global_for_first
        self._create_step_sub_layout()
        self._add_filter_at_layout(additional_filter_description)

        if not as_global:
            self.button_copy_results = TextPushButton("Copy results as last selection")
            self._layout.addWidget(self.button_copy_results)
            self.button_copy_results.setEnabled(False)  # can only be enabled after the first run
        if with_delete:
            self._add_settings_and_delete_buttons()

        self.init_arguments += [self.additional_filter_description, self.as_global, with_delete, self.global_for_first]

        self.setLayout(self._layout)

    def _show_settings(self) -> None:
        """
        Display the settings in a pop-up and manipulate them based on changes.
        """
        setting_widget = ClassOptionsWidget(
            self.exploration_step.options.__dict__, self._docstring_dict, parent=self, add_close_button=True,
            allow_removal=False
        )
        setting_widget.exec_()
        self.changed_settings_signal.emit(self.exploration_step.options.__dict__)


class StepWidget(ExplorationStepWidget):
    """
    Constructs a widget holding a NetworkExpansion.
    """
    exploration_step_label_text = "Network Expansion:"

    def __init__(self, parent: Optional[QObject], step: NetworkExpansion, label: str, step_name: str,
                 gear_options: Optional[GearOptions] = None) -> None:
        """
        Construct the widget with the Expansion, some name information and the gear options of the step.

        Parameters
        ----------
        parent : Optional[QObject]
            The parent widget
        step : NetworkExpansion
            The underlying network expansion.
        label : str
            The name of the widget
        step_name : str
            The name of the network expansion
        gear_options : Optional[GearOptions], optional
            The optional options of all the gears of the network expansion, by default None
        """
        super().__init__(parent, step, label, step_name)
        self.gear_options = gear_options
        self._create_step_sub_layout()
        self._add_settings_and_delete_buttons()
        self.setLayout(self._layout)
        self.init_arguments.append(self.gear_options)

    def _show_settings(self) -> None:
        """
        Displays the settings of the network expansion including its gear options in a pop-up
        and manipulate them based on changes.

        Notes
        -----
        Accesses main window to get the current database credentials so that we can set-up the
        network expansion without running it to get the correct gear options.
        """
        from scine_heron import find_main_window
        main = find_main_window()
        suggestions: Optional[dict] = None
        if main is not None:
            credentials = main.toolbar.current_credentials()
            if credentials is not None:
                self.exploration_step.dry_setup_protocol(credentials)
                current_gears = self.exploration_step.current_gears()
                suggestions = generate_gear_name_settings_suggestions(current_gears)
                # very important to clean the protocol again, otherwise the object is not thread safe,
                # this would cause safe failures later on
                self.exploration_step.protocol = []
        settings = self.exploration_step.options.__dict__
        setting_widget = ClassOptionsWidget(
            settings, self._docstring_dict, parent=self, add_close_button=True,
            allow_removal=False, suggestions_by_name=suggestions
        )
        setting_widget.exec_()
        self.exploration_step.options.__dict__.update(settings)
        self.changed_settings_signal.emit(self.exploration_step.options.__dict__)


def generate_gear_name_settings_suggestions(possible_gears: Optional[List[Gear]] = None) \
        -> Dict[str, Dict[str, Callable]]:
    """
    Utility function that allows us to generate an object that can be passed to DictOptionWidget,
    such that we can give the correct suggestion for the case of adding a new GearOptions entry.

    Returns
    -------
    Dict[str, Dict[str, Callable]]
        A dictionary with the names of gears and a callable that returns their settings
    """
    suggestions: Dict[str, Dict[str, Callable]] = {"gear_options": {}}
    if possible_gears is None:
        possible_gears = construct_all_possible_gears()
    suggestions["gear_options"] = {'gears': lambda: possible_gears}
    return suggestions


def construct_all_possible_gears() -> List[Gear]:
    """
    A utility function that constructs a list of all gears found by the ChemotonClassSearcher.

    Returns
    -------
    List[Gear]
        The list of found gears
    """
    gear_searcher = ChemotonClassSearcher(Gear)
    return [gear() for gear in gear_searcher.values()]
