#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from time import sleep
from typing import Optional, List, Callable, Any, Union
from threading import Thread

from PySide2.QtCore import QObject
from PySide2.QtGui import QCloseEvent
from PySide2.QtWidgets import (
    QLineEdit,
    QLabel,
    QHBoxLayout,
    QWidget,
    QStyle,
)

from scine_heron.steering.wheel_handling import WheelThread
from scine_database import Manager, Model
from scine_chemoton.steering_wheel.datastructures import (
    SelectionResult,
    Status,
    RestartPartialExpansionInfo
)
from scine_chemoton.steering_wheel.network_expansions import (
    GiveWholeDatabaseWithModelResult
)
from scine_chemoton.steering_wheel.selections import (
    Selection,
    AllCompoundsSelection,
    SelectionAndArray,
    SelectionOrArray,
    PredeterminedSelection,
)

from scine_heron.chemoton.chemoton_widget_container import ChemotonWidgetContainer
from scine_heron.chemoton.chemoton_widget import StepWidget, SelectionWidget, ExplorationStepWidget

from scine_heron.containers.start_stop_widget import StartStopWidget
from scine_heron.io.text_box import yes_or_no_question
from scine_heron.utilities import (
    write_error_message,
    write_info_message,
)


class SteeringDisplay(ChemotonWidgetContainer):
    """
    This class is the main class for the steering display.
    It holds all the subwidgets, handles the communication between them and
    holds the thread that takes care of the Steering Wheel communication.
    It also starts and stops the exploration.
    It inherits from the Chemoton container and burrows most of its functionality.

    Notes
    -----
    So far the SteeringWheel logic and display logic are not well decoupled, hence
    currently still some knowledge about the underlying Chemoton logic is recommended when manipulate things.
    """

    def __init__(self, parent: Optional[QObject], db_manager: Manager, wanted_classes: List[Any],
                 widget_creators: List[Callable], cls_black_list: Optional[List[type]] = None) -> None:
        """
        Construct the tab that holds the steering display.

        Parameters
        ----------
        parent : Optional[QObject]
            The parent of this widget.
        db_manager : Manager
            The database manager, determines the database we are exploring.
        wanted_classes : List[Any]
            The classes we should be able to construct.
        widget_creators : List[Callable]
            The functions that create the given classes.
        cls_black_list : Optional[List[type]], optional
            The classes that should not be creatable, by default None
        """
        steering_black_list = [SelectionAndArray, SelectionOrArray, PredeterminedSelection]
        if cls_black_list is None:
            cls_black_list = steering_black_list
        else:
            cls_black_list += steering_black_list
        # import to only call super here, because we want to pass the black list
        ChemotonWidgetContainer.__init__(self, parent, db_manager, wanted_classes, widget_creators, cls_black_list)

        self._settings_builder.remove_chemoton_button()
        self._max_widgets_per_row = 2
        self._is_currently_deleting = False

        self._wheel_thread = WheelThread(self, self.db_manager.get_credentials())

        self._toolbar.shortened_add_action(QStyle.SP_BrowserReload, "Restart exploration",
                                           "F5", self._restart)
        self._toolbar.shortened_add_action(QStyle.SP_DialogCancelButton, "Terminate exploration",
                                           "Ctrl+K", self._terminate)

        # take care of global selection
        self._global_selection_widget = self._default_global_selection()
        self._global_selection_position = (1, 0)
        self._grid_layout.addWidget(self._global_selection_widget, *self._global_selection_position)

        # take care of run information
        run_info_holder = QWidget()
        run_info_label = QLabel("Exploration status:")
        self._run_info = QLineEdit("not running")
        self._run_info.setReadOnly(True)
        run_info_layout = QHBoxLayout()
        run_info_layout.addWidget(run_info_label)
        run_info_layout.addWidget(self._run_info)
        run_info_holder.setLayout(run_info_layout)
        self._scroll_area_content_layout.addWidget(run_info_holder)

        # take care of Selection Display
        from .current_selection import CurrentSelectionDisplay
        self._current_selection_widget = CurrentSelectionDisplay(self)
        self._current_selection_position = (0, 2)
        self._grid_layout.addWidget(self._current_selection_widget, *self._current_selection_position)

        # take care of signals
        self._wheel_thread.status_signal.connect(  # pylint: disable=no-member
            self.color_widget
        )
        self._wheel_thread.status_signal.connect(  # pylint: disable=no-member
            self.activate_copy
        )
        self._wheel_thread.selection_signal.connect(  # pylint: disable=no-member
            self.construct_new_current_selection_widget
        )
        self._wheel_thread.run_info_signal.connect(  # pylint: disable=no-member
            self._handle_running_status
        )
        self._wheel_thread.error_signal.connect(  # pylint: disable=no-member
            write_error_message
        )
        self._stop_thread: Optional[Thread] = None
        self._wheel_thread.start()

        self.setMinimumWidth(600)
        self.setLayout(self._grid_layout)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Takes care of closing existing threads.
        """
        if self._stop_thread is not None:
            self._stop_thread.join()
        self._wheel_thread.terminate_wheel(save_progress=True)
        self._wheel_thread.terminate()
        self._wheel_thread.wait()
        super().closeEvent(event)

    def _handle_running_status(self, is_running: bool) -> None:
        """
        Should be called whenever the running status changes.
        Updates the box and the settings buttons of all subwidgets, because
        we do not want to change the settings while the exploration is running.

        Parameters
        ----------
        is_running : bool
            Our status
        """
        for widget in self.created_chemoton_widgets:
            if widget.button_settings is not None:
                widget.button_settings.setEnabled(not is_running)
            if widget.button_delete is not None:
                widget.button_delete.setEnabled(not is_running)
        if self._global_selection_widget.button_settings is not None:
            self._global_selection_widget.button_settings.setEnabled(not is_running)
        if self._global_selection_widget.button_delete is not None:
            self._global_selection_widget.button_delete.setEnabled(not is_running)
        text = "running" if is_running else "not running"
        self._run_info.setText(text)

    def _pre_io_operations(self) -> None:
        """
        Any operations to be carried out shortly before reading/writing to disk.
        Retrieves the current results from the thread and updates the widgets.

        Raises
        ------
        RuntimeError
            If unknown subwidgets are encountered.
        """
        # makes sure that all results are updated
        results = self._wheel_thread.get_results()
        if results is not None:
            scheme = self._wheel_thread.get_scheme()
            for i, (result, step) in enumerate(zip(results, scheme)):
                widget = self.created_chemoton_widgets[i]
                if not isinstance(widget, StepWidget) and not isinstance(widget, SelectionWidget):
                    raise RuntimeError("Encountered unexpected widget type")
                widget.exploration_step.status = step.status
                widget.exploration_step.set_result(result)
        self._wheel_thread.pause()

    def _post_io_operations(self) -> None:
        """
        Any operations to be carried out shortly after reading/writing to disk.
        """
        self._wheel_thread.resume()

    def _default_global_selection(self) -> SelectionWidget:
        """
        Returns the default global selection widget,
        reconstruct every time to avoid mutability issues.

        Returns
        -------
        SelectionWidget
            The default global selection widget, which is a selection of all compounds.
        """
        widget = SelectionWidget(
            self,
            AllCompoundsSelection(self.get_model()),
            "Global Selection",
            "none",
            "None",
            True,
            True
        )
        widget.setMinimumWidth(300)
        widget.setMaximumWidth(500)
        widget.setMaximumHeight(200)
        widget.setMinimumHeight(200)
        return widget

    def add_widget(self, chemoton_widget: Union[StepWidget, SelectionWidget],
                   predefined_position: bool = False) -> None:
        """
        Overloads the base widget with additional logic based on modifications,
        that the SteeringWheel may do with added steps.

        Possible modifications are:
        - adding a global selection widget
        - adding a current selection widget
        - combining subsequent selection widgets
        - added a whole DB expansion widget before the first selection

        Parameters
        ----------
        chemoton_widget : Union[StepWidget, SelectionWidget]
            The subwidget that is to be added.
        predefined_position : bool, optional
            If the widget should be on a special position, by default False

        Raises
        ------
        RuntimeError
            If the addition was not successful.
        """
        from .current_selection import CurrentSelectionDisplay
        super().add_widget(chemoton_widget, predefined_position)
        wrong_input = False
        previous_length = len(self._wheel_thread)
        if predefined_position:
            # special widget
            if isinstance(chemoton_widget, SelectionWidget):
                # global selection widget
                self._global_selection_widget.close()
                self._grid_layout.replaceWidget(self._global_selection_widget, chemoton_widget)
                self._global_selection_widget = chemoton_widget
                self._global_selection_widget.setMaximumWidth(300)
                self._global_selection_widget.setMinimumWidth(300)
                self._global_selection_widget.setMaximumHeight(200)
                self._global_selection_widget.setMinimumHeight(200)
                self._global_selection_widget.updateGeometry()
                self._wheel_thread.set_global_selection(chemoton_widget.exploration_step,
                                                        chemoton_widget.global_for_first)
            elif isinstance(chemoton_widget, CurrentSelectionDisplay):
                # current selection widget
                self._current_selection_widget.close()
                self._grid_layout.replaceWidget(self._current_selection_widget, chemoton_widget)
                self._current_selection_widget.setParent(None)  # type: ignore
                self._current_selection_widget = chemoton_widget
                self._current_selection_widget.updateGeometry()
            else:
                raise RuntimeError("Internal error, unknown widget")
        elif isinstance(chemoton_widget, StepWidget):
            # try to add step
            try:
                self._wheel_thread.append(chemoton_widget.exploration_step)
            except TypeError as e:
                write_error_message(f"Could not add step: {e}")
                super().delete_widget(chemoton_widget)
                wrong_input = True
        elif isinstance(chemoton_widget, SelectionWidget):
            # try to add selection
            try:
                self._wheel_thread.append(chemoton_widget.exploration_step)
            except TypeError as e:
                write_error_message(f"Could not add selection: {e}")
                super().delete_widget(chemoton_widget)
                wrong_input = True
        else:
            raise RuntimeError("Internal error, unknown widget")
        settings_index = len(self._wheel_thread) - 1
        if not predefined_position and not wrong_input and len(self._wheel_thread) == previous_length:
            # wheel combined selections, update widgets accordingly
            index = len(self.created_chemoton_widgets) - 2
            new_widget = self._construct_combined_selection_widget(index)

            new_widget.changed_settings_signal.connect(  # pylint: disable=no-member
                lambda settings: self._update_wheel_settings(settings, settings_index)
            )
            if new_widget.button_copy_results is not None:
                new_widget.button_copy_results.clicked.connect(  # pylint: disable=no-member
                    lambda: self._copy_results(new_widget)
                )
            super().add_widget(new_widget, predefined_position=False)
        elif not predefined_position and not wrong_input and len(self._wheel_thread) == previous_length + 2:
            # wheel added WholeDatabaseStep before selection
            # this is done if the first selection is not a first safe selection
            # but the database already contains structures
            added_index = len(self.created_chemoton_widgets) - 1
            added_widget = self.created_chemoton_widgets[added_index]
            assert isinstance(added_widget, SelectionWidget)
            additional_filters = added_widget.additional_filter_description
            new_selection = self._wheel_thread.get_scheme()[-1]
            assert isinstance(new_selection, Selection)
            whole_db_step = self._wheel_thread.get_scheme()[-2]
            assert isinstance(whole_db_step, GiveWholeDatabaseWithModelResult)
            super().delete_widget(added_widget)
            step_widget = StepWidget(self, whole_db_step, whole_db_step.name, whole_db_step.name)
            super().add_widget(step_widget, predefined_position=False)
            selection_widget = SelectionWidget(self, new_selection, new_selection.name, new_selection.name,
                                               additional_filter_description=additional_filters)
            super().add_widget(selection_widget, predefined_position=False)
            for i, w in enumerate([step_widget, selection_widget]):
                assert isinstance(w, ExplorationStepWidget)
                idx = len(self._wheel_thread) - i - 1
                w.changed_settings_signal.connect(  # pylint: disable=no-member
                    lambda settings, index=idx: self._update_wheel_settings(settings, index)
                )
                if w.button_copy_results is not None:
                    w.button_copy_results.clicked.connect(  # pylint: disable=no-member
                        lambda widget=w: self._copy_results(widget)
                    )
        elif isinstance(chemoton_widget, ExplorationStepWidget):
            # SteeringWheel did not mess with our addition
            # we can simply connect some signals
            chemoton_widget.changed_settings_signal.connect(  # pylint: disable=no-member
                lambda settings: self._update_wheel_settings(settings, settings_index)
            )
            if chemoton_widget.button_copy_results is not None:
                chemoton_widget.button_copy_results.clicked.connect(  # pylint: disable=no-member
                    lambda: self._copy_results(chemoton_widget)
                )

    def _construct_combined_selection_widget(self, step_index: int) -> SelectionWidget:
        """
        Deletes the two widgets that were combined and returns a new widget
        that represents the combined selection.

        Notes
        -----
        * Assumes that the combination has already been done in the SteeringWheel.
        * Assumes that exactly two widgets have been combined.

        Parameters
        ----------
        step_index : int
            The index of the new combined selection in the SteeringWheel.

        Returns
        -------
        SelectionWidget
            The new widget that represents the combined selection.
        """
        new_selection = self._wheel_thread.get_scheme()[step_index]
        assert isinstance(new_selection, Selection)
        additional_filters = ""
        for _ in range(2):
            widget = self.created_chemoton_widgets[step_index]
            assert isinstance(widget, SelectionWidget)
            if widget.additional_filter_description not in additional_filters:
                additional_filters += widget.additional_filter_description + "\n"
            super().delete_widget(widget)
        self._wheel_thread.reset_selection_index()
        return SelectionWidget(self, new_selection, new_selection.name, new_selection.name,
                               additional_filters)

    def _update_wheel_settings(self, settings: dict, index: int) -> None:
        """
        Propagates changes in the settings of a widget to the SteeringWheel.

        Parameters
        ----------
        settings : dict
            The new settings.
        index : int
            The index of the widget in the SteeringWheel.
        """
        self._wheel_thread.update_step_options(settings, index)

    def delete_widget(self, chemoton_widget: Union[StepWidget, SelectionWidget]) -> int:
        """
        Overloads the delete_widget method of the ChemotonWidgetContainer.
        Takes care that not only the widget is deleted but also corresponding step
        in the SteeringWheel.

        Parameters
        ----------
        chemoton_widget : Union[StepWidget, SelectionWidget]
            The widget to be deleted.

        Returns
        -------
        int
            The index of the deleted widget.
        """
        # avoid race condition if user presses delete button of multiple widgets,
        # before deletion is finished
        while self._is_currently_deleting:
            sleep(0.1)
        self._is_currently_deleting = True
        # take care of global selection
        if chemoton_widget is self._global_selection_widget:
            self._wheel_thread.remove_global_selection(chemoton_widget.exploration_step)
            self.add_widget(self._default_global_selection(), predefined_position=True)
            return 0
        # try to delete step + widget
        previous_length = len(self._wheel_thread)
        index = self.created_chemoton_widgets.index(chemoton_widget)
        try:
            self._wheel_thread.pop(index)
            index = super().delete_widget(chemoton_widget)
        except RuntimeError as e:
            write_error_message(str(e))
            index = -1
        else:
            # additional things if deletion was successful
            if len(self._wheel_thread) == previous_length - 2:
                # we combined some selections, update widgets accordingly
                # we assume we combined those around 'index'
                combined_widget = self._construct_combined_selection_widget(index - 1)
                widgets_after = []
                for i in range(index + 1, len(self._wheel_thread)):
                    widgets_after.append(self.created_chemoton_widgets[i])
                for widget in widgets_after:
                    super().delete_widget(widget)
                super().add_widget(combined_widget)
                for widget in widgets_after:
                    super().add_widget(widget)
        self._is_currently_deleting = False
        return index

    def _start_stop_all(self, start: bool, force_join: bool = False) -> None:
        """
        Overloads the _start_stop_all method of the ChemotonWidgetContainer.
        Simply propagates the run/stop calls with the SteeringWheel thread +
        some sanity checks to catch multiple calls etc.

        Parameters
        ----------
        start : bool
            Whether to start or stop the exploration.
        force_join : bool, optional
            Name stems from base class, if true the wheel is stopped also within a step,
            otherwise wait for the current step to finish.
        """
        if self.is_blocked:
            write_error_message("Currently in the process of stopping exploration, please be patient")
            return
        if start and force_join:
            write_error_message("Internal error, conflicting inputs")
            return
        if not self._wheel_thread:
            write_error_message("You have not specified any exploration steps, yet")
            return
        if start == self._wheel_thread.wheel_is_running():
            message = f"You wanted to {'start' if start else 'stop'} the exploration, but exploration is " \
                      f"{'already' if start else 'not'} running"
            write_error_message(message)
            return
        if start:
            self._play.setChecked(True)
            self._wheel_thread.start_wheel()
            self._play.setChecked(False)
        else:
            self._stop.setChecked(True)
            answer = False
            if self._wheel_thread and self._wheel_thread.wheel_is_running():
                answer = yes_or_no_question(
                    self, "You are currently exploring. "
                    "Do you want to wait for the current exploration step to finish (y) or "
                    "stop it within the step (n)", default_answer="no")
            self._stop_thread = Thread(target=self._stop_impl, args=(not answer,))
            self._stop_thread.start()

    def _stop_impl(self, within_step: bool) -> None:
        """
        Stops the SteeringWheel
        """
        self.is_blocked = True
        if within_step:
            self._wheel_thread.terminate_wheel(save_progress=True)
        else:
            self._wheel_thread.stop_wheel()
        self.is_blocked = False
        self._stop.setChecked(False)

    def _restart(self) -> None:
        """
        Restarts the exploration from scratch based on the given protocol
        without considering existing results.
        """
        if self.is_blocked:
            write_error_message("Currently in the process of stopping exploration, please be patient")
            return
        if not self._wheel_thread:
            write_error_message("You have not specified any exploration steps, yet")
            return
        answer = yes_or_no_question(self, "Are you sure you want to restart the exploration?")
        if not answer:
            write_info_message("Reset cancelled")
            return
        write_info_message("Stopping exploration")
        self._stop.setChecked(True)
        self._stop_impl(within_step=True)
        write_info_message("Restarting exploration")
        self._wheel_thread.start_wheel(restart=False)
        self._wheel_thread.reset_selection_index()

    def _terminate(self) -> None:
        """
        Terminates the underlying thread.
        """
        if self.is_blocked:
            write_error_message("Currently in the process of stopping exploration, please be patient")
            return
        answer = yes_or_no_question(self, "Are you sure you want to terminate the exploration")
        if not answer:
            write_info_message("Termination cancelled")
            return
        write_info_message("Terminate exploration")
        answer = yes_or_no_question(self, "Do you want to safe the progress before termination")
        self._wheel_thread.terminate_wheel(save_progress=answer)

    def construct_new_current_selection_widget(self, name: str, selection_result: SelectionResult) -> None:
        """
        Builds a new current selection widget, that shows the results the current selection gives
        for different potential expansions.

        Parameters
        ----------
        name : str
            The name of the widget
        selection_result : SelectionResult
            The result of the selection the widget should be built around

        Notes
        -----
        Since we always reconstruct the widget, this can lead to a large number of molecular widgets over
        time, which may eventually hit the 100 mark.
        This can be avoided by a redesign by separating the molecular widget, or update the whole widget
        instead of rebuilding it every time.
        """
        from .current_selection import CurrentSelectionDisplay
        # push quickly constructed loading info widget
        self.add_widget(CurrentSelectionDisplay.with_loading_info(self), predefined_position=True)
        # now construct real thing which requires some querying
        selection_display = CurrentSelectionDisplay(self, self.db_manager, selection_result, name)
        self.add_widget(selection_display, predefined_position=True)

    def color_widget(self, index: int, status: Status) -> None:
        """
        Colors a step widget based on its status.

        Parameters
        ----------
        index : int
            Index of the widget
        status : Status
            The status of the widget
        """
        if status == Status.FINISHED:
            color = StartStopWidget.green
        elif status == Status.FAILED:
            color = StartStopWidget.red
        elif status == Status.CALCULATING:
            color = StartStopWidget.orange
        else:
            color = ""
        self.created_chemoton_widgets[index].change_color(color)

    def activate_copy(self, index: int, status: Status) -> None:
        """
        Enables the copy results button of a widget if its type and status are appropriate.

        Parameters
        ----------
        index : int
            The index of the widget
        status : Status
            The status of the widget
        """
        if status != Status.FINISHED:
            return
        widget = self.created_chemoton_widgets[index]
        if isinstance(widget, SelectionWidget) and widget.button_copy_results is not None:
            widget.button_copy_results.setEnabled(True)

    def _copy_results(self, widget: SelectionWidget) -> None:
        """
        Creates and adds a new widget to our protocol that gives the same result as the given
        selection widget.

        Parameters
        ----------
        widget : SelectionWidget
            The widget we copy the results from
        """
        if not isinstance(widget, SelectionWidget):
            write_error_message("Failed to copy results: Exploration step is not a selection")
            return
        try:
            index = self.created_chemoton_widgets.index(widget)
        except ValueError:
            write_error_message("Failed to copy results: Selection not found")
            return
        results = self._wheel_thread.get_results()
        if results is None or index >= len(results):
            write_error_message("Failed to copy results: Results not found")
            return
        result = results[index]
        if not isinstance(result, SelectionResult):
            write_error_message("Failed to copy results: Results are not of type SelectionResult")
            return
        self._pre_io_operations()  # necessary because this ensures that selection in widget has results
        selection = widget.exploration_step
        new_widget = SelectionWidget(
            self,
            PredeterminedSelection(selection.options.model, result, logic_coupling=selection.logic_coupling),
            f"Copied results from {widget.label} at index {index}",
            widget.name, widget.additional_filter_description, False, True, False
        )
        self.add_widget(new_widget, predefined_position=False)

    def _generate_save_object(self) -> List[List[Any]]:
        """
        Puts all current widgets into one object from which the widgets can be reconstructed.

        Returns
        -------
        List[List[Any]]
            The save object
        """
        save_object = super()._generate_save_object()
        save_object.append([self._wheel_thread.get_partial_restart_info()])
        return save_object

    def _unpack_save_object(self, save_object: List[List[Any]]) -> None:
        """
        Reconstructs all widgets from the given save object.

        Parameters
        ----------
        save_object : List[List[Any]]
            The save object
        """
        partial_steps = save_object.pop(-1)[0]
        # for backwards compatibility
        if not isinstance(partial_steps, RestartPartialExpansionInfo) and isinstance(partial_steps, Model):
            save_object.append([partial_steps])
            partial_steps = None
        super()._unpack_save_object(save_object)
        self._wheel_thread.set_partial_restart_info(partial_steps)
