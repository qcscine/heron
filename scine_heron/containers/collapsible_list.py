#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from abc import abstractmethod
from typing import Any, Optional, Dict

from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QCompleter,
    QToolButton,
    QSizePolicy,
    QLineEdit,
    QLabel,
    QPushButton,
)
from PySide2.QtCore import Qt, QObject, QSize

from scine_heron.utilities import write_error_message


class AbstractList(QWidget):  # typing help

    @abstractmethod
    def set_current_item(self, item: Any) -> None:
        pass

    def focus(self) -> None:
        pass


class CollapsibleListItem(QWidget):

    def __init__(self, parent: AbstractList, name: str, content_widget: QWidget) -> None:
        super().__init__(parent)
        self._parent = parent
        self.name = name

        self.toggle_button = QToolButton(parent=self)
        self.toggle_button.setText(name)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.pressed.connect(self.on_pressed)  # pylint: disable=no-member

        self.content = content_widget
        self.content.setVisible(False)
        self.content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content)
        layout.setAlignment(Qt.AlignTop)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_visibility(self, visible: bool) -> None:
        self.toggle_button.setChecked(visible)
        self.on_pressed()

    def on_pressed(self):
        self.content.setVisible(not self.content.isVisible())
        self.toggle_button.setArrowType(Qt.DownArrow if self.content.isVisible() else Qt.RightArrow)
        self.content.updateGeometry()
        self.updateGeometry()

    def size(self) -> QSize:
        content_size = self.content.size().height() if not self.toggle_button.isChecked() else 0
        return self.toggle_button.size() + QSize(0, content_size)


class CollapsibleList(AbstractList):

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self._parent = parent
        self._layout = QVBoxLayout()
        self._layout.setAlignment(Qt.AlignTop)

        self._search_button = QPushButton("Ok")
        self._search_button.clicked.connect(  # pylint: disable=no-member
            self._search_and_display
        )
        self._search_box = QLineEdit("")
        self._search_box.returnPressed.connect(  # pylint: disable=no-member
            self._search_button.click
        )

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Jump to:"))
        search_layout.addWidget(self._search_box)
        search_layout.addWidget(self._search_button)
        self._layout.addLayout(search_layout)

        self._widgets: Dict[str, CollapsibleListItem] = {}
        self._current_widget: Optional[str] = None
        self.setLayout(self._layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def clear(self) -> None:
        for widget in self._widgets.values():
            self._layout.removeWidget(widget)
            widget.deleteLater()
        self._widgets = {}
        self._current_widget = None

    def _search_and_display(self) -> None:
        query = self._search_box.text().strip()
        if query not in self._widgets:
            write_error_message(f"The item '{query}' does not exist in the list")
        else:
            self.set_current_item(self._widgets[query])
            self.focus()

    def set_current_item(self, item: CollapsibleListItem) -> None:
        self._current_widget = item.name

    def focus(self):
        self._widgets[self._current_widget].set_visibility(True)
        if hasattr(self._parent, "focus"):
            self._parent.focus()
        self.updateGeometry()

    def add_widget(self, item: CollapsibleListItem) -> None:
        self._layout.addStretch(1)
        self._layout.addWidget(item)
        self._widgets[item.name] = item
        self._update_suggestions()

    def remove_widget(self, item: CollapsibleListItem) -> None:
        self._layout.removeWidget(item)
        item.deleteLater()
        self._widgets.pop(item.name)
        self._layout.removeWidget(item)
        item.deleteLater()
        self._update_suggestions()

    def _update_suggestions(self):
        completer = QCompleter(list(self._widgets.keys()))
        self._search_box.setCompleter(completer)

    def get_item_by_name(self, name: str) -> Optional[CollapsibleListItem]:
        try:
            return self._widgets[name]
        except KeyError:
            return None

    def current_item(self) -> Optional[CollapsibleListItem]:
        if self._current_widget is None:
            return None
        return self._widgets[self._current_widget]

    def contextMenuEvent(self, event):
        current = self.current_item()
        if current is not None:
            current.contextMenuEvent(event)

    def __len__(self):
        return len(self._widgets)

    def __iter__(self):
        return (w for w in self._widgets.values())
