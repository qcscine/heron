#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the ElectronicDataImageGenerator class.
"""

import math
import numpy as np
from typing import List, Dict
import scine_utilities as su
from vtk import (
    vtkImageData,
    VTK_DOUBLE,
)
from scine_heron.electronic_data.electronic_data import ElectronicData


class ElectronicDataImageGenerator:
    """
    Generate vtkImageData that contains electronic data.
    Important: Code here only works in spherical harmonics and not in Cartesians.
    """

    def __init__(self, electronic_data: ElectronicData):
        self.__electronic_data = electronic_data
        self.__block_size = 8
        self.__threshold = 1e-2
        self.__step_size = 0.2
        self.__dim = self.__get_box_size()
        self.__cache: Dict[int, np.ndarray] = dict()
        self.__steps = [
            int((self.__dim[1] - self.__dim[0]) / self.__step_size + 0.5),
            int((self.__dim[3] - self.__dim[2]) / self.__step_size + 0.5),
            int((self.__dim[5] - self.__dim[4]) / self.__step_size + 0.5),
        ]
        self.__dx, self.__dy, self.__dz = (
            (self.__dim[1] - self.__dim[0]) / (self.__steps[0] - 1),
            (self.__dim[3] - self.__dim[2]) / (self.__steps[1] - 1),
            (self.__dim[5] - self.__dim[4]) / (self.__steps[2] - 1),
        )

    def __get_box_size(self) -> List[float]:
        x = np.array(
            [
                self.__electronic_data.atoms[index].coordinates[0]
                for index in range(len(self.__electronic_data.atoms))
            ]
        )
        y = np.array(
            [
                self.__electronic_data.atoms[index].coordinates[1]
                for index in range(len(self.__electronic_data.atoms))
            ]
        )
        z = np.array(
            [
                self.__electronic_data.atoms[index].coordinates[2]
                for index in range(len(self.__electronic_data.atoms))
            ]
        )
        borders = np.array(
            [
                np.sqrt(-np.log(self.__threshold * 10) / atom.min_alpha)
                for atom in self.__electronic_data.atoms
            ]
        )
        box = [
            min(x - borders),
            max(x + borders),
            min(y - borders),
            max(y + borders),
            min(z - borders),
            max(z + borders),
        ]
        return box

    def generate_mo_image(self, orbital_index: int) -> vtkImageData:
        """
        Generate molecular orbital image.
        """
        image = vtkImageData()
        image.SetDimensions(self.__steps[0], self.__steps[1], self.__steps[2])
        image.SetOrigin(self.__dim[0], self.__dim[2], self.__dim[4])
        image.SetSpacing(self.__dx, self.__dy, self.__dz)
        image.AllocateScalars(VTK_DOUBLE, 1)
        image.GetPointData().GetScalars().Fill(0.0)

        block_index = 0
        i = 0
        x = self.__dim[0]
        while i < self.__steps[0]:
            j = 0
            y = self.__dim[2]
            while j < self.__steps[1]:
                k = 0
                z = self.__dim[4]
                while k < self.__steps[2]:
                    block = None
                    if orbital_index == -4:
                        # Electron Density
                        for orb in self.__electronic_data.mo:
                            coefficients_size = len(orb.coefficients)
                            if block_index not in self.__cache:
                                self.__calc_mo_at_block_and_save_in_cache(
                                    block_index, coefficients_size, x, y, z
                                )
                            block_tmp = self.__cache[block_index].dot(orb.coefficients)
                            block_tmp = np.square(block_tmp)
                            try:
                                block += block_tmp
                            except BaseException:
                                block = block_tmp
                    else:
                        mo = self.__electronic_data.mo[orbital_index]
                        coefficients_size = len(mo.coefficients)
                        if block_index not in self.__cache:
                            self.__calc_mo_at_block_and_save_in_cache(
                                block_index, coefficients_size, x, y, z
                            )
                        block = self.__cache[block_index].dot(mo.coefficients)
                    if np.sum(np.abs(block)) > 1.0e-4:
                        self.__add_mo_block_at_image(image, block, i, j, k)

                    k += self.__block_size
                    z += self.__dz * self.__block_size
                    block_index += 1
                j += self.__block_size
                y += self.__dy * self.__block_size
            i += self.__block_size
            x += self.__dx * self.__block_size
        return image

    def __add_mo_block_at_image(
        self,
        image: vtkImageData,
        block: np.ndarray,
        origin_i: int,
        origin_j: int,
        origin_k: int,
    ) -> None:
        index = 0
        for i in range(self.__block_size):
            for j in range(self.__block_size):
                for k in range(self.__block_size):
                    if (
                        origin_i + i < self.__steps[0]
                        and origin_j + j < self.__steps[1]
                        and origin_k + k < self.__steps[2]
                    ):
                        if block[index] != 0.0:
                            image.SetScalarComponentFromDouble(
                                origin_i + i,
                                origin_j + j,
                                origin_k + k,
                                0,
                                block[index],
                            )
                        index += 1

    def __nearest_value_in_list(
        self, atom_value: float, block_value: float, step: float
    ) -> float:
        max_block_val = block_value + (self.__block_size - 1) * step
        if atom_value < block_value:
            return block_value
        elif atom_value > max_block_val:
            return max_block_val
        else:
            return block_value + int(((atom_value - block_value) / step) + 0.5) * step

    def __calc_mo_at_block_and_save_in_cache(
        self, block_index: int, coefficients_size: int, x: float, y: float, z: float,
    ) -> None:
        """
        Calculate the MO value at given point.
        """
        chi_index = 0
        self.__cache[block_index] = np.zeros(
            (
                self.__block_size * self.__block_size * self.__block_size,
                coefficients_size,
            )
        )
        block = self.__cache[block_index].reshape(
            (
                self.__block_size
                * self.__block_size
                * self.__block_size
                * coefficients_size
            )
        )

        for atom in self.__electronic_data.atoms:
            atom_x = atom.coordinates[0]
            atom_y = atom.coordinates[1]
            atom_z = atom.coordinates[2]

            nearest_x = self.__nearest_value_in_list(atom_x, x, self.__dx)
            nearest_y = self.__nearest_value_in_list(atom_y, y, self.__dy)
            nearest_z = self.__nearest_value_in_list(atom_z, z, self.__dz)

            nearest_x_ang = (nearest_x - atom_x) * su.BOHR_PER_ANGSTROM
            nearest_y_ang = (nearest_y - atom_y) * su.BOHR_PER_ANGSTROM
            nearest_z_ang = (nearest_z - atom_z) * su.BOHR_PER_ANGSTROM

            ra2_nearest = (
                nearest_x_ang * nearest_x_ang
                + nearest_y_ang * nearest_y_ang
                + nearest_z_ang * nearest_z_ang
            )

            if ra2_nearest > 1:
                if math.exp(-ra2_nearest * atom.min_alpha) < self.__threshold:
                    chi_index += atom.sum_chi_step
                    continue

            for orbital in atom.gaussian_orbitals:
                if ra2_nearest > 1:
                    if (
                        np.dot(orbital.coeff, np.exp(-ra2_nearest * orbital.alpha))
                        < self.__threshold
                    ):
                        chi_index += orbital.chi_step()
                        continue

                for i in range(self.__block_size):
                    xx = x + (i * self.__dx)
                    xa = (xx - atom_x) * su.BOHR_PER_ANGSTROM
                    xa2 = xa * xa
                    iOff = i * self.__block_size

                    for j in range(self.__block_size):
                        yy = y + (j * self.__dy)
                        ya = (yy - atom_y) * su.BOHR_PER_ANGSTROM
                        ya2 = ya * ya
                        ijOff = (iOff + j) * self.__block_size

                        for k in range(self.__block_size):
                            zz = z + (k * self.__dz)
                            za = (zz - atom_z) * su.BOHR_PER_ANGSTROM
                            za2 = za * za
                            ijkOff = (ijOff + k) * coefficients_size + chi_index

                            ra2 = xa2 + ya2 + za2

                            radial_sum = np.dot(
                                orbital.coeff, np.exp(-ra2 * orbital.alpha)
                            )

                            if radial_sum < self.__threshold:
                                continue

                            if orbital.orb_type == "s":  # s orbital
                                block[ijkOff] = radial_sum
                            elif orbital.orb_type == "p":  # p orbital
                                block[ijkOff] = xa * radial_sum
                                block[ijkOff + 1] = ya * radial_sum
                                block[ijkOff + 2] = za * radial_sum
                            elif orbital.orb_type == "d":  # d orbital [5D]
                                block[ijkOff] = (
                                    0.288675135 * (2 * za2 - xa2 - ya2) * radial_sum
                                )
                                block[ijkOff + 1] = 0.5 * (xa2 - ya2) * radial_sum
                                block[ijkOff + 2] = xa * ya * radial_sum
                                block[ijkOff + 3] = xa * za * radial_sum
                                block[ijkOff + 4] = ya * za * radial_sum
                            elif orbital.orb_type == "f":  # f orbital [7F]
                                block[ijkOff] = (
                                    radial_sum * za * (5.0 * za2 - 3.0 * ra2)
                                )
                                block[ijkOff + 1] = radial_sum * xa * (5.0 * za2 - ra2)
                                block[ijkOff + 2] = radial_sum * ya * (5.0 * za2 - ra2)
                                block[ijkOff + 3] = radial_sum * za * (xa2 - ya2)
                                block[ijkOff + 4] = radial_sum * xa * ya * za
                                block[ijkOff + 5] = radial_sum * (
                                    xa * xa2 - 3.0 * xa * ya2
                                )
                                block[ijkOff + 6] = radial_sum * (
                                    3.0 * xa2 * ya - ya2 * ya
                                )
                            else:
                                raise NotImplementedError(
                                    "The atomic orbital type '"
                                    + orbital.orb_type
                                    + "' is not implemented."
                                )
                chi_index += orbital.chi_step()
