#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the ElectronicDataWidget class.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from vtk import (
    vtkRenderer,
    vtkActor,
    vtkMarchingCubes,
    vtkPolyDataMapper,
    vtkImageData,
)

from scine_heron.electronic_data.electronic_data_image_generator import (
    ElectronicDataImageGenerator,
)
from scine_heron.electronic_data.electronic_data_status_manager import (
    ElectronicDataStatusManager,
)
from scine_heron.electronic_data.electronic_data import ElectronicData
from scine_heron.electronic_data.molden_file_reader import MoldenFileReader
from scine_heron.settings.settings_status_manager import SettingsStatusManager
from scine_heron.utilities import write_error_message


class ElectronicDataWidget:
    """
    Displays electronic data in a 3D view.
    """

    def __init__(
        self, renderer: vtkRenderer, settings_status_manager: SettingsStatusManager, mol_widget: Any
    ):
        self.electronic_data_status_manager = ElectronicDataStatusManager()
        self.electronic_data_status_manager.molden_input_changed_signal.connect(
            self.read_molden_input
        )
        self.electronic_data_status_manager.hamiltonian_changed.connect(
            self.clear_surfaces_and_data
        )

        self.__renderer = renderer
        self.__mo_plus_actor: vtkActor = None
        self.__mo_minus_actor: vtkActor = None
        self.__pool = ThreadPoolExecutor(2)

        # read electronic data from Molden file
        self.__reader = MoldenFileReader()
        self.__settings_status_manager = settings_status_manager
        self.__electronic_data: Optional[ElectronicData] = None
        self.__data_image_generator: Optional[ElectronicDataImageGenerator] = None
        self.__settings_status_manager.selected_mo_changed.connect(
            self.view_molecular_orbital
        )
        self.__settings_status_manager.hamiltonian_changed.connect(
            self.clear_surfaces_and_data
        )

        self.__mol_widget = mol_widget

    def get_electronic_data(self):
        return self.__electronic_data

    def read_molden_input(self, molden_input: str) -> None:
        self.__clear_isosurface()
        self.__electronic_data = self.__reader.read_molden(molden_input)
        self.__data_image_generator = ElectronicDataImageGenerator(
            self.__electronic_data
        )

        self.__settings_status_manager.number_of_molecular_orbital = len(
            self.__electronic_data.mo
        )

    # Do not use this function if you do not use autocas
    # I was/still am just to stupid to understand this
    # Will fix it in the future
    def view_orbital(self, mo_index):
        if self.__data_image_generator is None and mo_index == 0:
            return
        if self.__data_image_generator is not None:
            self.__settings_status_manager.selected_molecular_orbital = mo_index

    def view_molecular_orbital(self, molecular_orbital_index: int) -> None:
        if self.__data_image_generator is None and molecular_orbital_index == 0:
            return
        if molecular_orbital_index == 0:
            # reset MO data
            self.clear_surfaces_and_data()
        else:
            if self.__data_image_generator is None:
                result = self.__mol_widget.single_point_calculation()
                if not result:
                    return
                if not result.molden_input:
                    write_error_message("Chosen calculator does not support MO output")
                    return
                self.read_molden_input(result.molden_input)
            self.__clear_isosurface()
            if molecular_orbital_index == -1:  # HOMO
                self.__settings_status_manager.selected_molecular_orbital = self.__get_actual_index(
                    molecular_orbital_index
                )
                # we update to actual value and return to ensure that we have the actual number in the GUI
                return
            elif molecular_orbital_index == -2:  # LUMO
                # we update to actual value and return to ensure that we have the actual number in the GUI
                self.__settings_status_manager.selected_molecular_orbital = self.__get_actual_index(
                    molecular_orbital_index
                )
                return
            elif molecular_orbital_index == -3:
                msg = "The electron density is being calculated ..."
            else:
                msg = (
                    "The molecular orbital number "
                    + str(molecular_orbital_index)
                    + " is being calculated ..."
                )
            if self.__data_image_generator is not None:
                self.__settings_status_manager.info_message = msg
                future = self.__pool.submit(
                    self.__data_image_generator.generate_mo_image,
                    molecular_orbital_index - 1,
                )
                future.add_done_callback(self.__show_mo)

    def __get_actual_index(self, orbital_index: int) -> int:
        if self.__electronic_data is None:
            raise RuntimeError("Electronic Data has not been setup properly")
        i = 0
        while self.__electronic_data.mo[i].occupation >= 1.0:
            i += 1
        return i if orbital_index == -1 else i + 1

    def __show_mo(self, calculation_result) -> None:
        """
        Show molecular orbital with index "molecular_orbital_index" as an isosurface
        """
        if not self.__settings_status_manager.selected_molecular_orbital:
            return
        image = calculation_result.result()
        self.__create_isosurface(
            image, self.__settings_status_manager.molecular_orbital_value
        )
        self.__create_isosurface(
            image, -self.__settings_status_manager.molecular_orbital_value
        )
        self.__renderer.GetRenderWindow().Render()
        self.__settings_status_manager.info_message = (
            "The molecular orbital has been calculated."
        )
        return

    def __create_actor(
        self, mapper: vtkPolyDataMapper, value: float = 0.05
    ) -> vtkActor:
        """
        Create actor and set colors and opacity for it.
        """
        actor = vtkActor()
        actor.GetProperty().SetOpacity(0.5)
        actor_property = actor.GetProperty()

        # TODO dynamic style sheet colors
        if value < 0:
            actor_property.SetColor(1, 0.2, 0.2)  # red
        elif value > 0:
            actor_property.SetColor(0.2, 0.2, 1)  # blue

        actor.SetMapper(mapper)

        return actor

    def __create_isosurface(self, image: vtkImageData, value: float) -> None:
        iso_sphere = vtkMarchingCubes()
        iso_sphere.SetInputData(image)
        iso_sphere.ComputeNormalsOn()
        iso_sphere.GenerateValues(1, value, value)
        iso_sphere.Update()

        # Create a mapper and actor
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(iso_sphere.GetOutputPort())
        mapper.ScalarVisibilityOff()
        if value > 0:
            if self.__mo_plus_actor is not None:
                self.__renderer.RemoveActor(self.__mo_plus_actor)

            self.__mo_plus_actor = self.__create_actor(mapper, value)
            self.__renderer.AddActor(self.__mo_plus_actor)
        else:
            if self.__mo_minus_actor is not None:
                self.__renderer.RemoveActor(self.__mo_minus_actor)

            self.__mo_minus_actor = self.__create_actor(mapper, value)
            self.__renderer.AddActor(self.__mo_minus_actor)

    def __clear_isosurface(self) -> None:
        self.__renderer.RemoveActor(self.__mo_plus_actor)
        self.__renderer.RemoveActor(self.__mo_minus_actor)

        self.__mo_plus_actor = None
        self.__mo_minus_actor = None

        self.__renderer.GetRenderWindow().Render()

    def clear_surfaces_and_data(self) -> None:
        self.__electronic_data = None
        self.__data_image_generator = None
        self.__clear_isosurface()
