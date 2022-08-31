#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Mocks for the scine_heron_haptic module.
"""
from typing import List


class HapticData:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z


class AtomData:
    def __init__(self, id: int, x: float, y: float, z: float, dis: float) -> None:
        self.id = id
        self.x = x
        self.y = y
        self.z = z
        self.dis = dis


class HapticCallback:
    pass


class HapticDeviceManager:
    def __init__(self) -> None:
        identity = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        self.inited = True
        self.callbacks: List[HapticCallback] = list()
        self.molecule: List[AtomData] = list()
        self.transformation_matrix: List[float] = identity
        self.invert_matrix: List[float] = identity

    def init_haptic_device(self) -> bool:
        self.inited = True
        return self.inited

    def add_haptic_callback(self, callback: HapticCallback) -> None:
        self.callbacks.append(callback)

    def exit_haptic_device(self) -> None:
        self.inited = False

    def clear_molecule(self) -> None:
        self.molecule.clear()

    def add_atom(self, atom: AtomData) -> None:
        self.molecule.append(atom)

    def update_atom(self, atom: AtomData) -> None:
        self.molecule[atom.id] = atom

    def set_transformation_matrix(
        self, transformation_matrix: list, invert_matrix: list
    ) -> None:
        self.transformation_matrix = transformation_matrix
        self.invert_matrix = invert_matrix
