#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from functools import partial
from os import path, mkdir, getcwd
from typing import Any, List, Optional, Dict, TYPE_CHECKING
from threading import Thread
from time import sleep

from PySide2.QtWidgets import (
    QWidget,
    QScrollArea,
    QVBoxLayout,
    QStyle,
    QSplitter,
)
from PySide2.QtCore import Qt, QObject, QThread
from PySide2.QtGui import QCloseEvent

if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal

import scine_readuct as readuct
import scine_utilities as su

from scine_heron.containers.layouts import HorizontalLayout
from scine_heron.io.text_box import yes_or_no_question
from scine_heron.io.file_browser_popup import get_load_file_name, get_save_file_name
from scine_heron.toolbar.io_toolbar import ToolBarWithSaveLoad
from scine_heron.utilities import write_error_message, clear_status_bar, write_info_message

from .create_readuct_task import CreateReaductTaskWidget
from .task_widget import TaskWidget
from .calculator_container import CalculatorContainer


class ReaductTab(QWidget):
    """
    Container Widget to handle ReaDuct systems and tasks
    """

    input_file_dir_name: str = 'input_files'

    def __init__(self, parent: Optional[QObject]) -> None:
        QWidget.__init__(self, parent)
        self._joiner: Optional[TaskJoiner] = None
        self._delete_join_threads: List[Thread] = []

        # systems
        self._calc_container = CalculatorContainer(self)

        # generate the widgets to build widgets
        self.__task_creator_widget = CreateReaductTaskWidget(self)

        # create widget for scroll area
        scroll_area_content = QWidget()
        self._scroll_area_content_layout = QVBoxLayout()
        # add toolbar
        self._toolbar = ToolBarWithSaveLoad(self._save_file, self._load_file, self)
        # play button
        self._play = self._toolbar.shortened_add_action(QStyle.SP_MediaPlay, "Start all tasks (consecutively)",
                                                        "Ctrl+M", lambda: self._start_stop_all(start=True))
        self._stop = self._toolbar.shortened_add_action(QStyle.SP_MediaPause, "Stop all tasks",
                                                        "Ctrl+R", lambda: self._start_stop_all(start=False,
                                                                                               force_join=True))
        self._play.setCheckable(True)
        self._stop.setCheckable(True)
        self.is_blocked = False
        self._scroll_area_content_layout.addWidget(self._toolbar)
        # add holder of all the created widgets
        self.created_readuct_task_widgets: List[TaskWidget] = []
        self._created_readuct_widgets_holder = QWidget()
        self.__created_readuct_widgets_layout = HorizontalLayout()
        self.__created_readuct_widgets_layout.setAlignment(Qt.AlignLeft)
        self._created_readuct_widgets_holder.setLayout(self.__created_readuct_widgets_layout)
        # finish scroll area content
        self._scroll_area_content_layout.addWidget(self._created_readuct_widgets_holder)
        scroll_area_content.setLayout(self._scroll_area_content_layout)

        # create scroll area
        self._scroll_area = QScrollArea()
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._scroll_area.setWidget(scroll_area_content)
        self._scroll_area.setWidgetResizable(True)

        # fill total grid layout of the tab
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.addWidget(self.__task_creator_widget)
        right_splitter.addWidget(self._scroll_area)

        total_splitter = QSplitter(Qt.Orientation.Horizontal, parent=self)
        total_splitter.addWidget(self._calc_container)
        total_splitter.addWidget(right_splitter)
        total_splitter.setSizes([320, 280])

        total_layout = QVBoxLayout()
        total_layout.addWidget(total_splitter)
        self.setLayout(total_layout)

        self._calc_container.new_system_added.connect(
            self.__task_creator_widget.add_possible_input_system
        )

    def get_systems(self) -> Dict[str, su.core.Calculator]:
        return self._calc_container.get_systems()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._runner is not None:
            self._runner.wait()
            self._joiner = TaskJoiner(self, force_join=True)
            self._joiner.start()
            self._joiner.wait()
        if self._joiner is not None:
            self._joiner.wait()
        super().closeEvent(event)

    def update_systems(self, inputs: List[str], outputs: List[str], systems: Dict[str, su.core.Calculator]) -> None:
        existing_systems = self._calc_container.get_augmented_systems()
        method_family = None
        program = None
        for inp in inputs:
            if inp not in existing_systems:
                continue
            method_family, program = existing_systems[inp][:2]
            break
        if method_family is None or program is None:
            write_error_message("Failed to update systems due to improper input information")
            return
        for out in outputs:
            if out not in systems:
                write_error_message("Failed to update systems due to improper output information")
                return
            calc = systems[out]
            self._calc_container.add_item(method_family, program, calc.structure, calc.settings.as_dict(), out)

    def add_widget(self, readuct_widget: TaskWidget) -> None:
        # connect functionalities
        if readuct_widget.button_delete is not None:
            readuct_widget.button_delete.clicked.connect(  # pylint: disable=no-member
                partial(self.delete_widget, readuct_widget)
            )
        readuct_widget.update_systems.connect(  # pylint: disable=no-member
            self.update_systems
        )

        self.created_readuct_task_widgets.append(readuct_widget)
        self.__created_readuct_widgets_layout.addWidget(readuct_widget)

    def delete_widget(self, task_widget: TaskWidget) -> int:
        idx = self.created_readuct_task_widgets.index(task_widget)
        removed_outputs = task_widget.outputs

        for widget in self.created_readuct_task_widgets[idx + 1:]:
            if any(inp in removed_outputs for inp in widget.inputs):
                write_error_message(f"You cannot delete this task, because its outputs are used by task {widget.name}!")
                return -1

        self.created_readuct_task_widgets.pop(idx)
        task_widget.stop_class_if_working()
        self._delete_join_threads.append(Thread(target=task_widget.join, kwargs={'force_join': True}))
        self._delete_join_threads[-1].start()

        self.__created_readuct_widgets_layout.removeWidget(task_widget)
        task_widget.setAttribute(Qt.WA_DeleteOnClose)
        task_widget.close()
        task_widget.setParent(None)  # type: ignore
        self._created_readuct_widgets_holder.updateGeometry()

        return idx

    def _start_stop_all(self, start: bool, force_join: bool = False) -> None:
        if not self.created_readuct_task_widgets:
            write_error_message("You have not created any tasks, yet")
            return
        if self.is_blocked:
            write_error_message("Currently in the process of stopping all tasks, please be patient")
            return
        if start and force_join:
            write_error_message("Internal error, conflicting inputs")
            return
        button = self._play if start else self._stop
        button.setChecked(True)
        if not start:
            for widget in self.created_readuct_task_widgets:
                widget.start_stop(stop_all=True)
            # additional loop for shutdown to collect processes
            self.is_blocked = True
            self._joiner = TaskJoiner(self, force_join)
            self._joiner.start()
        else:
            self._runner = RunAllTasks(self)

            def handle_question(x):
                ans = yes_or_no_question(self, x)
                self._runner.answer_signal.emit(ans)

            self._runner.question_signal.connect(handle_question)  # pylint: disable=no-member
            self._runner.error_signal.connect(write_error_message)  # pylint: disable=no-member
            self._runner.start()
        button.setChecked(False)

    def _load_from_yaml(self, filename: str) -> None:
        systems, names, settings = readuct.load_yaml(filename)
        for name, (method_family, program, calc) in systems.items():
            self._calc_container.add_item(method_family, program, calc.structure, calc.settings.as_dict(), name)

        for (name, inputs, outputs), task_settings in zip(names, settings):
            task_settings['output'] = outputs
            new_widget = TaskWidget(
                parent=self,
                inputs=inputs,
                task_name=CreateReaductTaskWidget.task_mapping[name][0],
                widget_title=name,
                task_settings=task_settings,
                settings_suggestions=None,
            )
            self.add_widget(new_widget)

    def _load_file(self) -> None:
        filename = get_load_file_name(self, "ReaDuctSession", ["yaml", "yml"])
        if filename is None:
            return
        self._load_from_yaml(str(filename))

    def _save_to_yaml(self, filename: str) -> None:
        input_dir = path.join(getcwd(), self.input_file_dir_name)
        aug_systems = self._calc_container.get_augmented_systems()
        if len(aug_systems.keys()) == 0:
            write_error_message("No systems have been created")
            return
        if len(self.created_readuct_task_widgets) == 0:
            write_error_message("No tasks have been created")
            return
        task_names = [task.get_names() for task in self.created_readuct_task_widgets]
        task_settings = [task.get_settings() for task in self.created_readuct_task_widgets]
        if len(task_names) != len(task_settings):
            write_error_message("Could not read all task names and settings")
            return
        # write to calculators to files
        if not path.exists(input_dir):
            mkdir(input_dir)
        for name, (method_family, program, calc) in aug_systems.items():
            su.io.write(str(path.join(input_dir, name)) + ".xyz", calc.structure)
        with open(filename, "w") as f:
            f.write("systems:\n")
            for name, (method_family, program, calc) in aug_systems.items():
                system_file_name = str(path.join(input_dir, name)) + ".xyz"
                f.write(f"  - name: {name}\n")
                f.write(f"    path: {system_file_name}\n")
                f.write(f"    program: {program}\n")
                f.write(f"    method_family: {method_family}\n")
                f.write("    settings:\n")
                for key, value in calc.settings.items():
                    if isinstance(value, str) and not value:
                        f.write(f"      {key}: ''\n")
                    else:
                        f.write(f"      {key}: {value}\n")
                f.write("\n")
            f.write("tasks:\n")
            for (name, inputs, outputs), settings in zip(task_names, task_settings):
                f.write(f"  - type: {name}\n")
                f.write(f"    input: {inputs}\n")
                f.write(f"    output: {outputs}\n")
                if "output" in settings:
                    del settings['output']
                if settings:
                    f.write("    settings:\n")
                    for key, value in settings.items():
                        if isinstance(value, str) and not value:
                            f.write(f"      {key}: ''\n")
                        else:
                            f.write(f"      {key}: {value}\n")

    def _save_file(self) -> None:
        if not self.created_readuct_task_widgets:
            write_error_message("You have not created any tasks, yet")
            return
        filename = get_save_file_name(self, "ReaDuctSession", ["yaml", "yml"])
        if filename is None:
            return
        write_info_message("Stopping all tasks, this may take some time...", timer=1_000_000_000)
        self._start_stop_all(start=False, force_join=True)
        # wait for all tasks to be joined
        while self.is_blocked:
            pass
        clear_status_bar()
        write_info_message("Writing to disk")
        self._save_to_yaml(str(filename))

    def add_system_from_molecular_viewer(self):
        self._calc_container.molecular_viewer_add_button.clicked.emit()  # pylint: disable=no-member


class RunAllTasks(QThread):

    question_signal = Signal(str)
    answer_signal = Signal(bool)
    error_signal = Signal(str)

    def __init__(self, parent: ReaductTab):
        super().__init__(parent)
        self.container = parent
        self._answer: Optional[bool] = None

    def _stop_waiting(self, answer: bool) -> None:
        self._answer = answer
        self.answer_signal.disconnect(self._stop_waiting)

    def _wait_for_answer(self, widget: TaskWidget) -> None:
        self._answer = None
        self.answer_signal.connect(self._stop_waiting)
        self.question_signal.emit(f"The task '{widget.name}' is already finished. "
                                  f"Do you want to re-run it")
        while self._answer is None:
            pass

    def run(self):
        for widget in self.container.created_readuct_task_widgets:
            if not widget.is_working():
                if widget.get_result()[1]:
                    self._wait_for_answer(widget)
                    if not self._answer:
                        # user said no, so we skip this task
                        continue
                messages = []
                widget.start_stop(start_all=True, message_container=messages)
                for message in messages:
                    self.error_signal.emit(message)
            systems, success = widget.join(force_join=False)
            if success:
                print("Updating ", widget.inputs, widget.outputs, systems.keys())
                widget.update_systems.emit(widget.inputs, widget.outputs, systems)
                sleep(0.1)
            else:
                self.error_signal.emit(f"Task '{widget.name}' failed")
            color = widget.green if success else widget.red
            widget.change_color(color)
        self.exit(0)


class TaskJoiner(QThread):

    def __init__(self, parent: ReaductTab, force_join: bool = False):
        super().__init__(parent)
        self.container = parent
        self._force = force_join

    def run(self):
        for widget in self.container.created_readuct_task_widgets:
            widget.join(self._force)
        self.container.is_blocked = False
        self.exit(0)
