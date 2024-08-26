#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional
from PySide2.QtWidgets import QLabel
from PySide2.QtCore import QObject


class WrappedLabel(QLabel):
    """
    A QLabel with the word wrap enabled by default.
    """

    def __init__(self, text: str, parent: Optional[QObject] = None):
        """
        Construct the label with the text and activate word wrap.

        Parameters
        ----------
        text : str
            The text in the label
        parent : Optional[QObject], optional
            The parent of the widget, by default None
        """
        super().__init__(text, parent=parent)
        self.setWordWrap(True)
