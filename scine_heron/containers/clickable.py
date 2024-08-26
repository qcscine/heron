#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from PySide2.QtWidgets import QWidget
from PySide2.QtGui import QCursor
from PySide2.QtCore import Qt


class Clickable(QWidget):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def setEnabled(self, value: bool) -> None:
        cursor = Qt.CursorShape.PointingHandCursor if value else Qt.CursorShape.ForbiddenCursor
        self.setCursor(QCursor(cursor))
        super().setEnabled(value)
