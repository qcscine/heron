#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the HapticInteractorStyle class.
"""

from typing import Dict, Any, Tuple
from vtk import (
    vtkActor,
    vtkRenderer,
    vtkMoleculeMapper,
)

from typing import Optional, Callable
from scine_heron.haptic.haptic_client import HapticClient
from scine_heron.haptic.haptic_pointer_data import HapticPointerData
from scine_heron.haptic.haptic_pointer_representation import HapticPointerRepresentation
from scine_heron.molecule.styles.mouse_interactor_style import (
    MouseInteractorStyle,
    InteractionMode,
)
from scine_heron.electronic_data.electronic_data_status_manager import (
    ElectronicDataStatusManager,
)

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor


class HapticInteractorStyle(MouseInteractorStyle):
    """
    An interactor style (based on "MouseInteractorStyle") that supports
    picking and moving particles with the haptic device.
    """

    def __init__(
        self,
        interactor: QVTKRenderWindowInteractor,
        renderer: vtkRenderer,
        mapper: vtkMoleculeMapper,
        haptic_client: Optional[HapticClient],
        actors_dict: Dict[str, vtkActor],
        selected_atom_callback: Callable[[Optional[int]], None],
    ):
        super().__init__(
            interactor, renderer, mapper, actors_dict, selected_atom_callback
        )

        self.__haptic_client = haptic_client
        self.__last_haptic_pos: Tuple[float, float, float] = (0, 0, 0)
        self.__add_haptic_pointer()

    def set_electronic_data_status_manager(
        self, electronic_data_status_manager: ElectronicDataStatusManager
    ) -> None:
        self._electronic_data_status_manager = electronic_data_status_manager

    def __add_haptic_pointer(self) -> None:
        if (
            self.__haptic_client is not None
            and self.__haptic_client.device_is_available
            and self.__haptic_client.callback is not None
        ):
            self.__haptic_pointer = HapticPointerData()
            self.__haptic_pointer_representation = HapticPointerRepresentation(
                self.__haptic_pointer
            )
            self._renderer.AddActor(self.__haptic_pointer_representation.actor)
            self.__haptic_client.callback.signals.first_button_down_signal.connect(
                self._handle_left_button_press
            )
            self.__haptic_client.callback.signals.first_button_up_signal.connect(
                self._handle_left_button_release
            )
            self.__haptic_client.callback.signals.second_button_down_signal.connect(
                self.__handle_right_button_press_from_haptic
            )
            self.__haptic_client.callback.signals.second_button_up_signal.connect(
                self.__handle_right_button_release_from_haptic
            )
            self.__haptic_client.callback.signals.move_signal.connect(
                self.__handle_haptic_move
            )
        else:
            return

    @property
    def haptic_pointer(self) -> HapticPointerData:
        return self.__haptic_pointer

    def __handle_right_button_press_from_haptic(self, index: int) -> None:
        """
        Sets the member haptic_picked_atom_id to the picked atom.
        """
        self._pressed_buttons.add("right_haptic")
        self._settings_status_manager.haptic_picked_atom_id = index if index >= 0 else None

    def __handle_right_button_release_from_haptic(
        self, _1: Any = None, _2: Any = None
    ) -> None:
        """
        Resets the member haptic_picked_atom_id to None and update atom position in haptic_device.
        """
        self._pressed_buttons.remove("right_haptic")
        if (
            self.__haptic_client is not None
            and self._settings_status_manager.haptic_picked_atom_id is not None
        ):
            self.__haptic_client.update_atom(
                self._settings_status_manager.haptic_picked_atom_id,
                self._molecule.GetAtom(self._settings_status_manager.haptic_picked_atom_id),
            )
        self._selected_atom_callback(self._settings_status_manager.haptic_picked_atom_id)
        self._settings_status_manager.haptic_picked_atom_id = None

    def _rotate_camera(self, azimuth: Any, elevation: Any) -> None:
        super()._rotate_camera(azimuth, elevation)
        if self.__haptic_client is not None:
            self.__haptic_client.update_transform_matrix(
                self._renderer.GetActiveCamera(), azimuth, elevation
            )

    def _move_atom_by_mouse(self) -> None:
        super()._move_atom_by_mouse()
        if (
            self.__haptic_client is not None
            and self._settings_status_manager.mouse_picked_atom_id is not None
        ):
            self.__haptic_client.update_atom(
                self._settings_status_manager.mouse_picked_atom_id,
                self._molecule.GetAtom(self._settings_status_manager.mouse_picked_atom_id),
            )

    def __handle_haptic_move(
        self, pos: Any, azimuth: float, elevation: float, zoom: float
    ) -> None:
        """
        Moves the picked atom to the location defined by the mouse position.
        """

        self.__haptic_pointer.update_pointer_position(pos)
        last_pos = self.__last_haptic_pos
        self.__last_haptic_pos = pos.x, pos.y, pos.z

        interaction_mode = self._interaction_mode(
            self._pressed_buttons, self._settings_status_manager.haptic_picked_atom_id
        )

        if interaction_mode == InteractionMode.ROTATE_CAMERA:
            self._rotate_camera(azimuth, elevation)
            self._renderer.GetActiveCamera().Zoom(zoom)
            self._render()
        elif interaction_mode == InteractionMode.MOVE_CAMERA:
            move_pos = (
                last_pos[0] - pos.x,
                last_pos[1] - pos.y,
                last_pos[2] - pos.z,
            )
            self._move_camera(move_pos)
        elif interaction_mode == InteractionMode.MOVE_ATOM:
            self._settings_status_manager.selected_molecular_orbital = None
            self._settings_status_manager.number_of_molecular_orbital = None

            atom = self._molecule.GetAtom(self._settings_status_manager.haptic_picked_atom_id)
            atom.SetPosition(pos.x, pos.y, pos.z)
            self._render()
        else:
            self._render()
