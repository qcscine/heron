#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the ElectronicData class.
"""
import re
import math
import numpy as np
from typing import List, Any
from scine_heron.molecule.utils.molecule_utils import times_angstrom_per_bohr


class MolecularOrbital:
    """
    Provide molecular orbital.
    """

    def __init__(
        self,
        symmetry: str,
        energy: float,
        spin: str,
        occupation: float,
        coefficients: List[float],
    ):
        self.symmetry = symmetry
        self.energy = energy
        self.spin = spin
        self.occupation = occupation
        self.coefficients = np.array(coefficients)

    @classmethod
    def from_molden_file(cls, lines: List[str]) -> Any:
        symmetry = re.match(r"\s?Sym(?:.*)=(.*)", lines[0]).groups()[0].strip()  # type: ignore[union-attr]
        energy = float(
            re.match(  # type: ignore[union-attr]
                r"\s?Ene(?:.*)=(.*)",
                lines[1]).groups()[0].strip())  # type: ignore[union-attr]
        spin = re.match(r"\s?Spin(?:.*)=(.*)", lines[2]).groups()[0].strip()  # type: ignore[union-attr]
        occupation = float(
            re.match(  # type: ignore[union-attr]
                r"\s?Occup(?:.*)=(.*)",
                lines[3]).groups()[0].strip())  # type: ignore[union-attr]
        coefficients = [float(line.split()[1]) for line in lines[4:] if len(line) > 0]

        return cls(symmetry, energy, spin, occupation, coefficients)


class GaussianOrbital:
    """
    Provide gaussian orbital.
    """

    def __init__(self, orb_type: str, coefficients: List[List[float]]):
        self.orb_type = orb_type
        self.nr_gaussians = len(coefficients)

        self.coefficients = coefficients
        self.alpha = np.array([coefficients[i][0] for i in range(self.nr_gaussians)])
        self.coeff = np.array(
            [
                self.__calculate_coefficients(i, orb_type)
                for i in range(self.nr_gaussians)
            ]
        )

    def chi_step(self) -> int:
        if self.orb_type == "s":  # s orbital
            return 1
        elif self.orb_type == "p":  # p orbital
            return 3
        elif self.orb_type == "d":  # d orbital [5D]
            return 5
        elif self.orb_type == "f":  # f orbital [7F]
            return 7
        else:
            raise NotImplementedError(
                "The atomic orbital type '" + self.orb_type + "' is not implemented."
            )

    def __calculate_coefficients(self, index: int, orb_type: str) -> float:
        if self.orb_type == "s":  # s orbital
            return self.coefficients[index][1] * pow(
                2.0 * self.alpha[index] / math.pi, 0.75
            )
        elif self.orb_type == "p":  # p orbital
            return self.coefficients[index][1] * pow(
                128.0 * pow(self.alpha[index], 5) / pow(math.pi, 3), 0.25
            )
        elif self.orb_type == "d":  # d orbital
            return self.coefficients[index][1] * pow(
                2048.0 * pow(self.alpha[index], 7) / pow(math.pi, 3), 0.25
            )
        elif self.orb_type == "f":  # f orbital
            return self.coefficients[index][1] * pow(
                32768.0 * pow(self.alpha[index], 9) / pow(math.pi, 3), 0.25
            )
        else:
            raise NotImplementedError(
                "The atomic orbital type '" + orb_type + "' is not implemented."
            )


class Atom:
    """
    Provide Atom.
    """

    def __init__(self, name: str, elem: int, x: float, y: float, z: float):
        self.name = name
        self.elem = elem
        self.coordinates = times_angstrom_per_bohr([x, y, z])
        self.gaussian_orbitals: List[GaussianOrbital] = list()
        self.min_alpha = 0
        self.sum_chi_step = 0  # sum_chi_step will be used in case atom will be skipped

    @classmethod
    def from_molden_line(cls, line: str) -> Any:
        split = line.split()
        parsed_line = (
            # example : C 1 6 6.1052194517 1.7410254664 1.1040800477
            split[0],
            # ignore split[1], which is the number of the atom
            int(split[2]),
            float(split[3]),
            float(split[4]),
            float(split[5]),
        )
        return cls(*parsed_line)


class ElectronicData:
    """
    Provide electronic data.
    """

    def __init__(self, atoms: List[Atom], mo: List[MolecularOrbital]) -> None:
        self.atoms = atoms
        self.mo = mo
