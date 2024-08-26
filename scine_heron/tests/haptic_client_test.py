#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Tests of HapticClient.
"""

import pytest
from scine_heron.haptic.haptic_client import HapticClient
from typing import Optional
from vtk import vtkMolecule, vtkCamera


@pytest.fixture(name="haptic_client")  # type: ignore[misc]
def create_haptic_client() -> Optional[HapticClient]:
    """
    Returns a HapticClient.
    """
    haptic_client = HapticClient()

    assert haptic_client.device_is_available is False
    assert haptic_client.callback is None

    haptic_client.init_haptic_device()

    if haptic_client.device_is_available:
        return haptic_client
    else:
        return None


def test_save_and_update_molecule(haptic_client: HapticClient) -> None:
    molecule = vtkMolecule()
    molecule.AppendAtom(1, 0, 0.00, 0.00)
    molecule.AppendAtom(1, 1, 0.00, 0.00)

    if haptic_client is None:
        return
    # update molecule
    assert len(haptic_client.haptic_device_manager.molecule) == 0
    haptic_client.update_molecule(molecule)
    assert len(haptic_client.haptic_device_manager.molecule) == 2

    # update first atom
    assert haptic_client.haptic_device_manager.molecule[0].x == 0
    assert haptic_client.haptic_device_manager.molecule[0].y == 0
    assert haptic_client.haptic_device_manager.molecule[0].z == 0

    atom = molecule.GetAtom(0)
    atom.SetPosition([1, 1, 1])
    haptic_client.update_atom(0, atom, False)

    assert haptic_client.haptic_device_manager.molecule[0].x == 1
    assert haptic_client.haptic_device_manager.molecule[0].y == 1
    assert haptic_client.haptic_device_manager.molecule[0].z == 1

    # add new atom
    new_atom = molecule.AppendAtom(1, 2, 2, 2)

    assert len(haptic_client.haptic_device_manager.molecule) == 2
    haptic_client.update_atom(2, new_atom, True)
    assert len(haptic_client.haptic_device_manager.molecule) == 3


def test_update_transform_matrix(haptic_client: HapticClient) -> None:

    if haptic_client is None:
        return

    # init as identity matrix
    matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    assert haptic_client.haptic_device_manager.transformation_matrix == matrix
    assert haptic_client.haptic_device_manager.invert_matrix == matrix

    # don't move
    haptic_client.update_transform_matrix(vtkCamera(), 0, 0)
    assert haptic_client.haptic_device_manager.transformation_matrix == matrix
    assert haptic_client.haptic_device_manager.invert_matrix == matrix

    # move
    haptic_client.update_transform_matrix(vtkCamera(), 1, 1)
    assert haptic_client.haptic_device_manager.transformation_matrix != matrix
    assert haptic_client.haptic_device_manager.invert_matrix != matrix
