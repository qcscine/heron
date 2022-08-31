#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Tests for the MoleculeLabels.
"""
import pytest
from vtk import vtkMolecule, vtkRenderer, vtkRenderWindow, vtkDoubleArray

from scine_heron.molecule.molecule_labels import MoleculeLabels, LabelGenerator
from scine_heron.settings.settings import LabelsStyle


def test_style_of_generator_can_be_set() -> None:
    """
    Test that the labels generator stores the style.
    """
    generator = LabelGenerator()
    generator.style = LabelsStyle.Symbol

    assert generator.style == LabelsStyle.Symbol


def test_default_style_of_generator_is_empty() -> None:
    """
    If no style is specified, then the generator defaults to Empty.
    """
    generator = LabelGenerator()

    assert generator.style == LabelsStyle.Empty


def test_generates_correct_label_for_empty_style(molecule: vtkMolecule) -> None:
    """
    Returns an empty label when the style is Empty.
    """
    generator = LabelGenerator()

    assert generator.generate_label(molecule, 0) == ""


def test_generates_correct_label_for_empty_style_with_data(
    molecule: vtkMolecule,
) -> None:
    """
    Returns the value when the style is Empty and data is present.
    """
    generator = LabelGenerator()

    array = vtkDoubleArray()
    array.SetNumberOfValues(molecule.GetNumberOfAtoms())
    for i in range(molecule.GetNumberOfAtoms()):
        array.SetValue(i, i)
    array.SetName("scine_labels")
    molecule.GetVertexData().AddArray(array)

    assert generator.generate_label(molecule, 0) == "0.0"
    assert generator.generate_label(molecule, 1) == "1.0"


def test_generates_correct_label_for_symbol_style(molecule: vtkMolecule) -> None:
    """
    Returns corresponding letter when the style is Symbol.
    """
    generator = LabelGenerator()
    generator.style = LabelsStyle.Symbol

    assert generator.generate_label(molecule, 0) == "H"


def test_generates_correct_label_for_atomic_number_style(molecule: vtkMolecule) -> None:
    """
    Returns atomic number when the style is AtomicNumber.
    """
    generator = LabelGenerator()
    generator.style = LabelsStyle.AtomicNumber

    assert generator.generate_label(molecule, 0) == "1"


def test_generates_correct_label_for_index_number_style(molecule: vtkMolecule) -> None:
    """
    Returns index number when the style is IndexNumber.
    """
    generator = LabelGenerator()
    generator.style = LabelsStyle.IndexNumber

    assert generator.generate_label(molecule, 0) == "0"


@pytest.fixture(name="labels")  # type: ignore[misc]
def create_labels(molecule: vtkMolecule) -> MoleculeLabels:
    """
    Creates an instance of MoleculeLabels with style AtomicNumber.
    """
    fixture = MoleculeLabels(style=LabelsStyle.AtomicNumber)
    fixture.set_molecule(molecule)
    return fixture


def render_labels(labels: MoleculeLabels) -> None:
    """
    Renders the provided labels to execute the pipeline.
    """
    renderer = vtkRenderer()
    renderer.AddActor2D(labels.actor)
    window = vtkRenderWindow()
    window.AddRenderer(renderer)
    window.SetOffScreenRendering(True)
    window.Render()


def test_label_is_at_center_of_atom(
    molecule: vtkMolecule, labels: MoleculeLabels
) -> None:
    """
    Test that labels are positioned at the center of an atom.
    """
    atom = molecule.GetAtom(0)
    atom_position = [0.0, 0.0, 0.0]
    atom.GetPosition(atom_position)

    render_labels(labels)
    position = [0.0, 0.0, 0.0]
    labels.actor.GetMapper().GetLabelPosition(0, position)

    assert position == pytest.approx(atom_position)


def test_label_specifies_atomic_number(
    molecule: vtkMolecule, labels: MoleculeLabels
) -> None:
    """
    Test that the label (for style AtomicNumber) specifies the
    atomic number.
    """
    render_labels(labels)

    assert labels.actor.GetMapper().GetLabelText(0) == str(
        molecule.GetAtom(0).GetAtomicNumber()
    )


def test_label_specifies_symbol(labels: MoleculeLabels) -> None:
    """
    Test that the label (for style Symbol) specifies the
    atomic number.
    """
    labels.display_labels_style(LabelsStyle.Symbol)

    render_labels(labels)

    assert labels.actor.GetMapper().GetLabelText(0) == "H"


def test_modifiying_position_moves_label(
    molecule: vtkMolecule, labels: MoleculeLabels
) -> None:
    """
    Test that the label is moved when the atom is moved.
    """
    render_labels(labels)

    modified_position = [1.0, 0.0, 0.0]
    molecule.GetAtom(0).SetPosition(modified_position)
    render_labels(labels)

    position = [0.0, 0.0, 0.0]
    labels.actor.GetMapper().GetLabelPosition(0, position)

    assert position == pytest.approx(modified_position)
