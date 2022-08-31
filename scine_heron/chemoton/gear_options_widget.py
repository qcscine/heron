#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the GearOptionsWidget class.
"""

from typing import Optional, Dict
from scine_chemoton import gears  # pylint: disable=import-error
from scine_heron.chemoton.dict_option_widget import DictOptionWidget
from PySide2.QtGui import QCloseEvent
from PySide2.QtCore import Qt, QObject
from PySide2.QtWidgets import (
    QVBoxLayout,
    QScrollArea,
    QDialog,
)


class GearOptionsWidget(QDialog):
    """
    QDialog for gear settings.
    """

    def __init__(
        self,
        gear: gears.Gear,
        docstring: Dict[str, str],
        parent: Optional[QObject] = None,
    ) -> None:
        super(GearOptionsWidget, self).__init__(parent)
        self.__gear = gear  # pylint: disable=unused-private-member
        self.__options = gear.options
        self.__option_widget = DictOptionWidget(
            DictOptionWidget.get_attributes_of_object(self.__options),
            parent=self,
            docstring_dict=docstring,
        )

        self.setWindowTitle("Options")
        self.setMinimumWidth(350)
        self.setMinimumHeight(100)
        self.setMaximumWidth(650)
        self.setMaximumHeight(900)

        layout = QVBoxLayout()

        self.__scroll_area = QScrollArea()
        self.__scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.__scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.__scroll_area.setWidget(self.__option_widget)
        self.__scroll_area.setWidgetResizable(True)
        layout.addWidget(self.__scroll_area)

        self.setLayout(layout)

    def closeEvent(self, _: QCloseEvent) -> None:
        """
        Update gear options.
        """
        DictOptionWidget.set_attributes_to_object(
            self.__options, self.__option_widget.get_widget_data()
        )
