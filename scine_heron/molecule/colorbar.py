#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Functions to create and work with colorbars.
"""

import vtk
import typing
import sys


def create_symmetric_color_transfer_function(
    value_range: typing.Tuple[float, float]
) -> vtk.vtkColorTransferFunction:
    """
    Creates a default symmetric vtkColorTransferFunction with the given range.
    In particular, the color white is used for the value 0.
    """
    assert value_range[0] <= value_range[1]

    series = vtk.vtkColorSeries()
    series.SetColorScheme(vtk.vtkColorSeries.BREWER_DIVERGING_BROWN_BLUE_GREEN_11)

    # The colors need to be converted from range [0, 255] to range [0, 1].
    colors = [
        (x / 255 for x in series.GetColor(i)) for i in range(series.GetNumberOfColors())
    ]

    # Spread points evenly over [-m, m], where m = max(|x| for x in value_range)
    # (note that this means that the 5th color (white) is assigned to 0).
    #
    # In case the values are (almost) zero, we use a range of [-eps, eps] to avoid
    # identical points.
    absolute_max = max(max(abs(x) for x in value_range), sys.float_info.epsilon)
    points = [
        (2 * i / (len(colors) - 1) - 1) * absolute_max for i in range(len(colors))
    ]

    function = vtk.vtkColorTransferFunction()

    # Reverse colors to assign blue to negative numbers.
    for point, color in zip(points, reversed(colors)):
        function.AddRGBPoint(point, *color)

    # The colorbar only needs to show used colors.
    function.AdjustRange(value_range)

    return function


def create_colorbar() -> vtk.vtkScalarBarActor:
    """
    Creates a default color bar with default colors.
    """
    colorbar = vtk.vtkScalarBarActor()
    colorbar.SetMaximumWidthInPixels(50)
    colorbar.GetLabelTextProperty().SetBold(False)
    colorbar.GetLabelTextProperty().SetItalic(False)

    from scine_heron.utilities import qcolor_by_key
    color = qcolor_by_key('primaryTextColor')
    colorbar.GetLabelTextProperty().SetColor(color.getRgbF()[0], color.getRgbF()[1], color.getRgbF()[2])

    colorbar.GetLabelTextProperty().ShadowOff()
    return colorbar
