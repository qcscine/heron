#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides tests for the ControlledCheckBox class.
"""

import pytest
from PySide2.QtCore import Qt
from PySide2.QtWidgets import QApplication
from scine_heron.settings.controlled_check_box import ControlledCheckBox
from scine_heron.status_manager import StatusManager


@pytest.fixture(name="manager")  # type: ignore[misc]
def create_manager() -> StatusManager[Qt.CheckState]:
    """
    Returns a StatusManager that contains `Unchecked`.
    """
    return StatusManager(Qt.Checked)


@pytest.fixture(name="checkbox")  # type: ignore[misc]
def create_check_box(manager: StatusManager[Qt.CheckState]) -> ControlledCheckBox:
    """
    Returns a ControlledCheckBox that is connected to the manager.
    """
    return ControlledCheckBox(status=manager)


def test_check_box_is_initially_checked(
    _app: QApplication,
    manager: StatusManager[Qt.CheckState],
    checkbox: ControlledCheckBox,
) -> None:
    """
    The state of the checkbox initially reflects the state of the
    status manager.
    """
    assert manager.value == Qt.Checked
    assert checkbox.checkState() == Qt.Checked


def test_check_box_is_updated_on_change(
    _app: QApplication,
    manager: StatusManager[Qt.CheckState],
    checkbox: ControlledCheckBox,
) -> None:
    """
    The state of the checkbox reflects the state of the
    status manager after a modification.
    """
    manager.value = Qt.Unchecked
    assert checkbox.checkState() == Qt.Unchecked


def test_check_box_is_updated_on_second_change(
    _app: QApplication,
    manager: StatusManager[Qt.CheckState],
    checkbox: ControlledCheckBox,
) -> None:
    """
    The state of the checkbox reflects the state of the
    status manager after two modifications.
    """
    manager.value = Qt.Unchecked
    manager.value = Qt.Checked
    assert checkbox.checkState() == Qt.Checked


def test_setting_the_checkbox_updates_the_state_in_the_manager(
    _app: QApplication,
    manager: StatusManager[Qt.CheckState],
    checkbox: ControlledCheckBox,
) -> None:
    """
    The state of the manager reflects the state of the
    checkbox after a modification.
    """
    checkbox.setCheckState(Qt.Unchecked)
    assert manager.value == Qt.Unchecked
