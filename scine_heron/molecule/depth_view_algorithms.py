#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides a number of vtkAlgorithms and their wrappers
that can be used in MoleculeDepthView classes.
"""

from typing import List, Tuple, Any
from vtk import (
    vtkMolecule,
    vtkArrayData,
    vtkTrivialProducer,
    vtkArray,
    VTK_FLOAT,
    vtkActor,
    vtkInformationVector,
    vtkAlgorithmOutput,
)
import numpy as np

from vtk.util.vtkAlgorithm import VTKPythonAlgorithmBase, vtkAlgorithm
from vtkmodules.vtkCommonDataModel import vtkPolyData


class DepthProjectionAlgorithm(VTKPythonAlgorithmBase):  # type: ignore[misc]
    """
    Takes a molecule and projects every atom to the line of sight
    of a camera.
    The center of the view is the haptic pointer.
    The atoms in the visible are selected
    based on the distance from the haptic pointer.
    The z-movement of the atoms is not uniform,
    but it is magnified close to the haptic pointer.
    """

    def __init__(self, filter_radius: float, zscale: float) -> None:
        super().__init__(
            nInputPorts=3,
            nOutputPorts=1,
            inputType=[
                "vtkPolyData",  # The position of the haptic pointer
                "vtkMolecule",  # The molecule
                "vtkArrayData",  # The camera information - depth vector
            ],
            outputType="vtkMolecule",
        )
        self.filter_radius = filter_radius
        self.zscale = zscale

    def FillInputPortInformation(self, port: int, info: Any) -> int:
        """Sets the required input type to InputType."""
        info.Set(vtkAlgorithm.INPUT_REQUIRED_DATA_TYPE(), self.InputType[port])
        return 1

    def _core_algorithm(
        self,
        haptic_position_data: vtkPolyData,
        in_molecule: vtkMolecule,
        camera_data: vtkArrayData,
        out_molecule: vtkMolecule,
    ) -> None:
        """
        An easier-to-test method that uses typed data.
        """
        # CAMERA_ARRAYS: order must match (see other CAMERA_ARRAYS label)
        depth_vector = camera_data.GetArray(0)

        # Preparing data
        haptic_position = np.array([*haptic_position_data.GetPoints().GetPoint(0)])
        depth_vector = np.array([depth_vector.GetValue(i) for i in range(3)])

        atom_positions = np.array(
            [
                in_molecule.GetAtom(i).GetPosition()
                for i in range(in_molecule.GetNumberOfAtoms())
            ]
        )

        if in_molecule.GetNumberOfAtoms() > 0:
            depths_absolute = atom_positions @ depth_vector
            depths = depths_absolute - haptic_position @ depth_vector

            position_wrt_haptic = atom_positions - haptic_position
            dist_from_haptic_sq = (position_wrt_haptic ** 2).sum(axis=1)
            plot_condition = dist_from_haptic_sq < self.filter_radius ** 2

            depths_remapped = self.depthremap(depths)
            for i in range(in_molecule.GetNumberOfAtoms()):
                if plot_condition[i]:
                    new_atom = out_molecule.AppendAtom()

                    atom = in_molecule.GetAtom(i)
                    new_atom.SetAtomicNumber(atom.GetAtomicNumber())
                    new_atom.SetPosition((0, 0, depths_remapped[i]))

    def RequestData(
        self,
        _: Any,
        in_info: List[vtkInformationVector],
        out_info: vtkInformationVector,
    ) -> int:
        """
        Performs the transformation
        """
        haptic_position = vtkPolyData.GetData(in_info[0])
        in_molecule = vtkMolecule.GetData(in_info[1])

        camera_data = vtkArrayData.GetData(in_info[2])
        out_molecule = vtkMolecule.GetData(out_info)

        self._core_algorithm(haptic_position, in_molecule, camera_data, out_molecule)

        # return True (as an integer) to signal success
        return 1

    def depthremap(self, z: np.array) -> np.array:
        return self.zscale * (2.0 / (1 + np.exp(-2 * z / self.zscale)) - 1.0)


class DepthProjection:
    def __init__(self, filter_range: float, zscale: float) -> None:
        """
        haptic pointer -----------------------------,
        molecule -> producer ------------------------> MoleculeDepthProjectionAlgorithm -> output
        cameradata -> (focus_position, -> producer /
                       depth_vector)
        """
        # Haptic pointer data is hooked directly to the algorithm.

        # Molecule
        self.__producer = vtkTrivialProducer()

        # Camera Data
        self.__depth_vector = vtkArray.CreateArray(vtkArray.DENSE, VTK_FLOAT)
        self.__depth_vector.Resize(3)

        self.__camera_data = vtkArrayData()
        self.__camera_data_producer = vtkTrivialProducer()

        self.__depth_projector = DepthProjectionAlgorithm(filter_range, zscale)
        # connecting all together
        # molecule not yet!

        # camera data
        # CAMERA_ARRAYS: order must match (see other CAMERA_ARRAYS label)
        self.__camera_data.AddArray(self.__depth_vector)

        self.__camera_data_producer.SetOutput(self.__camera_data)
        # Algorithm
        self.__depth_projector.SetInputConnection(1, self.__producer.GetOutputPort())
        self.__depth_projector.SetInputConnection(
            2, self.__camera_data_producer.GetOutputPort()
        )

    @property
    def output(self) -> vtkActor:
        return self.__depth_projector.GetOutputPort()

    def set_molecule(self, molecule: vtkMolecule) -> None:
        """
        Setting a vtkMolecule as input,
        using the internale vtkTrivialProducer.
        """
        self.__producer.SetOutput(molecule)
        self.__depth_projector.SetInputConnection(1, self.__producer.GetOutputPort())

    def set_molecule_input(self, output_port: vtkAlgorithmOutput) -> None:
        """
        Setting directly the input connection
        for the molecule input port
        of the depth projection algorithm.
        """
        self.__depth_projector.SetInputConnection(1, output_port)

    def set_haptic_pointer_data(self, output_port: vtkAlgorithmOutput) -> None:
        """
        Setting directly the input connection
        for the haptic pointer data input port
        of the depth projection algorithm.
        """
        self.__depth_projector.SetInputConnection(0, output_port)

    def set_camera_data(self, depth_vector: Tuple[float, float, float],) -> None:

        for i in range(3):
            self.__depth_vector.SetValue(i, depth_vector[i])
        self.__camera_data.Modified()
