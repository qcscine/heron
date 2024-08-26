#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

import os

from PySide2.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget
from PySide2.QtGui import QBrush, QColor, QPixmap

from scine_heron.autocas.autocas_settings import AutocasSettings
from scine_heron.autocas.signal_handler import SignalHandler
from scine_heron.styling.delegates import CustomLightDelegate
import scine_heron.config as config


class FileTreeWidget(QTreeWidget):
    def __init__(
        self,
        parent: QWidget,
        signal_handler: SignalHandler,
        autocas_settings: AutocasSettings,
    ):
        super().__init__(parent)
        if config.MODE in config.LIGHT_MODES:
            self.setItemDelegate(CustomLightDelegate())
        self.signal_handler = signal_handler
        self.settings = autocas_settings

        self.main_dir = os.getcwd()
        self.setHeaderLabels([self.main_dir])
        # self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # self.setColumnCount(1)
        # self.setAlternatingRowColors(False)
        self.fillTree()
        # self.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        # self.header().setStretchLastSection(False)
        # self.header().setSectionResizeMode(5, QHeaderView.Stretch)
        self.show()
        # pylint: disable-next=E1101
        self.itemClicked.connect(self.load_item)

        self.visible = True
        self.expand_ico = QPixmap(":teRightArrow.png")
        self.collapse_ico = QPixmap(":teLeftArrow.png")
        self.signal_handler.toggle_file_tree.connect(self.__toggle)

    def __toggle(self):
        if self.visible:
            self.setVisible(False)
            self.visible = False
        else:
            self.setVisible(True)
            self.visible = True

    def fillTree(self):
        def iterate(currentDir, currentItem):
            for f in os.listdir(currentDir):
                path = os.path.join(currentDir, f)
                if f.startswith("."):
                    pass
                else:
                    if os.path.isdir(path):
                        dirItem = QTreeWidgetItem(currentItem)
                        dirItem.setText(0, f)
                        dirItem.setText(1, path)
                        iterate(path, dirItem)
                    elif not os.path.isdir(path):
                        dirItem = QTreeWidgetItem(currentItem)
                        dirItem.setText(0, f)
                        dirItem.setText(1, path)
                        if dirItem.text(0).endswith(".xyz") or dirItem.text(0).endswith(".molden")\
                                or dirItem.text(0).endswith("groups.dat"):
                            pass
                        else:
                            dirItem.setForeground(0, QBrush(QColor("red")))
        iterate(self.main_dir, self)

    def load_item(self, item):
        if item.text(0).endswith(".xyz"):
            # print("Loading xyz-file")
            self.signal_handler.open_molecule_widget_signal.emit()
            self.signal_handler.load_xyz_file_signal.emit(item.text(1))
        elif item.text(0).endswith(".molden"):
            # print("Loading molden-file")
            self.signal_handler.open_molecule_widget_signal.emit()
            self.signal_handler.load_molden_file_signal.emit(item.text(1))
        elif item.text(0).endswith("groups.dat"):
            # print("Loading orbital groups-file")
            self.signal_handler.load_orbital_groups_file_signal.emit(item.text(1))
            # TODO
