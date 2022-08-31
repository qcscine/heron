#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""

from scine_heron.molecule.atom_selection import (
    AtomSelection,
    AtomSelectionAlgorithm,
    NonEmptyMoleculeError,
)

from vtk import (
    vtkMolecule,
    vtkRenderer,
    vtkRenderWindow,
    vtkActor,
)

import pytest
from hypothesis import strategies as st
from hypothesis import given
import numpy as np

from typing import List


def test_atom_selection_algorithm_setup() -> None:
    """
    Testing that setup is successful.
    """
    _ = AtomSelectionAlgorithm()


@given(
    selection=st.lists(st.integers(min_value=0, max_value=4), min_size=0, max_size=5)
)
def test_filter_molecule(selection: List[int], methane_like: vtkMolecule) -> None:
    """
    Test that the original molecule is filtered correctly.
    """
    # information out 0
    out_molecule = vtkMolecule()

    # Assembling information vector lists, in and out

    AtomSelectionAlgorithm.filter_molecule(methane_like, selection, out_molecule)

    assert out_molecule.GetNumberOfAtoms() == len(selection)
    maximum_atomic_number_methane = 6
    for out_i, in_i in enumerate(selection):
        new_atom = out_molecule.GetAtom(out_i)
        old_atom = methane_like.GetAtom(in_i)
        # unfortunately == does not do what we need for vtkAtom
        assert new_atom.GetAtomicNumber() == maximum_atomic_number_methane
        assert new_atom.GetPosition().Compare(old_atom.GetPosition(), 1e-6)


def test_empty_molecules_can_be_filtered() -> None:
    """
    Test that filtering an empty molecule returns an empty molecule
    without raising an exception.
    """
    out_molecule = vtkMolecule()
    AtomSelectionAlgorithm.filter_molecule(vtkMolecule(), [], out_molecule)

    assert out_molecule.GetNumberOfAtoms() == 0


def test_filter_molecule_throws_if_not_empty_molecule() -> None:

    molecule = vtkMolecule()
    out_molecule = vtkMolecule()
    out_molecule.AppendAtom()

    with pytest.raises(NonEmptyMoleculeError):
        AtomSelectionAlgorithm.filter_molecule(molecule, [], out_molecule)


def test_atom_selection_reset_molecule(methane_like: vtkMolecule) -> None:
    """
    Test that changing the molecule in the selection object
    clears the selection data.
    """
    atom_selection = AtomSelection()

    atom_selection.set_molecule(methane_like)
    atom_selection.set_selection([1, 2, 3])
    another_molecule = vtkMolecule()
    atom_selection.set_molecule(another_molecule)
    assert len(atom_selection) == 0


def offscreen_window(actor: vtkActor) -> vtkRenderWindow:
    """
    Helper function to test the pipeline in AtomSelection.
    """
    renderer = vtkRenderer()
    renderer.AddActor(actor)
    window = vtkRenderWindow()
    window.AddRenderer(renderer)
    window.SetOffScreenRendering(True)
    return window


def test_modifying_atom_position_moves_selection(molecule: vtkMolecule) -> None:
    """
    Test that changing the position of an atom
    in the original molecule
    changes the position of the atom
    in the output molecule
    when the atom is selected
    (Pipeline test for input #1)
    """
    atom_selection = AtomSelection()
    window = offscreen_window(atom_selection.actor)

    atom_selection.set_molecule(molecule)
    atom_selection.set_selection([0])
    # Make sure we CHANGE the atom position
    modified_position0 = [0.0, 0.0, 0.0]
    molecule.GetAtom(0).SetPosition(modified_position0)
    modified_position1 = [1.0, 0.0, 0.0]
    molecule.GetAtom(0).SetPosition(modified_position1)

    window.Render()
    position = atom_selection.actor.GetMapper().GetInput().GetAtom(0).GetPosition()

    # Stricter test
    assert np.array(position) == pytest.approx(np.array(modified_position1))


def test_modifying_atom_position_does_not_selection(molecule: vtkMolecule) -> None:
    """
    Test that changing the position of an atom
    in the original molecule
    does not change the position of any atom
    in the output molecule
    when the atom is not selected
    (Pipeline test for input #1)
    """
    atom_selection = AtomSelection()
    window = offscreen_window(atom_selection.actor)
    old_position_0 = molecule.GetAtom(0).GetPosition()

    atom_selection.set_molecule(molecule)
    atom_selection.set_selection([0])
    # Make sure we CHANGE the position of atom 1
    modified_position10 = [0.0, 0.0, 0.0]
    molecule.GetAtom(1).SetPosition(modified_position10)
    modified_position11 = [1.0, 0.0, 0.0]
    molecule.GetAtom(1).SetPosition(modified_position11)

    window.Render()
    position = atom_selection.actor.GetMapper().GetInput().GetAtom(0).GetPosition()

    # Stricter test
    assert np.array(position) == pytest.approx(np.array(old_position_0))


def test_modifying_selection_changes_atom_position(molecule: vtkMolecule) -> None:
    """
    Test that changing the selection
    changes the position of any atom
    in the output molecule
    (Pipeline test for input #2)
    """
    atom_selection = AtomSelection()
    window = offscreen_window(atom_selection.actor)
    position_0 = molecule.GetAtom(0).GetPosition()
    position_1 = molecule.GetAtom(1).GetPosition()

    atom_selection.set_molecule(molecule)
    atom_selection.set_selection([0])
    window.Render()
    position = atom_selection.actor.GetMapper().GetInput().GetAtom(0).GetPosition()
    # Stricter test
    assert np.array(position) == pytest.approx(np.array(position_0))

    atom_selection.set_selection([1])
    window.Render()
    position = atom_selection.actor.GetMapper().GetInput().GetAtom(0).GetPosition()
    # Stricter test
    assert np.array(position) == pytest.approx(np.array(position_1))
