#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""


from PySide2.QtWidgets import QProgressBar
from PySide2.QtGui import QPainter, QColor
from PySide2.QtCore import Qt

import scine_heron.config as config


class HeronProgressBar(QProgressBar):
    def paintEvent(self, event):
        super().paintEvent(event)
        if config.MODE in config.LIGHT_MODES:
            painter = QPainter(self)
            painter.setPen(QColor('#FFFFFF'))
            painter.drawText(self.rect(), Qt.AlignCenter, self.text())
