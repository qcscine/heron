#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the DictOptionWidget class.
"""
import inspect
from typing import Optional, Dict, Any
from scine_utilities import ValueCollection
from scine_database import Model, Job
from PySide2.QtWidgets import (
    QWidget,
    QFrame,
    QLabel,
    QSpinBox,
    QLineEdit,
    QDoubleSpinBox,
    QCheckBox,
    QGridLayout,
)


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
    ) -> None:
        super(DictOptionWidget, self).__init__(parent)
        self.__options = options
        self.__option_widgets: Dict[str, QWidget] = {}

        self.__default_min_value = -1000000000
        self.__default_max_value = 1000000000
        self.__double_spin_step = 0.1
        self.__double_spin_decimals = 5

        if show_border:
            self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)

        layout = QGridLayout()
        index = 0

        for option_name, option in self.__options.items():
            if isinstance(option, int):
                widget = self.__generate_spin_widget(option)
            elif isinstance(option, bool):
                widget = self.__generate_checkbox_widget(option)
            elif isinstance(option, float):
                widget = self.__generate_double_spin_widget(option)
            elif isinstance(option, str):
                widget = self.__generate_line_editor_widget(option)
            elif isinstance(option, dict):
                widget = DictOptionWidget(option, parent=self, show_border=True)
            elif isinstance(option, ValueCollection):
                widget = DictOptionWidget(
                    option.as_dict(), parent=self, show_border=True
                )
            elif type(option) in [Model, Job]:
                widget = DictOptionWidget(
                    self.get_attributes_of_object(option), parent=self, show_border=True
                )
            else:
                widget = QLabel("Type " + str(type(option)) + " is not implemented.")
            self.__option_widgets[option_name] = widget

            name_widget = QLabel(option_name)
            if docstring_dict and option_name in docstring_dict:
                name_widget.setToolTip(docstring_dict[option_name])

            layout.addWidget(name_widget, index, 0)
            layout.addWidget(widget, index, 1)

            index += 1

        self.setLayout(layout)

    def __generate_spin_widget(self, option: int) -> QSpinBox:
        spin_edit = QSpinBox()
        spin_edit.setMinimum(self.__default_min_value)
        spin_edit.setMaximum(self.__default_max_value)
        spin_edit.setValue(option)
        return spin_edit

    def __generate_double_spin_widget(self, option: float) -> QDoubleSpinBox:
        spin_edit = QDoubleSpinBox()
        spin_edit.setMinimum(float(self.__default_min_value))
        spin_edit.setMaximum(float(self.__default_max_value))
        spin_edit.setSingleStep(self.__double_spin_step)
        spin_edit.setDecimals(self.__double_spin_decimals)
        spin_edit.setValue(option)
        return spin_edit

    @staticmethod
    def __generate_checkbox_widget(option: bool) -> QCheckBox:
        check_box = QCheckBox()
        check_box.setChecked(option)
        return check_box

    @staticmethod
    def __generate_line_editor_widget(option: str) -> QLineEdit:
        line_edit = QLineEdit()
        line_edit.setText(option)
        return line_edit

    @staticmethod
    def get_attributes_of_object(o: object) -> Dict[str, Any]:
        attributes = inspect.getmembers(
            o.__class__, lambda a: not (inspect.isroutine(a))
        )
        return {
            a[0]: getattr(o, a[0])
            for a in attributes
            if not (a[0].startswith("__") and a[0].endswith("__"))
        }

    @staticmethod
    def set_attributes_to_object(o: object, d: Dict[str, Any]) -> None:
        for option_name, option in d.items():
            setattr(o, option_name, option)

    def get_widget_data(self) -> Dict[str, Any]:
        data: Dict[str, Any] = dict()

        for option_name, option in self.__options.items():
            widget = self.__option_widgets[option_name]
            if isinstance(option, int):
                data[option_name] = widget.value()
            elif isinstance(option, bool):
                data[option_name] = widget.isChecked()
            elif isinstance(option, float):
                data[option_name] = widget.value()
            elif isinstance(option, str):
                data[option_name] = widget.text()
            elif isinstance(option, dict):
                data[option_name] = widget.get_widget_data()
            elif isinstance(option, ValueCollection):
                data[option_name] = option.from_dict(widget.get_widget_data())
            elif type(option) in [Model, Job]:
                self.set_attributes_to_object(option, widget.get_widget_data())
                data[option_name] = option
            else:
                raise NotImplementedError(
                    "Type " + str(type(option)) + " is not implemented."
                )
        return data
