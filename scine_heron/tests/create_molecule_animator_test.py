#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Tests for the create_molecule_animator function.
"""

from scine_heron.energy_profile.energy_profile_status_manager import (
    EnergyProfileStatusManager,
)
from scine_heron.status_manager import StatusManager
from scine_heron.haptic.haptic_client import HapticClient
from scine_heron.electronic_data.electronic_data_status_manager import (
    ElectronicDataStatusManager,
)
from scine_heron.settings.settings_status_manager import SettingsStatusManager
from scine_heron.molecule.create_molecule_animator import create_molecule_animator
from scine_heron.molecule.animator import Animator
from typing import Optional, List, TYPE_CHECKING, Any
import pytest
from vtk import vtkMolecule
# TODO Disabled as long as test_updates_molecule is disabled
# from PySide2.QtWidgets import QApplication
# from PySide2.QtCore import QEventLoop
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


@pytest.fixture(name="animator")  # type: ignore[misc]
def create_animator(molecule: vtkMolecule) -> Animator:
    """
    Creates a molecule animator with the function
    `create_molecule_animator`.
    """
    settings_manager = SettingsStatusManager()
    energy_status_manager = EnergyProfileStatusManager()
    charge_status_manager = StatusManager[Optional[List[float]]](None)
    electronic_data_status_manager = ElectronicDataStatusManager()

    return create_molecule_animator(
        0,
        molecule,
        settings_manager,
        HapticClient(),
        energy_status_manager,
        electronic_data_status_manager,
        charge_status_manager,
        Signal(),
    )

# TODO this test does not work without a haptic device
# def test_updates_molecule(
#     _app: QApplication, animator: Animator, molecule: vtkMolecule
# ) -> None:
#     """
#     Checks that the animator applies the gradient to the molecule.
#     """
#     startX = molecule.GetAtom(0).GetPosition().GetX()
#     animator.start()

#     loop = QEventLoop()
#     animator.render_signal.connect(loop.quit)
#     loop.exec_()

#     assert molecule.GetAtom(0).GetPosition().GetX() > startX
#     assert molecule.GetAtom(0).GetPosition().GetY() == pytest.approx(0.0)
#     assert molecule.GetAtom(0).GetPosition().GetZ() == pytest.approx(0.0)

#     assert molecule.GetAtom(1).GetPosition().GetX() == pytest.approx(
#         -1.0 * molecule.GetAtom(0).GetPosition().GetX()
#     )
#     assert molecule.GetAtom(1).GetPosition().GetY() == pytest.approx(0.0)
#     assert molecule.GetAtom(1).GetPosition().GetZ() == pytest.approx(0.0)
