#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Testing that vtkSimpleBondPerceiver doesn't change atom IDs in vtkMolecule.
"""

from vtk import (
    vtkMolecule,
    vtkSimpleBondPerceiver,
)


def assert_identical_atoms(
    old_molecule: vtkMolecule, new_molecule: vtkMolecule
) -> None:
    """
    This function checks that both molecules have identical atoms. The function does not check bonds.
    """
    assert old_molecule.GetNumberOfAtoms() == new_molecule.GetNumberOfAtoms()

    number_of_atoms = old_molecule.GetNumberOfAtoms()

    for atom_index in range(number_of_atoms):
        old_atom = old_molecule.GetAtom(atom_index)
        new_atom = new_molecule.GetAtom(atom_index)

        old_position = old_atom.GetPosition()
        new_position = new_atom.GetPosition()

        assert old_atom.GetAtomicNumber() == new_atom.GetAtomicNumber()
        assert old_position.GetX() == new_position.GetX()
        assert old_position.GetY() == new_position.GetY()
        assert old_position.GetZ() == new_position.GetZ()


def test_atom_ids_do_not_change() -> None:
    """
    When vtkSimpleBondPerceiver calculates bonds it does not change the sequence of atoms.
    """
    molecule = vtkMolecule()
    molecule.AppendAtom(1, 0.0, 0.0, 1.0)
    molecule.AppendAtom(2, 0.0, 1.0, 0.0)
    molecule.AppendAtom(3, 1.0, 0.0, 0.0)

    filter = vtkSimpleBondPerceiver()
    filter.SetInputData(molecule)
    filter.Update()
    new_molecule = filter.GetOutput()

    assert_identical_atoms(molecule, new_molecule)
