#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from PySide2.QtWidgets import QTabWidget
from PySide2.QtGui import QCursor
from PySide2.QtCore import Qt


class TabWidget(QTabWidget):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tabBar().setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
