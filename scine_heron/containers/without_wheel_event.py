#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from PySide2.QtWidgets import QSpinBox, QDoubleSpinBox

from scine_heron.containers.combo_box import BaseBox


class NoWheelSpinBox(QSpinBox):
    """
    QSpinBox that does not react to mouse wheel events
    """

    def wheelEvent(self, event) -> None:
        event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    """
    QDoubleSpinBox that does not react to mouse wheel events
    """

    def wheelEvent(self, event) -> None:
        event.ignore()


class NoWheelComboBox(BaseBox):
    """
    QComboBox that does not react to mouse wheel events
    """

    def wheelEvent(self, event) -> None:
        event.ignore()
