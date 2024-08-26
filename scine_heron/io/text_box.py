#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional
from PySide2.QtCore import QObject
from PySide2.QtWidgets import (
    QLineEdit,
    QInputDialog,
    QDialog,
    QLabel,
    QVBoxLayout,
    QWidget
)


def text_input_box(parent: Optional[QWidget], label: str, question: str, input_field: QLineEdit, hint: str) -> str:
    """
    Create a pop-up window with a single text input field and return text, when the window is closed.

    Parameters
    ----------
    parent : Optional[QWidget]
        The parent of the pop-up window
    label : str
        The label of the pop-up window
    question : str
        The question to be asked before the input field
    input_field : QLineEdit
        The input field
    hint : str
        A prefilled text in the input field

    Returns
    -------
    str
        The entered text
    """
    dialog = QInputDialog(parent=parent)
    return dialog.getText(dialog.parent(), label, question, input_field, hint)[0].strip()


def yes_or_no_question(parent: QObject, question: str, default_answer: str = "yes") -> bool:
    """
    Ask a yes or no question in a pop-up window in which the user can enter
    'y', 'yes', 'n' or 'no' and return True or False, respectively.

    Parameters
    ----------
    parent : QObject
        The parent of the pop-up window
    question : str
        The question to be asked

    Returns
    -------
    bool
        The answer to the question as a bool
    """
    answer = text_input_box(parent, "Scine Heron", f"{question} (y/n)? ", QLineEdit.Normal, default_answer)
    while True:
        if answer.lower().strip() in ["y", "yes"]:
            return True
        if answer.lower().strip() in ["n", "no"]:
            return False
        answer = text_input_box(parent, "Scine Heron", "Did not understand your answer, please write 'yes' or 'no'",
                                QLineEdit.Normal, "yes")


def pop_up_message(parent: QObject, message: str) -> None:
    """
    A pop-up window with a message.

    Parameters
    ----------
    parent : QObject
        The parent of the pop-up window
    message : str
        The message to be displayed
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle("Scine Heron Message")
    layout = QVBoxLayout()
    layout.addWidget(QLabel(message))
    dialog.setLayout(layout)
    dialog.exec_()
