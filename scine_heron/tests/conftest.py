#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Contains Fixtures that are shared between tests.
"""

import pytest
from vtk import vtkMolecule
from PySide2.QtWidgets import QApplication


@pytest.fixture(name="_app")  # type: ignore[misc]
def create_app() -> QApplication:
    """
    Creates a QApplication if necessary.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication()
    return app


@pytest.fixture(name="molecule")  # type: ignore[misc]
def create_molecule() -> vtkMolecule:
    """
    Returns a molecule of two atoms.
    """

    molecule = vtkMolecule()
    # positions in Bohr (a.u.)
    molecule.AppendAtom(1, -0.7, 0.00, 0.00)
    molecule.AppendAtom(1, +0.7, 0.00, 0.00)
    return molecule


methane_positions = [
    [0.00, 0.00, 2.05],
    [1.94, 0.00, -0.68],
    [-0.97, -1.68, -0.68],
    [-0.97, 1.68, -0.68],
]


@pytest.fixture(name="methane_like", scope="session")  # type: ignore[misc]
def get_methane_like() -> vtkMolecule:
    molecule = vtkMolecule()

    # positions in Bohr (a.u.)
    molecule.AppendAtom(6, [0.00, 0.00, 0.00])
    molecule.AppendAtom(1, methane_positions[0])
    molecule.AppendAtom(1, methane_positions[1])
    molecule.AppendAtom(1, methane_positions[2])
    molecule.AppendAtom(1, methane_positions[3])

    return molecule
