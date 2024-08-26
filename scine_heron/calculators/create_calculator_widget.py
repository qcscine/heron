#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from copy import deepcopy
from typing import Any, Dict, Optional, TYPE_CHECKING, Tuple

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
)
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal

# ensures we can load a calculator
import scine_sparrow  # noqa # pylint: disable=unused-import
import scine_utilities as su

from scine_heron.calculators.calculator import ScineCalculatorWrapper
from scine_heron.containers.buttons import TextPushButton
from scine_heron.containers.layouts import HorizontalLayout, VerticalLayout
from scine_heron.settings.class_options_widget import ClassOptionsWidget
from scine_heron.utilities import write_error_message


class CreateCalculatorWidget(QWidget):

    settings_changed_signal = Signal(str, str, su.Settings)

    def __init__(self, parent: Optional[QWidget] = None, method_family: Optional[str] = None,
                 program: Optional[str] = None, atoms: Optional[su.AtomCollection] = None,
                 settings: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(parent)

        # immediately load Sparrow calculator, so we have less complications, because we always have a calculator
        self._loaded_method_family = "PM6" if method_family is None else method_family
        self._loaded_program = "Sparrow" if program is None else program
        self._calc_wrapper = ScineCalculatorWrapper(self._loaded_method_family, self._loaded_program,
                                                    hessian_required=False, settings=settings, atoms=atoms)

        # doc
        self._docstring_dict: Optional[Dict[str, str]] = None

        # calculators require Method family + program
        # method family
        self.method_family_edit = QLineEdit(self._loaded_method_family)
        mf_layout = HorizontalLayout([QLabel("Method family:"), self.method_family_edit])

        # program
        self.program_edit = QLineEdit(self._loaded_program)
        program_layout = HorizontalLayout([QLabel("Program:"), self.program_edit])

        # buttons
        self._button_settings = TextPushButton("Settings", self._edit_settings)
        self._button_load = TextPushButton("Load\ncalculator", self._load_calculator)
        self._button_layout = HorizontalLayout([self._button_load, self._button_settings])

        # connect signals
        self.method_family_edit.returnPressed.connect(self.program_edit.setFocus)  # pylint: disable=no-member
        self.method_family_edit.returnPressed.connect(self.program_edit.selectAll)  # pylint: disable=no-member
        self.program_edit.returnPressed.connect(self._button_load.click)  # pylint: disable=no-member
        self.program_edit.returnPressed.connect(self._button_load.animateClick)  # pylint: disable=no-member

        self._can_be_edited = True

        # fill layout
        self._layout = VerticalLayout([QLabel("Specify calculator")])
        self._layout.setAlignment(Qt.AlignTop)
        self._layout.add_layouts([mf_layout, program_layout, self._button_layout])
        self.setLayout(self._layout)
        self.setMinimumHeight(200)
        self.emit_signal()

    def get_calculator_args(self) -> Tuple[str, str]:
        return self._loaded_method_family, self._loaded_program

    def get_structure(self) -> Optional[su.AtomCollection]:
        if self._calc_wrapper.prev_molecule_version is None:
            write_error_message("No structure loaded into calculator yet")
            return None
        return self._calc_wrapper.get_calculator().structure

    def get_calculator(self) -> su.core.Calculator:
        return self._calc_wrapper.get_calculator()

    def get_settings(self) -> su.Settings:
        return self._calc_wrapper.get_settings()

    def toggle_editable(self):
        if self._can_be_edited:
            self.method_family_edit.setReadOnly(True)
            self.program_edit.setReadOnly(True)
            self._button_settings.setEnabled(False)
            self._button_load.setEnabled(False)
            self._can_be_edited = False
        else:
            self.method_family_edit.setReadOnly(False)
            self.program_edit.setReadOnly(False)
            self._button_settings.setEnabled(True)
            self._button_load.setEnabled(True)
            self._can_be_edited = True

    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        result = self._calc_wrapper.update_settings(new_settings)
        if result:
            self.emit_signal()
        else:
            write_error_message("Failed to modify calculator settings")

    def _edit_settings(self) -> None:
        d_settings = deepcopy(self._calc_wrapper.get_settings())
        setting_widget = ClassOptionsWidget(
            d_settings, self._docstring_dict, parent=self, add_close_button=True, allow_removal=False
        )
        setting_widget.exec_()
        if self._calc_wrapper.update_settings(d_settings.as_dict()):
            self.emit_signal()

    def _load_calculator(self) -> None:
        method_family = self.method_family_edit.text()
        program = self.program_edit.text()
        atoms = self._calc_wrapper.get_structure()
        if self._calc_wrapper.load_calculator(method_family, program, atoms=atoms):
            self._loaded_method_family = method_family
            self._loaded_program = program
            self.emit_signal()
            self._docstring_dict = self._calc_wrapper.get_docstring_dict()

    def emit_signal(self) -> None:
        self.settings_changed_signal.emit(self._loaded_method_family, self._loaded_program,
                                          self._calc_wrapper.get_settings())
