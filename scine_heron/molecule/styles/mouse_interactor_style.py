#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the MouseInteractorStyle class.
"""

from uuid import uuid1
from enum import Enum, auto
from typing import cast, Any, Optional, Callable, Dict, Tuple, Set

from vtk import (
    vtkActor,
    vtkRenderer,
    vtkIdTypeArray,
    vtkMolecule,
    vtkMoleculeMapper,
    vtkHardwareSelector,
    vtkTransform,
    vtkInteractorStyleTrackballCamera,
)
from scine_heron.electronic_data.electronic_data_status_manager import (
    ElectronicDataStatusManager,
)
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from scine_heron.settings.settings_status_manager import SettingsStatusManager


class InteractionMode(Enum):
    NO_INTERACTION = auto()
    ROTATE_CAMERA = auto()
    MOVE_CAMERA = auto()
    MOVE_ATOM = auto()


class MouseInteractorStyle(vtkInteractorStyleTrackballCamera):  # type: ignore[misc]
    """
    An interactor style (based on "vtkInteractorStyleTrackballCamera") that supports
    picking and moving particles with the right mouse button.
    """

    def __init__(
        self,
        interactor: QVTKRenderWindowInteractor,
        renderer: vtkRenderer,
        mapper: vtkMoleculeMapper,
        actors_dict: Dict[str, vtkActor],
        selected_atom_callback: Callable[[Optional[int]], None],
    ):
        vtkInteractorStyleTrackballCamera.__init__(self)

        self.__interactor = interactor
        self.__mapper = mapper
        self.__actors_dict = actors_dict

        self._renderer = renderer
        self._selected_atom_callback = selected_atom_callback
        self._pressed_buttons: Set[str] = set()

        self._settings_status_manager: SettingsStatusManager = None  # type: ignore[assignment]

        self._electronic_data_status_manager: Optional[
            ElectronicDataStatusManager
        ] = None

        self._molecule = vtkMolecule()
        self._molecule_version = uuid1()

        self.__add_observers()

    @staticmethod
    def _interaction_mode(
        pressed_buttons: Set[str], selected_atom_id: Optional[int]
    ) -> InteractionMode:
        if "left_mouse" in pressed_buttons and " " not in pressed_buttons:
            mode = InteractionMode.ROTATE_CAMERA
        elif "left_mouse" in pressed_buttons and " " in pressed_buttons:
            mode = InteractionMode.MOVE_CAMERA
        elif "right_mouse" in pressed_buttons and selected_atom_id is not None:
            mode = InteractionMode.MOVE_ATOM
        elif "right_haptic" in pressed_buttons and selected_atom_id is not None:
            mode = InteractionMode.MOVE_ATOM
        else:
            mode = InteractionMode.NO_INTERACTION

        return mode

    def set_settings_status_manager(
        self, settings_status_manager: SettingsStatusManager
    ) -> None:
        self._settings_status_manager = settings_status_manager

    def set_electronic_data_status_manager(
        self, electronic_data_status_manager: ElectronicDataStatusManager
    ) -> None:
        self._electronic_data_status_manager = electronic_data_status_manager

    def __add_observers(self) -> None:
        """
        Add observers for mouse presses and movements.
        """
        priority = 1.0
        self.AddObserver(
            "LeftButtonPressEvent", self._handle_left_button_press, priority
        )
        self.AddObserver(
            "LeftButtonReleaseEvent", self._handle_left_button_release, priority
        )
        self.AddObserver(
            "RightButtonPressEvent", self.__handle_right_button_press, priority
        )
        self.AddObserver(
            "RightButtonReleaseEvent", self.__handle_right_button_release, priority
        )
        self.AddObserver("MouseMoveEvent", self.__handle_mouse_move, priority)
        self.AddObserver("KeyPressEvent", self.__key_press, priority)
        self.AddObserver("KeyReleaseEvent", self.__key_release, priority)
        self.AddObserver(
            "MouseWheelForwardEvent", self._handle_mouse_wheel_forward, priority
        )
        self.AddObserver(
            "MouseWheelBackwardEvent", self._handle_mouse_wheel_backward, priority
        )

    def _handle_mouse_wheel_forward(self, _1: Any = None, _2: Any = None) -> None:
        self.OnMouseWheelForward()
        self._render()

    def _handle_mouse_wheel_backward(self, _1: Any = None, _2: Any = None) -> None:
        self.OnMouseWheelBackward()
        self._render()

    def _handle_left_button_press(self, _1: Any = None, _2: Any = None) -> None:
        """
        Activates "rotation mode".
        """
        self._pressed_buttons.add("left_mouse")

    def _handle_left_button_release(self, _1: Any = None, _2: Any = None) -> None:
        """
        Deactivates "rotation mode".
        """
        self._pressed_buttons.remove("left_mouse")

    def __handle_right_button_press(self, _1: Any = None, _2: Any = None) -> None:
        """
        Sets the member mouse_picked_atom_id to the picked atom.
        """
        self._pressed_buttons.add("right_mouse")
        self._settings_status_manager.mouse_picked_atom_id = self.__picked_atom()
        self._selected_atom_callback(self._settings_status_manager.mouse_picked_atom_id)

    def __handle_right_button_release(self, _1: Any = None, _2: Any = None) -> None:
        """
        Resets the member mouse_picked_atom_id to None.
        """
        self._pressed_buttons.remove("right_mouse")
        self._settings_status_manager.mouse_picked_atom_id = None

    def __handle_mouse_move(self, _1: Any, _2: Any) -> None:
        """
        Moves the picked atom to the location defined by the mouse position.
        """
        interaction_mode = self._interaction_mode(
            self._pressed_buttons, self._settings_status_manager.mouse_picked_atom_id
        )

        last_xy_pos = self.GetInteractor().GetLastEventPosition()
        xy_pos = self.GetInteractor().GetEventPosition()

        if interaction_mode == InteractionMode.ROTATE_CAMERA:
            self._rotate_camera(last_xy_pos[0] - xy_pos[0], last_xy_pos[1] - xy_pos[1])
            self._render()
        elif interaction_mode == InteractionMode.MOVE_CAMERA:
            self._move_camera(self.__calculate_motion_vector(last_xy_pos, xy_pos))
        elif interaction_mode == InteractionMode.MOVE_ATOM:
            self._settings_status_manager.selected_molecular_orbital = None
            self._settings_status_manager.number_of_molecular_orbital = None

            self._move_atom_by_mouse()
            self._render()
        else:
            self.OnMouseMove()

    def __calculate_motion_vector(
        self, last_xy_pos: Tuple[float, float], xy_pos: Tuple[float, float]
    ) -> Tuple[float, float, float]:
        last_xy_pos_world = self.__view_to_world(self.__display_to_view(last_xy_pos))
        xy_pos_world = self.__view_to_world(self.__display_to_view(xy_pos))

        return (
            last_xy_pos_world[0] - xy_pos_world[0],
            last_xy_pos_world[1] - xy_pos_world[1],
            last_xy_pos_world[2] - xy_pos_world[2],
        )

    def _move_camera(self, motion_vector: Tuple[float, float, float]) -> None:
        camera = self._renderer.GetActiveCamera()
        focal = camera.GetFocalPoint()
        point = camera.GetPosition()

        camera.SetFocalPoint(
            motion_vector[0] + focal[0],
            motion_vector[1] + focal[1],
            motion_vector[2] + focal[2],
        )
        camera.SetPosition(
            motion_vector[0] + point[0],
            motion_vector[1] + point[1],
            motion_vector[2] + point[2],
        )
        camera.OrthogonalizeViewUp()

        self._render()

    def _rotate_camera(self, azimuth: Any, elevation: Any) -> None:
        camera = self._renderer.GetActiveCamera()
        view_up = camera.GetViewUp()
        axis = [
            -camera.GetViewTransformMatrix().GetElement(0, 0),
            -camera.GetViewTransformMatrix().GetElement(0, 1),
            -camera.GetViewTransformMatrix().GetElement(0, 2),
        ]

        rotate_transform = vtkTransform()

        # azimuth
        rotate_transform.Identity()
        rotate_transform.RotateWXYZ(azimuth, view_up)

        # elevation
        rotate_transform.RotateWXYZ(elevation, axis)
        rotate_transform.Update()

        camera.ApplyTransform(rotate_transform)

    def _move_atom_by_mouse(self) -> None:
        # get atom position
        atom = self._molecule.GetAtom(self._settings_status_manager.mouse_picked_atom_id)

        # get mouse position and convert it to view coordinates
        to_view = self.__display_to_view(self.GetInteractor().GetEventPosition())
        from_view = self.__world_to_view(atom.GetPosition())
        to_world = self.__view_to_world((to_view[0], to_view[1], from_view[2]))

        atom.SetPosition(to_world[0], to_world[1], to_world[2])

    def __display_to_view(
        self, display: Tuple[float, float]
    ) -> Tuple[float, float, float]:
        """
        Converts display coordinates to view coordinates.
        """
        self._renderer.SetDisplayPoint(display[0], display[1], 0)
        self._renderer.DisplayToView()
        return cast(Tuple[float, float, float], self._renderer.GetViewPoint())

    def __world_to_view(
        self, world: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """
        Converts world to view coordinates.
        """
        self._renderer.SetWorldPoint(world[0], world[1], world[2], 1.0)
        self._renderer.WorldToView()
        return cast(Tuple[float, float, float], self._renderer.GetViewPoint())

    def __view_to_world(
        self, view: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """
        Converts view to world coordinates.
        """
        self._renderer.SetViewPoint(view[0], view[1], view[2])
        self._renderer.ViewToWorld()
        return cast(Tuple[float, float, float], self._renderer.GetWorldPoint())

    def __key_press(self, _1: Any = None, _2: Any = None) -> None:
        """
        Translate camera if the space bar has been pressed.
        """
        self._pressed_buttons.add(self.__interactor.GetKeyCode())

    def __key_release(self, _1: Any = None, _2: Any = None) -> None:
        """
        Stop translating camera if the space bar has been released.
        """
        key = self.__interactor.GetKeyCode()
        if key in self._pressed_buttons:
            self._pressed_buttons.remove(self.__interactor.GetKeyCode())

    def __picked_atom(self) -> Optional[int]:
        """
        Uses the event position to return the picked atom or None.
        """
        selector = vtkHardwareSelector()
        selector.SetRenderer(self._renderer)
        position = self.GetInteractor().GetEventPosition()

        selector.SetArea(position[0], position[1], position[0], position[1])

        # temporarily remove all actors (except the molecule) for picking
        removed_actors2D = []
        removed_actors3D = []
        try:
            actors2D = [a for a in self._renderer.GetActors2D()]
            for actor in actors2D:
                self._renderer.RemoveActor(actor)
                removed_actors2D.append(actor)
            actors3D_to_remove = [
                a
                for a in self._renderer.GetActors()
                if a != self.__actors_dict["molecule"]
            ]
            for actor in actors3D_to_remove:
                self._renderer.RemoveActor(actor)
                removed_actors3D.append(actor)

            selection = selector.Select()

        finally:
            for actor in removed_actors2D:
                self._renderer.AddActor2D(actor)
            for actor in removed_actors3D:
                self._renderer.AddActor(actor)

        ids = vtkIdTypeArray()
        self.__mapper.GetSelectedAtoms(selection, ids)
        if ids.GetSize() > 0:
            return int(ids.GetValue(0))
        return None

    def _render(self) -> None:
        """
        Render the scene.
        """
        self._renderer.GetRenderWindow().Render()
