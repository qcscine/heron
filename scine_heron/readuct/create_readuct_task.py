#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from collections import UserList
from typing import Optional, Dict, List, Iterable, Tuple

from PySide2.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QTreeView,
)
from PySide2.QtCore import QObject, Qt
from PySide2.QtGui import QStandardItem, QStandardItemModel, QKeySequence

from scine_utilities import opt_settings_names

from scine_heron.containers.buttons import TextPushButton
from scine_heron.containers.combo_box import BaseBox
from scine_heron.containers.layouts import HorizontalLayout, VerticalLayout
from scine_heron.readuct.task_widget import TaskWidget
from scine_heron.utilities import write_error_message, write_info_message
import scine_heron.config as config
from scine_heron.styling.delegates import CustomLightDelegate


class TreeView(QTreeView):
    def __init__(self) -> None:
        super().__init__()
        if config.MODE in config.LIGHT_MODES:
            self.setItemDelegate(CustomLightDelegate())


class ReaductTaskComboBox(BaseBox):
    def __init__(self, parent: Optional[QObject], task_names: List[str]) -> None:
        super().__init__(parent)

        self.setView(TreeView())
        self.setModel(QStandardItemModel())
        self.view().setHeaderHidden(True)
        self.view().setItemsExpandable(False)
        self.view().setRootIsDecorated(False)

        sorted_names = sorted(task_names)
        for name in sorted_names:
            item = QStandardItem(name)
            item.setEnabled(True)
            self.model().appendRow(item)

        self.setCurrentText(sorted_names[0])


class CreateReaductTaskWidget(QWidget):
    default_name: str = "default_name"

    # keys: box name,
    # values:
    #   readuct callable task name if surrounded with "run_{}_task"
    #   number of inputs
    #   number of outputs
    task_mapping: Dict[str, Tuple[str, int, int]] = {
        "Single Point Calculation": ("sp", 1, 1),
        "Structure Optimization": ("opt", 1, 1),
        "Hessian": ("hessian", 1, 1),
        "Transition State Optimization": ("tsopt", 1, 1),
        "Newton Trajectory": ("nt", 1, 1),
        "Newton Trajectory 2": ("nt2", 1, 1),
        "Intrinsic Reaction Coordinate (IRC)": ("irc", 1, 2),
        "B-Spline Transition State Optimization": ("bspline", 2, 1),
        "Artificial Force Induced Reaction (AFIR)": ("afir", 1, 1),
        "AFIR Optimization": ("afir", 1, 1),
        "BSpline Interpolation": ("bspline", 2, 1),
        "Bond Order Calculation": ("bond_order", 1, 1),
        "Geometry Optimization": ("opt", 1, 1),
        "Hessian Calculation": ("hessian", 1, 1),
        "IRC Optimizations": ("irc", 1, 2),
        "NT2 Optimization": ("nt2", 1, 1),
        "NT1 Optimization": ("nt", 1, 1),
        "TS Optimization": ("tsopt", 1, 1)
    }

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._parent = parent
        self.name_edit = QLineEdit(self.default_name)
        name_layout = HorizontalLayout([QLabel("Name:"), self.name_edit])

        self.inputs_edit = MultiHComboBox(self)
        self._input_widget = self.inputs_edit.widget
        inputs_layout = HorizontalLayout([QLabel("Inputs:"), self._input_widget])

        self.outputs_edit = MultiHLineEdit(self)
        outputs_layout = HorizontalLayout([QLabel("Outputs:"), self.outputs_edit])

        self.task_box = ReaductTaskComboBox(self, list(self.task_mapping.keys()))
        self.task_box.setCurrentText("Structure Optimization")
        box_sub_layout = HorizontalLayout([QLabel("Select type:"), self.task_box])

        self.button_add = TextPushButton("Add task", self._generate_new_widget)
        self.button_add.setShortcut(QKeySequence("Return"))

        self.task_box.currentTextChanged.connect(  # pylint: disable=no-member
            self._determine_io_possibilities
        )
        self._determine_io_possibilities()  # call ourselves here once to evaluate default

        self._layout = VerticalLayout()
        self._layout.setAlignment(Qt.AlignTop)
        self._layout.add_layouts([
            box_sub_layout,
            name_layout,
            inputs_layout,
            outputs_layout,
        ])
        self._layout.addWidget(self.button_add)
        self.setLayout(self._layout)

    def add_possible_input_system(self, name: str) -> None:
        self.inputs_edit.append(name)

    def _determine_name(self, cls_name: str) -> str:
        name = self.name_edit.text()
        if name == self.default_name:
            return cls_name
        return name

    def _determine_io_possibilities(self) -> None:
        n_in, n_out = self.task_mapping[self.task_box.currentText()][1:]
        if n_in < 2:
            self.inputs_edit.hide_second()
        else:
            self.inputs_edit.show_second()
        if n_out < 2:
            self.outputs_edit.hide_second()
        else:
            self.outputs_edit.show_second()

    def add_new_possible_system(self, name: str) -> None:
        if name not in self.inputs_edit:
            self.inputs_edit.append(name)

    def _get_settings_suggestions(self) -> Optional[List[str]]:
        if self.task_box.currentText() == "Artificial Force Induced Reaction (AFIR)":
            return self._construct_settings_names(opt_settings_names.Afir) + \
                self._construct_settings_names(opt_settings_names.Convergence)
        if self.task_box.currentText() == "B-Spline Transition State Optimization":
            return None
        if self.task_box.currentText() == "Hessian":
            return ["temperature", "pressure"]
        if self.task_box.currentText() == "Intrinsic Reaction Coordinate (IRC)":
            return self._construct_settings_names(opt_settings_names.Irc) + \
                self._construct_settings_names(opt_settings_names.Convergence)
        if self.task_box.currentText() == "Newton Trajectory":
            return self._construct_settings_names(opt_settings_names.Nt) + \
                self._construct_settings_names(opt_settings_names.Convergence)
        if self.task_box.currentText() == "Newton Trajectory 2":
            return self._construct_settings_names(opt_settings_names.Nt2) + \
                self._construct_settings_names(opt_settings_names.Convergence)
        if self.task_box.currentText() == "Single Point Calculation":
            return ["require_charges", "require_gradients", "require_stress_tensor", "require_bond_orders",
                    "orbital_energies", "silent_stdout_calculator", "spin_propensity_check"]
        if self.task_box.currentText() == "Structure Optimization":
            return self._construct_settings_names(opt_settings_names.Convergence) + \
                self._construct_settings_names(opt_settings_names.Bfgs) + \
                self._construct_settings_names(opt_settings_names.Lbfgs) + \
                self._construct_settings_names(opt_settings_names.NewtonRaphson) + \
                self._construct_settings_names(opt_settings_names.SteepestDescent) + \
                self._construct_settings_names(opt_settings_names.GeometryOptimizer) + \
                self._construct_settings_names(opt_settings_names.CellOptimizer)
        if self.task_box.currentText() == "Transition State Optimization":
            return self._construct_settings_names(opt_settings_names.Convergence) + \
                self._construct_settings_names(opt_settings_names.Bofill) + \
                self._construct_settings_names(opt_settings_names.EigenvectorFollowing) + \
                self._construct_settings_names(opt_settings_names.Dimer) + \
                self._construct_settings_names(opt_settings_names.GeometryOptimizer)
        return None

    @staticmethod
    def _construct_settings_names(obj: object) -> List[str]:
        return [getattr(obj, k) for k in vars(obj).keys() if not k.startswith("_")]

    def _generate_new_widget(self) -> None:
        inputs = self.inputs_edit.get_values()
        if not inputs:
            write_error_message("Must give input systems")
            return
        outputs = self.outputs_edit.get_values()
        task_settings = {}
        if any(out for out in outputs):
            task_settings['output'] = outputs
            self.inputs_edit.extend(outputs)
        else:
            task_settings['output'] = inputs
            write_info_message("No outputs given, using inputs as outputs")

        new_widget = TaskWidget(
            parent=self._parent,
            inputs=inputs,
            task_name=self.task_mapping[self.task_box.currentText()][0],
            widget_title=self._determine_name(self.task_box.currentText()),
            task_settings=task_settings,
            settings_suggestions=self._get_settings_suggestions(),
        )
        self._parent.add_widget(new_widget)


class MultiHComboBox(UserList):

    def __init__(self, parent: Optional[QObject]):
        super().__init__()
        self.widget = QWidget(parent)
        self._first = BaseBox()
        self._second = BaseBox()
        self._layout = HorizontalLayout([self._first, self._second])
        self.widget.setLayout(self._layout)

    def hide_second(self) -> None:
        self._second.setVisible(False)

    def show_second(self) -> None:
        self._second.setVisible(True)

    def get_values(self) -> List[str]:
        if self._second.isVisible():
            return [self._first.currentText(), self._second.currentText()]
        return [self._first.currentText()]

    def _update_impl(self):
        if hasattr(self, "_first") and hasattr(self, "_second"):
            for w in [self._first, self._second]:
                w.clear()
                w.addItems(self.data)

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if "data" in key:
            self._update_impl()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._update_impl()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._update_impl()

    def append(self, item: str) -> None:
        if not item or item in self.data:
            return
        super().append(item)
        self._update_impl()

    def extend(self, other: Iterable[str]) -> None:
        for item in other:
            if not item or item not in self.data:
                super().append(item)
        self._update_impl()

    def insert(self, i: int, item: str) -> None:
        super().insert(i, item)
        self._update_impl()

    def pop(self, i: int) -> str:  # type: ignore  # pylint: disable=signature-differs
        res = super().pop(i)
        self._update_impl()
        return res

    def clear(self) -> None:
        super().clear()
        self._update_impl()

    def remove(self, item: str) -> None:
        super().remove(item)
        self._update_impl()


class MultiHLineEdit(QWidget):

    def __init__(self, parent: Optional[QObject]):
        super().__init__(parent)
        self._first = QLineEdit()
        self._second = QLineEdit()
        self._layout = HorizontalLayout([self._first, self._second])
        self.setLayout(self._layout)

    def hide_second(self) -> None:
        self._second.setVisible(False)

    def show_second(self) -> None:
        self._second.setVisible(True)

    def get_values(self) -> List[str]:
        if self._second.isVisible():
            return [self._first.text().strip(), self._second.text().strip()]
        return [self._first.text().strip()]
