#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the molden file reader.
"""

import re
import numpy as np
from scine_heron.electronic_data.electronic_data import (
    ElectronicData,
    Atom,
    MolecularOrbital,
    GaussianOrbital,
)
from typing import List, Tuple, Any


class MoldenFileReader:
    """
    Provide molden file reader.
    """

    def read_molden(self, molden: str) -> ElectronicData:
        """
        This method read molden file and return ElectronicData.
        """
        atoms, gto, mo = self.__parse_molden(molden)

        parsed_atoms = self.__parse_atoms(atoms)
        self.__parse_gto(parsed_atoms, gto)

        return ElectronicData(parsed_atoms, self.__parse_mo(mo))

    def __parse_molden(self, molden: str) -> Tuple[List[str], List[str], List[str]]:
        """
        This method parse molden file.
        """

        is_atom_line = False
        is_gto_line = False
        is_mo_line = False

        atoms: List[str] = list()
        gto: List[str] = list()
        mo: List[str] = list()

        for line in molden.split("\n"):
            if re.match("^" + re.escape("[Atoms]"), line):
                is_atom_line = True
                is_gto_line = False
                is_mo_line = False
                continue
            elif re.match("^" + re.escape("[GTO]"), line):
                is_atom_line = False
                is_gto_line = True
                is_mo_line = False
                continue
            elif re.match("^" + re.escape("[MO]"), line):
                is_atom_line = False
                is_gto_line = False
                is_mo_line = True
                continue

            if is_atom_line:
                atoms.append(line)
            elif is_gto_line:
                if line.startswith("["):
                    continue
                gto.append(line)
            elif is_mo_line:
                mo.append(line)

        return atoms, gto, mo

    def __parse_atoms(self, atoms: List[str]) -> List[Atom]:
        return [Atom.from_molden_line(line) for line in atoms]

    def __parse_mo(self, mo: List[str]) -> List[MolecularOrbital]:
        """
        This method parse MolecularOrbital.
        """
        mo_section_heads = self.__get_section_heads_and_positions(mo, r"\s?Sym=")
        mo_orbital_blocks = self.__split_by_sections(mo, mo_section_heads)
        return [
            MolecularOrbital.from_molden_file(block)
            for _, block in enumerate(mo_orbital_blocks)
        ]

    def __parse_gto(self, atoms: List[Atom], gto: List[str]) -> None:
        """
        This method parse AtomicOrbitalsGTO.
        """
        gto_sections_heads = self.__get_section_heads_and_positions(
            gto, r"\s*[0-9]+ [0-9]+"
        )
        gto_sections = self.__split_by_sections(gto, gto_sections_heads)

        gto_blocks = []
        for gto_section in gto_sections:
            orb_sections_heads = self.__get_section_heads_and_positions(
                gto_section, "[spdfgh]"
            )
            orb_sections = self.__split_by_sections(gto_section, orb_sections_heads)
            gto_blocks.append(orb_sections)

        atom_numbers = [int(x[1].split()[0]) for x in gto_sections_heads]

        for atom_number, gto_block in zip(atom_numbers, gto_blocks):
            atom = atoms[atom_number - 1]
            atom.gaussian_orbitals = self.__parse_orbital_blocks(gto_block)

            atom.min_alpha = min(
                [
                    np.min(atom.gaussian_orbitals[i].alpha)
                    for i in range(len(atom.gaussian_orbitals))
                ]
            )

            for i in range(len(atom.gaussian_orbitals)):
                atom.sum_chi_step += atom.gaussian_orbitals[i].chi_step()

    @staticmethod
    def __parse_orbital_blocks(gto_block: List[Any]) -> List[GaussianOrbital]:
        gaussian_orbitals = []
        for orb_block in gto_block:
            try:
                orb_type, _, _ = orb_block[0].split()
            except ValueError:
                orb_type, _ = orb_block[0].split()

            gaussian_coeffs = [
                [float(x.replace("D", "E")) for x in coeff_line.split()]
                for coeff_line in orb_block[1:]
                if coeff_line not in ("", "\n")
            ]
            gaussian_orbitals.append(GaussianOrbital(orb_type, gaussian_coeffs))
        return gaussian_orbitals

    @staticmethod
    def __get_section_heads_and_positions(
        lines: List[str], section_re: str
    ) -> List[Any]:
        re_filter = re.compile(section_re)
        sections = [[i, line] for i, line in enumerate(lines) if re_filter.match(line)]
        return sections

    @staticmethod
    def __split_by_sections(
        lines: List[str], section_heads_and_positions: List[Any]
    ) -> List[Any]:
        blocks = []
        for i in range(len(section_heads_and_positions)):
            line_nr = section_heads_and_positions[i][0]
            try:
                next_line_nr = section_heads_and_positions[i + 1][0] - 1
            except IndexError:
                next_line_nr = len(lines) - 1
            blocks.append(lines[line_nr: next_line_nr + 1])
        return blocks
