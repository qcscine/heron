#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the ChemotonEnginesWidget class.
"""

from PySide2.QtWidgets import (
    QWidget,
    QScrollArea,
    QGridLayout,
)
from functools import partial
from PySide2.QtCore import Qt
from PySide2.QtCore import QObject
from scine_database import Manager
from typing import List, Optional
from scine_heron.chemoton.engines_widget import EngineWidget
from scine_heron.chemoton.create_engine_widget import CreateEngineWidget
from scine_heron.chemoton.gear_searcher import GearSearcher
from scine_heron.chemoton.docstring_parser import DocStringParser


class ChemotonEnginesWidget(QWidget):
    """
    Container Widget for EngineWidgets in a grid view.
    """

    def __init__(self, parent: Optional[QObject], db_manager: Manager) -> None:
        QWidget.__init__(self, parent)
        self.db_manager = db_manager
        self.gear_searcher = GearSearcher()
        self.doc_string_parser = DocStringParser()

        self.__add_engine_widget = CreateEngineWidget(
            self, self.db_manager, self.gear_searcher
        )

        self.__engines: List[EngineWidget] = []
        self.__engines_widget = QWidget()
        self.__engines_layout = QGridLayout()
        self.__engines_widget.setLayout(self.__engines_layout)

        self.__scroll_area = QScrollArea()
        self.__scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.__scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.__scroll_area.setWidget(self.__engines_widget)
        self.__scroll_area.setWidgetResizable(True)

        self.__layout = QGridLayout()
        self.__layout.addWidget(self.__scroll_area, 0, 0)
        self.__layout.addWidget(self.__add_engine_widget, 0, 1)

        self.__max_engines_per_row = 3
        self.setLayout(self.__layout)

    def add_engine(self, engine_widget: EngineWidget) -> None:
        count = len(self.__engines)
        row = count // self.__max_engines_per_row
        column = count % self.__max_engines_per_row

        self.__engines.append(engine_widget)
        self.__engines_layout.addWidget(engine_widget, row, column)

        engine_widget.set_docstring_dict(
            self.doc_string_parser.get_docstring_for_object_attrs(
                engine_widget.gear.__class__.__name__, engine_widget.gear.options
            )
        )
        engine_widget.button_delete.clicked.connect(  # pylint: disable=no-member
            partial(self.delete_engine, engine_widget)
        )

    def delete_engine(self, engine_widget: EngineWidget) -> None:
        idx = self.__engines.index(engine_widget)
        self.__engines.pop(idx)
        engine_widget.stop_engine_if_working()

        # clear layout
        for i in reversed(range(self.__engines_layout.count())):
            self.__engines_layout.itemAt(i).widget().setParent(None)  # type: ignore[call-overload]

        # add remaining widgets
        for i in range(len(self.__engines)):
            row = i // self.__max_engines_per_row
            column = i % self.__max_engines_per_row
            self.__engines_layout.addWidget(self.__engines[i], row, column)
