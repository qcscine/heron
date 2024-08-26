#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import List, Optional

from PySide2.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLayout


class VerticalLayout(QVBoxLayout):
    """
    Inherits from QVBoxLayout and is equal in all aspects but can be constructed
    with multiple widgets to be in the layout add once and can add multiple widgets at
    once later.
    """

    def __init__(self, widgets: Optional[List[QWidget]] = None):
        """
        Construct the widget with an optional list of widgets to be added to the
        constructed layout. The order in the list determines the order in the layout.

        Parameters
        ----------
        widgets : Optional[List[QWidget]], optional
            The optional widgets for the layout, by default None
        """
        super().__init__()
        if widgets is not None:
            for w in widgets:
                self.addWidget(w)

    def add_widgets(self, widgets: List[QWidget]) -> None:
        """
        Add multiple widgets to the layout.
        The order in the list determines the order in the layout.

        Parameters
        ----------
        widgets : List[QWidget]
            The added widgets
        """
        for w in widgets:
            self.addWidget(w)

    def add_layouts(self, layouts: List[QLayout]) -> None:
        """
        Add multiple sublayouts to the layout.
        The order in the list determines the order in the layout.

        Parameters
        ----------
        layouts : List[QLayout]
            The added layouts
        """
        for layout in layouts:
            self.addLayout(layout)


class HorizontalLayout(QHBoxLayout):
    """
    Inherits from QHBoxLayout and is equal in all aspects but can be constructed
    with multiple widgets to be in the layout add once and can add multiple widgets at
    once later.
    """

    def __init__(self, widgets: Optional[List[QWidget]] = None):
        """
        Construct the widget with an optional list of widgets to be added to the
        constructed layout. The order in the list determines the order in the layout.

        Parameters
        ----------
        widgets : Optional[List[QWidget]], optional
            The optional widgets for the layout, by default None
        """
        super().__init__()
        if widgets is not None:
            for w in widgets:
                self.addWidget(w)

    def add_widgets(self, widgets: List[QWidget]) -> None:
        """
        Add multiple widgets to the layout.
        The order in the list determines the order in the layout.

        Parameters
        ----------
        widgets : List[QWidget]
            The added widgets
        """
        for w in widgets:
            self.addWidget(w)

    def add_layouts(self, layouts: List[QLayout]) -> None:
        """
        Add multiple sublayouts to the layout.
        The order in the list determines the order in the layout.

        Parameters
        ----------
        layouts : List[QLayout]
            The added layouts
        """
        for layout in layouts:
            self.addLayout(layout)
