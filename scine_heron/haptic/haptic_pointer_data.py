#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the HapticPointer class.
"""
from typing import Any

from vtk import (
    vtkTrivialProducer,
    vtkAlgorithmOutput,
)
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkPolyData


class HapticPointerData:
    """
    Displays haptic pointer in a 3D view.
    """

    def __init__(self) -> None:

        # Center only
        self.__center = vtkPoints()
        self.__center.InsertPoint(0, 0.0, 0.0, 0.0)
        self.__center_data = vtkPolyData()
        self.__center_data.SetPoints(self.__center)
        self.__center_data_producer = vtkTrivialProducer()
        self.__center_data_producer.SetOutput(self.__center_data)

    @property
    def position(self) -> Any:
        return self.__center.GetPoint(0)

    @property
    def output(self) -> vtkAlgorithmOutput:
        return self.__center_data_producer.GetOutputPort()

    def get_center_data(self) -> Any:
        return self.__center_data

    def update_pointer_position(self, pos: Any) -> None:
        """
        Update pointer position.
        """
        self.__center.InsertPoint(0, pos.x, pos.y, pos.z)
        self.__center_data_producer.Modified()
