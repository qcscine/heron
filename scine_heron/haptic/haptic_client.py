#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the HapticClient class.
"""

try:
    import scine_heron_haptic as suh
    from scine_heron.haptic.haptic_callback import HapticCallback
except ImportError:
    pass
except NameError:
    pass

from vtk import (
    vtkAtom,
    vtkMolecule,
    vtkTransform,
    vtkMatrix4x4,
    vtkCamera,
)
from typing import List, Optional

from scine_utilities import (
    ANGSTROM_PER_BOHR,
    ElementInfo,
)


class HapticClient:
    def __init__(self) -> None:
        self.device_is_available: bool = False
        self.transform = vtkTransform()
        self.callback: Optional[HapticCallback] = None

    def init_haptic_device(self) -> None:
        try:
            self.haptic_device_manager = suh.HapticDeviceManager()  # pylint: disable=attribute-defined-outside-init
            self.device_is_available = self.haptic_device_manager.init_haptic_device()
        except NameError:
            print("No haptic device interface detected. Continuing without haptic feedback.")

        if self.device_is_available:
            self.callback = HapticCallback()  # type: ignore[assignment]
            self.haptic_device_manager.add_haptic_callback(self.callback)

    def exit_haptic_device(self) -> None:
        if self.device_is_available:
            self.haptic_device_manager.exit_haptic_device()

    def update_atom(
        self, atom_index: int, atom: vtkAtom, new_atom: bool = False
    ) -> None:
        if self.device_is_available:
            position = atom.GetPosition()
            radius = ElementInfo.covalent_radius(ElementInfo.element(atom.GetAtomicNumber())) * ANGSTROM_PER_BOHR

            atom = suh.AtomData(
                atom_index, position.GetX(), position.GetY(), position.GetZ(), radius
            )

            if new_atom:
                self.haptic_device_manager.add_atom(atom)
            else:
                self.haptic_device_manager.update_atom(atom)

    def update_molecule(self, molecule: vtkMolecule) -> None:
        if self.device_is_available:
            self.haptic_device_manager.clear_molecule()

            for atom_index in range(molecule.GetNumberOfAtoms()):
                self.update_atom(atom_index, molecule.GetAtom(atom_index), True)

    def update_transform_matrix(
        self, camera: vtkCamera, azimuth: float, elevation: float
    ) -> None:
        view_up = camera.GetViewUp()
        axis = [
            -camera.GetViewTransformMatrix().GetElement(0, 0),
            -camera.GetViewTransformMatrix().GetElement(0, 1),
            -camera.GetViewTransformMatrix().GetElement(0, 2),
        ]

        rotate_transform = vtkTransform()

        # azimuth
        rotate_transform.Identity()
        rotate_transform.RotateWXYZ(azimuth, view_up)

        # elevation
        rotate_transform.RotateWXYZ(elevation, axis)
        rotate_transform.Update()

        transform = vtkTransform()
        transform.Concatenate(rotate_transform)
        transform.Concatenate(self.transform)
        transform.Update()

        self.transform = transform
        self.__set_transformation_matrix()

    def __set_transformation_matrix(self) -> None:
        if self.device_is_available:
            vtk_matrix = self.transform.GetMatrix()

            invert_matrix = vtkMatrix4x4()
            vtkMatrix4x4.Invert(vtk_matrix, invert_matrix)

            self.haptic_device_manager.set_transformation_matrix(
                self.__matrix2list(vtk_matrix), self.__matrix2list(invert_matrix)
            )

    @staticmethod
    def __matrix2list(vtk_matrix: vtkMatrix4x4) -> List[float]:
        matrix = list()

        for i in range(0, 4):
            for j in range(0, 4):
                matrix.append(vtk_matrix.GetElement(i, j))

        return matrix

    def set_calc_gradient_in_loop(self, calc_gradient_in_loop: bool) -> None:
        if self.device_is_available:
            self.haptic_device_manager.set_calc_gradient_in_loop(calc_gradient_in_loop)

    def update_gradient(self, gradients: List[List[float]]) -> None:
        if self.device_is_available:
            self.haptic_device_manager.update_gradient(
                [
                    elem for gradient in gradients for elem in gradient
                ]  # convert 2d gradient to 1d
            )
