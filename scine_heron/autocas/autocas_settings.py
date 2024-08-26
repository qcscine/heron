#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

import os
from enum import Enum
from typing import List, Set, Optional


class Stage(Enum):
    InitialOrbitals = 1
    InitialDMRG = 2
    FinalDMRG = 3


class AutocasSettings:
    def __init__(self):
        # not for autocas
        self.molecule_xyz_file = None
        self.molcas_orbital_file = ""
        self.orbital_energies = None
        self.orbital_occupations = None
        # for autocas

        self.molecule_charge = 0
        self.molecule_spin_multiplicity = 1
        self.molecule_double_d_shell = True

        self.plateau_values = 10
        self.threshold_step = 0.01

        self.weak_correlation_threshold = 0.02
        self.single_reference_threshold = 0.14

        self.enable_large_cas = False
        self.large_spaces_max_orbitals = 20

        # self.molecule_core_orbitals = 0
        # self.molecule_valence_orbitals = 0
        # self.molecule_electrons = 0
        # self.molecule_occupation = []

        self.molcas_dump = True
        self.molcas_project_name = "autocas"
        # setup interface

        self.molcas_work_dir = os.getcwd() + "/test"
        # Interface
        self.interface_dmrg_bond_dimension = 250
        self.interface_dmrg_sweeps = 5
        self.interface_basis_set = "cc-pvdz"
        self.interface_method = "dmrg_ci"
        self.interface_post_cas_method = ""
        # self.interface_spin_multiplicity = 1
        # self.interface_charge = 0
        self.interface_xyz_file = None
        self.molcas_point_group = "C1"
        self.molcas_ipea = 0.0
        self.interface_cholesky = False
        self.interface_uhf = False
        self.interface_fiedler = False
        # self.interface_only_hf = True
        self.interface_n_excited_states = 0

        self.result_initial_occupation = None
        self.result_initial_indices = None

        self.result_initial_s1 = None
        self.result_initial_mutual_information = None
        self.result_initial_energy = None

        self.result_final_occupation = None
        self.result_final_indices = None

        self.user_occupation = None
        self.user_indices = None

        self.orbital_index_sets: Optional[List[Set[int]]] = None

    def get_orbital_file(self, stage: Stage = Stage.InitialOrbitals):
        molden_string = self.molcas_work_dir + "/" + self.molcas_project_name + \
            "/initial/" + self.molcas_project_name + ".scf.molden"
        if stage == Stage.InitialOrbitals:
            self.molcas_orbital_file = molden_string
            return molden_string
        # TODO: make this useful
        return molden_string

        # MOLCAS
        # self.molcas_orbital_localisation = False
        # self.molcas_localisation_space = "OCCUpied"
        # self.molcas_localisation_method = "PIPEk-Mezey"
