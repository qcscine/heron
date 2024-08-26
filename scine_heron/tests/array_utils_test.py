#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Tests for functions in the array_utils module.
"""

from typing import Generator

import vtk
import pytest

from scine_heron.molecule.utils.array_utils import rescale_to_range, iterable_to_vtk_array


@pytest.fixture(name="array")  # type: ignore[misc]
def create_array() -> vtk.vtkDoubleArray:
    """
    Returns the array [-1, 0, 1].
    """
    array = vtk.vtkDoubleArray()
    array.SetNumberOfValues(3)
    array.InsertValue(0, -1)
    array.InsertValue(1, 0)
    array.InsertValue(2, 1)
    return array


class TestRescaleToRange:
    """
    Tests for the function rescale_to_range.
    """

    def test_increasing_span_works(self, array: vtk.vtkDoubleArray) -> None:
        """
        The array [-1, 0, 1] is scaled to [-2, 0, 2].
        """
        result = rescale_to_range(array, (-2, 2))

        assert result.GetValue(0) == pytest.approx(-2)
        assert result.GetValue(1) == pytest.approx(0)
        assert result.GetValue(2) == pytest.approx(2)

    def test_shifting_array_works(self, array: vtk.vtkDoubleArray) -> None:
        """
        The array [-1, 0, 1] is moved to [-2, -1, 0].
        """
        result = rescale_to_range(array, (-2, 0))

        assert result.GetValue(0) == pytest.approx(-2)
        assert result.GetValue(1) == pytest.approx(-1)
        assert result.GetValue(2) == pytest.approx(0)

    def test_invalid_range_yields_exception(self, array: vtk.vtkDoubleArray) -> None:
        """
        The array [-1, 0, 1] cannot be scaled to [1, 0].
        """
        with pytest.raises(AssertionError):
            rescale_to_range(array, (1, 0))

    def test_arrays_of_zero_span_at_1_are_moved_to_center(
        self, array: vtk.vtkDoubleArray,
    ) -> None:
        """
        The array [1, 1, 1] is moved to [-1, -1, -1].
        """
        array.InsertValue(0, 1)
        array.InsertValue(1, 1)
        array.InsertValue(2, 1)

        result = rescale_to_range(array, (-2, 0))

        assert result.GetValue(0) == pytest.approx(-1)
        assert result.GetValue(1) == pytest.approx(-1)
        assert result.GetValue(2) == pytest.approx(-1)

    def test_arrays_of_zero_span_at_zero_are_moved_to_center(
        self, array: vtk.vtkDoubleArray,
    ) -> None:
        """
        The array [0, 0, 0] is moved to [-1, -1, -1].
        """
        array.InsertValue(0, 0)
        array.InsertValue(1, 0)
        array.InsertValue(2, 0)

        result = rescale_to_range(array, (-2, 0))

        assert result.GetValue(0) == pytest.approx(-1)
        assert result.GetValue(1) == pytest.approx(-1)
        assert result.GetValue(2) == pytest.approx(-1)

    def test_arrays_of_zero_span_at_1e32_are_moved_to_center(
        self, array: vtk.vtkDoubleArray,
    ) -> None:
        """
        The array [1e32, 1e32, 1e32] is moved to [-1, -1, -1].
        """
        array.InsertValue(0, 1e32)
        array.InsertValue(1, 1e32)
        array.InsertValue(2, 1e32)

        result = rescale_to_range(array, (-2, 0))

        assert result.GetValue(0) == pytest.approx(-1)
        assert result.GetValue(1) == pytest.approx(-1)
        assert result.GetValue(2) == pytest.approx(-1)


class TestIterableToVtkArray:
    """
    Tests for the function iterable_to_vtk_array.
    """

    def test_empty_iterable_yields_empty_array(self) -> None:
        """
        An empty list is converted to an empty array.
        """
        result = iterable_to_vtk_array([], 0)

        assert result.GetNumberOfValues() == 0

    def test_all_values_are_copied_to_array(self) -> None:
        """
        An non-empty list is converted to a corresponding array.
        """
        result = iterable_to_vtk_array([1.0, 3.0], 2)

        assert result.GetNumberOfValues() == 2
        assert result.GetValue(0) == 1.0
        assert result.GetValue(1) == 3.0

    def test_generators_can_be_converted_to_arrays(self) -> None:
        """
        All values produced by a generator are copied into the array.
        """

        def generator() -> Generator[float, None, None]:
            """
            Generates the values 0, 1, 2.
            """
            for i in range(3):
                yield float(i)

        result = iterable_to_vtk_array(generator(), 3)

        assert result.GetNumberOfValues() == 3
        assert result.GetValue(0) == 0.0
        assert result.GetValue(1) == 1.0
        assert result.GetValue(2) == 2.0

    def test_only_returns_provided_number_of_elements(self) -> None:
        """
        Only the provided number of elements are copied to the array.
        """
        result = iterable_to_vtk_array([1.0, 2.0], 1)

        assert result.GetNumberOfValues() == 1
        assert result.GetValue(0) == 1.0

    def test_fills_missing_numbers_with_default(self) -> None:
        """
        If the iterable contains fewer elements than expected, then
        the rest of the elements in the array are filled with
        the default_value.
        """
        default_value = 0.7
        result = iterable_to_vtk_array([1.0], 2, default_value=default_value)

        assert result.GetNumberOfValues() == 2
        assert result.GetValue(0) == 1.0
        assert result.GetValue(1) == default_value
