#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from typing import Tuple, List
import pytest

from vtk import (
    vtkArray,
    vtkArrayData,
    VTK_FLOAT,
    vtkMolecule,
    vtkPolyData,
    vtkPoints
)

from scine_heron.molecule import depth_view_algorithms as dva


def get_algorithm(filter_radius: float, zscale: float) -> dva.DepthProjectionAlgorithm:
    algorithm = dva.DepthProjectionAlgorithm(filter_radius=filter_radius, zscale=zscale)
    return algorithm


# These functions are used to prepare the data to test the algorithm
def prepare_haptic_pointer_data(position: Tuple[float, float, float]) -> vtkPolyData:
    haptic_ponter_pos = vtkPoints()
    haptic_ponter_pos.InsertPoint(0, *position)
    haptic_pointer_data = vtkPolyData()
    haptic_pointer_data.SetPoints(haptic_ponter_pos)
    return haptic_pointer_data


def prepare_molecule(data: List[Tuple[int, float, float, float]]) -> vtkMolecule:
    molecule = vtkMolecule()
    for a, x, y, z in data:
        atom = molecule.AppendAtom()
        atom.SetAtomicNumber(a)
        atom.SetPosition(x, y, z)
    return molecule


def prepare_camera_data(depth_direction: Tuple[float, float, float]) -> vtkArrayData:
    depth_vector = vtkArray.CreateArray(vtkArray.DENSE, VTK_FLOAT)
    depth_vector.Resize(3)
    _ = [depth_vector.SetValue(i, x) for i, x in enumerate(depth_direction)]

    camera_data = vtkArrayData()
    camera_data.AddArray(depth_vector)
    return camera_data


@pytest.fixture(name="out_molecule_1", scope="session")  # type: ignore[misc]
def get_out_molecule1() -> vtkMolecule:
    """
    A small molecule where an atom is out of range.
    The algorithm has reasonable filter range.
    The haptic pointer is relatively close the the molecule.
    """

    algorithm = get_algorithm(filter_radius=5, zscale=3)

    haptic_pointer_data = prepare_haptic_pointer_data((0.0, -1.0, 0.0))
    molecule = prepare_molecule(
        [
            (1, 0.1, 0.0, 0.1),
            (2, 0.2, 2.0, 0.2),
            (4, 0.0, 4.0, 1.0),  # This won't be visible
            (3, 0.3, 3.9, 0.3),
        ]
    )
    camera_data = prepare_camera_data(depth_direction=(0.0, 1.0, 0.0))

    out_molecule = vtkMolecule()
    algorithm._core_algorithm(haptic_pointer_data, molecule, camera_data, out_molecule)
    return out_molecule


def test_filtering_natoms(out_molecule_1: vtkMolecule) -> None:
    assert out_molecule_1.GetNumberOfAtoms() == 3


@pytest.mark.parametrize("iatom, expected", zip(range(3), [1, 2, 3]))  # type: ignore[misc]
def test_atom_species(iatom: int, expected: int, out_molecule_1: vtkMolecule) -> None:
    atom = out_molecule_1.GetAtom(iatom)
    assert atom.GetAtomicNumber() == expected


@pytest.mark.parametrize("iatom", range(3))  # type: ignore[misc]
def test_xy_zero(iatom: int, out_molecule_1: vtkMolecule) -> None:
    atom = out_molecule_1.GetAtom(iatom)
    position = atom.GetPosition()
    assert position[0] == 0
    assert position[1] == 0


@pytest.mark.parametrize("iatom", range(3))  # type: ignore[misc]
def test_z_limited(iatom: int, out_molecule_1: vtkMolecule) -> None:
    atom = out_molecule_1.GetAtom(iatom)
    position = atom.GetPosition()
    assert -3 < position[2] < 3
    assert position[2] != 0


@pytest.fixture(name="out_molecule_2", scope="session")  # type: ignore[misc]
def get_out_molecule2() -> vtkMolecule:
    """
    The algorithm has huge filter range.
    No atom is out of range.
    The haptic pointer is really far from the molecule
    """

    algorithm = get_algorithm(filter_radius=5000, zscale=3)

    haptic_pointer_data = prepare_haptic_pointer_data((0.0, -2000.0, 0.0))
    molecule = prepare_molecule(
        [
            (1, 0.0, 0.0, 0.0),
            (2, 0.0, 2.0, 0.0),
            (4, 0.0, 4.0, 1.0),
            (3, 0.0, 3.9, 0.0),
        ]
    )
    camera_data = prepare_camera_data(depth_direction=(0.0, 1.0, 0.0))

    out_molecule = vtkMolecule()
    algorithm._core_algorithm(haptic_pointer_data, molecule, camera_data, out_molecule)

    return out_molecule


def test_all_atoms_are_visible(out_molecule_2: vtkMolecule) -> None:
    assert out_molecule_2.GetNumberOfAtoms() == 4


@pytest.mark.parametrize("iatom", range(4))  # type: ignore[misc]
def test_all_atoms_are_very_close_to_max(
    iatom: int, out_molecule_2: vtkMolecule
) -> None:
    atom = out_molecule_2.GetAtom(iatom)
    position = atom.GetPosition()
    assert position[2] == pytest.approx(3)
