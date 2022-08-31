#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the MoleculeDepthView class
and its subclasses.
"""
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtk import (
    vtkMoleculeMapper,  #
    vtkMolecule,  #
    vtkActor,  #
    vtkRenderer,  #
    vtkRenderWindow,  #
    vtkInteractorStyle,  #
    vtkAlgorithmOutput,  #
    vtkPolyDataMapper,  #
    vtkSphereSource,
)  #

import scine_heron.config as config
from scine_heron.utilities import hex_to_rgb_base_1

from PySide2.QtWidgets import QWidget
from scine_heron.molecule.depth_view_algorithms import DepthProjection

from abc import ABC, abstractmethod
from typing import Any


class MoleculeDepthView(ABC):
    """
    A base class that wraps a QVTKRenderWindowInteractors
    displaying an additional representation of a molecule
    and a haptic pointer.
    It exposes:
    - the interactor, so that it can be added
      to existing QWidgets and QLayouts;
    - a callback for camera change,
      that can be used as an observer
      for the RenderEvent of a vtkRenderWindow
      (i.e., the main renderwindow,
      where the main view of the molecule
      is displayed.)
    - an input port for a molecule
    - an input port for the haptic pointer data
    It is responsibility of the owner of this object
    to pass the `camera_changed` callback to the right caller
    (i.e., to use the `AddObserver` method
    on the main RenderWindow).
    """

    def __init__(self, parent: QWidget) -> None:
        # Haptic pointer pipeline - general
        # This needs to be connected with the subclass-specific pipeline
        self._haptic_pointer_mapper = vtkPolyDataMapper()
        self._haptic_pointer_actor = vtkActor()
        self._haptic_pointer_actor.SetMapper(self._haptic_pointer_mapper)
        self._haptic_pointer_actor.GetProperty().SetColor(0, 0.75, 0.75)

        # Molecule vis graphic pipeline - general
        self._molecule_mapper = vtkMoleculeMapper()
        self._molecule_actor = vtkActor()
        self._molecule_actor.SetMapper(self._molecule_mapper)

        # renderer
        self._renderer = vtkRenderer()
        self._renderer.SetPreserveColorBuffer(True)
        self._renderer.SetLayer(0)
        rgb = hex_to_rgb_base_1(config.COLORS['secondaryLightColor'])
        self._renderer.SetBackground(*rgb)
        self._renderer.AddActor(self._molecule_actor)
        self._renderer.AddActor(self._haptic_pointer_actor)

        # interactor
        self._interactor = QVTKRenderWindowInteractor(parent=parent)
        self._interactor.Initialize()
        self._interactor.GetRenderWindow().AddRenderer(self._renderer)

        # interactor style, which does nothing
        self._style = vtkInteractorStyle()
        self._interactor.SetInteractorStyle(self._style)

    @abstractmethod
    def set_molecule_input(self, output_port: vtkAlgorithmOutput) -> None:
        """
        This method takes the output ports of an algorithm
        producing a vtkMolecule
        and connects it to the part of the molecule visualization pipeline
        for which this object is responsible.
        """

    @abstractmethod
    def set_haptic_pointer_data_input(self, output_port: vtkAlgorithmOutput) -> None:
        """
        This method takes the output port of an algorithm
        producing a (x,y,z) vtkPolyData
        and connects it to the haptic pointer visualization pipeline
        in this object.
        """

    @property
    def interactor(self) -> QVTKRenderWindowInteractor:
        return self._interactor

    @abstractmethod
    def camera_changed(self, main_window: vtkRenderWindow, _2: Any) -> None:
        """
        This method signature allows it to be used
        as an Observer for a vtkRenderWindow
        for a RenderEvent.
        """

    def render(self) -> None:
        self._renderer.GetRenderWindow().Render()

    def set_molecule(self, molecule: vtkMolecule) -> None:
        """
        Sets the molecule object that is represented
        """


class DepthViewZ1dFixedOnHapticSoftMaxMin(MoleculeDepthView):
    def __init__(self, parent: QWidget) -> None:
        super(DepthViewZ1dFixedOnHapticSoftMaxMin, self).__init__(parent)

        # The maximum distance from the haptic pointer
        # beyond which the atoms will not be plotted
        # in the depth view.
        self.filter_range = 5

        # The "saturation" distance of the atoms
        # from the haptic pointer (i.e., the origin)
        # in the depth view
        self.zscale = 3
        self._projection = DepthProjection(
            filter_range=self.filter_range, zscale=self.zscale
        )
        self._molecule_mapper.SetInputConnection(self._projection.output)
        self._molecule_mapper.SetAtomicRadiusScaleFactor(0.15)  # default is 0.3

        # The haptic pointer in this view is a sphere always in the center.
        # NOTE: we can move it if needed,
        #       e.g. to the left of the right
        #       to improve readability.
        self._haptic_pointer_source = vtkSphereSource()
        self._haptic_pointer_source.SetCenter(0, 0, 0)
        self._haptic_pointer_source.SetRadius(0.25)
        self._haptic_pointer_source.SetPhiResolution(25)
        self._haptic_pointer_source.SetThetaResolution(25)

        # Hooking the haptic data
        self._haptic_pointer_mapper.SetInputConnection(
            self._haptic_pointer_source.GetOutputPort()
        )

    def set_molecule_input(self, output_port: vtkAlgorithmOutput) -> None:
        """
        We connect the molecule output
        and connect it to the input of the depth projection algorithm.
        """
        self._projection.set_molecule_input(output_port)

    def set_haptic_pointer_data_input(self, output_port: vtkAlgorithmOutput) -> None:
        """
        Set the polydata connection for the haptic data.
        It must be fed directly to the projection algorithm.
        """
        self._projection.set_haptic_pointer_data(output_port)

    def camera_changed(self, main_window: vtkRenderWindow, _2: Any) -> None:
        main_camera = main_window.GetRenderers().GetFirstRenderer().GetActiveCamera()
        main_depth_direction = main_camera.GetDirectionOfProjection()

        # Camera orientation is the same - it's the atoms in the depth view that move.
        # But we change the zoom and the distance
        camera = self._renderer.GetActiveCamera()
        camera.SetFocalPoint((0, 0, 0))
        camera.SetViewUp((0, 0, 1))

        # to make sure no atom is cut in half in the depth view
        distance_safety_margin = 1.15
        distance = self.zscale * distance_safety_margin
        camera.SetPosition((0, distance, 0))
        camera.SetViewAngle(90)  # +- 45 to make calculations easy.
        camera.SetClippingRange([0.001, distance + 5])

        self._projection.set_camera_data(main_depth_direction)
        self.render()
        # There is no haptic pointer projection to update.

    def set_molecule(self, molecule: vtkMolecule) -> None:
        self._projection.set_molecule(molecule)
