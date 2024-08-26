__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    Signal = Any
else:
    pass
import numpy as np
from PySide2.QtCore import QObject, Signal


class SignalHandler(QObject):
    open_entanglement_widget_signal = Signal()
    update_entanglement_plot_signal = Signal(np.ndarray, np.ndarray, list)
    update_mo_diagram = Signal()
    change_iso_value = Signal(float)

    open_molecule_widget_signal = Signal()
    load_xyz_file_signal = Signal(str)
    load_molden_file_signal = Signal(str)
    load_orbital_groups_file_signal = Signal(str)
    view_orbital = Signal(int)

    start_initial_orbital_calculation_signal = Signal()
    start_initial_dmrg_calculation_signal = Signal()
    start_final_calculation_signal = Signal()

    toggle_file_tree = Signal()

    def __init__(self, parent=None):
        if parent is not None:
            super().__init__(parent)
