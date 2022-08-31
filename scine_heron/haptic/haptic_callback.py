#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the HapticClient class.
"""
from PySide2.QtCore import QObject
import typing
if typing.TYPE_CHECKING:
    Signal = typing.Any
else:
    from PySide2.QtCore import Signal

try:
    import scine_heron_haptic as suh
except ImportError:
    pass


class HapticSignals(QObject):
    """
    Inherited from QObject.
    Connect callback to UI.
    """

    move_signal = Signal(object, float, float, float)
    first_button_down_signal = Signal()
    first_button_up_signal = Signal()

    second_button_down_signal = Signal(object)
    second_button_up_signal = Signal()


class HapticCallback(suh.HapticCallback):  # type: ignore[misc]
    """
    Inherited from HapticCallback.
    Connect to haptic events.
    """

    def __init__(self) -> None:
        super().__init__()
        self.signals = HapticSignals()

    def move(
        self, data: suh.HapticData, azimuth: float, elevation: float, zoom: float
    ) -> None:
        self.signals.move_signal.emit(data, azimuth, elevation, zoom)

    def first_button_down(self) -> None:
        self.signals.first_button_down_signal.emit()

    def first_button_up(self) -> None:
        self.signals.first_button_up_signal.emit()

    def second_button_down(self, atom_index: int) -> None:
        self.signals.second_button_down_signal.emit(atom_index)

    def second_button_up(self) -> None:
        self.signals.second_button_up_signal.emit()
