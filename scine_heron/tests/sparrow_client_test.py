#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Testing of SparrowClient.
"""

import unittest
from numpy.testing import assert_array_almost_equal

import numpy as np
import scine_utilities as su

from scine_heron.calculators.calculator import ScineCalculatorWrapper
from scine_heron.tests.mocks.settings import CalculatorSettings


class TestSparrowClient(unittest.TestCase):

    def test_calculate_gradients(self) -> None:
        """
        Check that calculate_gradients calculates the correct gradient for vtkMolecule.
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()

        client = ScineCalculatorWrapper(
            settings.method,
            "sparrow",
            True,
            settings.__dict__,
            su.AtomCollection(
                elements,
                pos))
        result = client.calculate_custom_result()

        assert result.energy is not None
        assert result.atomic_charges is not None
        assert result.gradients is not None

        self.assertAlmostEqual(result.energy, -0.8782779599166628, delta=1e-6)
        assert_array_almost_equal(result.gradients, [
            [-0.15099689, 0.0, 0.0],
            [0.15099689, 0.0, 0.0],
        ], decimal=6)
        assert_array_almost_equal(result.atomic_charges, [2.220446049250313e-16, 2.220446049250313e-16], decimal=6)

        assert result.hessian is not None
        ref_hessian = [
            [0.05022484, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.05707437, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.05707437, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.05022484, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.05707437, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.05707437],
        ]
        assert_array_almost_equal(result.hessian, ref_hessian, decimal=4)

        well_center = result.positions
        assert well_center is not None
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[0], pos[0])])
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[1], pos[1])])

    def test_calculate_custom_result_with_mndo(self) -> None:
        """
        Check that calculate_custom_result using "MNDO" calc_method calculates the correct gradient.
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()
        settings.method = "MNDO"

        client = ScineCalculatorWrapper(settings.method, "sparrow", True, settings.__dict__,
                                        su.AtomCollection(elements, pos))
        result = client.calculate_custom_result()

        assert result.energy is not None
        assert result.atomic_charges is not None
        assert result.gradients is not None

        self.assertAlmostEqual(result.energy, -0.9010157296470183, delta=1e-6)
        assert_array_almost_equal(result.gradients, [
            [-0.11476439, 0.0, 0.0],
            [0.11476439, 0.0, 0.0],
        ], decimal=6)
        assert_array_almost_equal(result.atomic_charges, [
                                  2.220446049250313e-16, -2.220446049250313e-16], decimal=6)

        assert result.hessian is not None
        ref_hessian = [
            [0.03935188, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.04337907, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.04337907, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.03935188, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.04337907, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.04337907],
        ]
        assert_array_almost_equal(result.hessian, ref_hessian, decimal=4)

        well_center = result.positions
        assert well_center is not None
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[0], pos[0])])
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[1], pos[1])])

    def test_calculate_custom_result_with_am1(self) -> None:
        """
        Check that calculate_custom_result using "AM1" calc_method calculates the correct gradient.
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()
        settings.method = "AM1"

        client = ScineCalculatorWrapper(settings.method, "sparrow", True, settings.__dict__,
                                        su.AtomCollection(elements, pos))
        result = client.calculate_custom_result()

        assert result.energy is not None
        assert result.atomic_charges is not None
        assert result.gradients is not None
        if result.energy is not None:
            self.assertAlmostEqual(result.energy, -0.879196405474689, delta=1e-6)
        assert_array_almost_equal(result.gradients, [
            [-0.10885832, 0.0, 0.0],
            [0.10885832, 0.0, 0.0],
        ], decimal=6)
        assert_array_almost_equal(result.atomic_charges, [
                                  2.220446049250313e-16, -2.220446049250313e-16], decimal=6)

        assert result.hessian is not None
        ref_hessian = [
            [0.03432682, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.04114667, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.04114667, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.03432682, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.04114667, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.04114667],
        ]
        assert_array_almost_equal(result.hessian, ref_hessian, decimal=4)

        well_center = result.positions
        assert well_center is not None
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[0], pos[0])])
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[1], pos[1])])

    def test_calculate_custom_result_with_rm1(self) -> None:
        """
        Check that calculate_custom_result using "RM1" calc_method calculates the correct gradient.
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()
        settings.method = "RM1"

        client = ScineCalculatorWrapper(
            settings.method,
            "sparrow",
            True,
            settings.__dict__,
            su.AtomCollection(
                elements,
                pos))
        result = client.calculate_custom_result()

        assert result.energy is not None
        assert result.atomic_charges is not None
        assert result.gradients is not None
        if result.energy is not None:
            self.assertAlmostEqual(result.energy, -0.922618885532389, delta=1e-6)
        assert_array_almost_equal(result.gradients, [
            [-0.1124197, 0.0, 0.0],
            [0.1124197, 0.0, 0.0],
        ], decimal=6)
        assert_array_almost_equal(result.atomic_charges, [2.220446049250313e-16, 2.220446049250313e-16], decimal=6)

        assert result.hessian is not None
        ref_hessian = [
            [0.01911018, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.04249282, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.04249282, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.01911018, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.04249282, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.04249282],
        ]
        assert_array_almost_equal(result.hessian, ref_hessian, decimal=4)

        well_center = result.positions
        assert well_center is not None
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[0], pos[0])])
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[1], pos[1])])

    def test_calculate_custom_result_with_pm3(self) -> None:
        """
        Check that calculate_custom_result using "PM3" calc_method calculates the correct gradient.
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()
        settings.method = "PM3"

        client = ScineCalculatorWrapper(
            settings.method,
            "sparrow",
            True,
            settings.__dict__,
            su.AtomCollection(
                elements,
                pos))
        result = client.calculate_custom_result()

        assert result.energy is not None
        assert result.atomic_charges is not None
        assert result.gradients is not None
        if result.energy is not None:
            self.assertAlmostEqual(result.energy, -1.015120608923506, delta=1e-6)
        assert_array_almost_equal(result.gradients, [
            [-0.108699, 0.0, 0.0],
            [+0.108699, 0.0, 0.0],
        ], decimal=6)
        assert_array_almost_equal(result.atomic_charges, [2.220446049250313e-16, 2.220446049250313e-16], decimal=6)

        assert result.hessian is not None
        ref_hessian = [
            [0.0330, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0411, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0411, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0330, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0411, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0411],
        ]
        assert_array_almost_equal(result.hessian, ref_hessian, decimal=4)

        well_center = result.positions
        assert well_center is not None
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[0], pos[0])])
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[1], pos[1])])

    def test_calculate_custom_result_with_dftb0(self) -> None:
        """
        Check that calculate_custom_result using "DFTB0" calc_method calculates the correct gradient.
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()
        settings.method = "DFTB0"
        settings_dictionary = settings.__dict__
        client = ScineCalculatorWrapper(
            settings.method,
            "sparrow",
            True,
            settings_dictionary,
            su.AtomCollection(
                elements,
                pos))
        result = client.calculate_custom_result()

        assert result.energy is not None
        assert result.atomic_charges is not None
        assert result.gradients is not None
        if result.energy is not None:
            self.assertAlmostEqual(result.energy, -0.6040405615738355, delta=1e-6)
        assert_array_almost_equal(result.gradients, [
            [-0.06049923, 0.0, 0.0],
            [0.06049923, 0.0, 0.0],
        ], decimal=6)
        assert_array_almost_equal(result.atomic_charges,
                                  [-3.885780586188048e-16, -2.220446049250313e-16], decimal=6)

        assert result.hessian is not None
        ref_hessian = [
            [0.01980095, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.02286773, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.02286773, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.01980095, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.02286773, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.02286773],
        ]
        assert_array_almost_equal(result.hessian, ref_hessian, decimal=4)

        well_center = result.positions
        assert well_center is not None
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[0], pos[0])])
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[1], pos[1])])

    def test_calculate_custom_result_with_dftb2(self) -> None:
        """
        Check that calculate_custom_result using "DFTB2" calc_method calculates the correct gradient.
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()
        settings.method = "DFTB2"

        client = ScineCalculatorWrapper(
            settings.method,
            "sparrow",
            True,
            settings.__dict__,
            su.AtomCollection(
                elements,
                pos))
        result = client.calculate_custom_result()

        assert result.energy is not None
        assert result.atomic_charges is not None
        assert result.gradients is not None
        if result.energy is not None:
            self.assertAlmostEqual(result.energy, -0.604040780992713, delta=1e-6)
        assert_array_almost_equal(result.gradients, [
            [-0.0604983, 0.0, 0.0],
            [0.0604983, 0.0, 0.0],
        ], decimal=6)
        assert_array_almost_equal(result.atomic_charges, [
                                  2.7755575615628914e-17, 3.3306690738754696e-16], decimal=6)

        assert result.hessian is not None
        ref_hessian = [
            [0.0198, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0229, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0229, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0198, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0229, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0229],
        ]
        assert_array_almost_equal(result.hessian, ref_hessian, decimal=4)

        well_center = result.positions
        assert well_center is not None
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[0], pos[0])])
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[1], pos[1])])

    def test_calculate_custom_result_with_dftb3(self) -> None:
        """
        Check that calculate_custom_result using "DFTB3" calc_method calculates the correct gradient.
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()
        settings.method = "DFTB3"

        client = ScineCalculatorWrapper(
            settings.method,
            "sparrow",
            True,
            settings.__dict__,
            su.AtomCollection(
                elements,
                pos))
        result = client.calculate_custom_result()

        assert result.energy is not None
        assert result.atomic_charges is not None
        assert result.gradients is not None
        if result.energy is not None:
            self.assertAlmostEqual(result.energy, -0.6040405615738358, delta=1e-6)
        assert_array_almost_equal(result.gradients, [
            [-0.06049923, 0.0, 0.0],
            [0.06049923, 0.0, 0.0],
        ], decimal=6)
        assert_array_almost_equal(result.atomic_charges,
                                  [-1.6653345369377348e-16, -4.440892098500626e-16], decimal=6)

        assert result.hessian is not None
        ref_hessian = [
            [0.01980849, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.02286737, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.02286737, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.01980849, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.02286737, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.02286737],
        ]
        assert_array_almost_equal(result.hessian, ref_hessian, decimal=4)

        well_center = result.positions
        assert well_center is not None
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[0], pos[0])])
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[1], pos[1])])

    def test_calculate_custom_result_with_molecular_charge_0(self) -> None:
        """
        Check that calculate_custom_result returns correct gradient with molecular_charge = 0.
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()
        settings.molecular_charge = 0

        client = ScineCalculatorWrapper(
            settings.method,
            "sparrow",
            True,
            settings.__dict__,
            su.AtomCollection(
                elements,
                pos))
        result = client.calculate_custom_result()
        assert result.energy is not None
        assert result.atomic_charges is not None
        assert result.gradients is not None
        energy = result.energy
        gradients = result.gradients
        new_hessian = result.hessian
        well_center = result.positions
        charges = result.atomic_charges

        if energy is not None:
            self.assertAlmostEqual(energy, -0.8782779599166628, delta=1e-6)
        assert_array_almost_equal(gradients, [
            [-0.15099689, 0.0, 0.0],
            [0.15099689, 0.0, 0.0],
        ], decimal=6)
        assert_array_almost_equal(charges, [2.220446049250313e-16, 2.220446049250313e-16], decimal=6)

        assert new_hessian is not None
        ref_hessian = [
            [0.05022484, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.05707437, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.05707437, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.05022484, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.05707437, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.05707437],
        ]
        assert_array_almost_equal(new_hessian, ref_hessian, decimal=4)

        assert well_center is not None
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[0], pos[0])])
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[1], pos[1])])

    def test_calculate_custom_result_with_molecular_charge_1(self) -> None:
        """
        Check that calculate_custom_result returns correct gradient with molecular_charge = 1.
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()
        settings.spin_multiplicity = 2
        settings.molecular_charge = 1

        client = ScineCalculatorWrapper(
            settings.method,
            "sparrow",
            True,
            settings.__dict__,
            su.AtomCollection(
                elements,
                pos))
        result = client.calculate_custom_result()

        assert result.energy is not None
        assert result.atomic_charges is not None
        assert result.gradients is not None
        energy = result.energy
        gradients = result.gradients
        new_hessian = result.hessian
        well_center = result.positions
        charges = result.atomic_charges

        self.assertAlmostEqual(energy, -0.4896792008443987, delta=1e-6)
        assert_array_almost_equal(gradients, [
            [-0.04621013, 0.0, 0.0],
            [0.04621013, 0.0, 0.0],
        ], decimal=6)
        assert_array_almost_equal(charges, [0.4999999999999999, 0.5000000000000001], decimal=6)

        assert new_hessian is not None
        ref_hessian = [
            [0.00390809, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.01746668, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.01746668, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.00390809, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.01746668, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.01746668],
        ]
        assert_array_almost_equal(new_hessian, ref_hessian, decimal=4)

        assert well_center is not None
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[0], pos[0])])
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[1], pos[1])])

    def test_calculate_custom_result_with_spin_multiplicity_1(self) -> None:
        """
        Check that calculate_custom_result returns correct gradient with spin_multiplicity = 1.
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()
        settings.spin_multiplicity = 1
        settings.molecular_charge = 0

        client = ScineCalculatorWrapper(
            settings.method,
            "sparrow",
            True,
            settings.__dict__,
            su.AtomCollection(
                elements,
                pos))
        result = client.calculate_custom_result()
        assert result.energy is not None
        assert result.atomic_charges is not None
        assert result.gradients is not None
        energy = result.energy
        gradients = result.gradients
        new_hessian = result.hessian
        well_center = result.positions
        charges = result.atomic_charges

        self.assertAlmostEqual(energy, -0.8782779599166628, delta=1e-6)
        assert_array_almost_equal(gradients, [
            [-0.15099689, 0.0, 0.0],
            [0.15099689, 0.0, 0.0],
        ], decimal=6)
        assert_array_almost_equal(charges, [2.220446049250313e-16, 2.220446049250313e-16], decimal=6)

        assert new_hessian is not None
        ref_hessian = [
            [0.05022484, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.05707437, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.05707437, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.05022484, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.05707437, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.05707437],
        ]
        assert_array_almost_equal(new_hessian, ref_hessian, decimal=4)

        assert well_center is not None
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[0], pos[0])])
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[1], pos[1])])

    def test_calculate_custom_result_with_spin_multiplicity_3(self) -> None:
        """
        Check that calculate_custom_result returns correct gradient with spin_multiplicity = 3.
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()
        settings.spin_multiplicity = 3
        settings.molecular_charge = 0

        client = ScineCalculatorWrapper(
            settings.method,
            "sparrow",
            True,
            settings.__dict__,
            su.AtomCollection(
                elements,
                pos))
        result = client.calculate_custom_result()
        assert result.energy is not None
        assert result.atomic_charges is not None
        assert result.gradients is not None

        energy = result.energy
        gradients = result.gradients
        new_hessian = result.hessian
        well_center = result.positions
        charges = result.atomic_charges

        self.assertAlmostEqual(energy, -0.816192264836425, delta=1e-6)
        assert_array_almost_equal(gradients, [
            [0.01995274, 0.0, 0.0],
            [-0.01995274, 0.0, 0.0],
        ], decimal=6)
        assert_array_almost_equal(charges, [0.0, 0.0], decimal=6)

        assert new_hessian is not None
        ref_hessian = [
            [0.04357255, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.00754181, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.00754181, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.04357255, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.00754181, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.00754181],
        ]
        assert_array_almost_equal(new_hessian, ref_hessian, decimal=4)

        assert well_center is not None
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[0], pos[0])])
        assert all([abs(a - b) <= 0.0001 for a, b in zip(well_center[1], pos[1])])

    def test_element_from_symbol_does_not_depend_on_letter_case(self) -> None:
        """
        Check that element_from_symbol does not depend on the letter case.
        """
        assert su.ElementInfo.element_from_symbol("Cu") == su.ElementType.Cu
        assert su.ElementInfo.element_from_symbol("CU") == su.ElementType.Cu
        assert su.ElementInfo.element_from_symbol("cu") == su.ElementType.Cu
        assert su.ElementInfo.element_from_symbol("cU") == su.ElementType.Cu

    def test_checking_of_multiplicity_validity(self) -> None:
        """
        Check that check_setting_validity finds and corrects all invalid setting
        combinations for spin multiplicity
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()
        settings.spin_multiplicity = 4
        settings.molecular_charge = 0
        settings.spin_mode = "unrestricted"

        client = ScineCalculatorWrapper(
            settings.method,
            "sparrow",
            False,
            settings.__dict__,
            su.AtomCollection(
                elements,
                pos))
        result = client.calculate_custom_result()
        new_settings = result.settings
        assert new_settings["spin_multiplicity"] == 3

        new_settings["spin_mode"] = "any"
        client.update_system(-1, [str(e) for e in elements], pos, new_settings)
        result = client.calculate_custom_result()
        new_settings = result.settings
        assert new_settings["spin_mode"] == "unrestricted"

        new_settings["spin_multiplicity"] = 2
        client.update_system(-1, [str(e) for e in elements], pos, new_settings)
        result = client.calculate_custom_result()
        new_settings = result.settings
        assert new_settings["spin_multiplicity"] == 1

    def test_checking_of_unrestricted_validity(self) -> None:
        """
        Check that check_setting_validity finds and corrects all invalid setting
        combinations for spin mode
        """
        pos = np.array([
            [-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
            [0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0],
        ])
        elements = [su.ElementType.H, su.ElementType.H]
        settings = CalculatorSettings()
        settings.spin_mode = "restricted"
        settings.spin_multiplicity = 3
        settings.molecular_charge = 0

        client = ScineCalculatorWrapper(
            settings.method,
            "sparrow",
            False,
            settings.__dict__,
            su.AtomCollection(
                elements,
                pos))
        result = client.calculate_custom_result()
        new_settings = result.settings
        assert new_settings["spin_mode"] == "unrestricted"
