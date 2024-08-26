#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the GroupedComboBox class.
"""

from PySide2.QtCore import QObject
from PySide2.QtGui import QStandardItem
from scine_heron.containers.combo_box import BaseBox
from scine_heron.chemoton.class_searcher import ChemotonClassSearcher


class GroupedComboBox(BaseBox):
    """
    A combo box that can be constructed with a ChemotonClassSearcher to include all its
    held classes as selectable items and split them based on its module information.
    """

    def __init__(self, parent: QObject, class_searcher: ChemotonClassSearcher, add_none: bool = False) -> None:
        """
        Construct the widget based on the class searcher

        Parameters
        ----------
        parent : QObject
            The parent widget
        class_searcher : ChemotonClassSearcher
            The class searcher holding the classes that are selectable
        add_none : bool, optional
            If 'None' should be added as an option to the combo box, by default False
        """
        BaseBox.__init__(self, parent=parent)

        self.gear_searcher = class_searcher
        child_buffer = ' ' * 3
        child_name = str()  # use for gear name selection.

        if add_none:
            parent_item = QStandardItem("none")
            parent_item.setEnabled(False)
            self.model().appendRow(parent_item)
            child_name = child_buffer + "none"
            child_item = QStandardItem(child_name)
            self.model().appendRow(child_item)

        for module in sorted(self.gear_searcher.module_to_class.keys()):
            parent_item = QStandardItem(module)
            parent_item.setEnabled(False)
            self.model().appendRow(parent_item)

            for item_name in self.gear_searcher.module_to_class[module]:
                child_name = child_buffer + item_name
                child_item = QStandardItem(child_name)
                self.model().appendRow(child_item)

        self.setCurrentText(child_name)
