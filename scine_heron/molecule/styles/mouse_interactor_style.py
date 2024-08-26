#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the MouseInteractorStyle class.
"""

from uuid import uuid1
from enum import Enum, auto
from typing import cast, Any, Optional, Callable, Dict, Tuple, Set, List

from vtk import (
    vtkActor,
    vtkRenderer,
    vtkIdTypeArray,
    vtkMolecule,
    vtkMoleculeMapper,
    vtkHardwareSelector,
    vtkInteractorStyleTrackballCamera,
)

import scine_utilities as su

from scine_heron.electronic_data.electronic_data_status_manager import (
    ElectronicDataStatusManager,
)
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from scine_heron.molecule.utils.molecule_utils import molecule_to_atom_collection
from scine_heron.settings.settings_status_manager import SettingsStatusManager


class InteractionMode(Enum):
    NO_INTERACTION = auto()
    ROTATE_CAMERA = auto()
    MOVE_CAMERA = auto()
    MOVE_ATOMS = auto()


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
        selected_atom_callback: Callable[[Optional[List[int]]], None],
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
        pressed_buttons: Set[str], selected_atom_ids: Optional[List[int]]
    ) -> InteractionMode:
        if "left_mouse" in pressed_buttons and " " not in pressed_buttons:
            mode = InteractionMode.ROTATE_CAMERA
        elif "left_mouse" in pressed_buttons and " " in pressed_buttons:
            mode = InteractionMode.MOVE_CAMERA
        elif "right_mouse" in pressed_buttons and selected_atom_ids:
            mode = InteractionMode.MOVE_ATOMS
        elif "right_haptic" in pressed_buttons and selected_atom_ids:
            mode = InteractionMode.MOVE_ATOMS
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

    def _handle_mouse_wheel_forward(self, _1: Optional[Any] = None, _2: Optional[Any] = None) -> None:
        self.OnMouseWheelForward()
        self._render()

    def _handle_mouse_wheel_backward(self, _1: Optional[Any] = None, _2: Optional[Any] = None) -> None:
        self.OnMouseWheelBackward()
        self._render()

    def _handle_left_button_press(self, _1: Optional[Any] = None, _2: Optional[Any] = None) -> None:
        """
        Activates "rotation mode".
        """
        self._pressed_buttons.add("left_mouse")

    def _handle_left_button_release(self, _1: Optional[Any] = None, _2: Optional[Any] = None) -> None:
        """
        Deactivates "rotation mode".
        """
        self._pressed_buttons.remove("left_mouse")

    def __handle_right_button_press(self, _1: Optional[Any] = None, _2: Optional[Any] = None) -> None:
        """
        Sets the member mouse_picked_atom_ids to the picked atoms.
        """
        self._pressed_buttons.add("right_mouse")
        self._settings_status_manager.mouse_picked_atom_ids = self.__picked_atoms(
            self._settings_status_manager.mouse_picked_atom_ids)
        self._selected_atom_callback(self._settings_status_manager.mouse_picked_atom_ids)

    def __handle_right_button_release(self, _1: Optional[Any] = None, _2: Optional[Any] = None) -> None:
        """
        Resets the member mouse_picked_atom_ids to None.
        """
        self.__key_press()
        self._pressed_buttons.remove("right_mouse")
        if (
            self._settings_status_manager.mouse_picked_atom_ids
            and len(self._settings_status_manager.mouse_picked_atom_ids) == 1
            and "s" not in self._pressed_buttons
        ):
            self._settings_status_manager.mouse_picked_atom_ids = []

    def __handle_mouse_move(self, _1: Any, _2: Any) -> None:
        """
        Moves the picked atoms to the location defined by the mouse position.
        """
        interaction_mode = self._interaction_mode(
            self._pressed_buttons, self._settings_status_manager.mouse_picked_atom_ids
        )

        last_xy_pos = self.GetInteractor().GetLastEventPosition()
        xy_pos = self.GetInteractor().GetEventPosition()

        if interaction_mode == InteractionMode.ROTATE_CAMERA:
            self._rotate_camera(last_xy_pos[0] - xy_pos[0], last_xy_pos[1] - xy_pos[1])
            self._render()
        elif interaction_mode == InteractionMode.MOVE_CAMERA:
            self._move_camera(self.__calculate_motion_vector(last_xy_pos, xy_pos))
        elif interaction_mode == InteractionMode.MOVE_ATOMS:
            self._settings_status_manager.selected_molecular_orbital = None
            self._settings_status_manager.number_of_molecular_orbital = None

            self._move_atoms_by_mouse()
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
        atoms = molecule_to_atom_collection(self._molecule)
        com = su.geometry.get_center_of_mass(atoms) * su.ANGSTROM_PER_BOHR
        camera.SetFocalPoint(com)
        camera.OrthogonalizeViewUp()
        camera.Azimuth(azimuth)
        camera.Elevation(elevation)

    def _move_atoms_by_mouse(self) -> None:
        # get atom position
        if self._settings_status_manager.mouse_picked_atom_ids:
            for atom_id in self._settings_status_manager.mouse_picked_atom_ids:
                atom = self._molecule.GetAtom(atom_id)
                from_view = self.__world_to_view(atom.GetPosition())

            for this in self._settings_status_manager.mouse_picked_atom_ids:
                atom = self._molecule.GetAtom(this)
                # get mouse position and convert it to view coordinates
                to_view = self.__display_to_view(self.GetInteractor().GetEventPosition())
                from_view = self.__world_to_view(atom.GetPosition())
                to_world = self.__view_to_world((to_view[0], to_view[1], from_view[2]))
                atom.SetPosition(to_world[0], to_world[1], to_world[2])

                for other in self._settings_status_manager.mouse_picked_atom_ids:
                    if other is not this:
                        otherAtom = self._molecule.GetAtom(other)
                        from_view_other = self.__world_to_view(otherAtom.GetPosition())
                        dx = (from_view_other[0] - from_view[0])
                        dy = (from_view_other[1] - from_view[1])
                        to_world_other = self.__view_to_world((to_view[0] + dx, to_view[1] + dy, from_view_other[2]))
                        otherAtom.SetPosition(to_world_other[0], to_world_other[1], to_world_other[2])

            # break bonds without running calculation
            bonds = self._molecule.GetNumberOfBonds()
            for bond in range(bonds):
                if self._molecule.GetBondLength(bond) > 1.0:
                    self._molecule.SetBondOrder(bond, 0)

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

    def __key_press(self, _1: Optional[Any] = None, _2: Optional[Any] = None) -> None:
        """
        Translate camera if the space bar has been pressed.
        """
        self._pressed_buttons.add(self.__interactor.GetKeyCode())

    def __key_release(self, _1: Optional[Any] = None, _2: Optional[Any] = None) -> None:
        """
        Stop translating camera if the space bar has been released.
        """
        key = self.__interactor.GetKeyCode()
        if key in self._pressed_buttons:
            self._pressed_buttons.remove(self.__interactor.GetKeyCode())

    def __picked_atoms(self, picked_atoms_list: Optional[List[int]]) -> Optional[List[int]]:
        """
        Uses the event position to return the picked atoms or None.
        """
        from scine_heron.molecular_viewer import get_mol_viewer_tab
        self.__key_press()
        mol_tab = get_mol_viewer_tab(want_atoms_there=True)

        if not picked_atoms_list:
            picked_atoms_list = []

        selector = vtkHardwareSelector()
        selector.SetRenderer(self._renderer)
        position = self.GetInteractor().GetEventPosition()

        selector.SetArea(position[0], position[1], position[0], position[1])

        # before we retrieve the selection, we hide all actors but the molecule actor
        # this allows the selector to correctly select the atom that was picked
        # removing the actors caused problems with multiple active selections, but hiding looks to be fine
        actors_2d = [a for a in self._renderer.GetActors2D()]
        actors_3d = [a for a in self._renderer.GetActors()
                     if a != self.__actors_dict["molecule"]]
        all_actors = actors_2d + actors_3d
        for actor in all_actors:
            actor.SetVisibility(False)
        selection = selector.Select()
        for actor in all_actors:
            actor.SetVisibility(True)
        ids = vtkIdTypeArray()  # ids are written into here from mapper
        self.__mapper.GetSelectedAtoms(selection, ids)

        if ids.GetSize() > 0 and int(ids.GetValue(0)) not in picked_atoms_list:
            if "s" in self._pressed_buttons:
                picked_atoms_list.append(int(ids.GetValue(0)))
            else:
                picked_atoms_list = [int(ids.GetValue(0))]
        elif (
            ids.GetSize() > 0
            and int(ids.GetValue(0)) in picked_atoms_list
            and "s" in self._pressed_buttons
            and len(picked_atoms_list) > 1
        ):
            picked_atoms_list.remove(int(ids.GetValue(0)))
        if mol_tab and mol_tab.mol_widget:
            mol_tab.mol_widget.set_selection(picked_atoms_list)
        return picked_atoms_list

    def _render(self) -> None:
        """
        Render the scene.
        """
        self._renderer.GetRenderWindow().Render()
