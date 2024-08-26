#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from vtk import vtkMolecule
import pytest

from scine_heron.edit_molecule import edit_molecule_functions as emf
from scine_heron.settings.settings_status_manager import SettingsStatusManager


@pytest.mark.parametrize("id_atom_to_remove", range(5))  # type: ignore[misc]
def test_build_molecule_without_removed_atoms(
    methane_like: vtkMolecule, id_atom_to_remove: int
) -> None:
    """
    Check that the new molecule has an atom less than the original.
    """

    new_atom_collection = emf.build_molecule_without_removed_atoms(
        methane_like, [id_atom_to_remove]
    )
    assert new_atom_collection.GetNumberOfAtoms() == methane_like.GetNumberOfAtoms() - 1


def test_build_molecule_with_new_atom(methane_like: vtkMolecule) -> None:
    settings_status_manager = SettingsStatusManager()
    new_atom_collection = emf.build_molecule_with_new_atom_structural_completion(
        methane_like, 7, [1], settings_status_manager
    )

    assert new_atom_collection.GetAtom(5).GetAtomicNumber() == 7
