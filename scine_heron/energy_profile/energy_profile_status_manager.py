#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the EnergyProfileStatusManager class.
"""

from typing import Any, List, TYPE_CHECKING
from PySide2.QtCore import QObject
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


class EnergyProfileStatusManager(QObject):
    """
    Provides a Status Manager that hold a list and emits events on resize
    """

    changed_signal = Signal(list)

    def __init__(self, *args: Any):
        super().__init__(*args)
        self.value: List[Any] = []

    def append(self, item: Any) -> None:
        """
        Appends data to inner list
        """
        self.value.append(item)
        self.changed_signal.emit(self.value)

    def __len__(self) -> int:
        """
        Returns the len of the inner list
        """
        return len(self.value)

    def reset(self) -> None:
        """
        Empties the inner list
        """
        self.value = []
