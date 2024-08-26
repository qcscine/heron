__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

import sys
from typing import TYPE_CHECKING, Any

from PySide2.QtCore import QObject  # , QProcess

if TYPE_CHECKING:
    Signal = Any
else:
    pass
from PySide2.QtCore import Signal
from PySide2.QtWidgets import QTextEdit, QVBoxLayout, QWidget


class OutputWidget(QWidget):
    class EmittingStream(QObject):
        textWritten = Signal(str)

        def __init__(self):
            QObject.__init__(self)

        def write(self, text):
            self.textWritten.emit(str(text))

    def __init__(self, parent: QWidget):
        QWidget.__init__(self, parent)
        self.output = QTextEdit()
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(self.output)
        # self.process = QProcess(self)
        # self.process.readyRead.connect(self.writeOutput)

        # sys.stdout = self.EmittingStream()
        # sys.stdout.textWritten.connect(self.writeOutput)

        self.setLayout(self.__layout)

    def __del__(self):
        sys.stdout = sys.__stdout__

    def writeOutput(self, text):
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.End)
        # cursor.insertText(str(text))
        cursor.insertText(str(text))
        self.output.ensureCursorVisible()
