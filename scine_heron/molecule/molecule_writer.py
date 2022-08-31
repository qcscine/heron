#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Tools for writing a molecule to a file.
"""

from pathlib import Path
from vtk import vtkMolecule
from typing import Union
import os

from scine_heron.molecule.utils.molecule_utils import molecule_to_atom_collection, molecule_to_bond_order_collection


def write_molecule_to_file(molecule: vtkMolecule, file_name: Union[Path, str]) -> None:
    """
    This method writes molecule in specified format as supported by SCINE Utilities.
    """
    import scine_utilities as utils

    _, extension = os.path.splitext(file_name)
    if extension in [".mol", ".pdb"]:
        utils.io.write_topology(str(file_name), molecule_to_atom_collection(molecule),
                                molecule_to_bond_order_collection(molecule))
    else:
        utils.io.write(str(file_name), molecule_to_atom_collection(molecule))


def write_trajectory_to_file(trajectory, file_name: Union[Path, str]) -> None:
    """
    This method writes a trajectory in specified format as supported by SCINE Utilities.
    """
    import scine_utilities as utils

    _, extension = os.path.splitext(file_name)
    if extension == ".bin":
        file_format = utils.io.TrajectoryFormat.Binary
    elif extension == ".xyz":
        file_format = utils.io.TrajectoryFormat.Xyz
    else:
        raise RuntimeError(f"Unsupported file extension {extension}, only support 'bin' and 'xyz'.")

    utils.io.write_trajectory(file_format, str(file_name), trajectory)
