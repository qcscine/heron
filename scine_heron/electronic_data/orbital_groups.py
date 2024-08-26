#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import List, Set


class OrbitalGroup:
    def __init__(self, n_systems: int):
        if n_systems == 0:
            raise RuntimeError("There must be at least one system in an orbital group.")
        self._system_wise_indices: List[Set[int]] = [set() for _ in range(n_systems)]

    def n_systems(self):
        return len(self._system_wise_indices)

    def add_orbitals(self, new_indices: List[int]):
        if self.n_systems() != len(new_indices):
            raise RuntimeError("The number of systems is inconsistent in the orbital mapping.")
        for i_sys, i in enumerate(new_indices):
            self._system_wise_indices[i_sys].add(i)

    def get_indices_for_system(self, i_sys: int) -> Set[int]:
        if i_sys >= self.n_systems():
            raise RuntimeError("System index out of bounds.")
        return self._system_wise_indices[i_sys]

    def n_orbitals(self):
        return len(self._system_wise_indices[0])

    def empty(self):
        return self.n_orbitals() == 0


class OrbitalGroupMap:
    def __init__(self, orbital_groups: List[OrbitalGroup]):
        self._groups: List[OrbitalGroup] = orbital_groups

    def add_orbital_group(self, orbital_group: OrbitalGroup):
        self._groups.append(orbital_group)

    def get_n_systems(self):
        if not self._groups:
            return 0
        return self._groups[0].n_systems()

    def get_orbital_groups(self):
        return self._groups

    def get_index_sets_for_system(self, i: int) -> List[Set[int]]:
        assert i < self.get_n_systems()
        index_sets = []
        for group in self._groups:
            index_sets.append(group.get_indices_for_system(i))
        return index_sets
