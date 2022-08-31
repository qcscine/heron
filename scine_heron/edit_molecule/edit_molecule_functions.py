#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from vtk import vtkMolecule

from typing import List, TypeVar, Optional, Callable

from scine_heron.settings.settings_status_manager import SettingsStatusManager
from scine_heron.edit_molecule.new_atom_positions import new_atom_position_from_id_list

Position = TypeVar("Position")


def _add_atom_to_molecule(molecule: vtkMolecule, N: int, position: Position) -> None:

    atom = molecule.AppendAtom()
    atom.SetAtomicNumber(N)
    atom.SetPosition(position)


def build_molecule_without_removed_atoms(
    old_molecule: vtkMolecule, id_atoms_to_remove: List[int]
) -> vtkMolecule:
    """
    Creates a new molecule copying all the atoms
    except the one with the given id.
    """
    new_molecule = vtkMolecule()
    for i in range(old_molecule.GetNumberOfAtoms()):
        if i not in id_atoms_to_remove:
            old_atom = old_molecule.GetAtom(i)
            _add_atom_to_molecule(
                new_molecule, old_atom.GetAtomicNumber(), old_atom.GetPosition()
            )

    return new_molecule


def build_molecule_with_new_atom_structural_completion(
    old_molecule: vtkMolecule,
    new_atomic_number: int,
    other_atom_ids: List[int],
    settings_status_manager: SettingsStatusManager,
) -> vtkMolecule:
    def structural_completion_strategy(
        molecule: vtkMolecule, new_n: int
    ) -> Optional[Position]:
        new_position, method = new_atom_position_from_id_list(
            other_atom_ids, new_n, molecule
        )
        settings_status_manager.info_message = "method used: " + str(method)
        return new_position

    return _build_molecule_with_new_atom(
        old_molecule, new_atomic_number, structural_completion_strategy
    )


def _build_molecule_with_new_atom(
    old_molecule: vtkMolecule,
    new_atomic_number: int,
    positioning_strategy: Callable[[vtkMolecule, int], Position],
) -> vtkMolecule:

    new_molecule = vtkMolecule()
    new_molecule.DeepCopy(old_molecule)

    new_position = positioning_strategy(new_molecule, new_atomic_number)

    if new_position is None:
        return new_molecule

    _add_atom_to_molecule(new_molecule, new_atomic_number, new_position)

    return new_molecule
