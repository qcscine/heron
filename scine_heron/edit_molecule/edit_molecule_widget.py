#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the EditMoleculeWidget class.
"""

from silx.gui.widgets.PeriodicTable import PeriodicTable, PeriodicTableItem
from PySide2.QtGui import QIntValidator
from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QWidget,
    QPushButton,
    QLabel,
    QGridLayout,
    QLineEdit,
)
from typing import Optional, Any, TYPE_CHECKING
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


class EditMoleculeWidget(QWidget):
    """
    Contains the tools to change the composition of the molecule.
    """

    addAtom = Signal(int)
    removeSelectedAtom = Signal()

    def __init__(self) -> None:
        super(EditMoleculeWidget, self).__init__()

        self.__atomNumberLabel = QLabel("Atomic Number:")
        self.__atomNumberField = QLineEdit(self)
        self.__popUpPeriodicTableButton = QPushButton("Search...", self)
        self.__appendAtomButton = QPushButton("Add Atom", self)
        self.__atomNumberValidator = QIntValidator(1, 109, self)
        self.__atomNumberField.setValidator(self.__atomNumberValidator)
        self.__atomNumberField.setText("6")  # Default value
        self.__atomNumberField.textChanged.connect(  # pylint: disable=no-member
            self.__sanitize_atom_number
        )

        self.__removeAtomButton = QPushButton("Remove Selected Atom", self)

        self.__layout = QGridLayout()
        self.__layout.addWidget(self.__atomNumberLabel, 0, 0)
        self.__layout.addWidget(self.__atomNumberField, 0, 1)
        self.__layout.addWidget(self.__popUpPeriodicTableButton, 1, 0)
        self.__layout.addWidget(self.__appendAtomButton, 1, 1)
        self.__layout.addWidget(self.__removeAtomButton, 2, 0, 1, 2)
        self.__layout.setAlignment(Qt.AlignTop)

        self.setLayout(self.__layout)

        self.__appendAtomButton.clicked.connect(self.__appendAtom)  # pylint: disable=no-member
        self.__removeAtomButton.clicked.connect(self.__removeAtom)  # pylint: disable=no-member
        self.__popUpPeriodicTableButton.clicked.connect(  # pylint: disable=no-member
            self.__open_periodict_table_dialog
        )
        self.__periodicTableDialog: Optional[PeriodicTable] = None

    def __set_atom_number(self, periodic_table_item: PeriodicTableItem) -> None:
        atomic_number = periodic_table_item.Z
        self.__atomNumberField.setText(str(atomic_number))
        if self.__periodicTableDialog is not None:
            self.__periodicTableDialog.close()
        self.addAtom.emit(int(atomic_number))

    def __open_periodict_table_dialog(self) -> None:
        self.__periodicTableDialog = PeriodicTable()
        self.__periodicTableDialog.setStyleSheet(
            """
            color: #000000;
            """
        )
        self.__periodicTableDialog.sigElementClicked.connect(self.__set_atom_number)
        self.__periodicTableDialog.show()

    def __sanitize_atom_number(self, _):
        if not self.__atomNumberField.hasAcceptableInput():
            text = self.__atomNumberField.text()
            if not text:
                return
            if text.isdigit():
                i = int(self.__atomNumberField.text())
                if i > 109:
                    self.__atomNumberField.setText("109")
                elif i < 1:
                    self.__atomNumberField.setText("1")
            else:
                self.__atomNumberField.setText("6")

    def __appendAtom(self) -> None:
        text = self.__atomNumberField.text()
        if text:
            atomic_number = self.__atomNumberField.displayText().strip()
            self.addAtom.emit(int(atomic_number))

    def __removeAtom(self) -> None:
        self.removeSelectedAtom.emit()
