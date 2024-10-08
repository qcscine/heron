#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the EnergyProfileStatusManager class.
"""

from typing import Any, List, Optional, TYPE_CHECKING
from datetime import datetime
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

    def get_latest_energy(self, seconds) -> Optional[float]:
        if len(self.value) > 0:
            if (datetime.now() - self.value[-1].time_stamp).total_seconds() < seconds:
                return self.value[-1].energy
        return None
