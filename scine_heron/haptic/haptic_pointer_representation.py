#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from vtk import (
    vtkPolyData,
    vtkAlgorithm,
    vtkSphereSource,
    vtkPolyDataMapper,
    vtkActor,
    vtkInformationVector,
)
from vtk.util.vtkAlgorithm import VTKPythonAlgorithmBase
from scine_heron.haptic.haptic_pointer_data import HapticPointerData

from typing import Any, List


class PointToSphereAlgorithm(VTKPythonAlgorithmBase):  # type: ignore[misc]
    """
    vtkAlgorithm that can be used to convert the haptic pointer
    to a sphere source.
    """

    def __init__(self) -> None:
        super().__init__(
            nInputPorts=1,
            nOutputPorts=1,
            inputType=["vtkPolyData"],
            outputType="vtkPolyData",
        )

    def FillInputPortInformation(self, port: int, info: Any) -> int:
        """Sets the required input type to InputType."""
        info.Set(vtkAlgorithm.INPUT_REQUIRED_DATA_TYPE(), self.InputType[port])
        return 1

    def RequestData(
        self,
        _: Any,
        in_info: List[vtkInformationVector],
        out_info: vtkInformationVector,
    ) -> int:
        """
        Performs the transformation
        """
        in_position = vtkPolyData.GetData(in_info[0]).GetPoints().GetPoint(0)

        out_sphere = vtkPolyData.GetData(out_info)

        sphere = vtkSphereSource()
        sphere.SetCenter(*in_position)
        sphere.SetRadius(0.25)
        sphere.SetPhiResolution(25)
        sphere.SetThetaResolution(25)
        sphere.Update()
        out_sphere.DeepCopy(sphere.GetOutput())

        return 1


class HapticPointerRepresentation:
    def __init__(self, haptic_pointer_data: HapticPointerData) -> None:
        self._haptic_pointer_data = haptic_pointer_data
        self._haptic_pointer_source = PointToSphereAlgorithm()
        self._haptic_pointer_mapper = vtkPolyDataMapper()
        self._haptic_pointer_actor = vtkActor()

        # connecting everything
        self._haptic_pointer_source.SetInputConnection(haptic_pointer_data.output)
        self._haptic_pointer_mapper.SetInputConnection(
            self._haptic_pointer_source.GetOutputPort()
        )
        self._haptic_pointer_actor.SetMapper(self._haptic_pointer_mapper)
        self._haptic_pointer_actor.GetProperty().SetColor(0, 0.75, 0.75)

    @property
    def actor(self) -> vtkActor:
        return self._haptic_pointer_actor

    def update_pointer_position(self, pos: Any) -> None:
        self._haptic_pointer_data.update_pointer_position(pos)

    @property
    def source(self) -> vtkSphereSource:
        return self._haptic_pointer_source
