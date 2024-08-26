#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional, Dict
from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout,
)
from PySide2.QtCore import QObject

from scine_heron.containers.combo_box import BaseBox


class ComboBoxTabWidget(QWidget):
    """
    Manually implements tabs and tab changes, by only displaying a combo box and change according to the box.
    We do this because a combo box requires less space than listing all tabs next to each other.
    """

    def __init__(self, tabs: Optional[Dict[str, Optional[QWidget]]] = None, parent: Optional[QObject] = None):
        """
        Construct this container widget with the underlying widgets.

        Parameters
        ----------
        tabs : Optional[Dict[str, QWidget]], optional
            The tabs we hold based on the text and the actual widget.
            Can also be None and be set later via setter, by default None.
        parent : Optional[QObject], optional
            The parent widget, by default None
        """
        super().__init__(parent=parent)
        self._box = BaseBox(self)
        self._layout = QVBoxLayout()
        self._layout.addWidget(self._box)
        self.setLayout(self._layout)
        if tabs is not None:
            self._tabs: Dict[str, Optional[QWidget]] = tabs
            self.set_tabs(tabs)
        else:
            self._tabs = {}

    def _change_tab(self) -> None:
        """
        Changes the displayed widget
        """
        for widget in self._tabs.values():
            if widget is not None:
                widget.setVisible(False)
        wanted = self._box.currentText()
        new_widget = self._tabs[wanted]
        if new_widget is not None:
            new_widget.setVisible(True)

    def set_tabs(self, tabs: Dict[str, Optional[QWidget]]) -> None:
        """
        Rebuilds the container widget with new subwidgets.

        Parameters
        ----------
        tabs : Dict[str, QWidget]
            The new subwidgets.
        """
        self._tabs = tabs
        try:
            self._box.currentIndexChanged.disconnect()  # pylint: disable=no-member
        except RuntimeError:
            pass
        self._box.clear()
        self._box.addItems(list(self._tabs.keys()))
        for key, widget in self._tabs.items():
            if widget is not None:
                self._layout.addWidget(widget)
                self._box.setCurrentText(key)
        self._box.setCurrentText(list(self._tabs.keys())[0])
        self._change_tab()
        self.updateGeometry()
        self._box.currentIndexChanged.connect(  # pylint: disable=no-member
            self._change_tab
        )

    def add_tab(self, tab_name: str, tab: Optional[QWidget]) -> None:
        """
        Adds a new tab to the widget.

        Parameters
        ----------
        tab_name : str
            The name of the tab to appear in the combo box.
        tab : QWidget
            The new tab.
        """
        self._tabs[tab_name] = tab
        self.set_tabs(self._tabs)

    def remove_tab(self, tab_name: str) -> None:
        """
        Removes a tab from the widget.

        Parameters
        ----------
        tab_name : str
            The tab to remove.
        """
        widget = self._tabs.pop(tab_name)
        if widget is not None:
            widget.deleteLater()
            widget.setParent(None)  # type: ignore
        self.set_tabs(self._tabs)
