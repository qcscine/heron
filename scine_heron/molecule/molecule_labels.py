#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the MoleculeLabels class.
"""

from typing import Any, List, Optional

from vtk import (
    vtkActor2D,
    vtkInformationVector,
    vtkLabeledDataMapper,
    vtkMolecule,
    vtkPeriodicTable,
    vtkPoints,
    vtkPolyData,
    vtkStringArray,
    vtkTrivialProducer,
    vtkSelectVisiblePoints,
    vtkAlgorithm,
)
from vtk.util.vtkAlgorithm import VTKPythonAlgorithmBase

from scine_heron.settings.settings import LabelsStyle


class LabelGenerator:
    """
    Converts atoms to labels based on a given style.
    """

    def __init__(self, style: LabelsStyle = LabelsStyle.Empty):
        self.style = style

    def generate_label(self, molecule: vtkMolecule, atom_index: int) -> str:
        """
        Generates the label for the atom with the given atomic index.
        """
        if self.style == LabelsStyle.Empty:
            array = molecule.GetVertexData().GetArray("scine_labels")
            return "" if array is None else str(array.GetValue(atom_index))

        atom = molecule.GetAtom(atom_index)
        if self.style == LabelsStyle.Symbol:
            return str(vtkPeriodicTable().GetSymbol(atom.GetAtomicNumber()))
        if self.style == LabelsStyle.AtomicNumber:
            return str(atom.GetAtomicNumber())
        if self.style == LabelsStyle.IndexNumber:
            return str(atom_index)

        assert False, "Unknown label style."
        return ""


class MoleculeToLabel(VTKPythonAlgorithmBase):  # type: ignore[misc]
    """
    Convert the input (a vtkMolecule) to the output (a vtkPolyData)
    by transforming each volume to its center and its label.
    """

    def __init__(self, style: LabelsStyle = LabelsStyle.Empty):
        super().__init__(
            nInputPorts=1,
            nOutputPorts=1,
            inputType="vtkMolecule",
            outputType="vtkPolyData",
        )

        self.__generator = LabelGenerator(style)

    def RequestData(
        self,
        _: Any,
        in_info: List[vtkInformationVector],
        out_info: vtkInformationVector,
    ) -> int:
        """
        Performs the transformation.
        """
        molecule = vtkMolecule.GetData(in_info[0])

        number_of_atoms = molecule.GetNumberOfAtoms()

        points = vtkPoints()
        strings = vtkStringArray()
        points.SetNumberOfPoints(number_of_atoms)
        strings.SetNumberOfValues(number_of_atoms)

        for atom_index in range(number_of_atoms):
            atom = molecule.GetAtom(atom_index)
            points.SetPoint(atom_index, atom.GetPosition())
            strings.SetValue(
                atom_index, self.__generator.generate_label(molecule, atom_index)
            )

        data = vtkPolyData.GetData(out_info)
        data.SetPoints(points)
        data.GetPointData().AddArray(strings)

        # return True (as an integer) to signal success
        return 1

    @property
    def style(self) -> LabelsStyle:
        """
        Returns the style of the labels.
        """
        return self.__generator.style

    @style.setter
    def style(self, style: LabelsStyle) -> None:
        """
        Sets the label style and updates the output if necessary.
        """
        if self.__generator.style == style:
            return

        self.__generator.style = style

        # the output of the algorithm needs to be recomputed
        # because different labels will be generated
        self.Modified()


class MoleculeLabels:
    """
    Displays molecule labels in a 3D view.
    """

    def __init__(
        self,
        selector: Optional[vtkSelectVisiblePoints] = None,
        style: LabelsStyle = LabelsStyle.Empty,
    ):
        self.__producer = vtkTrivialProducer()
        self.__labeler = MoleculeToLabel(style)
        mapper = self.__create_mapper()
        self.__connect_pipeline(self.__producer, self.__labeler, selector, mapper)

        self.__actor = self.__create_actor(mapper)

    @staticmethod
    def __create_mapper() -> vtkLabeledDataMapper:
        """
        Creates a mapper that converts strings at points to 2D labels.
        """
        mapper = vtkLabeledDataMapper()
        mapper.SetLabelModeToLabelFieldData()
        mapper.GetLabelTextProperty().SetFontSize(12)
        mapper.GetLabelTextProperty().SetJustificationToCentered()
        mapper.GetLabelTextProperty().SetVerticalJustificationToCentered()

        return mapper

    @staticmethod
    def __create_actor(mapper: vtkLabeledDataMapper) -> vtkActor2D:
        """
        Create 2D actor that displays the atom labels.
        """
        actor = vtkActor2D()
        actor.SetMapper(mapper)

        return actor

    @staticmethod
    def __connect_pipeline(*args: Optional[vtkAlgorithm]) -> None:
        """
        Connects the provided components in a pipeline.
        Ignores None components.
        """
        previous = None
        for arg in args:
            if previous is None:
                previous = arg
                continue

            if arg is None:
                continue

            arg.SetInputConnection(previous.GetOutputPort())
            previous = arg

    @property
    def actor(self) -> vtkActor2D:
        """
        Returns the label actor.
        """
        return self.__actor

    def display_labels_style(self, style: LabelsStyle) -> None:
        """
        Change labels style.
        """
        self.__labeler.style = style

    def set_molecule(self, molecule: vtkMolecule) -> None:
        self.__producer.SetOutput(molecule)
