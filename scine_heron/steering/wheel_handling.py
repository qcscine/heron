#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from time import sleep
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PySide2.QtCore import QThread, QObject
from PySide2.QtWidgets import QLineEdit

if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal

from scine_chemoton.steering_wheel import FailedSaveException, SteeringWheel
from scine_chemoton.steering_wheel.selections import (
    Selection,
)
from scine_chemoton.steering_wheel.datastructures import (
    SelectionResult,
    Status,
    ExplorationSchemeStep,
    ExplorationResult,
    RestartPartialExpansionInfo,
)

from scine_database import Credentials

from scine_heron.io.text_box import text_input_box
from scine_heron.utilities import construct_sound


def _input(question: str) -> str:
    return text_input_box(None, "Scine Heron", question, QLineEdit.Normal, "y")


class WheelThread(QThread):
    """
    This Thread is constructed and controlled by the Steering Tab.
    When constructed, it constructs the underlying SteeringWheel and when started
    it continuously queries the SteeringWheel for certain properties and holds them in
    memory.
    It communicates mainly with its signals, but is also a wrapper around
    many SteeringWheel methods.
    """

    # signals that this threads sends to main display for transfer wheel information
    status_signal = Signal(int, Status)
    run_info_signal = Signal(bool)
    selection_signal = Signal(str, SelectionResult)

    # technical reasons
    error_signal = Signal(str)  # error message cannot be displayed from thread

    def __init__(self, parent: QObject, credentials: Credentials):
        """
        Construct the Thread and the SteeringWheel underneath.

        Parameters
        ----------
        parent : QObject
            The parent widget
        credentials : Credentials
            The credentials of the database the Wheel should work on.
        """
        super().__init__(parent)
        self._parent = parent
        self._stop = False
        self._paused = False
        self._sleep_time = 1.0
        self._last_selection_index: int = -1
        self._status_report: Dict[str, Status] = {}

        self._wheel = SteeringWheel(credentials, [], callable_input=_input)
        self._sound_start = construct_sound("engine-0")
        self._sound_stop = construct_sound("break")

    def start_wheel(self, restart: bool = True) -> None:
        """
        Starts the underlying wheel, this forks a process.

        Parameters
        ----------
        restart : bool, optional
            If the wheel should be restarted, if not, the results are deleted, by default True
        """
        if not restart:
            self._wheel.delete_results()
        self._wheel.run(allow_restart=restart, ask_for_how_many_results=True)
        if getattr(self._parent, "sound_allowed", False):
            self._sound_stop.stop()
            self._sound_start.play()

    def stop_wheel(self) -> None:
        """
        Stop the wheel gracefully.
        Whether the wheel tries to save its process, depends on the wheel defaults
        """
        if self._wheel.is_running():
            self._wheel.stop()
            if getattr(self._parent, "sound_allowed", False):
                self._sound_start.stop()
                self._sound_stop.play()
        self._wheel.join()

    def wheel_is_running(self) -> bool:
        """
        Whether the underlying wheel is currently running

        Returns
        -------
        bool
            The result
        """
        return self._wheel.is_running()

    def terminate_wheel(self, save_progress: bool) -> None:
        """
        Stop the wheel without waiting for the current step.
        """
        if getattr(self.parent(), "sound_allowed", False):
            self._sound_start.stop()
            self._sound_stop.play()
        self._wheel.terminate(try_save_progress=save_progress, suppress_warning=True)

    def terminate(self) -> None:
        """
        Stop the wheel without trying to save its progress.
        """
        if self.wheel_is_running():
            self.terminate_wheel(save_progress=False)
        super().terminate()

    def stop(self) -> None:
        """
        Stop the underlying wheel gracefully and also stop this thread.
        """
        self.stop_wheel()
        self._stop = True

    def save(self) -> None:
        """
        Save the current progress.
        """
        try:
            self._wheel.save()
        except FailedSaveException as e:
            self.error_signal.emit(f"Could not save {self._wheel.name} because {e}")

    def pause(self) -> None:
        """
        Pauses the constant result querying on the wheel by this thread.
        """
        self._paused = True

    def resume(self) -> None:
        """
        Resumes the constant result querying on the wheel by this thread.
        """
        self._paused = False

    def run(self) -> None:
        """
        Start the constant result querying on the wheel by this thread.
        """
        while not self._stop:
            while self._paused:
                sleep(0.1)
            try:
                self._run_info_check()
                self._status_check()
                self._selection_check()
            except BaseException as e:
                print(e)
                import traceback
                traceback.print_exc()
                self._abort_run()
            else:
                sleep(self._sleep_time)
        self.exit(0)

    def reset_selection_index(self) -> None:
        """
        Reset the thread's information what the latest active selection is.
        """
        self._last_selection_index = -1

    def _abort_run(self) -> None:
        """
        Stop the wheel and prints an error message
        """
        self.error_signal.emit(f"Had to stop {self._wheel.name} because an unhandable error occurred")
        self.stop_wheel()

    def _run_info_check(self) -> None:
        """
        Send the current run status as a signal
        """
        self.run_info_signal.emit(self._wheel.is_running())

    def _status_check(self) -> None:
        """
        Gather the status report of the underlying wheel and send it as a signal.

        Notes
        -----
        Strongly coupled to the exact status report construction of the SteeringWheel
        """
        report = self._wheel.get_status_report()
        if report != self._status_report:
            self._status_report = report
            for k, v in self._status_report.items():
                index = int(k.split(":")[0].strip())
                self.status_signal.emit(index, v)
            if not self._wheel.is_running():
                self.save()

    def _selection_check(self) -> None:
        """
        Queries results of the underlying wheel and send the current selection as a signal.

        Raises
        ------
        RuntimeError
            If the result retrieval fails
        """
        results = self._wheel.get_results()
        if results is None:
            return
        last_selection_result_index = max([i for i, r in enumerate(results)
                                           if r is not None and isinstance(r, SelectionResult)], default=None)
        if last_selection_result_index is not None and last_selection_result_index > self._last_selection_index:
            self._last_selection_index = last_selection_result_index
            result = results[self._last_selection_index]
            if result is None or not isinstance(result, SelectionResult) \
                    or len(self._wheel) <= last_selection_result_index:
                raise RuntimeError("No results available or wrong type")
            name = f"{last_selection_result_index}: {self._wheel.scheme[last_selection_result_index].name}"
            self.selection_signal.emit(name, result)

    def update_step_options(self, settings: dict, index: int) -> None:
        """
        Updates the options of one step in der underlying wheel.

        Parameters
        ----------
        settings : dict
            The new options
        index : int
            The index of the step
        """
        if self._wheel.is_running():
            self.error_signal.emit("Exploration running, ignoring given settings")
            return
        try:
            self._wheel.scheme[index].options.__dict__.update(settings)
        except BaseException as e:
            self.error_signal.emit(f"Failed to transfer settings: {str(e)}")
        self._wheel.save()

    def append(self, exploration_step: ExplorationSchemeStep) -> None:
        """
        Add an exploration step to the wheel.
        """
        self._wheel += exploration_step

    def pop(self, index: int) -> None:
        """
        Remove a step based on index.
        Negative indexing is supported, slicing is not supported.
        """
        self._wheel.pop(index)

    def set_global_selection(self, selection: Selection, for_first: bool) -> None:
        """
        Set a global selection to the wheel.

        Parameters
        ----------
        selection : Selection
            The global selection
        for_first : bool
            If the global selection should be added to the first step.
        """
        self._wheel.set_global_selection(selection, for_first)

    def remove_global_selection(self, selection: Selection) -> None:
        """
        Remove an already set global selection.

        Parameters
        ----------
        selection : Selection
            The already set global selection
        """
        self._wheel.remove_global_selection(selection)

    def get_scheme(self) -> List[ExplorationSchemeStep]:
        """
        Getter for the underlying exploration protocol.

        Returns
        -------
        List[ExplorationResult]
            The exploration protocol
        """
        return self._wheel.scheme

    def get_results(self) -> List[ExplorationResult]:
        """
        Retrieve results and status report from the wheel

        Returns
        -------
        List[ExplorationResult]
            The exploration protocol
        """
        self._wheel.get_status_report()  # to ensure both members are up-to-date
        return self._wheel.get_results()

    def get_partial_restart_info(self) -> Optional[RestartPartialExpansionInfo]:
        return self._wheel.get_partial_restart_info()

    def set_partial_restart_info(self, restart_info: Optional[RestartPartialExpansionInfo]) -> None:
        self._wheel.set_partial_restart_info(restart_info)

    def __len__(self) -> int:
        """
        The length of the wheel (the length of its exploration protocol)
        """
        return len(self._wheel)

    def __bool__(self) -> bool:
        """
        Whether the wheel has an exploration protocol
        """
        return bool(self._wheel)
