#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the MoleculeInteractorStyle class.
"""

from scine_heron.molecule.animator import Animator
from scine_heron.status_manager import StatusManager
from scine_heron.energy_profile.energy_profile_status_manager import (
    EnergyProfileStatusManager,
)
from scine_heron.haptic.haptic_client import HapticClient
from scine_heron.electronic_data.electronic_data_status_manager import (
    ElectronicDataStatusManager,
)
from scine_heron.settings.settings_status_manager import SettingsStatusManager
from scine_heron.molecule.styles.haptic_interactor_style import HapticInteractorStyle
from scine_heron.molecule.create_molecule_animator import create_molecule_animator
from uuid import uuid1
from typing import Optional, Dict, Callable, List, TYPE_CHECKING, Any

from vtk import (
    vtkRenderer,
    vtkMoleculeMapper,
    vtkMolecule,
    vtkActor,
)
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


class MoleculeInteractorStyle(HapticInteractorStyle):
    """
    An interactor style (based on "HapticInteractorStyle") that supports
    picking and moving particles with mouse or haptic device.
    """

    def __init__(
        self,
        interactor: QVTKRenderWindowInteractor,
        renderer: vtkRenderer,
        mapper: vtkMoleculeMapper,
        haptic_client: Optional[HapticClient],
        actors_dict: Dict[str, vtkActor],
        selected_atom_callback: Callable[[Optional[int]], None],
        settings_changed_signal: Signal,
    ):
        super(MoleculeInteractorStyle, self).__init__(
            interactor,
            renderer,
            mapper,
            haptic_client,
            actors_dict,
            selected_atom_callback,
        )

        self.__haptic_client = haptic_client
        self.__animator: Optional[Animator] = None

        self.__energy_status_manager: Optional[EnergyProfileStatusManager] = None
        self.__charge_status_manager: StatusManager[Optional[List[float]]] = None  # type: ignore[assignment]

        self.__settings_changed_signal = settings_changed_signal

    def set_status_managers(
        self,
        settings_status_manager: SettingsStatusManager,
        energy_status_manager: Optional[EnergyProfileStatusManager],
        charge_status_manager: StatusManager[Optional[List[float]]],
        electronic_data_status_manager: ElectronicDataStatusManager,
    ) -> None:
        super().set_settings_status_manager(settings_status_manager)
        super().set_electronic_data_status_manager(electronic_data_status_manager)

        self.__energy_status_manager = energy_status_manager
        self.__charge_status_manager = charge_status_manager

    def set_calc_gradient_in_loop(self, calc_gradient_in_loop: bool) -> None:
        """
        Save calc_gradient_in_loop flag and start or stop the loop.
        """
        if self.__haptic_client is not None:
            self.__haptic_client.set_calc_gradient_in_loop(calc_gradient_in_loop)

        if self.__animator is not None:
            if calc_gradient_in_loop:
                self.__animator.start()
            else:
                self.__animator.stop()

    def __setup_animator(self) -> None:
        """
        Create molecule gradient calculator.
        """

        old_animator_running = False
        if self.__animator is not None:
            # Cleanup of current animator
            old_animator_running = self.__animator.running
            self.__animator.render_signal.disconnect(self._render)
            self.__animator.stop()

        self.__animator = create_molecule_animator(
            self._molecule_version.int,
            self._molecule,
            self._settings_status_manager,
            self.__haptic_client,
            self.__energy_status_manager,
            self._electronic_data_status_manager,
            self.__charge_status_manager,
            self.__settings_changed_signal,
        )

        self.__animator.render_signal.connect(self._render)

        # If the old animator was running before,
        # start the new one
        if old_animator_running:
            self.__animator.start()

    @property
    def molecule(self) -> vtkMolecule:
        return self._molecule

    @molecule.setter
    def molecule(self, molecule: vtkMolecule) -> None:
        self._molecule = molecule
        self._molecule_version = uuid1()
        self.__setup_animator()
