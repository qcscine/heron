__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import List

from PySide2.QtWidgets import QGridLayout, QLabel, QPushButton, QWidget


class OrbitalOptionsWidget(QWidget):
    def __init__(self, parent: QWidget) -> None:
        QWidget.__init__(self, parent)
        self.__layout = QGridLayout()
        self.buttons: List[QPushButton] = []
        self.setLayout(self.__layout)

    def update(self):
        self.buttons = []
        button_grid = [[]]
        last = None
        diff = 10.0
        row = 0
        energies = self.parent().options.orbital_energies
        occupations = self.parent().options.occupations
        for i, e in enumerate(reversed(energies)):
            # print(i, e)
            x = len(energies) - i - 1
            string = "{:n}".format(x - 1)
            # print(string)
            button = QPushButton(string)
            button.setCheckable(True)
            button.setMinimumWidth(60)
            button.setMaximumWidth(60)
            button.setMinimumHeight(20)
            button.setMaximumHeight(20)
            self.buttons.append(button)
            if last is not None:
                diff = abs(e - last)
            if diff > 1e-4:
                row += 1
                button_grid.append([button])
            else:
                button_grid[row].append(button)
            last = e
        max_cols = 4
        r = 0
        counter = 0
        printed_gap_info = False
        for row in button_grid:
            modulo_modifier = 0
            for c, col in enumerate(row):
                if occupations[len(energies) - counter - 1] and not printed_gap_info:
                    printed_gap_info = True
                    r += 1
                    # self.layout.addWidget(QHLine(), r, 0, 1, max_cols)
                    r += 1
                    label = QLabel("HOMO-LUMO Gap")
                    label.setMinimumHeight(20)
                    label.setMaximumHeight(20)
                    self.__layout.addWidget(label, r, 0, 1, max_cols)
                    r += 1
                    # self.layout.addWidget(QHLine(), r, 0, 1, max_cols)
                    r += 1
                    modulo_modifier = c
                mod = (c - modulo_modifier) % max_cols
                if mod == 0:
                    r += 1
                self.__layout.addWidget(col, r, mod, 1, 1)
                counter += 1
            r += 1
            # self.layout.addWidget(QHLine(), r, 0, 1, max_cols)

    def get_checked(self):
        cas = []
        cas_occupation = []
        occupation = self.parent().parent().parent().settings.occupations
        for i, b in enumerate(self.buttons[::-1]):
            if b.isChecked():
                # print(i, occupation[i])
                cas.append(i)
                cas_occupation.append(occupation[i])
        self.parent().parent().parent().settings.cas = cas
        self.parent().parent().parent().settings.cas_occupations = cas_occupation
