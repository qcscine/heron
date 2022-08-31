#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
import pytest
from vtk import vtkMolecule
from typing import TypeVar, Callable, List
import numpy as np

from hypothesis import strategies as st
from hypothesis import given, assume

from scine_heron.edit_molecule import new_atom_positions as nap
from scine_utilities import StructuralCompletion

from scine_heron.tests.conftest import methane_positions

Position = TypeVar("Position")


@pytest.mark.parametrize("n_candidates", range(3))  # type: ignore[misc]
def test_create_writeable_candidates_len(n_candidates: int) -> None:
    candidates = nap._create_writeable_candidates(n_candidates)
    assert len(candidates) == n_candidates


@pytest.mark.parametrize("n_candidates", range(3))  # type: ignore[misc]
def test_create_writeable_candidates_shape(n_candidates: int) -> None:
    candidates = nap._create_writeable_candidates(n_candidates)
    for candidate in candidates:
        assert candidate.shape == (3, 1)


@pytest.mark.parametrize("n_candidates", range(3))  # type: ignore[misc]
def test_create_writeable_candidates_writeable(n_candidates: int) -> None:
    candidates = nap._create_writeable_candidates(n_candidates)
    for i, candidate in enumerate(candidates):
        # Note: the shape is not (3,)  but (3,1)
        candidate[:] = [i * 3], [i * 3 + 1], [i * 3 + 2]


@pytest.mark.parametrize("n_candidates", range(2, 3))  # type: ignore[misc]
def test_create_writeable_candidates_not_same(n_candidates: int) -> None:
    candidates = nap._create_writeable_candidates(n_candidates)
    for i in range(n_candidates - 1):
        assert candidates[i] is not candidates[i + 1]


@pytest.fixture(name="HvsCH4_like_validator", scope="session")  # type: ignore[misc]
def get_validator(methane_like: vtkMolecule) -> Callable[[Position], bool]:
    return nap._create_molecule_validator(new_n=1, molecule=methane_like)


@pytest.mark.parametrize("atom_id", range(5))  # type: ignore[misc]
def test_create_molecule_validator_false(
    atom_id: int,
    methane_like: vtkMolecule,
    HvsCH4_like_validator: Callable[[Position], bool],
) -> None:
    """
    Checks that the positions of the atoms in the molecule
    are not valid.
    Note: more thorough checks are delegated to the tests
    of the function "collision_multiple".
    """
    pos = np.array(methane_like.GetAtom(atom_id).GetPosition())
    assert not HvsCH4_like_validator(pos)


@pytest.mark.parametrize("atom_id", range(1, 5))  # type: ignore[misc]
def test_create_molecule_validator_true(
    atom_id: int,
    methane_like: vtkMolecule,
    HvsCH4_like_validator: Callable[[Position], bool],
) -> None:
    """
    Checks that the positions of the atoms in the molecule
    are valid, as these are for sure far from the molecule.
    Note: more thorough checks are delegated to the tests
    of the function "collision_multiple".
    """
    pos_h = methane_like.GetAtom(atom_id).GetPosition()
    center = methane_like.GetAtom(0).GetPosition()
    # Note: conversion from vtkVector3f to 1D np.array
    pos = 2.0 * np.array(pos_h) - np.array(center)
    assert HvsCH4_like_validator(pos)


def test_get_pos_array(methane_like: vtkMolecule) -> None:
    pos = nap._get_pos_array(1, methane_like)
    assert pos.shape == (3, 1)
    assert pos.reshape((3,)) == pytest.approx(np.array(methane_positions[0]), rel=1e-2)


@given(atom_ids=st.lists(st.integers(min_value=0, max_value=4), min_size=2, max_size=4))
def test_new_atom_position_from_id_list_has_solution(
    atom_ids: List[int], methane_like: vtkMolecule
) -> None:
    """
    This just tries that the function does not crash
    and always returns a valid result for the simple geometry used.
    Note that the StructuralCompletion functions ARE MOCKED.
    """
    assume(len(set(atom_ids)) == len(atom_ids))
    new_n = 1
    new_position, method = nap.new_atom_position_from_id_list(
        atom_ids, new_n, methane_like
    )

    assert method in dir(StructuralCompletion)

    # Note: case checking must be in this order
    #       or it will throw a ValueError
    #        ValueError: The truth value of an array with more than one element is ambiguous
    assert new_position is not None and method is not None


@pytest.mark.parametrize("natoms", [0, 5, 6])  # type: ignore[misc]
def test_new_atom_position_from_id_list_wrong_no_of_atoms(
    natoms: int, methane_like: vtkMolecule
) -> None:
    """
    When there are too many atoms selected (or too little)
    result is (None,None).
    """
    new_n = 1
    new_position, method = nap.new_atom_position_from_id_list(
        list(range(natoms)), new_n, methane_like
    )

    assert isinstance(new_position, np.ndarray)
    assert method in ["origin", "generate_random_position_around_atom"]


def test_new_atom_position_from_id_repeated(methane_like: vtkMolecule) -> None:
    """
    Test that passing the same index more than once
    does not have an effect
    """
    new_n = 1
    atom_ids0 = [0, 1, 0, 1, 0, 1]
    new_position0, method0 = nap.new_atom_position_from_id_list(
        atom_ids0, new_n, methane_like
    )
    atom_ids1 = [0, 1]
    new_position1, method1 = nap.new_atom_position_from_id_list(
        atom_ids1, new_n, methane_like
    )
    if new_position0 is not None and new_position1 is not None:
        assert (new_position0 == new_position1).all()
    else:
        assert False
    assert method0 == method1


def test_new_atom_position_empty_molecule() -> None:
    """
    Test that for an empty molecule we always get (0,0,0).
    """

    position, _method = nap.new_atom_position_from_id_list(
        atom_ids=[], new_atom_n=6, molecule=vtkMolecule()
    )
    assert np.all(position == np.array((0, 0, 0)))
