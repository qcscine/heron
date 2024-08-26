#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import List, Tuple, Optional
from copy import deepcopy
from math import nan

from PySide2.QtWidgets import (
    QGridLayout,
    QLabel,
    QPushButton,
    QWidget,
    QRadioButton,
    QHBoxLayout,
    QDoubleSpinBox,
    QVBoxLayout
)

from scine_heron.autocas.autocas_settings import AutocasSettings
from scine_heron.autocas.signal_handler import SignalHandler


class MODiagram(QWidget):
    def __init__(self, parent: QWidget, signal_handler: SignalHandler, settings: AutocasSettings):
        # TODO: make mo diagram scrollable
        QWidget.__init__(self, parent)
        self.__layout = QVBoxLayout()

        self.signal_handler = signal_handler
        self.autocas_settings = settings

        self.buttons: List[Tuple[QRadioButton, QPushButton]] = []

        self.apply_button = QPushButton("Set CAS")
        self.__layout.addWidget(self.apply_button)
        # pylint: disable-next=E1101
        self.apply_button.clicked.connect(self.get_checked)

        self.setLayout(self.__layout)

        # self.signal_handler.update_mo_diagram.connect(self.make_new)
        self.signal_handler.update_mo_diagram.connect(self.update)
        self.signal_handler.update_mo_diagram.connect(self.contour_setter)
        self.signal_handler.update_mo_diagram.connect(self.check_buttons)

        self.__homo_lumo_label: Optional[QWidget] = None
        self.__contour_value_layout: Optional[QHBoxLayout] = None

    # def make_new(self):
    #     self.__layout = QVBoxLayout()
    #     self.setLayout(self.__layout)

    def contour_setter(self):
        self.__contour_value_layout = QHBoxLayout()
        label = QLabel("Contour Value")
        self.__contour_value_layout.addWidget(label)
        box = QDoubleSpinBox()
        box.setValue(0.05)
        self.__contour_value_layout.addWidget(label)
        self.__contour_value_layout.addWidget(box)
        self.__layout.addLayout(self.__contour_value_layout)
        self.setLayout(self.__layout)

    def get_value(self):
        for orb_index, (show, _) in enumerate(reversed(self.buttons)):
            if show.isChecked():
                self.signal_handler.view_orbital.emit(orb_index + 1)
                break

    def check_buttons(self):
        # occupation = self.autocas_settings.user_occupation
        indices = self.autocas_settings.user_indices
        # print(indices)
        # print(occupation)
        if indices is None:
            # print("Note: No autoCAS selection available/read from disk!")
            return
        if self.buttons is None:
            return
        for i, (_, b) in enumerate(self.buttons[::-1]):
            # print(i, occupation[i])
            if i in indices:
                b.setChecked(True)

    def clean_up(self):
        """
        Removes all buttons, the contour value layout and the HOMO-LUMO gap label.
        """
        for s, b in self.buttons:
            s.deleteLater()
            b.deleteLater()
        self.buttons = []
        if self.__homo_lumo_label:
            self.__homo_lumo_label.deleteLater()
        if self.__contour_value_layout:
            for i in reversed(range(self.__contour_value_layout.count())):
                self.__contour_value_layout.itemAt(i).widget().deleteLater()
            self.__contour_value_layout.deleteLater()

    @staticmethod
    def degenerate(e, last_e, g, last_g) -> bool:
        if g != last_g:
            return False
        return abs(e - last_e) < 1e-4

    def update(self):
        # label = QLabel("Molecular Orbitals")
        # self.__layout.addWidget(label)
        layout = QGridLayout()
        self.clean_up()
        button_grid = [[]]
        show_button_grid = [[]]
        last_e = float("inf")
        last_g = nan
        row = 0
        energies = deepcopy(self.autocas_settings.orbital_energies)
        occupations = self.autocas_settings.orbital_occupations
        orbital_index_sets = self.autocas_settings.orbital_index_sets
        group_indices: List[int] = [len(energies) for _ in energies]
        if orbital_index_sets is not None:
            for i_group, indices in enumerate(orbital_index_sets):
                for i_orb in indices:
                    group_indices[i_orb - 1] = i_group
        for i, (e, g) in enumerate(zip(reversed(energies), reversed(group_indices))):
            x = len(energies) - i
            string = "{:n}".format(x)
            if g < len(energies):
                string += "|G" + str(g)

            button_show = QRadioButton()
            button_show.setChecked(False)
            button_show.setMinimumWidth(20)
            button_show.setMaximumWidth(20)
            button_show.setMinimumHeight(20)
            button_show.setMaximumHeight(20)
            # pylint: disable-next=E1101
            button_show.toggled.connect(self.get_value)

            button = QPushButton(string)
            button.setCheckable(True)
            button.setMinimumWidth(90)
            # button.setMaximumWidth(60)
            button.setMinimumHeight(20)
            button.setMaximumHeight(20)
            self.buttons.append((button_show, button))
            if not self.degenerate(e, last_e, g, last_g):
                row += 1
                button_grid.append([button])
                show_button_grid.append([button_show])
            else:
                button_grid[row].append(button)
                show_button_grid[row].append(button_show)
            last_e = e
            last_g = g
        max_cols = 3
        r = 1
        counter = 0
        printed_gap_info = False
        for r_ind, row in enumerate(button_grid):
            modulo_modifier = 0
            for c, col in enumerate(row):
                if occupations[len(energies) - counter - 1] and not printed_gap_info:
                    printed_gap_info = True
                    r += 1
                    # self.layout.addWidget(QHLine(), r, 0, 1, max_cols)
                    r += 1
                    self.__homo_lumo_label = QLabel("HOMO-LUMO-Gap")
                    self.__homo_lumo_label.setMinimumHeight(20)
                    self.__homo_lumo_label.setMaximumHeight(20)
                    layout.addWidget(self.__homo_lumo_label, r, 0, 1, max_cols)
                    r += 1
                    # self.layout.addWidget(QHLine(), r, 0, 1, max_cols)
                    r += 1
                    modulo_modifier = c
                mod = (c - modulo_modifier) % max_cols
                if mod == 0:
                    r += 1
                layout_2 = QHBoxLayout()
                layout_2.setSpacing(10)
                layout_2.setMargin(10)
                layout_2.setContentsMargins(0, 0, 0, 0)
                layout_2.addWidget(show_button_grid[r_ind][c])
                layout_2.addWidget(col)
                layout.addLayout(layout_2, r, mod, 1, 1)
                counter += 1
            r += 1
        self.__layout.addLayout(layout)
        self.setLayout(self.__layout)
        # self.layout.addWidget(QHLine(), r, 0, 1, max_cols)

    def get_checked(self):
        cas_indices = []
        cas_occupation = []
        for i, b in enumerate(self.buttons[::-1]):
            if b.isChecked():
                cas_indices.append(i)
                cas_occupation.append(self.autocas_settings.orbital_occupations[i])
        # print(cas_occupation)
        # print(cas_indices)
        self.autocas_settings.user_occupation = cas_occupation
        self.autocas_settings.user_indices = cas_indices
