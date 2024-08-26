#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional, List

from PySide2.QtWidgets import QGridLayout, QWidget, QTabWidget

from scine_heron.autocas.autocas_controller import AutocasController
from scine_heron.autocas.autocas_settings import AutocasSettings
from scine_heron.autocas.autocas_wrapper import AutocasWrapper
from scine_heron.autocas.file_tree_widget import FileTreeWidget
from scine_heron.autocas.options import OptionsWidget
from scine_heron.autocas.output_widget import OutputWidget
from scine_heron.autocas.signal_handler import SignalHandler
#  from scine_heron.autocas.toolbar_widget import ToolbarWidget
from scine_heron.autocas.autocas_project_widget import AutocasProjectWidget
from scine_heron.electronic_data.orbital_groups import OrbitalGroupMap
from scine_heron.electronic_data.orbital_group_file_reader import OrbitalGroupFileReader


class AutocasWidget(QWidget):
    def __init__(self, parent: QWidget) -> None:
        QWidget.__init__(self, parent)
        self.__all_projects: List[AutocasProjectWidget] = []
        self.project_tabs = QTabWidget()
        self.__add_project_tab()
        self.autocas_settings = self.__singular_project().autocas_settings
        self.signal_handler = self.__singular_project().signal_handler
        # toolbar
        # self.tool_bar = ToolbarWidget(self, self.signal_handler, self.autocas_settings)
        # expandable file tree
        self.file_tree = FileTreeWidget(
            self, self.signal_handler, self.autocas_settings
        )

        # shows stdout
        self.output = OutputWidget(self)
        # handles all autocas options
        self.options = OptionsWidget(self, self.signal_handler, self.autocas_settings)
        # handles autocas runs
        self.autocas_controler = AutocasController(self, self.signal_handler)
        # autocas instance
        self.autocas = AutocasWrapper(self.autocas_settings, self.signal_handler)

        # set layout
        self.__layout = QGridLayout()
        # from  height, width -> to height, width
        # self.__layout.addWidget(self.tool_bar, 0, 0)
        self.__layout.addWidget(self.file_tree, 1, 0, 2, 1)
        self.__layout.addWidget(self.project_tabs, 1, 1, 1, 3)
        # self.__layout.addWidget(self.result, 1, 1)  # , 2, 2)
        self.__layout.addWidget(self.output, 2, 1)  # , 3, 3)
        # self.__layout.addWidget(self.mo_diagram, 1, 3)  # , 2, 4)
        self.__layout.addWidget(self.autocas_controler, 2, 3)
        # self.file_tree.setMaximumWidth(int(self.tool_bar.width() * 0.55))
        self.setLayout(self.__layout)

        self.signal_handler.load_orbital_groups_file_signal.connect(self.__load_orbital_groups_file)
        self.__orbital_map: Optional[OrbitalGroupMap] = None

    def __singular_project(self):
        assert self.__all_projects
        return self.__all_projects[0]

    def __add_project_tab(self):
        n_projects = len(self.__all_projects)
        signal_handler = SignalHandler(self)
        autocas_settings = AutocasSettings()
        label = "Project " + str(n_projects)
        project_tab = AutocasProjectWidget(self, signal_handler, autocas_settings, label)
        self.project_tabs.addTab(project_tab, label)
        self.__all_projects.append(project_tab)

    def __load_all_xyz_files(self):
        for project in self.__all_projects:
            # print(project.autocas_settings.molecule_xyz_file)
            project.signal_handler.load_xyz_file_signal.emit(project.autocas_settings.molecule_xyz_file)

    def __load_all_orbital_files(self):
        for project in self.__all_projects:
            project.signal_handler.load_molden_file_signal.emit(project.autocas_settings.molcas_orbital_file)

    def __add_orbital_map_to_settings(self):
        for i, project in enumerate(self.__all_projects):
            project.autocas_settings.orbital_index_sets = self.__orbital_map.get_index_sets_for_system(i)

    def __load_orbital_groups_file(self, file_name: str):
        self.__orbital_map = OrbitalGroupFileReader.read_orbital_group_file(file_name)
        assert self.__orbital_map
        for _ in range(self.__orbital_map.get_n_systems() - 1):
            self.__add_project_tab()
        self.__add_orbital_map_to_settings()
        self.__load_all_xyz_files()
        self.__load_all_orbital_files()
