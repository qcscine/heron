#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Callable, Optional

from PySide2.QtWidgets import QPushButton, QWidget
from PySide2.QtGui import QKeySequence

from .clickable import Clickable


class TextPushButton(QPushButton, Clickable):
    """
    A push button that triggers a function and only displays some text.
    """

    def __init__(self,
                 text: str,
                 action: Optional[Callable[[], None]] = None,
                 parent: Optional[QWidget] = None,
                 shortcut: Optional[str] = None,
                 max_width: Optional[int] = None) -> None:
        """
        Construct the button with the displayed text and the function to be called
        when the button is clicked

        Parameters
        ----------
        text : str
            The displayed text
        action : Callable
            The function triggerd by clicking
        parent : Optional[QWidget], optional
            The parent widget, by default None
        shortcut : Optional[str], optional
            A keyboard shortcut for the button, which is also added as a tooltip, by default None
        """
        super().__init__(text, parent=parent)
        if action is not None:
            self.clicked.connect(action)  # pylint: disable=no-member
        if shortcut is not None:
            self.setShortcut(QKeySequence(shortcut))
            self.setToolTip(shortcut)
        if max_width is not None:
            self.setMaximumWidth(max_width)
