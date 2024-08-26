#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional
from PySide2.QtCore import QObject
from PySide2.QtWidgets import (
    QDialog,
    QLabel
)

from scine_chemoton.gears.kinetic_modeling.atomization import (
    MultiModelEnergyReferences,
    PlaceHolderMultiModelEnergyReferences
)

from scine_heron.containers.layouts import VerticalLayout


class EnergyReferenceBuilder(QDialog):
    def __init__(self, _: MultiModelEnergyReferences, parent: Optional[QObject] = None):
        """
        Builder for a MultiModelEnergyReferences object. This is a rather complicated object that can also be
        constructed by the kinetic modeling gear through a keyword argument. Therefore, we do not support its
        construction directly.
        """
        super().__init__(parent=parent)
        # widgets
        self._label = QLabel("Advanced option to set specific atomization energies.\n"
                             "This feature is not supported through the GUI.\n"
                             "Energies are referenced according to the option\n"
                             "<energy_reference_type>.")
        # layout
        layout = VerticalLayout([self._label])
        self.setLayout(layout)

    def get_energy_reference(self) -> MultiModelEnergyReferences:
        return PlaceHolderMultiModelEnergyReferences()
