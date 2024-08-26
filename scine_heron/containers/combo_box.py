#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import List, Optional

from PySide2.QtWidgets import (
    QComboBox,
    QTreeView,
)
from PySide2.QtCore import QObject, Qt
from PySide2.QtGui import QStandardItem, QStandardItemModel, QCursor
from scine_heron.styling.delegates import CustomLightDelegate
import scine_heron.config as config


class BaseBox(QComboBox):
    """
    A combo box serving as a base class for all QComboBoxes in Heron and handling some basic formatting.
    """

    def __init__(self, parent: Optional[QObject] = None, header: Optional[str] = None) -> None:
        QComboBox.__init__(self, parent=parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        tree_view = QTreeView()
        if config.MODE in config.LIGHT_MODES:
            tree_view.setItemDelegate(CustomLightDelegate())
        self.setView(tree_view)
        self.setModel(QStandardItemModel())
        self.view().setHeaderHidden(True)
        self.view().setItemsExpandable(False)
        self.view().setRootIsDecorated(False)

        if header is not None:
            parent_header = QStandardItem(header)
            parent_header.setEnabled(False)
            self.model().appendRow(parent_header)


class ComboBox(BaseBox):
    """
    A combo box that can be constructed with the given values that will be contained.
    """

    def __init__(self, parent: Optional[QObject], values: List[str], header: Optional[str] = None,
                 add_none: bool = False) -> None:
        """
        Construct the widget based on the class searcher

        Parameters
        ----------
        parent : QObject
            The parent widget
        values : List[str]
            The values within the combo box
        header : Optional[str], optional
            The non-selectable header in the combo box, by default no header
        add_none : bool, optional
            If 'None' should be added as an option to the combo box, by default False
        """
        super().__init__(parent=parent)

        if not values and not add_none:
            raise ValueError("No values given to ComboBox and add_none is False.")

        for name in values:
            child_name = name
            child_item = QStandardItem(name)
            self.model().appendRow(child_item)

        if add_none:
            child_name = 'none'
            child_item = QStandardItem(child_name)
            self.model().appendRow(child_item)

        self.setCurrentText(child_name)
