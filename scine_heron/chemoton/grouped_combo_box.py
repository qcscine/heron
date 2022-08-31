#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the GroupedComboBox class.
"""

from PySide2.QtWidgets import (
    QComboBox,
    QTreeView,
)
from PySide2.QtCore import QObject, QSize
from PySide2.QtGui import QStandardItem, QStandardItemModel
from scine_heron.chemoton.gear_searcher import GearSearcher


class GroupedComboBox(QComboBox):
    def __init__(self, parent: QObject, gear_searcher: GearSearcher) -> None:
        QComboBox.__init__(self, parent)

        self.setView(QTreeView())
        self.setModel(QStandardItemModel())
        self.view().setHeaderHidden(True)
        self.view().setItemsExpandable(False)
        self.view().setRootIsDecorated(False)

        self.gear_searcher = gear_searcher

        self.setFixedSize(QSize(230, 30))

        child_name = str()  # use for gear name selection.

        for module in sorted(self.gear_searcher.module_to_class.keys()):
            parent_item = QStandardItem(module)
            parent_item.setEnabled(False)
            self.model().appendRow(parent_item)

            for item_name in self.gear_searcher.module_to_class[module]:
                child_name = "   " + item_name
                child_item = QStandardItem(child_name)
                self.model().appendRow(child_item)

        self.setCurrentText(child_name)
