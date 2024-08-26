#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from PySide2.QtCore import Qt
from PySide2.QtWidgets import QStyledItemDelegate, QStyle
from PySide2.QtGui import QColor


class CustomLightDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor("#215CAF"))
        else:
            painter.fillRect(option.rect, QColor("#4D7DBF"))

        painter.setPen(QColor("#ffffff"))
        painter.drawText(option.rect, Qt.AlignLeft | Qt.AlignVCenter, index.data())
