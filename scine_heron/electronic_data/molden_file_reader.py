#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

import re
from typing import Any, List, Tuple, Optional

import numpy as np

from scine_heron.electronic_data.electronic_data import (Atom, ElectronicData,
                                                         GaussianOrbital,
                                                         MolecularOrbital)


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
        mos = self.__parse_mo(mo)
        return ElectronicData(parsed_atoms, mos)

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
            elif re.match("^" + re.escape("[5D]"), line):
                is_atom_line = False
                is_gto_line = False
                is_mo_line = False
                continue
            elif re.match("^" + re.escape("[7F]"), line):
                is_atom_line = False
                is_gto_line = False
                is_mo_line = False
                continue
            elif re.match("^" + re.escape("[9G]"), line):
                is_atom_line = False
                is_gto_line = False
                is_mo_line = False
                continue
            elif re.match("^" + re.escape("[Charge] (Mullike)"), line):
                is_atom_line = False
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

    # def __stupid_gto_thing(self, gtos: List[str], atoms):
    #     re_filter = re.compile("[spdfgh]")
    #     j = 0
    #     stupid_list = []
    #     gto_list = []
    #     other_list = []
    #     atom_numbers = []

    #     for _, line in enumerate(gtos):

    #         # empty line
    #         if line.strip() == "":
    #             # ....
    #             gto_list.append(line)
    #             other_list.append(gto_list)
    #             gto_list = []
    #             j = 0
    #             if other_list == []:
    #                 pass
    #             else:
    #                 stupid_list.append(other_list)
    #             other_list = []
    #
    #         # found s p d f g h
    #         elif re_filter.match(line):
    #             if gto_list == []:
    #                 pass
    #             else:
    #                 other_list.append(gto_list)
    #             gto_list = [line]

    #         elif j == 0:
    #             atom_numbers.append(int(line.split()[0]))
    #             j = 1

    #         elif j == 1:
    #             gto_list.append(line)

    #     return stupid_list, atom_numbers

    def __new_atoms(self, gtos: List[str], atoms):
        re_filter = re.compile("[spdfgh]")
        gaussian_orbitals: List[GaussianOrbital] = []
        gaussian_coeffs: List[List[float]] = []
        j = 0
        atom = atoms[0]
        orbital_type: Optional[str] = None
        new_atoms = []
        for i, line in enumerate(gtos):
            # last line
            if i + 1 == len(gtos):
                assert orbital_type
                gaussian_orbitals.append(GaussianOrbital(orbital_type, gaussian_coeffs))
                atom.gaussian_orbitals = gaussian_orbitals
                new_atoms.append(atom)
            # found s p d f g h
            elif re_filter.match(line.lstrip()):
                if orbital_type:
                    gaussian_orbitals.append(
                        GaussianOrbital(orbital_type, gaussian_coeffs)
                    )
                orbital_type = line.split()[0]
                gaussian_coeffs = []
            # empty line
            elif line.strip() == "":
                assert orbital_type
                gaussian_orbitals.append(GaussianOrbital(orbital_type, gaussian_coeffs))
                atom.gaussian_orbitals = gaussian_orbitals
                new_atoms.append(atom)
                orbital_type = None
                j = 0
            # atom
            elif j == 0:
                gaussian_orbitals = []
                atom = atoms[int(line.split()[0]) - 1]
                j = 1
            # coeffs
            elif j == 1:
                gaussian_coeffs.append([float(line.split()[0]), float(line.split()[1])])
        return new_atoms

    def __parse_gto(self, atoms: List[Atom], gto: List[str]) -> None:
        """
        This method parse AtomicOrbitalsGTO.
        """
        atoms = self.__new_atoms(gto, atoms)
        i = 0
        for atom in atoms:
            i = i + 1
            atom.min_alpha = min(
                [
                    np.min(atom.gaussian_orbitals[i].alpha)
                    for i in range(len(atom.gaussian_orbitals))
                ]
            )

            for u in range(len(atom.gaussian_orbitals)):
                atom.sum_chi_step += atom.gaussian_orbitals[u].chi_step()

    # @staticmethod
    # def __parse_orbital_blocks(gto_block: List[Any]) -> List[GaussianOrbital]:
    #     gaussian_orbitals = []
    #     for orb_block in gto_block:
    #         try:
    #             orb_type, _, _ = orb_block[0].split()
    #         except ValueError:
    #             orb_type, _ = orb_block[0].split()

    #         gaussian_coeffs = [
    #             [float(x.replace("D", "E")) for x in coeff_line.split()]
    #             for coeff_line in orb_block[1:]
    #             if coeff_line not in ("", "\n")
    #         ]
    #         gaussian_orbitals.append(GaussianOrbital(orb_type, gaussian_coeffs))
    #     return gaussian_orbitals

    # @staticmethod
    # def __get_section_heads_and_positions_alternative(lines):
    #     sections = []
    #     j = 0
    #     for i, line in enumerate(lines):
    #         if line.strip() == "":
    #             sections.append([j, lines[j]])
    #             j += i + 1
    #     return sections

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
