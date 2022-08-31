#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Testing of MediatorPotential.
"""

from scine_heron.mediator_potential.mediator_potential import MediatorPotential
from scine_heron.mediator_potential.sparrow_client import SparrowClient
from scine_heron.settings.settings import CalculatorSettings
import pytest
import numpy as np
import scine_utilities as su


@pytest.fixture(name="client")  # type: ignore[misc]
def create_sparrow_client() -> SparrowClient:
    """
    Creates a SparrowClient instance.
    """
    atomic_hessian_switch = True
    pos = [
        (-0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0),
        (0.7 * su.BOHR_PER_ANGSTROM, 0.0, 0.0),
    ]
    element_strings = ["H", "H"]
    settings = CalculatorSettings().__dict__

    client = SparrowClient(atomic_hessian_switch, settings, 1)
    client.update_calculator(pos, element_strings, settings)
    return client


@pytest.fixture(name="mediator_potential")  # type: ignore[misc]
def create_mediator_potential(client: SparrowClient) -> MediatorPotential:
    result = client.calculate_gradients()
    energy = result.energy
    gradients = result.gradients
    hessian = result.hessian
    well_center = result.positions
    charges = result.atomic_charges
    molden_input = result.molden_input
    error_msg = result.error_msg
    new_settings = result.settings

    assert energy is not None
    assert gradients is not None
    assert hessian is not None
    assert well_center is not None
    assert charges is not None
    assert molden_input is not None
    assert error_msg is not None
    assert new_settings is not None

    return MediatorPotential(0, result)


def test_approximate_gradient(mediator_potential: MediatorPotential) -> None:
    new_pos = [
        (-0.6 * su.BOHR_PER_ANGSTROM, 0.0, 0.0),
        (0.6 * su.BOHR_PER_ANGSTROM, 0.0, 0.0),
    ]
    approx_gradients = mediator_potential.get_gradients(new_pos)

    assert all(
        [
            abs(a - b) <= 0.0001
            for a, b in zip(approx_gradients[0], [-0.14150577, 0.0, 0.0])
        ]
    )
    assert all(
        [
            abs(a - b) <= 0.0001
            for a, b in zip(approx_gradients[1], [0.14150577, 0.0, 0.0])
        ]
    )


def test_approximate_energy(mediator_potential: MediatorPotential) -> None:
    new_pos = [
        (-0.6 * su.BOHR_PER_ANGSTROM, 0.0, 0.0),
        (0.6 * su.BOHR_PER_ANGSTROM, 0.0, 0.0),
    ]
    approx_energy = mediator_potential.get_energy(new_pos)

    assert approx_energy is not None
    assert abs(approx_energy + 0.9335529516024713) <= 1e-9


def test_most_recently_computed_atomic_charges_are_provided(
    mediator_potential: MediatorPotential,
) -> None:
    """
    The mediator potential returns the atomic charges that have
    most recently been computed by Sparrow.
    """
    charges = np.array(mediator_potential.get_atomic_charges())
    assert all(np.isclose(charges, np.zeros(2)))
