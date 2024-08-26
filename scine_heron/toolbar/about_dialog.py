#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

import os

import scine_heron
from scine_heron.resources import resource_path

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
)
from PySide2.QtSvg import QSvgWidget


class AboutDialog(QWidget):
    def __init__(
            self, parent: QWidget,
            window_title: str = "About Heron",
    ) -> None:
        super(AboutDialog, self).__init__(parent)
        self.setWindowTitle(window_title)

        # Class members for widgets
        self.__layout = QVBoxLayout()
        self.__logo_box = QWidget()
        self.__logo_box.setFixedSize(450, 250)
        self.__logo_box_layout = QHBoxLayout()
        self.__logo_box.setLayout(self.__logo_box_layout)
        heron_logo_path = os.path.join(resource_path(), 'heron_logo.svg')
        scine_logo_path = os.path.join(resource_path(), 'scine_logo.svg')
        self.__scine_logo = QSvgWidget(self)
        self.__scine_logo.load(scine_logo_path)
        self.__scine_logo.setFixedSize(200, 200)
        self.__logo_box_layout.addWidget(self.__scine_logo)
        self.__heron_logo = QSvgWidget(self)
        self.__heron_logo.load(heron_logo_path)
        self.__heron_logo.setFixedSize(200, 200)
        self.__logo_box_layout.addWidget(self.__heron_logo)
        self.__layout.addWidget(self.__logo_box)
        version = scine_heron.__version__
        self.__layout.addWidget(QLabel('Version:'))
        self.__layout.addWidget(QLabel(f'''
            {version}
        '''))
        self.__scine_link = QLabel('''
        https://scine.ethz.ch
        ''')
        self.__scine_link.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.__layout.addWidget(QLabel('SCINE Website:'))
        self.__layout.addWidget(self.__scine_link)
        self.__layout.addWidget(QLabel('Heron GitHub:'))
        self.__github_link = QLabel('''
        https://gitub.com/qcscine/heron
        ''')
        self.__github_link.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.__layout.addWidget(self.__github_link)
        self.__layout.addWidget(QLabel('Description:'))
        self.__layout.addWidget(QLabel('''
        Heron is a graphical user interface for all SCINE software packages.
        It is mainly developed in the Reiher group at ETH Zurich.
        '''))
        self.__layout.addWidget(QLabel('License:'))
        self.__layout.addWidget(QLabel('''
        This code is licensed under the 3-clause BSD license. Copyright
        ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
        '''))

        # Set dialog layout
        self.setLayout(self.__layout)
