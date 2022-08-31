#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from typing import List, Any

from vtk import (
    vtkMolecule,
    vtkArrayData,
    vtkMoleculeMapper,
    vtkTrivialProducer,
    vtkArray,
    VTK_INT,
    vtkActor,
    vtkInformationVector,
)

from vtk.util.vtkAlgorithm import VTKPythonAlgorithmBase, vtkAlgorithm


class NonEmptyMoleculeError(Exception):
    pass


class AtomSelectionAlgorithm(VTKPythonAlgorithmBase):  # type: ignore[misc]
    """
    Creates a "ghost" molecule
    out of a selection of atoms in the original molecule
    """

    def __init__(self) -> None:
        super().__init__(
            nInputPorts=2,
            nOutputPorts=1,
            inputType=["vtkMolecule", "vtkArrayData"],
            outputType="vtkMolecule",
        )
        self.selected_atom_id = None

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

        base_molecule = vtkMolecule.GetData(in_info[0])
        selection_indices_data = vtkArrayData.GetData(in_info[1])
        selection_indices = selection_indices_data.GetArray(0)
        selection = [
            selection_indices.GetValue(i)
            for i in range(
                selection_indices.GetExtent(0).GetBegin(),
                selection_indices.GetExtent(0).GetEnd(),
            )
        ]

        out_molecule = vtkMolecule.GetData(out_info)

        self.filter_molecule(base_molecule, selection, out_molecule)

        # return True (as an integer) to signal success
        return 1

    @staticmethod
    def filter_molecule(
        base_molecule: vtkMolecule, selection: List[int], out_molecule: vtkMolecule
    ) -> None:
        """
        Modifies the out_molecule in place,
        """
        if out_molecule.GetNumberOfAtoms() > 0:
            raise NonEmptyMoleculeError()

        max_atomic_number = max(
            (
                base_molecule.GetAtom(i).GetAtomicNumber()
                for i in range(base_molecule.GetNumberOfAtoms())
            ),
            default=1,
        )

        for atom_index in selection:
            atom = base_molecule.GetAtom(atom_index)
            new_atom = out_molecule.AppendAtom()

            # The radii of displayed atoms may be modified when values
            # are displayed via the radii. To make sure that selection
            # is visible we use the maximum atomic number for selection.
            new_atom.SetAtomicNumber(max_atomic_number)
            new_atom.SetPosition(atom.GetPosition())


class AtomSelection:
    def __init__(self) -> None:
        """
        The `atom_selector` algorithm has two inputs,
        given by two producers:
        - the molecule
        - the selection

        Pipeline Scheme:

        molecule -> producer ------------------------------> atom_selector -> mapper -> actor
        selection -> selection_data -> selection_producer/
        """

        # Molecule
        self.__producer = vtkTrivialProducer()
        self.__selection_producer = vtkTrivialProducer()

        # Atom selector
        self.__atom_selector = AtomSelectionAlgorithm()
        self.__selection = vtkArray.CreateArray(vtkArray.DENSE, VTK_INT)
        self.__selection.Resize(0)
        self.__selection_data = vtkArrayData()

        # Mapper
        self.__mapper = vtkMoleculeMapper()
        self.__mapper.CreateDefaultLookupTable()
        self.__mapper.SetAtomColorMode(vtkMoleculeMapper.SingleColor)
        self.__mapper.SetAtomicRadiusScaleFactor(0.35)  # default is 0.3

        # Actor
        self.__actor = vtkActor()

        # connecting all together
        self.__selection_data.AddArray(self.__selection)
        self.__selection_producer.SetOutput(self.__selection_data)
        self.__atom_selector.SetInputConnection(0, self.__producer.GetOutputPort())
        self.__atom_selector.SetInputConnection(
            1, self.__selection_producer.GetOutputPort()
        )

        self.__mapper.SetInputConnection(self.__atom_selector.GetOutputPort())
        self.__actor.SetMapper(self.__mapper)
        self.__actor.GetProperty().SetOpacity(0.5)
        self.__actor.GetProperty().SetColor(0.5, 0.5, 0.5)

    @property
    def actor(self) -> vtkActor:
        """
        Returns the label actor.
        """
        return self.__actor

    def set_molecule(self, molecule: vtkTrivialProducer) -> None:
        self.__producer.SetOutput(molecule)
        self.set_selection([])

    def set_selection(self, selection: List[int]) -> None:
        self.__selection.Resize(len(selection))
        for i, n in enumerate(selection):
            self.__selection.SetValue(i, n)
        self.__selection_data.Modified()

    def __len__(self):
        return self.__selection.GetSize()
