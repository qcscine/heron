#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the ControlledCheckBox class.
"""

import typing
from scine_heron.status_manager import WriteableStatus
from PySide2.QtWidgets import QCheckBox
from PySide2.QtCore import QObject, Qt


class ControlledCheckBox(QCheckBox):
    """
    A slightly modified version of Qt's QCheckBox that displays
    the state as defined by a model.
    """

    def __init__(
        self,
        status: WriteableStatus[Qt.CheckState],
        parent: typing.Optional[QObject] = None,
    ):
        """
        :param pull: Returns the current state of the model.
        :param push: Requests a change to the provided state.
        :param signal: Notifies when the state in model has changed.
        """
        super().__init__(parent)

        self.__configure_input_handling(status)
        self.__configure_output_handling(status)

        self.setCheckState(status.value)

    def __configure_output_handling(
        self, status: WriteableStatus[Qt.CheckState]
    ) -> None:
        """
        Configure how the view responds to changes in the model.
        """
        status.changed_signal.connect(self.setCheckState)

    def __configure_input_handling(
        self, status: WriteableStatus[Qt.CheckState]
    ) -> None:
        """
        Configure how the view responds to user input.
        """

        def handle_change(state: Qt.CheckState) -> None:
            """Handle user input."""
            blocked = self.signalsBlocked()
            self.blockSignals(True)
            try:
                self.setCheckState(status.value)
                status.value = state
            finally:
                self.blockSignals(blocked)

        self.stateChanged.connect(handle_change)  # pylint: disable=no-member
