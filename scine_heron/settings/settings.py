#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the Settings class.
"""
from typing import Optional, List
from enum import Enum


class MoleculeStyle(Enum):
    """
    Provide molecule style settings.
    """

    BallAndStick = "ball and stick"
    VDWSpheres = "VDW spheres"
    LiquoriceStick = "liquorice stick"
    Fast = "fast"
    PartialCharges = "partial charges"
    ForceArrow = "force arrow"


class LabelsStyle(Enum):
    """
    Provide labels style settings.
    """

    Empty = "empty"
    AtomicNumber = "atomic number"
    Symbol = "symbol"
    IndexNumber = "index number"


class MolViewSettings:
    """
    Provide settings for calculators and related quantities.

    calculator_settings defines the settings for running the backend.
    molecule_style defines the appearance of the molecule.
    """

    def __init__(self) -> None:
        self.molecule_style = MoleculeStyle.BallAndStick
        self.labels_style = LabelsStyle.Empty
        self.selected_molecular_orbital: Optional[int] = None
        self.number_of_molecular_orbital: Optional[int] = None
        self.molecular_orbital_value: float = 0.05
        self.mouse_picked_atom_ids: Optional[List[int]] = []
        self.haptic_picked_atom_id: Optional[int] = None
        self.force_scaling: float = 1.0
        self.error_message: str = ""
        self.info_message: str = ""
        self.haptic_force_scaling: float = 1.0
        self.gradients_scaling: float = 0.1
        self.bond_display: str = "distance"
