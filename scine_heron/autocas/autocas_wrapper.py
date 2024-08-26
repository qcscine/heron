#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from scine_autocas import Autocas
from scine_autocas.autocas_utils.molecule import Molecule
from scine_autocas.interfaces.molcas import Molcas

from scine_heron.autocas.autocas_settings import AutocasSettings
from scine_heron.autocas.signal_handler import SignalHandler

from PySide2.QtCore import QCoreApplication
translate = QCoreApplication.translate


class AutocasWrapper:
    def __init__(
        self, autocas_settings: AutocasSettings, signal_handler: SignalHandler
    ):
        # self.molecule = Molecule()
        # self.autocas = Autocas(self.molecule)
        # self.interface = Molcas(self.molecule)
        self.molecule = None
        self.autocas = None
        self.interface = None
        self.settings = autocas_settings
        self.signal_handler = signal_handler

        self.signal_handler.start_initial_orbital_calculation_signal.connect(
            self.generate_initial_orbitals
        )
        self.signal_handler.start_initial_dmrg_calculation_signal.connect(
            self.run_initial_dmrg
        )
        self.signal_handler.start_final_calculation_signal.connect(
            self.run_final_calculation
        )

    def check_settings(self):
        # print("--------------")
        # print(self.settings.molecule_xyz_file)
        if self.settings.molecule_xyz_file is None:
            # print("huhuhh")
            self.signal_handler.load_xyz_file_signal.emit("")

        if self.molecule is None or self.autocas is None or self.interface is None:
            # self.signal_handler.open_molecule_widget_signal.emit()
            self.signal_handler.load_xyz_file_signal.emit(self.settings.molecule_xyz_file)
            self.settings.interface_xyz_file = self.settings.molecule_xyz_file
            self.molecule = Molecule(self.settings.molecule_xyz_file)
            self.autocas = Autocas(self.molecule)
            self.interface = Molcas(self.molecule)
        else:
            pass

    def apply_settings(self):
        self.settings.interface_xyz_file = self.settings.molecule_xyz_file

        # Molecule
        self.autocas.molecule.charge = self.settings.molecule_charge
        self.autocas.molecule.spin_multiplicity = (
            self.settings.molecule_spin_multiplicity
        )
        self.autocas.molecule.double_d_shell = self.settings.molecule_double_d_shell
        # self.autocas.molecule.core_orbitals = self.settings.molecule_core_orbitals
        # self.autocas.molecule.valence_orbitals = self.settings.molecule_valence_orbitals
        # self.autocas.molecule.electrons = self.settings.molecule_electrons
        # self.autocas.molecule.occupation = self.settings.molecule_occupation
        # self.autocas.molecule.xyz_file = self.settings.molecule_xyz_file

        # AutoCAS
        self.autocas.plateau_values = self.settings.plateau_values
        self.autocas.threshold_step = self.settings.threshold_step
        # AutoCAS Diagnostics
        self.autocas.diagnostics.weak_correlation_threshold = (
            self.settings.weak_correlation_threshold
        )
        self.autocas.diagnostics.single_reference_threshold = (
            self.settings.weak_correlation_threshold
        )
        # AutoCAS Large Spaces
        self.autocas.large_spaces.max_orbitals = self.settings.large_spaces_max_orbitals

        # Interface
        self.interface.dump = self.settings.molcas_dump
        self.interface.project_name = self.settings.molcas_project_name

        # Interface Settings
        self.interface.settings.dmrg_bond_dimension = (
            self.settings.interface_dmrg_bond_dimension
        )
        self.interface.settings.dmrg_sweeps = self.settings.interface_dmrg_sweeps
        self.interface.settings.basis_set = self.settings.interface_basis_set
        self.interface.settings.method = self.settings.interface_method
        self.interface.settings.post_cas_method = (
            self.settings.interface_post_cas_method
        )
        self.interface.settings.work_dir = self.settings.molcas_work_dir
        self.interface.settings.xyz_file = self.settings.interface_xyz_file
        self.interface.settings.point_group = self.settings.molcas_point_group
        self.interface.settings.ipea = self.settings.molcas_ipea
        self.interface.settings.cholesky = self.settings.interface_cholesky
        self.interface.settings.uhf = self.settings.interface_uhf
        self.interface.settings.fiedler = self.settings.interface_fiedler
        self.interface.settings.n_excited_states = self.settings.interface_n_excited_states
        # self.interface.settings.spin_multiplicity = (
        #     self.settings.interface_spin_multiplicity
        # )
        # self.interface.settings.charge = self.settings.interface_charge
        # self.interface.settings.only_hf = self.settings.interface_only_hf

        # MOLCAS
        # self.interface.settings.ci_root_string = self.settings.molcas_ci_root_string
        # self.interface.settings.only_hf = self.settings.molcas_only_hf
        # self.interface.settings.orbital_localisation = (
        #     self.settings.molcas_orbital_localisation
        # )
        # self.interface.settings.localisation_space = (
        #     self.settings.molcas_localisation_space
        # )
        # self.interface.settings.localisation_method = (
        #     self.settings.molcas_localisation_method
        # )

        self.interface.orbital_file = self.settings.molcas_orbital_file

    def generate_initial_orbitals(self):
        self.check_settings()
        self.apply_settings()
        self.interface.calculate()

        (
            self.settings.result_initial_occupation,
            self.settings.result_initial_indices,
        ) = self.autocas.make_initial_active_space()
        self.settings.user_occupation = self.settings.result_initial_occupation
        self.settings.user_indices = self.settings.result_initial_indices
        molden_file = self.settings.get_orbital_file()

        self.signal_handler.open_molecule_widget_signal.emit()
        self.signal_handler.load_molden_file_signal.emit(molden_file)

    def run_initial_dmrg(self):
        self.check_settings()
        self.apply_settings()

        # pylint: disable-next=W0612
        (
            self.settings.result_initial_energy,
            self.settings.result_initial_s1,
            initial_s2,
            self.settings.result_initial_mutual_information,
        ) = self.interface.calculate(
            self.settings.user_occupation,
            self.settings.user_indices
        )
        # self.interface.calculate(
        #     self.settings.user_occupation,
        #     self.settings.user_indices
        # )

        self.signal_handler.update_entanglement_plot_signal.emit(
            self.settings.result_initial_s1,
            self.settings.result_initial_mutual_information,
            self.settings.user_indices
        )

        self.signal_handler.open_molecule_widget_signal.emit()
        order = [x + 1 for x in self.settings.user_indices]
        # print(order)
        self.signal_handler.update_entanglement_plot_signal.emit(
            self.settings.result_initial_s1, self.settings.result_initial_mutual_information, order)

        # self.parent().entanglement_diagram.update_plot(
        #    initial_s1, initial_mutual_information, initial_indices
        # )

        self.settings.result_final_occupation, self.settings.result_final_indices = self.autocas.get_active_space(
            self.settings.user_occupation, self.settings.result_initial_s1, force_cas=True
        )
        self.settings.user_occupation = self.settings.result_final_occupation
        self.settings.user_indices = self.settings.result_final_indices

        # self.signal_handler.update_entanglement_plot_signal.emit()

    def run_final_calculation(self):
        pass
