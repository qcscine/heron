#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Test utility functions for conversions between molecule/atom representations.
"""

from numpy.testing import assert_array_almost_equal
from vtk import vtkMolecule
import numpy as np
import pytest

import scine_utilities as su

from scine_heron.molecule.utils.molecule_utils import (
    atom_to_tuple,
    atom_collection_to_molecule,
    molecule_to_list_of_atoms,
    molecule_to_atom_collection,
    convert_gradients,
    apply_gradients,
    times_bohr_per_angstrom,
    times_angstrom_per_bohr,
    maximum_vdw_radius,
)


def test_atom_to_tuple() -> None:
    """
    An atom is converted to its symbol and list of positions.
    """
    molecule = vtkMolecule()
    molecule.AppendAtom(1, 2, 3, 4)
    symbol, pos = atom_to_tuple(molecule.GetAtom(0))

    assert symbol == "H"
    assert pos == (2.0, 3.0, 4.0)


def test_molecule_to_list_of_atoms() -> None:
    """
    Check that molecule_to_list_of_atoms correctly converts vtkMolecule to list.
    """
    molecule = vtkMolecule()
    molecule.AppendAtom(1, -0.7, 0, 0)
    molecule.AppendAtom(1, 0.7, 0, 0)

    atom = molecule_to_list_of_atoms(molecule)

    assert atom[0] == ("H", (-0.699999988079071, 0, 0))
    assert atom[1] == ("H", (0.699999988079071, 0, 0))


def test_molecule_to_atom_collection() -> None:
    """
    Check that the molecule_to_atom_collection correctly converts vtkMolecule to AtomCollection.
    """
    molecule = vtkMolecule()
    molecule.AppendAtom(1, -0.7, 0, 0)
    molecule.AppendAtom(1, 0.7, 0, 0)

    structure = molecule_to_atom_collection(molecule)

    assert structure.elements[0] == su.ElementType.H
    assert structure.elements[1] == su.ElementType.H
    ref_positions = [
        [-1.3228, 0, 0],
        [1.3228, 0, 0]
    ]
    assert_array_almost_equal(structure.positions, ref_positions, decimal=4)


def test_atom_collection_to_molecule() -> None:
    molecule = vtkMolecule()
    molecule.AppendAtom(1, -0.7, 0, 0)
    molecule.AppendAtom(1, 0.7, 0, 0)
    positions = su.BOHR_PER_ANGSTROM * np.array([[-0.7, 0, 0], [0.7, 0, 0]])
    atoms = su.AtomCollection([su.ElementType.H, su.ElementType.H], positions)
    other_molecule = atom_collection_to_molecule(atoms)
    n = molecule.GetNumberOfAtoms()
    other_n = other_molecule.GetNumberOfAtoms()
    assert n == other_n
    for i in range(n):
        a = molecule.GetAtom(i)
        b = other_molecule.GetAtom(i)
        assert a.GetAtomicNumber() == b.GetAtomicNumber()
        assert all(np.isclose(np.array(a.GetPosition()), np.array(b.GetPosition())))


def test_apply_gradients() -> None:
    """
    Test that the gradient is applied correctly.
    """
    molecule = vtkMolecule()
    molecule.AppendAtom(1, -0.7, 0, 0)
    molecule.AppendAtom(1, 0.7, 0, 0)

    gradients = np.array([[-0.15099689, 0.0, 0.0], [0.15099689, 0.0, 0.0]])

    convert_gradients(gradients)
    apply_gradients(molecule, gradients, None)
    pos0 = molecule.GetAtom(0).GetPosition()
    pos1 = molecule.GetAtom(1).GetPosition()

    assert (pos0.GetX(), pos0.GetY(), pos0.GetZ()) == (-0.6600479483604431, 0, 0)
    assert (pos1.GetX(), pos1.GetY(), pos1.GetZ()) == (0.6600479483604431, 0, 0)


def test_times_bohr_per_angstrom() -> None:
    """
    Test that the positions of the atom were correctly converted from Bohr to Angstrom.
    """
    assert times_bohr_per_angstrom([0, 0, 0]) == [0, 0, 0]
    assert all(
        [
            abs(a - b) <= 0.0001
            for a, b in zip(
                times_bohr_per_angstrom([-0.1802, 0.3609, -1.1203]),
                [-0.3405, 0.6820, -2.117],
            )
        ]
    )


def test_times_angstrom_per_bohr() -> None:
    """
    Test that the positions of the atom were correctly converted from Angstrom to Bohr.
    """
    assert times_bohr_per_angstrom([0, 0, 0]) == [0, 0, 0]
    assert all(
        [
            abs(a - b) <= 0.0001
            for a, b in zip(
                times_angstrom_per_bohr([-0.3405, 0.6820, -2.117]),
                [-0.1802, 0.3609, -1.1203],
            )
        ]
    )


def test_maximum_vdw_radius() -> None:
    """
    Test that the VDW radius for helium is returned.
    """
    molecule = vtkMolecule()
    molecule.AppendAtom(1, 0, 0, 0)
    molecule.AppendAtom(2, 0, 0, 0)

    assert maximum_vdw_radius(molecule) == pytest.approx(1.4)


def test_maximum_vdw_radius_of_no_atoms_is_zero() -> None:
    """
    Test that a maximum radius of 0. is returned for a molecule
    without atoms.
    """
    molecule = vtkMolecule()

    assert maximum_vdw_radius(molecule) == 0.0
