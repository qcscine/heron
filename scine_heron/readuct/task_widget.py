#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

import signal
from time import sleep
from typing import Dict, Optional, Any, List, TYPE_CHECKING, Tuple, Callable
from threading import Thread

from PySide2.QtGui import QCloseEvent
from PySide2.QtWidgets import (
    QLabel,
    QPushButton,
    QWidget
)
from PySide2.QtCore import QObject, QThread
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal

import scine_utilities as su
import scine_readuct as readuct  # noqa  pylint: disable=unused-import  # used via eval

from scine_heron.containers.buttons import TextPushButton
from scine_heron.settings.class_options_widget import ClassOptionsWidget
from scine_heron.settings.docstring_parser import DocStringParser
from scine_heron.utilities import write_error_message, thread_safe_error


from scine_heron.containers.start_stop_widget import StartStopWidget


class TaskWidget(StartStopWidget):
    """
    Widget for any ReaDuct Task
    """

    finished_task = Signal()
    """
    emitted when the task is finished
    """
    update_systems = Signal(list, list, dict)
    """
    update_systems
        list of input names of the task they got created from
        list of names to be updated
        a dictionary with the names as keys and calculators as values
    """

    def __init__(
        self,
        parent: QWidget,
        inputs: List[str],
        task_name: str,
        widget_title: str,
        task_settings: Dict[str, Any],
        settings_suggestions: Optional[List[str]] = None
    ) -> None:
        """
        Construct a task widgets with all the required details to execute it.
        Task settings can still be modified later

        Parameters
        ----------
        parent : QWidget
            The parent of the widget, has to actually be a ReaductTab widget,
            but cannot be specified due to circular imports
        inputs : List[str]
            The names of the input systems
        task_name : str
            The name of the task
        widget_title : str
            The title of the widget
        task_settings : Dict[str, Any]
            The settings of the task
        settings_suggestions : Optional[List[str]], optional
            An optional list of setting names that are suggested, when the user wants to add
            a task setting, by default None
        """
        super().__init__(parent)
        self._parent = parent
        self._result: Optional[Tuple[Dict[str, su.core.Calculator], bool]] = None
        self.inputs = inputs
        self._task_name = task_name
        self._task_settings = task_settings
        self._settings_suggestions = settings_suggestions
        outputs = self._task_settings.get("output")
        self.outputs: List[str] = self.inputs if outputs is None else outputs

        self.__task_is_joining = False

        # Create layout and add widgets
        self.name = widget_title
        self._layout.addWidget(QLabel(widget_title))

        self.button_settings = QPushButton("Settings")
        self.button_delete = QPushButton("Delete")
        self.button_start_stop = TextPushButton("Start", self.start_stop)
        self._layout.addWidget(self.button_start_stop)
        self._add_settings_and_delete_buttons()

        self._run_thread: Optional[RunThread] = None
        self._join_thread: Optional[Thread] = None
        self._finish_check: Optional[CheckForFinishedTask] = None
        self.finished_task.connect(lambda: self.join(force_join=True))
        self.finished_task.connect(lambda: self.__switch_status(False))

        self.init_arguments += [self.inputs, self._task_name, self._task_settings]

        self.setMaximumWidth(300)
        self.setLayout(self._layout)

    def _stop_finish_check(self):
        """
        Stop our sub thread that checks on our task if it is finished.
        """
        if self._finish_check is not None:
            if self._finish_check.is_running():
                self._finish_check.stop()
            self._finish_check.wait()

    def is_working(self) -> bool:
        """
        Return if the task we are wrapping is currently running.

        Returns
        -------
        bool
            True if the task is running, False otherwise
        """
        return self._run_thread is not None and self._run_thread.isRunning()

    def _stop(self) -> None:
        """
        Stop our task.
        """
        if self._run_thread is not None:
            self._run_thread.terminate()
            self.change_color()

    def _run(self, message_container: Optional[List[str]] = None) -> None:
        """
        Run our task. The argument controls if we run it in blocking or non-blocking mode.

        Parameters
        ----------
        message_container : Optional[List[str]], optional
            An optional list in which encountered error messages are stored, this ensures thread safety.
            It therefore also controls if the task is run non-blocking (empty list) or blocking (None),
            by default None
        """
        run_method = eval(f"readuct.run_{self._task_name.lower()}_task")  # pylint: disable=eval-used
        calculators = self._parent.get_systems()
        self.change_color(self.orange)
        if message_container is None:
            # non-blocking run
            self._run_thread = RunThread(self, target=run_method, args=(calculators, self.inputs),
                                         kwargs=self._task_settings)
            self._run_thread.error_signal.connect(  # pylint: disable=no-member
                write_error_message
            )
            self._run_thread.start()
            self._finish_check = CheckForFinishedTask(self, self.finished_task)
            self._finish_check.start()
        else:
            # blocking run
            try:
                self.__switch_status(True)
                self._result = run_method(calculators, self.inputs, **self._task_settings)
                self.finished_task.emit()
            except BaseException as e:
                message_container.append(str(e))
                self._result = ({}, False)
                self.change_color(self.red)
                self.__switch_status(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Make sure we stop and join all our sub threads

        Parameters
        ----------
        event : QCloseEvent
            The close event
        """
        if self._join_thread is not None:
            self._join_thread.join()
        if self._run_thread is not None:
            # if self._run_thread.is_alive():
            if self._run_thread.isRunning():
                self._stop()
            self._run_thread.wait()
        self._stop_finish_check()
        super().closeEvent(event)

    def set_docstring_dict(self, doc_string_parser: DocStringParser) -> None:
        """
        Set the docstring dictionary for our task settings.
        Currently not supported because no clear API on ReaDuct's side.

        Parameters
        ----------
        doc_string_parser : DocStringParser
            The parser that could parse doc from Python code.
        """
        self._docstring_dict = {}

    def stop_class_if_working(self) -> None:
        """
        Stops the class if we are working, but does not do anything if we are not working
        """
        if self.is_working():
            self._stop()

    def __switch_status(self, status: bool):
        """
        Changes our appearance and settings access based on the changed status.

        Parameters
        ----------
        status : bool
            The new status
        """
        if status:
            # we are starting
            self.button_start_stop.setText("Stop")
            if self.button_settings is not None:
                self.button_settings.setEnabled(False)
        else:
            # we have stopped
            self.button_start_stop.setText("Start")
            if self.button_settings is not None:
                self.button_settings.setEnabled(True)

    def get_result(self) -> Tuple[Dict[str, su.core.Calculator], bool]:
        """
        Returns the results of the executed task just like a direct ReaDuct call.
        Returns an empty dictionary and False, if the task is not finsihed yet.

        Returns
        -------
        Tuple[Dict[str, su.core.Calculator], bool]
            The results as tuple with the first argument being the systems map containing all calculators
            and the second being a boolean signalling if the task was successful or not
        """
        if self._result is None:
            return {}, False
        return self._result

    def start_stop(self, start_all: bool = False, stop_all: bool = False,
                   message_container: Optional[List[str]] = None) -> None:
        """
        Starts or stops the widget, i.e. the wrapping ReaDuct task.
        Optional arguments alter the behavior based on the fact that this is not the only task being
        started or stopped.

        Parameters
        ----------
        start_all : bool, optional
            If all tasks in the parent container are started, however blocking vs. non-blocking behavior
            is governed by the passed message_container, by default False
        stop_all : bool, optional
            If all tasks in the parent container are stopped at once, by default False
        message_container : Optional[List[str]], optional
            An optional list in which encountered error messages are stored, this ensures thread safety.
            It therefore also controls if the task is run non-blocking (empty list) or blocking (None),
            by default None
        """
        if start_all and stop_all:
            thread_safe_error("Internal Error", message_container)
            return
        if start_all and not self.is_working():
            self.__switch_status(True)
            self._run(message_container)
        elif stop_all and self.is_working():
            if self.__task_is_joining:
                # expect separate join() call from caller of this method with stop_all=True
                return
            self._stop()
        elif not start_all and self.is_working():
            if self.__task_is_joining:
                thread_safe_error("Still waiting for task to finish", message_container)
                return
            self._stop()
            # do join with thread here
            self._join_thread = Thread(target=self.join)
            self._join_thread.start()
        elif not stop_all and not self.is_working():
            self._run(message_container)
            self.__switch_status(True)

    def join(self, force_join: bool = False) -> Tuple[Dict[str, su.core.Calculator], bool]:
        """
        Joins the sub thread and gather the result of the task to save it in this wrapping class
        and make it obtainable through the getter and also return the result on this method.

        Parameters
        ----------
        force_join : bool, optional
            no effect here, by default False

        Returns
        -------
        Tuple[Dict[str, su.core.Calculator], bool]
            The results as tuple with the first argument being the systems map containing all calculators
            and the second being a boolean signalling if the task was successful or not
        """
        if not self.is_working() and not force_join:
            # no join required if not working
            return self.get_result()
        if self._run_thread is None:
            return self.get_result()
        if self.__task_is_joining:
            while self.__task_is_joining:
                # in case joining was initiated before and is in progress, we let the current join finish
                # and don't run another join, but this method is expected to only return once it was joined,
                # so, we imitate join behavior by stalling here
                sleep(0.1)
            # join is concluded, simply return
            return self.get_result()
        self.__task_is_joining = True
        if self.is_working():
            self._stop()
        try:
            self._run_thread.wait()
        except BaseException:
            pass
        self._result = self._run_thread.result
        assert self._result is not None
        self._stop_finish_check()
        if not force_join or self.is_working():
            # change if we don't force join, or if we are force joining a running task
            self.__switch_status(False)
        systems, success = self._result
        if success or not self._task_settings.get("stop_on_error", True):
            # handle via signal to be thread safe
            self.update_systems.emit(self.inputs, self.outputs, systems)
        color = self.green if success else self.red
        self.change_color(color)
        self.__task_is_joining = False
        self._run_thread = None
        return self._result

    def _show_settings(self) -> None:
        """
        Opens the task settings as a pop-up, which allows the user to modify the task settings.
        """
        setting_widget = ClassOptionsWidget(
            options=self._task_settings, docstring=self._docstring_dict, parent=self,
            add_close_button=True, allow_removal=True, allow_additions=True,
            addition_suggestions=self._settings_suggestions,
            keys_excluded_from_io=['outputs']  # makes sure we don't overwrite the auto-generated outputs
        )
        setting_widget.exec_()

    def get_names(self) -> Tuple[str, List[str], List[str]]:
        return self._task_name, self.inputs, self.outputs

    def get_settings(self) -> Dict[str, Any]:
        return self._task_settings


class CheckForFinishedTask(QThread):
    """
    A thread that receives a TaskWidget parent, continuously checks if its task is finished,
    and if so sends out a signal and ends itself.
    """

    def __init__(self, parent: TaskWidget, signal_to_send: Signal):
        """
        Constructs the parent with the task it should check on.

        Parameters
        ----------
        parent : TaskWidget
            The widget that runs a ReaDuct task
        signal_to_send : Signal
            The signal that we should emit when the task is finished
        """
        super().__init__(parent)
        self._parent = parent
        self._signal = signal_to_send
        self._stop = False
        self._sleep_time = 1.0

    def stop(self):
        """
        Stops the thread prematurely
        """
        self._stop = True

    def is_running(self) -> bool:
        """
        If we are still running

        Returns
        -------
        bool
            True when running
        """
        return not self._stop

    def run(self):
        """
        Starts observing the task and sends out a signal when it is finished.
        """
        while not self._stop:
            sleep(self._sleep_time)
            if not self._parent.is_working():
                self._signal.emit()
                break
        self.exit(0)


class RunThread(QThread):
    """
    A thread that runs the ReaDuct task and stores the result in the thread object.
    """

    error_signal = Signal(str)
    """
    A signal to transfer error messages
    """

    def __init__(self, parent: Optional[QObject], target: Callable,  # pylint: disable=dangerous-default-value
                 args=(), kwargs={}) -> None:
        """
        Constructs the thread with the task to run as a function call.

        Parameters
        ----------
        parent : Optional[QObject]
            The parent object
        target : Callable
            The function to call
        args : tuple, optional
            The arguments to pass to the function, by default ()
        kwargs : dict, optional
            The keyword arguments to pass to the function, by default {}
        """
        super().__init__(parent)
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.result: Optional[Tuple[Dict[str, su.core.Calculator], bool]] = None

    def run(self):
        """
        Run the task and store the result in the thread object.
        """
        self.result = ({}, False)
        try:
            self.result = self.target(*self.args, **self.kwargs)
        except BaseException as e:
            self.error_signal.emit(str(e))
            self.result = ({}, False)
        self.exit(0)

    def wait(self, *args, **kwargs):

        def do_nothing(*_):
            pass

        signal.signal(signal.SIGABRT, do_nothing)
        try:
            super().wait(*args, **kwargs)
        except BaseException:
            pass
