#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Contains tests for the SettingsStatusManager class.
"""


import pytest
from scine_heron.settings.settings_status_manager import SettingsStatusManager
from scine_heron.settings.settings import MoleculeStyle, LabelsStyle


@pytest.fixture(name="manager")  # type: ignore[misc]
def create_manager() -> SettingsStatusManager:
    """
    Returns a SettingsStatusManager.
    """
    return SettingsStatusManager()


def test_value_can_be_read(manager: SettingsStatusManager) -> None:
    """
    Asserts that the manager contains the value
    that was set by the constructor.
    """
    assert manager.molecule_style == MoleculeStyle.BallAndStick
    assert manager.labels_style == LabelsStyle.Empty
    assert manager.molecular_orbital_value == 0.05
    assert manager.get_calculator_settings()


def test_value_can_be_set(manager: SettingsStatusManager) -> None:
    """
    Asserts that the manager contains the value
    that has been set.
    """
    manager.molecule_style = MoleculeStyle.LiquoriceStick
    manager.labels_style = LabelsStyle.AtomicNumber
    manager.molecular_orbital_value = 0.05
    manager.number_of_molecular_orbital = 10
    manager.selected_molecular_orbital = 1

    assert manager.molecule_style == MoleculeStyle.LiquoriceStick
    assert manager.labels_style == LabelsStyle.AtomicNumber
    assert manager.molecular_orbital_value == 0.05
    assert manager.number_of_molecular_orbital == 10
    assert manager.selected_molecular_orbital == 1

    manager.molecular_charge = 0
    manager.spin_multiplicity = 1
    manager.spin_mode = "unrestricted"
    assert manager.molecular_charge == 0
    assert manager.spin_multiplicity == 1
    assert manager.spin_mode == "unrestricted"


def test_setting_value_notifies(manager: SettingsStatusManager) -> None:
    """
    Asserts that setting the value causes the signal to
    be emitted.
    """
    result = 0

    def increase() -> None:
        nonlocal result
        result = result + 1

    assert result == 0

    manager.molecule_style_changed.connect(increase)
    manager.molecule_style = MoleculeStyle.VDWSpheres

    assert result == 1

    manager.labels_style_changed.connect(increase)
    manager.labels_style = LabelsStyle.Symbol

    assert result == 2

    manager.error_update.connect(increase)
    manager.error_message = "error"

    assert result == 3

    manager.molecular_charge_changed.connect(increase)
    manager.spin_multiplicity_changed.connect(increase)
    manager.spin_mode_changed.connect(increase)
    manager.molecular_charge = 1
    manager.spin_multiplicity = 3
    manager.spin_mode = "restricted"

    assert result == 6


def test_setting_value_does_not_notify_if_same_value(
    manager: SettingsStatusManager,
) -> None:
    """
    Asserts that setting the value that the manager already contains
    does not cause a signal to be emitted.
    """
    result = 0

    def increase() -> None:
        nonlocal result
        result = result + 1

    assert result == 0

    manager.molecule_style_changed.connect(increase)
    manager.molecule_style = MoleculeStyle.BallAndStick

    assert result == 0

    manager.labels_style_changed.connect(increase)
    manager.labels_style = LabelsStyle.Empty

    assert result == 0

    manager.error_update.connect(increase)
    manager.error_message = ""

    assert result == 0

    manager.molecular_charge = 0
    manager.spin_multiplicity = 1
    manager.spin_mode = "unrestricted"
    manager.molecular_charge_changed.connect(increase)
    manager.spin_multiplicity_changed.connect(increase)
    manager.spin_mode_changed.connect(increase)
    manager.molecular_charge = 0
    manager.spin_multiplicity = 1
    manager.spin_mode = "unrestricted"

    assert result == 0
