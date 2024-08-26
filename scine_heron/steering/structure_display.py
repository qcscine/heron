#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""


from typing import Optional, List, Tuple

from PySide2.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

from scine_utilities import AtomCollection
from scine_heron.molecule.molecule_widget import MoleculeWidget


class StructureWithReactiveSites(QWidget):
    """
    A wrapper widget around a molecular viewer that highlights reactive sites.

    Notes
    -----
    Structure modifications are disabled.
    """

    color: Tuple[float, float, float] = (78., 128., 207.)
    """
    The color of the reactive site highlighting.
    """

    def __init__(self, parent: Optional[QWidget], atoms: Optional[AtomCollection] = None,
                 reactive_indices: Optional[List[int]] = None) -> None:
        """
        Constructor the widget, structures and reactive sites can be modified later.

        Parameters
        ----------
        parent : Optional[QWidget]
            The parent widget
        atoms : Optional[AtomCollection], optional
            The structure, by default None
        reactive_indices : Optional[List[int]], optional
            The reactive indices that should be hightlighted, by default None
        """
        super().__init__(parent)
        self._mol_widget = MoleculeWidget(parent=self, atoms=atoms, disable_modification=True)
        if atoms is not None and reactive_indices is not None:
            self.update_structure(atoms, reactive_indices)
        layout = QVBoxLayout()
        layout.addWidget(self._mol_widget)
        self.setLayout(layout)
        self.setMinimumHeight(250)

    def clear(self):
        """
        Removes the molecule
        """
        self._mol_widget.update_molecule()
        self._mol_widget.reset_camera()

    def reset_camera(self):
        """
        Resets the camera in the molecule widget
        """
        self._mol_widget.reset_camera()

    def update_structure(self, atoms: AtomCollection, reactive_indices: List[int]) -> None:
        """
        Plug in a new structure and reactive sites.
        The current structure and indices are removed.

        Parameters
        ----------
        atoms : AtomCollection
            The new structure
        reactive_indices : List[int]
            The new reactive indices
        """
        self._mol_widget.update_molecule(atoms=atoms)
        assert len(self.color) == 3
        color = (self.color[0] / 255.0, self.color[1] / 255.0, self.color[2] / 255.0)
        self._mol_widget.set_selection(reactive_indices, color=color)

    def get_structure(self) -> AtomCollection:
        """
        Get the current structure as an AtomCollection.

        Returns
        -------
        AtomCollection
            The current structure
        """
        return self._mol_widget.get_atom_collection()
