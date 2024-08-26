#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""


from PySide2.QtWidgets import QGridLayout, QPushButton, QWidget

from scine_heron.autocas.signal_handler import SignalHandler


class AutocasController(QWidget):
    def __init__(self, parent: QWidget, signal_handler: SignalHandler):
        QWidget.__init__(self, parent)

        self.signal_handler = signal_handler

        self.__layout = QGridLayout()

        self.button_generate_initial_orbitals = QPushButton("Generate Initial Orbitals")
        self.__layout.addWidget(self.button_generate_initial_orbitals)
        # pylint: disable-next=E1101
        self.button_generate_initial_orbitals.clicked.connect(
            self.signal_handler.start_initial_orbital_calculation_signal
        )

        self.button_run_initial_dmrg = QPushButton("Run Initial DMRG")
        self.__layout.addWidget(self.button_run_initial_dmrg)
        # pylint: disable-next=E1101
        self.button_run_initial_dmrg.clicked.connect(
            self.signal_handler.start_initial_dmrg_calculation_signal
        )

        self.button_run_final_calculation = QPushButton("Run Final Calculation")
        self.__layout.addWidget(self.button_run_final_calculation)
        # pylint: disable-next=E1101
        self.button_run_final_calculation.clicked.connect(
            self.signal_handler.start_initial_dmrg_calculation_signal
        )

        self.button_open_entanglement = QPushButton("Show Entganglement")
        self.__layout.addWidget(self.button_open_entanglement)
        # pylint: disable-next=E1101
        self.button_open_entanglement.clicked.connect(self.open_entanglement)
        # pylint: disable-next=E1101
        self.button_open_entanglement.clicked.connect(
            self.signal_handler.open_entanglement_widget_signal
        )

        self.button_open_threshold = QPushButton("Show Threshold")
        self.__layout.addWidget(self.button_open_threshold)
        # pylint: disable-next=E1101
        self.button_open_threshold.clicked.connect(self.open_threshold)

        self.button_open_orbitals = QPushButton("Show Orbitals")
        self.__layout.addWidget(self.button_open_orbitals)
        # pylint: disable-next=E1101
        self.button_open_orbitals.clicked.connect(self.open_orbitals)
        # pylint: disable-next=E1101
        self.button_open_orbitals.clicked.connect(
            self.signal_handler.open_molecule_widget_signal
        )

        self.setLayout(self.__layout)

    # @Slot()

    def open_entanglement(self):
        pass

    def open_threshold(self):
        pass

    def open_orbitals(self):
        pass
