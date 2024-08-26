#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from .orbital_groups import OrbitalGroup, OrbitalGroupMap


class OrbitalGroupFileReader:
    @staticmethod
    def read_orbital_group_file(file_name: str):
        orbital_index_shift = 1
        lines = open(file_name, "r").readlines()
        lines.pop(0)
        n_systems = OrbitalGroupFileReader.__get_n_systems(lines[0])
        orbital_group = OrbitalGroup(n_systems)
        map = OrbitalGroupMap([])
        for line in lines:
            n_indices = len(line.split())
            if not n_indices and not orbital_group.empty():
                orbital_group = OrbitalGroup(n_systems)
                map.add_orbital_group(orbital_group)
                continue
            orbital_group.add_orbitals([int(i) + orbital_index_shift for i in line.split()])
        map.add_orbital_group(orbital_group)
        return map

    @staticmethod
    def __get_n_systems(line):
        return len(line.split())
