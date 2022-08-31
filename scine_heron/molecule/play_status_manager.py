#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the PlayStatusManager class.
"""

import typing
from PySide2.QtCore import QObject
if typing.TYPE_CHECKING:
    Signal = typing.Any
else:
    from PySide2.QtCore import Signal


class PlayStatusManager(QObject):
    """
    A class that manages an on/off status.
    """

    on_signal = Signal()
    off_signal = Signal()

    def __init__(self, parent: typing.Optional[QObject] = None):
        super().__init__(parent)
        self.__active = False

    def is_on(self) -> bool:
        """
        Returns True if and only if the status is currently "on"
        """
        return self.__active

    def __emit_if_necessary(self, status: bool) -> None:
        """
        Emits a signal if the status has changed from the provides status.
        """
        target = self.is_on()
        if status != target:
            if target:
                self.on_signal.emit()
            else:
                self.off_signal.emit()

    def stop(self) -> None:
        """
        Sets the status to "off".
        """
        status = self.is_on()
        self.__active = False
        self.__emit_if_necessary(status)

    def start(self) -> None:
        """
        Sets the status to "on".
        """
        status = self.is_on()
        self.__active = True
        self.__emit_if_necessary(status)
