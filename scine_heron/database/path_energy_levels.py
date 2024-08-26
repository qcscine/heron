#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from typing import Any, List, Union, Tuple
import re
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

import scine_database as db

from scine_chemoton.utilities.get_molecular_formula import get_molecular_formula_of_aggregate

from scine_heron.database.energy_diagram import EnergyDiagram
from scine_heron.toolbar.io_toolbar import HeronToolBar
from scine_heron.io.file_browser_popup import get_save_file_name

from PySide2.QtWidgets import (
    QWidget,
    QCheckBox,
    QGraphicsView,
    QVBoxLayout,
    QHBoxLayout,
    QGraphicsScene,
    QScrollArea,
    QStyle,
)
from PySide2.QtGui import (
    QGuiApplication
)
from PySide2.QtCore import Qt


class CustomQScrollArea(QScrollArea):
    def wheelEvent(self, event):
        modifiers = QGuiApplication.keyboardModifiers()
        if self.widget().mol_widget.underMouse() and modifiers == Qt.ControlModifier:
            self.widget().mol_widget.wheelEvent(event)
        elif self.widget().mol_widget.underMouse():
            super(CustomQScrollArea, self).wheelEvent(event)
        else:
            super(CustomQScrollArea, self).wheelEvent(event)


class PathLevelWidget(QWidget):
    def __init__(self, parent: QWidget, db_manager: db.Manager,
                 levels: List[float], barrierless: List[bool], type_list: List[Any],
                 path_info: Tuple[int, float, List[Any]], rxn_equation: str, es_method_info: str) -> None:
        self.window_width = 1000
        self.window_height = 800
        self.scene_object = QGraphicsScene(0, 0, self.window_width, self.window_height)
        super(PathLevelWidget, self).__init__(parent=parent)
        self.db_manager = db_manager

        layout_main = QVBoxLayout()
        layout = QVBoxLayout()
        self.path_level_diagram = PathLevelDiagramWidget(self, self.db_manager, path_info[2],
                                                         levels, barrierless, type_list, rxn_equation, es_method_info)
        layout.addWidget(self.path_level_diagram)

        self.path_level_settings = PathLevelDiagramSettings(self, self.path_level_diagram)
        layout.addWidget(self.path_level_settings)
        # Add 1st Row
        layout_main.addLayout(layout)

        self.view = QGraphicsView(self.scene_object)
        self.view.setLayout(layout_main)
        self.view.setWindowTitle(
            "Path #" + str(path_info[0]) + " - Length " + str(path_info[1]))
        self.view.show()


class PathLevelDiagramWidget(QWidget):
    def __init__(self, parent: QWidget, db_manager: db.Manager, path: List[Any],
                 levels: List[float], barrierless: List[bool], type_list: List[Any], rxn_equation: str,
                 es_method_info: str) -> None:
        self.window_width = 1000
        self.window_height = 800
        self.scene_object = QGraphicsScene(0, 0, self.window_width, self.window_height)
        super(PathLevelDiagramWidget, self).__init__(parent=parent)
        self.db_manager = db_manager

        # db-info of selected compound
        self._compound_collection = self.db_manager.get_collection("compounds")
        self._flask_collection = self.db_manager.get_collection("flasks")
        self._structure_collection = self.db_manager.get_collection("structures")
        # # # private variables
        self.path = path
        self.levels = levels
        self.barrierless_list = barrierless
        self.type_list = type_list
        self.overall_rxn_equation = rxn_equation
        self.es_method_info = es_method_info

        layout_main = QVBoxLayout()

        layout = QHBoxLayout()

        self.fig = Figure(figsize=(self.window_width * 0.9, self.window_height * 0.9))
        self.ax1 = self.fig.add_subplot(1, 1, 1)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setMinimumHeight(250)
        self.canvas.setMinimumWidth(400)

        layout.addWidget(self.canvas)

        layout_main.addLayout(layout)

        self.setLayout(layout_main)

        self.generate_energy_diagram()
        self.set_x_label()
        self._format_plot(self.ax1)

    @staticmethod
    def _format_plot(ax):

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.set_ticks_position('left')
        ax.xaxis.set_ticks_position('bottom')
        # Ax lw normally 1.0
        ax.spines['bottom'].set_color('black')
        ax.spines['bottom'].set_linewidth(1.5)
        ax.spines['left'].set_color('black')
        ax.spines['left'].set_linewidth(1.5)
        ax.tick_params(direction='out', length=5, width=1.5, colors='black')

    def set_x_label(self):
        # Format reaction as well
        new_eq = ""
        first = True
        # Loop over sides and reactants to have easier string to regex
        if self.overall_rxn_equation != " = ":  # If no reaction is given, do not try to format it
            for side in self.overall_rxn_equation.split(" = "):
                new_side = ""
                for reactant in side.split(" + "):
                    tmp_factor = reactant.split(" ")[0]
                    tmp_reactant = re.sub(r'(\d+)', r'$_{\1}$', reactant.split(" ")[1].split("(")[0])
                    tmp_charge_multi = "(" + reactant.split("(")[1]
                    new_side += tmp_factor + " " + tmp_reactant + tmp_charge_multi + " + "
                if first:
                    new_side = new_side[:-3] + " = "
                    first = False
                    new_eq += new_side
                else:
                    new_eq += new_side[:-3]
        else:
            new_eq = self.overall_rxn_equation

        self.ax1.set_xlabel(f"{new_eq}\n{self.es_method_info}")

    def _construct_molecular_formula(self, aggregate_id: str, aggregate_type: db.CompoundOrFlask):

        aggregate_str = get_molecular_formula_of_aggregate(
            db.ID(aggregate_id), aggregate_type,
            self._compound_collection, self._flask_collection, self._structure_collection)
        split_aggregate = aggregate_str.split("[")
        if len(split_aggregate) == 1:
            # make subscript and remove (c: x, m: y)
            m_formula = re.sub(r'(\d+)', r'$_{\1}$', split_aggregate[0].split("(")[0].strip())
        else:
            # make subscript
            compounds_string = split_aggregate[1][:-1].replace(" | ", "\n+ ")
            m_formula = re.sub(r'(\d+)', r'$_{\1}$', compounds_string)

        return m_formula

    def generate_energy_diagram(self, print_bottom_formulas: bool = True):
        diagram = EnergyDiagram(9 / 16)  # self.window_width * 0.9/self.window_height * 0.9)
        diagram.dimension = 100
        diagram.top_text_fontsize = 'small'
        diagram.bottom_text_fontsize = 'small'
        digit_round = 1
        diagram.round_energies_at_digit = digit_round
        current_index = 0
        level_index = 0
        # Color scheme
        # TODO adapt to dark mode
        # TODO: Maybe as general setting
        default_line_color = '#85929e'
        barrierless_color = '#c2c9cf'
        ts_level_color = '#995151'
        if print_bottom_formulas:
            starting_state_formula = self._construct_molecular_formula(self.path[0], self.type_list[0])
        else:
            starting_state_formula = ""
        type_list_counter = 1
        # Ground Level at the beginning
        diagram.add_level(self.levels[level_index], bottom_text=starting_state_formula,
                          color=default_line_color, linewidth=4.5,
                          )
        # Skipping does not work yet
        for barrierless in self.barrierless_list:
            current_energy = self.levels[level_index]
            if not barrierless:
                level_index += 1
                # Derive relative change
                rel_energy_change = self.levels[level_index] - current_energy
                tmp_text = "+" if rel_energy_change > 0 else ""
                tmp_text += str(round(rel_energy_change, diagram.round_energies_at_digit))
                # Add TS level
                # Different Color for TS
                diagram.add_level(self.levels[level_index], '', top_text=tmp_text,
                                  color=ts_level_color, linewidth=4.5, linestyle='-')
                current_energy = self.levels[level_index]
                # Link up
                diagram.add_link(current_index, current_index + 1, linewidth=2.0, color=default_line_color)
                current_index += 1
                # Link Down
                diagram.add_link(current_index, current_index + 1, linewidth=2.0, color=default_line_color)
                current_index += 1
                level_index += 1
            else:
                # Jump to next ground state
                level_index += 2
                # Link ground states
                diagram.add_link(current_index, current_index + 1, linewidth=2.0, color=barrierless_color)
                current_index += 1
            # Derive relative change
            # NOTE: maybe make absolute energy optional as well
            rel_energy_change = self.levels[level_index] - current_energy
            tmp_text = "+" if rel_energy_change > 0 else ""
            tmp_text += str(round(rel_energy_change, diagram.round_energies_at_digit))
            tmp_bottom_level_info = ""
            if print_bottom_formulas:
                # # # Absolute energy to bottom
                tmp_bottom_level_info = str(round(self.levels[level_index], digit_round))
                tmp_bottom_level_info += "\n"
                tmp_bottom_level_info += self._construct_molecular_formula(self.path[level_index],
                                                                           self.type_list[type_list_counter])
            type_list_counter += 1  # Counter requires to be increased
            # Add next ground state
            diagram.add_level(self.levels[level_index], bottom_text=tmp_bottom_level_info, top_text=tmp_text,
                              color=default_line_color, linewidth=4.5, linestyle='-')
        # Plot diagram
        range_yaxis = abs(max(self.levels) - min(self.levels))
        custom_ylim = (min(self.levels) - 0.35 * range_yaxis,
                       max(self.levels) + 0.1 * range_yaxis)
        diagram.plot(ax=self.ax1, ylimits=custom_ylim)


class PathLevelDiagramSettings(QWidget):
    def __init__(self, parent: QWidget,
                 diagram_widget: Any
                 ) -> None:
        super(PathLevelDiagramSettings, self).__init__(parent=parent)
        self.p_layout = QHBoxLayout()
        # Elements of widget relative to width of ReactionProfile Canvas
        self._widget_width = 300
        # Fixed width for widget
        self.setMinimumWidth(self._widget_width)
        self.setMaximumWidth(self._widget_width)

        self.diagram_widget = diagram_widget
        self.status_widget: Union[None, QWidget] = None

        # Export svg diagram
        self.toolbar = HeronToolBar(parent=self)
        self.toolbar.shortened_add_action(
            QStyle.SP_DialogSaveButton, "Save Diagram", "Ctrl+S", self._save_svg
        )
        self.p_layout.addWidget(self.toolbar)

        self.show_formulas_of_level = QCheckBox("Show molecular formula")
        self.show_formulas_of_level.setChecked(True)
        self.show_formulas_of_level.stateChanged.connect(self._trigger_diagram_update)  # pylint: disable=no-member
        self.p_layout.addWidget(self.show_formulas_of_level)

        self.setLayout(self.p_layout)
        self.show()

    def _trigger_diagram_update(self):
        self.diagram_widget.ax1.cla()
        if self.show_formulas_of_level.isChecked():
            self.diagram_widget.generate_energy_diagram(print_bottom_formulas=True)
        else:
            self.diagram_widget.generate_energy_diagram(print_bottom_formulas=False)
        self.diagram_widget.set_x_label()
        self.diagram_widget.canvas.draw()

    def _save_svg(self):
        filename = get_save_file_name(self, "energy_diagram", ["svg"])
        self.diagram_widget.canvas.draw()
        self.diagram_widget.fig.savefig(filename, bbox_inches='tight', dpi=300, transparent=True)
