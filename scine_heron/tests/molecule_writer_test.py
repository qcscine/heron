#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Tests for the free functions in the molecule_writer module.
"""
import os
import numpy as np
from pathlib import Path
from vtk import vtkMolecule

import scine_utilities as su

from scine_heron.molecule.molecule_writer import write_molecule_to_file
from scine_heron.molecule.utils.molecule_utils import atom_collection_to_molecule
from scine_heron.tests.resources import test_resource_path


def test_write_simple_molecule(tmp_path: Path) -> None:
    """
    A molecule is written as its xyz line representation, split by newlines.
    """
    molecule = vtkMolecule()
    molecule.AppendAtom(6, 1.0, 2.0, 3.0)

    file_name = os.path.join(tmp_path, "test.xyz")
    write_molecule_to_file(molecule, file_name)

    assert os.path.exists(file_name)
    other_molecule = atom_collection_to_molecule(su.io.read(file_name)[0])
    n = molecule.GetNumberOfAtoms()
    other_n = other_molecule.GetNumberOfAtoms()
    assert n == other_n
    for i in range(n):
        a = molecule.GetAtom(i)
        b = other_molecule.GetAtom(i)
        assert a.GetAtomicNumber() == b.GetAtomicNumber()
        assert all(np.isclose(np.array(a.GetPosition()), np.array(b.GetPosition())))

    lines = open(file_name, "r").readlines()
    assert len(lines) == 3
    assert lines[0].strip() == "1"
    assert not lines[1].strip()
    assert lines[2][0] == "C"
    for i in range(1, 4):
        assert abs(float(lines[2].split()[i]) - i) < 1e-6


def test_xyz_mol_consistency(tmp_path: Path) -> None:
    # reference
    pyr_mol = os.path.join(test_resource_path(), "pyridine.mol")
    ac_mol, bo_mol = su.io.read(pyr_mol)
    # testing
    pyr_xyz = os.path.join(test_resource_path(), "pyridine.xyz")
    ac_xyz, _ = su.io.read(pyr_xyz)
    fit = su.QuaternionFit(ac_mol.positions, ac_xyz.positions)
    assert fit.get_rmsd() < 1e-4  # mol file is only written with 4 digits after comma
    molecule = atom_collection_to_molecule(ac_mol)
    write_molecule_to_file(molecule, os.path.join(tmp_path, "test.mol"))
    read_write_ac, read_write_bo = su.io.read(os.path.join(tmp_path, "test.mol"))
    assert ac_mol == read_write_ac
    assert bo_mol == read_write_bo
