#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
import numpy as np
from datetime import timedelta
from typing import Optional, List

from scine_heron.multithread import Worker
from scine_heron.utilities import (
    color_axis,
    color_figure,
    get_font,
)

from PySide2.QtCore import QObject, QThreadPool, SignalInstance
from PySide2.QtWidgets import QPushButton, QVBoxLayout, QDialog, QLabel

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from json import dumps

from .db_queries import finished_calculations, unstarted_calculations


class RuntimeHistogramDialog(QDialog):
    class Chart(FigureCanvasQTAgg):
        def __init__(self, db_manager, width=5, height=4) -> None:
            self.fig = Figure(figsize=(width, height))
            self.ax1 = self.fig.add_subplot(2, 1, 1)
            self.ax2 = self.fig.add_subplot(2, 1, 2)
            color_figure(self.fig)
            self.font = get_font()
            color_axis(self.ax2)
            color_axis(self.ax1)
            super(RuntimeHistogramDialog.Chart, self).__init__(self.fig)
            self.db_manager = db_manager
            self.ax1.cla()
            self.ax2.cla()
            self.fig.tight_layout()
            self.draw()
            self.__currently_updating = False
            self.walltime: List[float] = []
            self.cpuh: List[float] = []

        def update_complete(self):
            self.__draw_plot()
            self.__currently_updating = False

        def update_data(self):
            if not self.__currently_updating:
                self.__currently_updating = True
                worker = Worker(self.__update_data)
                worker.signals.finished.connect(self.update_complete)
                pool = QThreadPool.globalInstance()
                pool.start(worker)

        def __update_data(self, progress_callback: SignalInstance):   # pylint: disable=unused-argument
            calculations = self.db_manager.get_collection("calculations")
            selection = finished_calculations()
            # Loop over all results
            self.walltime = []
            self.cpuh = []
            for calculation in calculations.query_calculations(dumps(selection)):
                if calculation.has_runtime():
                    cores = calculation.get_job().cores
                    runtime = calculation.get_runtime()
                    self.walltime.append(runtime)
                    self.cpuh.append(cores * runtime)

            if not self.walltime:
                self.walltime = [1.0]
                self.cpuh = [1.0]

        def __draw_plot(self):
            min_val = np.floor(np.log10(np.min(self.walltime)))
            max_val = np.ceil(np.log10(np.max(self.walltime)))
            self.ax1.cla()
            self.ax1.hist(
                self.walltime,
                bins=10 ** np.linspace(min_val, max_val, 50),
                log=False,
                color="lightblue",
            )
            self.ax1.set_title("Walltime", self.font)
            self.ax1.set_xlabel("Walltime in s")
            self.ax1.set_ylabel("Count")
            self.ax1.set_xscale("log")

            min_val = np.floor(np.log10(np.min(self.cpuh)))
            max_val = np.ceil(np.log10(np.max(self.cpuh)))
            self.ax2.cla()
            self.ax2.hist(
                self.cpuh,
                bins=10 ** np.linspace(min_val, max_val, 50),
                log=False,
                color="lightblue",
            )
            self.ax2.set_title("CPU Time", self.font)
            self.ax2.set_xlabel("CPU Time in s")
            self.ax2.set_ylabel("Count")
            self.ax2.set_xscale("log")
            self.fig.tight_layout()
            self._add_reference_time_labels()
            self.draw()

        def _add_reference_time_labels(self):
            color = "C1"
            special_x = [60.0, 3600.0, 86400.0, 604800.0]
            labels = ['minute', 'hour', 'day', 'week']
            for ax in [self.ax1, self.ax2]:
                y_pos = np.mean(ax.get_ylim())
                for sx, label in zip(special_x, labels):
                    ax.axvline(x=sx, color=color)
                    ax.text(sx, y_pos, label,
                            fontsize=10, color=color,
                            rotation=90, rotation_mode='anchor')

    class InfoText(QLabel):
        def __init__(self, db_manager=None) -> None:
            super().__init__()
            self.db_manager = db_manager
            self.setText("Click on update to retrieve runtime information")

        def update_data(self):
            self.setText("Querying database...")
            self.repaint()  # required to update mid-function
            calculations = self.db_manager.get_collection("calculations")
            selection = finished_calculations()
            n_calcs = calculations.count(dumps(selection))
            if n_calcs == 0:
                self.setText("No finished calculations so far")
                return
            avg_wall_time = sum(
                c.runtime for c in calculations.query_calculations(dumps(selection)) if c.runtime is not None
            )
            avg_wall_time = timedelta(seconds=(avg_wall_time / n_calcs))
            text = (
                f"Total walltime so far: {self._string(avg_wall_time * n_calcs)} \n"
                + f"Average walltime per job: {self._string(avg_wall_time)} \n"
            )
            n_pending = calculations.count(dumps({"status": "pending"}))
            if n_pending > 0:
                avg_cores_for_pending = sum(
                    c.get_job().cores
                    for c in calculations.query_calculations(
                        dumps({"status": "pending"})
                    )
                )
                avg_cores_for_pending /= n_pending
                n_todo = calculations.count(dumps(unstarted_calculations()))
                walltime_left = (
                    n_todo * avg_wall_time * avg_cores_for_pending / n_pending
                )
                workers = "puffins" if n_pending > 1 else "puffin"
                text += f"Estimated walltime left with currently {n_pending} {workers}: {self._string(walltime_left)}"
            self.setText(text)

        @staticmethod
        def _string(t: timedelta) -> str:
            """
            Custom string conversion for timedelta to get rid of microseconds from default __str__
            """
            new_t = t - timedelta(microseconds=t.microseconds)
            return str(new_t)

    def __init__(
        self,
        parent: Optional[QObject] = None,
        db_manager=None,
        window_title: str = "Runtime Histogram",
    ) -> None:
        super(RuntimeHistogramDialog, self).__init__(parent)
        self.setWindowTitle(window_title)

        # Create layout and add widgets
        layout = QVBoxLayout()
        self.chart = self.Chart(db_manager)
        layout.addWidget(self.chart)
        self.info_text = self.InfoText(db_manager)
        layout.addWidget(self.info_text)

        self.button_update = QPushButton("Update")
        layout.addWidget(self.button_update)
        self.button_update.clicked.connect(self.update_data)  # pylint: disable=no-member

        self.button_close = QPushButton("Close")
        layout.addWidget(self.button_close)
        self.button_close.clicked.connect(self.close)  # pylint: disable=no-member

        # Set dialog layout
        self.setLayout(layout)
        self.exec_()

    def update_data(self):
        self.info_text.update_data()
        self.chart.update_data()
