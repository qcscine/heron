#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Tests for the functions in the colorbar module.
"""
import pytest
import vtk
import scine_heron.molecule.colorbar as cb


@pytest.fixture(name="colorbar")  # type: ignore[misc]
def create_colorbar() -> vtk.vtkScalarBarActor:
    """
    Returns a default colorbar.
    """
    return cb.create_colorbar()


def test_colorbar_has_maximum_width_of_50(colorbar: vtk.vtkScalarBarActor) -> None:
    """
    Checks that the maximum width is configured.
    """
    assert colorbar.GetMaximumWidthInPixels() == 50


def test_colorbar_has_nonbold_labels(colorbar: vtk.vtkScalarBarActor) -> None:
    """
    Checks that the label font is configured.
    """
    assert not colorbar.GetLabelTextProperty().GetBold()


def test_colorbar_has_nonitalic_labels(colorbar: vtk.vtkScalarBarActor) -> None:
    """
    Checks that the label font is configured.
    """
    assert not colorbar.GetLabelTextProperty().GetItalic()


def test_colorbar_has_black_labels(colorbar: vtk.vtkScalarBarActor) -> None:
    """
    Checks that the label font is configured.
    """
    assert colorbar.GetLabelTextProperty().GetColor() == (
        pytest.approx(1),
        pytest.approx(1),
        pytest.approx(1),
    )


def test_colorbar_has_no_label_shadows(colorbar: vtk.vtkScalarBarActor) -> None:
    """
    Checks that the label font is configured.
    """
    assert not colorbar.GetLabelTextProperty().GetShadow()


@pytest.fixture(name="transfer_function")  # type: ignore[misc]
def create_transfer_function() -> vtk.vtkColorTransferFunction:
    """
    Returns a color transfer function for the range [-1, 2].
    """
    return cb.create_symmetric_color_transfer_function((-1, 2))


def test_color_white_at_0(transfer_function: vtk.vtkColorTransferFunction) -> None:
    """
    Checks that the color white is used at 0.
    """
    assert transfer_function.GetColor(0.0) == (
        pytest.approx(1, abs=1e-1),
        pytest.approx(1, abs=1e-1),
        pytest.approx(1, abs=1e-1),
    )


def test_value_range_is_correct(
    transfer_function: vtk.vtkColorTransferFunction,
) -> None:
    """
    Checks that value range is the selected one.
    """
    assert transfer_function.GetRange() == (pytest.approx(-1), pytest.approx(2),)


def test_maximum_value_is_assigned_brownish_color(
    transfer_function: vtk.vtkColorTransferFunction,
) -> None:
    """
    Checks that color for the maximum value is correct.
    """
    assert transfer_function.GetColor(2) == (
        pytest.approx(0.3, abs=1e-1),
        pytest.approx(0.2, abs=1e-1),
        pytest.approx(0.0, abs=1e-1),
    )


def test_maximum_value_is_assigned_blueish_color(
    transfer_function: vtk.vtkColorTransferFunction,
) -> None:
    """
    Checks that color for the maximum value is correct.
    """
    assert transfer_function.GetColor(-1) == (
        pytest.approx(0.4, abs=1e-1),
        pytest.approx(0.7, abs=1e-1),
        pytest.approx(0.7, abs=1e-1),
    )


def test_empty_range_at_zero_is_assigned_correct_color() -> None:
    """
    Checks that color for the maximum value is correct.
    """
    function = cb.create_symmetric_color_transfer_function((0, 0))
    assert function.GetColor(0) == (
        pytest.approx(1, abs=1e-1),
        pytest.approx(1, abs=1e-1),
        pytest.approx(1, abs=1e-1),
    )


def test_invalid_range_raises_exception() -> None:
    """
    Checks that invalid ranges are rejected.
    """
    with pytest.raises(AssertionError):
        cb.create_symmetric_color_transfer_function((1, -1))
