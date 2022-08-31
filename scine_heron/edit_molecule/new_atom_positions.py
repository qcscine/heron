#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from scine_utilities import (
    StructuralCompletion,
    ANGSTROM_PER_BOHR,
    ElementInfo,
)

from vtk import vtkMolecule
import numpy as np
from typing import List, TypeVar, Optional, Callable, Tuple, Dict, Any

from scine_heron.edit_molecule.collision import collision_multiple

import itertools

Position = TypeVar("Position")


def _create_writeable_candidates(n: int) -> List[np.ndarray]:
    """
    Creates `n` np arrays, writable, of shape (3,1),
    to use as output for the methods of StructuralCompletion.
    """
    # Each array must be a different object in memory
    pos_candidates = [np.zeros((3, 1)) for _ in range(n)]
    for c in pos_candidates:
        c.setflags(write=True)
    return pos_candidates


def _get_covalent_radius(z: int) -> float:
    return ElementInfo.covalent_radius(ElementInfo.element(z)) * ANGSTROM_PER_BOHR


def _create_molecule_validator(
        new_n: int, molecule: vtkMolecule
) -> Callable[[np.ndarray], bool]:
    """
    Creates a validator for positions
    that can be used to check if the new atom
    (having atomic number "new_n")
    collides with the molecule.
    """
    # In vtk atoms are represented as balls
    # having a radius of .3,
    SAFETY_MARGIN = 0.35

    other_positions = [
        molecule.GetAtom(i).GetPosition()  # Do not reformat
        for i in range(molecule.GetNumberOfAtoms())
    ]
    other_ns = [
        molecule.GetAtom(i).GetAtomicNumber()  # Do not reformat
        for i in range(molecule.GetNumberOfAtoms())
    ]

    visual_radius_new_atom = SAFETY_MARGIN * _get_covalent_radius(new_n)
    visual_radii = [
        SAFETY_MARGIN * _get_covalent_radius(n) for n in other_ns
    ]

    def validator(position: np.ndarray) -> bool:
        assert position.shape == (3,)
        return not collision_multiple(
            radius=visual_radius_new_atom,
            position=position,
            radii=visual_radii,
            positions=other_positions,
        )

    return validator


def _get_pos_array(atom_id: int, molecule: vtkMolecule) -> np.ndarray:
    """
    Gets the position of the "atom_id"-th atom in the molecule
    as a ndarray.
    Needs to be of (3,1) shape to be used with the StructuralCompletion functions.
    """

    pos = molecule.GetAtom(atom_id).GetPosition()
    return np.array(pos).reshape((3, 1))


def generate_random_position_around_atom(*positions: np.ndarray) -> None:
    """
    Produces positions on the faces, edges and corners of a cube of side 2,
    sorted by distance to the center.
    """
    xs = ys = zs = [-1, 0, 1]
    suggestions = sorted(
        itertools.product(xs, ys, zs),  # producing a lattice
        key=lambda v: sum(x * x for x in v),
    )  # sort by distance
    # Skipping the centre
    for pos, suggestion in zip(positions, suggestions[1:]):
        # assigning to output arrays
        pos[:, 0] = suggestion


# Map between
# number of bonds given ->  list of (function to try, number or outputs of said function)
completion_functions_to_try: Dict[int, Any] = {
    0: [(generate_random_position_around_atom, 26)],
    1: [
        (StructuralCompletion.generate_two_triangle_corners_from_one, 2),
        (StructuralCompletion.generate_three_tetrahedron_corners_from_one, 3),
    ],
    2: [
        (StructuralCompletion.generate_one_triangle_corner_from_two, 1),
        (StructuralCompletion.generate_two_tetrahedron_corners_from_two, 2),
    ],
    3: [(StructuralCompletion.generate_one_tetrahedron_corner_from_three, 1)],
}


def new_atom_position_from_id_list(
        atom_ids: List[int], new_atom_n: int, molecule: vtkMolecule
) -> Tuple[Optional[Position], Optional[str]]:
    """
    Tries all the methods in scine_utilities
    until a possible position is found
    that does not collide with other atoms in the molecule.
    Returns also the name of the method that worked.

    The first element of the `atom_ids` list
    must be the base atom,
    the next ones must be the `ids` of the atoms
    that are bond to it.

    The vector for each bond is computed and fed
    to the `StructuralCompletion` functions.
    """
    default_result = (np.array([0., 0., 0.0]), "origin")
    if molecule.GetNumberOfAtoms() == 0 or not atom_ids:
        return default_result

    # Unique but preserving order
    # (which set() does not do)
    unique_atom_ids = []
    for atom_id in atom_ids:
        if atom_id not in unique_atom_ids:
            unique_atom_ids.append(atom_id)

    number_of_bonds = len(unique_atom_ids) - 1
    if number_of_bonds not in completion_functions_to_try.keys():
        number_of_bonds = 0

    base_atom_id = unique_atom_ids[0]
    n_base_atom = molecule.GetAtom(base_atom_id).GetAtomicNumber()

    new_atom_radius = _get_covalent_radius(new_atom_n)
    base_atom_radius = _get_covalent_radius(n_base_atom)
    safety_distance = new_atom_radius + base_atom_radius

    validator = _create_molecule_validator(new_atom_n, molecule)

    known_positions = [_get_pos_array(atom_id, molecule) for atom_id in unique_atom_ids]

    def position_to_displacement(position: np.ndarray) -> np.ndarray:
        return position - known_positions[0]

    def displacement_to_position(displacement: np.ndarray) -> np.ndarray:
        return displacement + known_positions[0]

    def rescale_safe(displacement: np.ndarray) -> np.ndarray:
        length = np.sqrt(np.sum(displacement ** 2))
        if length == 0:
            return displacement  # We give up
        return displacement * safety_distance / length

    known_displacements = [position_to_displacement(p) for p in known_positions[1:]]

    for function, n_position_candidates in completion_functions_to_try[number_of_bonds]:
        displacement_candidates = _create_writeable_candidates(n_position_candidates)
        function(*known_displacements, *displacement_candidates)
        displacement_candidates_rescaled = [
            rescale_safe(d) for d in displacement_candidates
        ]

        position_candidates = [
            displacement_to_position(d) for d in displacement_candidates_rescaled
        ]
        for candidate in position_candidates:
            if validator(candidate.reshape((3,))):
                return candidate, function.__name__

    return default_result
