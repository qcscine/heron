#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from scine_heron.database.runtime_histogram_dialog import RuntimeHistogramDialog
from scine_heron.utilities import (
    color_axis,
    color_figure,
    get_font,
)

from PySide2.QtWidgets import QWidget, QPushButton, QGridLayout, QFrame

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.colors import to_hex, to_rgb
from json import dumps
import numpy as np
from typing import List, Optional
from scine_database import Manager


class TwoPieCharts(FigureCanvasQTAgg):
    def __init__(self, width=5, height=4):
        self.fig = Figure(figsize=(width, height))
        self.ax1 = self.fig.add_subplot(1, 2, 1)
        self.ax2 = self.fig.add_subplot(1, 2, 2)
        color_figure(self.fig)
        self.font = get_font()
        color_axis(self.ax1)
        color_axis(self.ax2)
        super(TwoPieCharts, self).__init__(self.fig)

    def update_statistics(self, db_manager: Manager, fake: bool = False) -> None:

        select_all = dumps({})
        calculations = db_manager.get_collection("calculations")
        structures = db_manager.get_collection("structures")
        compounds = db_manager.get_collection("compounds")
        flasks = db_manager.get_collection("flasks")
        properties = db_manager.get_collection("properties")
        elementary_steps = db_manager.get_collection("elementary_steps")
        reactions = db_manager.get_collection("reactions")

        element_counts_labels = [
            "Calculations",
            "Structures",
            "Compounds",
            "Flasks",
            "Properties",
            "Elementary Steps",
            "Reactions",
        ]
        if fake:
            element_counts_data = [0, 0, 0, 0, 0, 0, 0]
        else:
            element_counts_data = [
                calculations.count(select_all),
                structures.count(select_all),
                compounds.count(select_all),
                flasks.count(select_all),
                properties.count(select_all),
                elementary_steps.count(select_all),
                reactions.count(select_all),
            ]
        self.set_up_pie(
            "ax1", "Document Counts", element_counts_data, element_counts_labels
        )

        calculation_counts_labels = ["Hold", "New", "Pending", "Complete", "Failed"]
        if fake:
            calculation_counts_data = [0, 0, 0, 0, 0]
        else:
            calculation_counts_data = [
                calculations.count(dumps({"status": "hold"})),
                calculations.count(dumps({"status": "new"})),
                calculations.count(dumps({"status": "pending"})),
                calculations.count(dumps({"status": "complete"})),
                calculations.count(dumps({"status": "failed"})),
            ]
        self.set_up_pie(
            "ax2",
            "Calculation Counts",
            calculation_counts_data,
            calculation_counts_labels,
        )

        self.fig.tight_layout()
        self.fig.canvas.draw_idle()

    def set_up_pie(
        self, ax: str, title: str, data: List[int], labels: List[str]
    ) -> None:
        axis = getattr(self, ax)
        axis.cla()

        def color_fade(c1, c2, mix):
            c1 = np.array(to_rgb(c1))
            c2 = np.array(to_rgb(c2))
            return to_hex((1 - mix) * c1 + mix * c2)

        colors = [
            color_fade("#214478", "#AFC6E9", i / len(labels))
            for i in range(len(labels))
        ]

        if sum(data) == 0:
            pie_data = [1 for _ in labels]
        else:
            pie_data = data

        pie = axis.pie(
            pie_data,
            colors=colors,
            explode=[0 for _ in labels],
            rotatelabels=True,
            shadow=False,
            startangle=90,
        )
        axis.set_title(title, self.font)

        if sum(data) == 0.0:
            percentages = [0.0 for _ in pie_data]
        else:
            percentages = [i * 100 / sum(pie_data) for i in pie_data]

        ll = [
            "{:d} ({:4.2f} %) {:s}".format(b, p, a)
            for a, b, p in zip(labels, data, percentages)
        ]
        axis.legend(pie[0], ll, loc="upper center", bbox_to_anchor=(0.5, -0.05))
        axis.axis("equal")


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class DatabaseMonitorWidget(QWidget):
    def __init__(self, parent: Optional[QWidget], db_manager) -> None:
        super(DatabaseMonitorWidget, self).__init__(parent)
        self.db_manager = db_manager

        # Create layout and add widgets
        layout = QGridLayout()
        self.element_counts = TwoPieCharts()
        self.element_counts.update_statistics(self.db_manager, fake=True)
        layout.addWidget(self.element_counts, 0, 0, 1, 3)
        self.button_update = QPushButton("Update")
        layout.addWidget(self.button_update, 1, 1)
        self.button_update.clicked.connect(self.update_statistics)  # pylint: disable=no-member
        layout.addWidget(QHLine(), 2, 0, 1, 3)

        self.button_runtime = QPushButton("Runtime Histogram")
        layout.addWidget(self.button_runtime, 3, 1)
        self.button_runtime.clicked.connect(self.display_runtime_histogram)  # pylint: disable=no-member

        # Set dialog layout
        self.setLayout(layout)

    def update_statistics(self) -> None:
        self.element_counts.update_statistics(self.db_manager)

    def display_runtime_histogram(self) -> None:
        RuntimeHistogramDialog(self, self.db_manager)
