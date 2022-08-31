#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the ElectronicDataStatusManager class.
"""

from typing import Optional, TYPE_CHECKING, Any
from PySide2.QtCore import QObject
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


class ElectronicDataStatusManager(QObject):
    """
    Provides a Status Manager that hold a list and emits events on resize
    """

    molden_input_changed_signal = Signal(str)
    hamiltonian_changed = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.__molden_input = str()

    @property
    def molden_input(self) -> str:
        """
        Returns the error_message.
        """
        return self.__molden_input

    @molden_input.setter
    def molden_input(self, value: str) -> None:
        """
        Sets the contained value. Notifies on change.
        """
        if value is None or value == "":
            return

        if value == self.__molden_input:
            return

        self.__molden_input = value
        self.molden_input_changed_signal.emit(value)

    def signal_hamiltonian_change(self) -> None:
        self.hamiltonian_changed.emit()
