#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Utility functions for conversions between molecule/atom representations.
"""

from vtk import vtkPeriodicTable, vtkAtom, vtkMolecule
from typing import List, Tuple, cast, Optional
import numpy as np
import scine_utilities as su


def atom_to_tuple(atom: vtkAtom) -> Tuple[str, Tuple[float, float, float]]:
    """
    Returns an atomic symbol and a tuple of atom positions.
    """
    symbol = vtkPeriodicTable().GetSymbol(atom.GetAtomicNumber())
    position = atom.GetPosition()

    return cast(
        Tuple[str, Tuple[float, float, float]],
        (symbol, (position.GetX(), position.GetY(), position.GetZ())),
    )


def molecule_to_list_of_atoms(
    molecule: vtkMolecule,
) -> List[Tuple[str, Tuple[float, float, float]]]:
    """
    Convert vtkMolecule to list of atoms.
    """
    atoms = list()

    for atom_index in range(molecule.GetNumberOfAtoms()):
        atoms.append(atom_to_tuple(molecule.GetAtom(atom_index)))

    return atoms


def molecule_to_atom_collection(molecule: vtkMolecule) -> su.AtomCollection:
    """
    Convert list of atoms to su.AtomCollection.
    The method gets the molecule in Angstrom units and returns the AtomCollection in Bohr units.
    """
    atom_list = molecule_to_list_of_atoms(molecule)
    if not atom_list:
        return su.AtomCollection()

    elements = list()
    positions = list()

    for symbol, position in atom_list:
        elements.append(su.ElementInfo.element_from_symbol(symbol))
        positions.append(su.BOHR_PER_ANGSTROM * np.array(position))

    return su.AtomCollection(elements, np.array(positions))


def molecule_to_bond_order_collection(molecule: vtkMolecule) -> su.BondOrderCollection:
    bo_collection = su.BondOrderCollection(molecule.GetNumberOfAtoms())

    n_bonds = molecule.GetNumberOfBonds()
    for n in range(n_bonds):
        bond = molecule.GetBond(n)
        i = bond.GetBeginAtomId()
        j = bond.GetEndAtomId()
        order = bond.GetOrder()
        bo_collection.set_order(i, j, order)

    return bo_collection


def atom_collection_to_molecule(atom_collection: su.AtomCollection) -> vtkMolecule:
    molecule = vtkMolecule()
    for atom in atom_collection:
        p = atom.position * su.ANGSTROM_PER_BOHR
        z = su.ElementInfo.Z(atom.element)
        molecule.AppendAtom(z, *p)
    return molecule


def convert_gradients(
    gradients: np.ndarray,
    boost_factor: float = 0.1400142601462408,
    trust_radius: float = 0.2
) -> None:
    """
    Convert gradients from hartree/bohr to hartree/angstrom.
    Dampen, if max displacement is > trust_radius (default 1 angstrom)
    to avoid shooting around nuclei.
    """
    gradients *= boost_factor * su.BOHR_PER_ANGSTROM
    max_coefficient = np.max(np.abs(gradients))
    if max_coefficient > trust_radius:
        gradients *= trust_radius / max_coefficient


def apply_gradients(
    molecule: vtkMolecule,
    gradients: np.ndarray,
    bonds: Optional[np.ndarray] = None,
    mouse_picked_atom_ids: Optional[List[int]] = None,
    haptic_picked_atom_id: Optional[int] = None,
) -> None:
    """
    Apply gradients to molecule.
    """
    n_atoms = molecule.GetNumberOfAtoms()
    for atom_index in range(n_atoms):
        if (
            mouse_picked_atom_ids is not None
            and (
                haptic_picked_atom_id is None
                or haptic_picked_atom_id in mouse_picked_atom_ids
            )
            and atom_index in mouse_picked_atom_ids
        ):
            continue
        if haptic_picked_atom_id is not None and atom_index == haptic_picked_atom_id:
            continue
        gradient = gradients[atom_index]
        atom = molecule.GetAtom(atom_index)
        position = atom.GetPosition()

        atom.SetPosition(
            position[0] - gradient[0],
            position[1] - gradient[1],
            position[2] - gradient[2],
        )
    if not isinstance(bonds, np.ndarray):
        bond_collection = su.BondDetector.detect_bonds(molecule_to_atom_collection(molecule))
        bonds = bond_collection.matrix.toarray()

    for i in range(n_atoms - 1):
        for j in range(i + 1, n_atoms):
            bond_id = molecule.GetBondId(i, j)
            if bond_id == -1:
                molecule.AppendBond(i, j, int(round(bonds[i, j])))
            else:
                molecule.SetBondOrder(bond_id, int(round(bonds[i, j])))


def times_bohr_per_angstrom(atom_positions: List[float]) -> List[float]:
    """
    Convert atom positions from bohr to angstrom.
    """
    return cast(
        List[float],
        [
            atom_positions[0] * su.BOHR_PER_ANGSTROM,
            atom_positions[1] * su.BOHR_PER_ANGSTROM,
            atom_positions[2] * su.BOHR_PER_ANGSTROM,
        ],
    )


def times_angstrom_per_bohr(atom_positions: List[float]) -> List[float]:
    """
    Convert atom positions from angstrom to bohr.
    """
    return cast(
        List[float],
        [
            atom_positions[0] * su.ANGSTROM_PER_BOHR,
            atom_positions[1] * su.ANGSTROM_PER_BOHR,
            atom_positions[2] * su.ANGSTROM_PER_BOHR,
        ],
    )


def maximum_vdw_radius(molecule: vtkMolecule) -> float:
    """
    Returns the maximum VDW radius of all the atoms in the molecule.
    """
    table = vtkPeriodicTable()
    return max(
        (
            cast(float, table.GetVDWRadius(molecule.GetAtom(id).GetAtomicNumber()))
            for id in range(molecule.GetNumberOfAtoms())
        ),
        default=0.0,
    )
