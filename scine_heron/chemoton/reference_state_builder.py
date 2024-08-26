#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional

from PySide2.QtCore import QObject

from scine_chemoton.utilities.db_object_wrappers.thermodynamic_properties import ReferenceState

from scine_heron.containers.combo_box import BaseBox
from scine_heron.containers.layouts import HorizontalLayout
from scine_heron.containers.without_wheel_event import NoWheelDoubleSpinBox


class ReferenceStateBuilder(BaseBox):
    """
    Construction of a ReferenceState object, defining temperature and pressure.
    """

    def __init__(self, options: ReferenceState, parent: Optional[QObject] = None):
        super().__init__(parent=parent)
        maximum = 1e+9
        self._temperature_edit = NoWheelDoubleSpinBox(parent=parent)
        self._temperature_edit.setMinimum(0.0)
        self._temperature_edit.setMaximum(maximum)
        self._temperature_edit.setSingleStep(0.01)
        self._temperature_edit.setDecimals(2)
        self._temperature_edit.setValue(options.temperature)

        self._pressure_edit = NoWheelDoubleSpinBox(parent=parent)
        self._pressure_edit.setMinimum(0.0)
        self._pressure_edit.setMaximum(maximum)
        self._pressure_edit.setSingleStep(0.01)
        self._pressure_edit.setDecimals(2)
        self._pressure_edit.setValue(options.pressure)

        layout = HorizontalLayout()
        layout.addWidget(self._temperature_edit)
        layout.addWidget(self._pressure_edit)
        self.setLayout(layout)

    def get_reference_state(self) -> ReferenceState:
        return ReferenceState(self._temperature_edit.value(),
                              self._pressure_edit.value())
