#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the StatusBar class.
"""

from typing import Optional

from PySide2.QtWidgets import QStatusBar
from PySide2.QtCore import QObject, QTimer


class StatusBar(QStatusBar):
    """
    Provide errors and warnings.
    """

    def __init__(self, parent: QObject):
        QStatusBar.__init__(self, parent)
        self.__current_message = ""
        self.__current_message_is_error = False
        self.__default_style = self.styleSheet()
        self.__timer = QTimer()
        self.__timer.timeout.connect(self.reset_style)  # pylint: disable=no-member

    def update_error_status(self, line: str, timer: Optional[int] = 10000, clear_status: bool = False) -> None:
        if self.__current_message and self.__current_message_is_error and not clear_status:
            line = f"{self.__current_message}; {line}"
        self.__current_message_is_error = True
        self.clear_message()
        self.__timer.stop()
        self.setStyleSheet(
            "QStatusBar{padding-left:8px;background:rgba(179, 43, 43, 255);color:black;font-weight:bold;}"
        )
        self.__write_content(line, timer)
        if timer is not None:
            self.__timer.start(timer + 50)
        else:
            self.__timer.start(50)

    def update_status(self, line: str, timer: Optional[int] = 10000) -> None:
        if self.__current_message and not self.__current_message_is_error:
            line = f"{self.__current_message}; {line}"
        self.__current_message_is_error = False
        self.clear_message()
        self.__write_content(line, timer)

    def __write_content(self, line: str, timer: Optional[int] = 10000) -> None:
        if timer is not None:
            self.showMessage(line, timer)
        else:
            self.showMessage(line)
        self.__current_message = line
        self.repaint()

    def reset_style(self):
        self.__current_message = ""
        self.setStyleSheet(self.__default_style)

    def clear_message(self):
        super().clearMessage()
        self.reset_style()
        self.repaint()
