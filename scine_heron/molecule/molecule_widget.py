#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the MoleculeWidget class.
"""

import multiprocessing
from multiprocessing.managers import ListProxy
from uuid import uuid1
from pathlib import Path
from typing import Optional, Tuple, List, Any, Dict, Union, TYPE_CHECKING
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal

import scine_utilities as utils
import numpy as np
from vtkmodules.vtkCommonExecutionModel import vtkTrivialProducer
from vtk import (
    vtkActor,
    vtkMolecule,
    vtkMoleculeMapper,
    vtkRenderer,
    vtkSelectVisiblePoints,
    vtkSimpleBondPerceiver,
    vtkDoubleArray,
    vtkUnsignedCharArray,
    vtkDataObject,
    vtkArrowSource,
    vtkPolyDataMapper,
    vtkTransformPolyDataFilter,
    vtkTransform,
)
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PySide2.QtCore import QObject, Qt
from PySide2.QtWidgets import QHBoxLayout, QWidget
from PySide2.QtGui import QGuiApplication

import scine_heron.config as config
from scine_heron.calculators.calculator import ScineCalculatorWrapper
from scine_heron.molecule.depth_view import DepthViewZ1dFixedOnHapticSoftMaxMin
from scine_heron.edit_molecule import edit_molecule_functions as emf
from scine_heron.status_manager import StatusManager
from scine_heron.haptic.haptic_client import HapticClient
from scine_heron.molecule.colorbar import (
    create_colorbar,
    create_symmetric_color_transfer_function,
)
from scine_heron.molecule.utils.molecule_utils import (
    maximum_vdw_radius,
    atom_collection_to_molecule,
    molecule_to_atom_collection,
)
from scine_heron.molecule.utils.array_utils import rescale_to_range, iterable_to_vtk_array
from scine_heron.molecule.atom_selection import AtomSelection
from scine_heron.molecule.molecule_labels import MoleculeLabels
from scine_heron.electronic_data.electronic_data_widget import ElectronicDataWidget
from scine_heron.energy_profile.energy_profile_status_manager import (
    EnergyProfileStatusManager,
)
from scine_heron.settings.settings_status_manager import SettingsStatusManager
from scine_heron.settings.settings import MoleculeStyle
from scine_heron.molecule.styles.molecule_interactor_style import MoleculeInteractorStyle
from scine_heron.mediator_potential.custom_results import CustomResult
from scine_heron.utilities import write_error_message, hex_to_rgb_base_1


class WrappedQVTKRenderWindowInteractor(QVTKRenderWindowInteractor):
    def __init__(self, *args, **kwargs):
        if 'alternative_zoom_controls' in kwargs:
            self.__alternative_zoom_controls = kwargs['alternative_zoom_controls']
            del kwargs['alternative_zoom_controls']
        else:
            self.__alternative_zoom_controls = False
        if 'disable_modification' in kwargs:
            self.__disable_modification = kwargs['disable_modification']
            del kwargs['disable_modification']
        else:
            self.__disable_modification = False
        QVTKRenderWindowInteractor.__init__(self, *args, **kwargs)

    def wheelEvent(self, ev):
        if self.__alternative_zoom_controls:
            modifiers = QGuiApplication.keyboardModifiers()
            if modifiers == Qt.ControlModifier:
                super().wheelEvent(ev)
            else:
                pass
        else:
            super().wheelEvent(ev)

    def mousePressEvent(self, ev):
        if self.__disable_modification and ev.button() == Qt.RightButton:
            pass
        else:
            super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev):
        if self.__disable_modification and ev.button() == Qt.RightButton:
            pass
        else:
            super().mouseReleaseEvent(ev)


class MoleculeWidget(QWidget):
    """
    Displays molecule in a 3D view.
    """

    total_number_of_mol_viewers = 0
    settings_changed_signal = Signal(int, int, str)

    def __init__(
        self,
        settings_status_manager: SettingsStatusManager = SettingsStatusManager(),
        parent: Optional[QObject] = None,
        file: Optional[Path] = None,
        atoms: Optional[object] = None,
        bonds: Optional[object] = None,
        haptic_client: Optional[HapticClient] = None,
        energy_status_manager: Optional[EnergyProfileStatusManager] = None,
        alternative_zoom_controls: bool = False,
        disable_modification: bool = False,
    ):
        QWidget.__init__(self, parent)
        if MoleculeWidget.total_number_of_mol_viewers < 100:
            MoleculeWidget.total_number_of_mol_viewers += 1
        else:
            msg = "Cannot open more MoleculeWidgets only 100 are allowed."
            write_error_message(msg)
            raise RuntimeError(msg)

        self.__disable_modification: bool = disable_modification
        self.__molecule_version = uuid1()
        self.__settings_status_manager = settings_status_manager
        self.__settings_status_manager.molecule_style_changed.connect(
            self.__update_molecule_style_if_necessary)
        self.__settings_status_manager.labels_style_changed.connect(
            self.__update_labels_style)
        self.__energy_status_manager = energy_status_manager
        self.__charge_status_manager = StatusManager[Optional[List[float]]](None)
        self.__force_status_manager = StatusManager[Optional[List[float]]](None)

        for signal in [
            self.__charge_status_manager.changed_signal,
            self.__settings_status_manager.molecule_style_changed,
        ]:
            signal.connect(self.__update_atomic_charge_display)
        self.__force_status_manager.changed_signal.connect(self.__update_force_arrow_display)
        self.__colorbar = create_colorbar()
        self.__haptic_client = haptic_client

        # setup
        self.__filter = vtkSimpleBondPerceiver()
        # We do not SetInputData(self.__molecule) just yet
        self.__molecule_mapper = vtkMoleculeMapper()
        self.__molecule_mapper.SetInputConnection(self.__filter.GetOutputPort())

        self.__molecule_actor = vtkActor()
        self.__molecule_actor.SetMapper(self.__molecule_mapper)

        self.__renderer = vtkRenderer()

        self.__interactor = WrappedQVTKRenderWindowInteractor(
            parent=self,
            alternative_zoom_controls=alternative_zoom_controls,
            disable_modification=disable_modification
        )
        self.__interactor.Initialize()
        self.__interactor.GetRenderWindow().AddRenderer(self.__renderer)

        self.__renderer.AddActor(self.__molecule_actor)

        self.__selector = self.__create_selector(self.__renderer)
        self.__labels = MoleculeLabels(
            style=self.__settings_status_manager.labels_style, selector=self.__selector
        )
        self.__renderer.AddActor2D(self.__labels.actor)

        self.__actors = {
            "molecule": self.__molecule_actor,
            "labels": self.__labels.actor,
        }
        # normal selection
        self._atom_selection = AtomSelection()
        self.__renderer.AddActor(self._atom_selection.actor)
        self.__actors['atom_selection'] = self._atom_selection.actor

        # qm selection for qm/mm
        self._qm_selection = AtomSelection()
        self._qm_selection.change_color(*list(np.array([118, 199, 115]) / 256.0))
        self.__renderer.AddActor(self._qm_selection.actor)
        self.__actors['qm_selection'] = self._qm_selection.actor

        self.__electronic_data_widget = ElectronicDataWidget(
            self.__renderer, self.__settings_status_manager, self
        )
        self.__settings_status_manager.hamiltonian_changed.connect(  # pylint: disable=no-member
            self.__electronic_data_widget.clear_surfaces_and_data
        )

        self.__renderer.SetPreserveColorBuffer(True)
        self.__renderer.SetLayer(0)
        rgb = hex_to_rgb_base_1(config.COLORS['secondaryLightColor'])
        self.__renderer.SetBackground(*rgb)

        self.__style = MoleculeInteractorStyle(
            self.__interactor,
            self.__renderer,
            self.__molecule_mapper,
            self.__haptic_client,
            self.__actors,
            self.append_selection,
        )
        self.__style.set_status_managers(
            self.__settings_status_manager,
            self.__energy_status_manager,
            self.__charge_status_manager,
            self.__force_status_manager,
            self.__electronic_data_widget.electronic_data_status_manager,
        )
        self.__interactor.SetInteractorStyle(self.__style)
        self.__selected_atoms: List[int] = []
        self.__arrow_filter_list: List[vtkTransformPolyDataFilter] = []

        """ Add a 3D viewer to the widget """
        self.__depth_view = None
        if self.__must_show_depth_view():
            """ setup_depth_view """
            self.__depth_view = DepthViewZ1dFixedOnHapticSoftMaxMin(parent=self)

            self.__depth_molecule_producer = vtkTrivialProducer()
            self.__depth_view.set_molecule_input(
                self.__depth_molecule_producer.GetOutputPort()
            )

            self.__depth_view.set_haptic_pointer_data_input(
                self.__style.haptic_pointer.output
            )
            self.__renderer.GetRenderWindow().AddObserver(
                "RenderEvent", self.__depth_view.camera_changed
            )
            """
            Adds a zero margin layout with the viewer,
            including a depth view.
            Depending on the type of the view,
            a different layout is chosen.
            """
            layout = QHBoxLayout(self)
            layout.setMargin(0)
            layout.addWidget(self.__interactor, stretch=4)
            layout.addWidget(self.__depth_view.interactor, stretch=1)
            self.setLayout(layout)
        else:
            self.__add_layout()

        self.__loaded_molecule_once = False
        if file is not None:
            self.__load_from_file(file)
            if self.__haptic_client is not None:
                self.__haptic_client.update_molecule(self.__molecule)
                self.__settings_status_manager.number_of_molecular_orbital = None
            self.__loaded_molecule_once = True
        elif atoms is not None:
            self.__load_from_atom_collection(atoms, bonds)
            self.__update_haptic_client()
            self.__loaded_molecule_once = True
        else:
            self.__plug_in_new_molecule(vtkMolecule())
        self.__renderer.ResetCamera()

    def get_electronic_data_widget(self):
        return self.__electronic_data_widget

    def update_molecule(
        self,
        file: Optional[Path] = None,
        atoms: Optional[object] = None,
        bonds: Optional[object] = None,
        reset_camera: bool = True
    ):
        if self.__electronic_data_widget is not None:
            self.__electronic_data_widget.clear_surfaces_and_data()
        if file is not None:
            self.__load_from_file(file)
            if self.__haptic_client is not None:
                self.__haptic_client.update_molecule(self.__molecule)
                self.__settings_status_manager.number_of_molecular_orbital = None
        if atoms is not None:
            self.__load_from_atom_collection(atoms, bonds)
            self.__update_haptic_client()
        if not self.__loaded_molecule_once:
            self.__loaded_molecule_once = True
            self.__renderer.ResetCamera()
        elif reset_camera:
            self.__renderer.ResetCamera()
        if not self.__disable_modification:
            self.__create_force_arrows()

    def reset_camera(self):
        self.__renderer.ResetCamera()

    def __must_show_depth_view(self) -> bool:
        return (
            self.__haptic_client is not None
            and self.__haptic_client.device_is_available
        )

    def __update_haptic_client(self) -> None:
        if self.__haptic_client is not None:
            self.__haptic_client.update_molecule(self.__molecule)
            self.__settings_status_manager.selected_molecular_orbital = None
            self.__settings_status_manager.number_of_molecular_orbital = None

    def __update_atomic_charge_display(self) -> None:
        """
        Updates the display of the population analysis/atomic charge.

        If the display is disabled, or the values are invalid,
        (this happens if e.g. no Sparrow computation has completed),
        then the usual colors and style-defined labels are shown.
        """
        enabled = (
            self.__settings_status_manager.molecule_style
            == MoleculeStyle.PartialCharges
        )
        values = self.__charge_status_manager.value
        if (
            enabled
            and values is not None
            and len(values) == self.__molecule.GetNumberOfAtoms()
        ):
            array = iterable_to_vtk_array((round(x, 2) for x in values), len(values))
            self.display_array_via_colors(array)
            self.display_array_via_labels(array)
            radii = iterable_to_vtk_array((-1.0 * x for x in values), len(values))
            self.display_array_via_radii(radii)
        else:
            self.display_atomic_number_colors()
            self.display_style_labels()
            self.display_atomic_number_radii()
        self.__render_molecule()

    def __update_force_arrow_display(self) -> None:
        """
        Updates gradient arrows for all atoms in system.
        """
        enabled = (
            self.__settings_status_manager.molecule_style
            == MoleculeStyle.ForceArrow
        )
        values = self.__force_status_manager.value
        n_atoms = self.__molecule.GetNumberOfAtoms()
        for id in range(n_atoms):
            transform = self.__arrow_filter_list[id].GetTransform()
            if (
                enabled
                and values is not None
                and len(self.__arrow_filter_list) == n_atoms
            ):
                gradient = values[id]
                force2 = np.dot(gradient, gradient)
                if force2 > 10E-4 and force2 < 10:
                    scale = -40
                    # transform.Identity will set the arrow to (1, 0, 0)
                    transform.Identity()
                    force = np.sqrt(force2)
                    unit_gradient = gradient / force
                    atom = self.__molecule.GetAtom(id)
                    position = atom.GetPosition()
                    # Translation has to be done before rotation!
                    transform.Translate(position)
                    # Rotate identity arrow (1,0,0) to direction of gradient
                    transform.RotateWXYZ(
                        np.degrees(np.arccos(unit_gradient[0])),
                        np.cross([1, 0, 0], unit_gradient)
                    )
                    # Scale by force
                    transform.Scale(scale * force, scale * force, scale * force)
                else:
                    transform.Scale(0.0, 0.0, 0.0)
            else:
                transform.Scale(0.0, 0.0, 0.0)
            self.__arrow_filter_list[id].Update()

    def __plug_in_new_molecule(self, molecule: vtkMolecule) -> None:
        self.__molecule = molecule
        self.__molecule_version = uuid1()
        self.__filter.SetInputData(self.__molecule)
        self.__style.molecule = self.__molecule
        self.__labels.set_molecule(self.__molecule)
        if not self.__disable_modification and \
                self.__molecule.GetNumberOfAtoms() != len(self.__arrow_filter_list):
            self.__create_force_arrows()
        self._atom_selection.set_molecule(self.__molecule)
        self._qm_selection.set_molecule(self.__molecule)
        self.set_selection(self.__selected_atoms)
        if self.__haptic_client is not None:
            self.__haptic_client.update_molecule(self.__molecule)
        if self.__must_show_depth_view():
            self.__depth_molecule_producer.SetOutput(self.__molecule)
        self.__update_atomic_charge_display()
        self.__render_molecule()

    @staticmethod
    def __create_selector(
        renderer: vtkRenderer, tolerance: float = 1e-6
    ) -> vtkSelectVisiblePoints:
        """
        Creates an instance of a class that selects visible points.
        """
        selector = vtkSelectVisiblePoints()
        selector.SetRenderer(renderer)
        selector.SetTolerance(tolerance)

        return selector

    def __add_layout(self) -> None:
        """
        Adds a zero margin layout with the viewer,
        """
        layout = QHBoxLayout(self)
        layout.setMargin(0)
        layout.addWidget(self.__interactor)
        self.setLayout(layout)

    def __load_from_atom_collection(
        self, atom_collection: Any, bond_order_collection: Union[Any, None] = None
    ) -> None:
        """
        Loads a molecule from an atom collection and an optional bond order collection.
        If no bond order collection is given, it is constructed based on distances.
        """
        self.__plug_in_new_molecule(atom_collection_to_molecule(atom_collection))
        if bond_order_collection is None:
            self.__set_bonds_based_on_distances(atom_collection)
        else:
            self.set_bonds(bond_order_collection)
        self.__update_selector()

    def __load_from_file(self, file: Path) -> None:
        """
        Loads a molecule from a file supported by scine_utilities
        """
        traj = None
        ending = file.suffix
        if ending == ".bin":
            traj = utils.io.read_trajectory(utils.io.TrajectoryFormat.Binary, str(file))
        elif ending == ".xyz":
            traj = utils.io.read_trajectory(utils.io.TrajectoryFormat.Xyz, str(file))
        if traj is not None:
            if len(traj) == 1:
                # just single frame, load as simple molecule
                atoms = utils.AtomCollection(traj.elements, traj[0])
                bonds = utils.BondOrderCollection()
            else:
                # display trajectory and then leave (generate no molecule)
                # but second window gives chance to save specific frame
                from scine_heron.molecule.molecule_video import MainVideo
                self.dialog = MainVideo(traj)
                self.dialog.show()
                return
        else:
            atoms, bonds = utils.io.read(str(file))
        if bonds.empty():
            self.__load_from_atom_collection(atoms, None)
        else:
            self.__load_from_atom_collection(atoms, bonds)

    def __set_bonds_based_on_distances(self, atom_collection: Any) -> None:
        bonds = utils.BondDetector.detect_bonds(atom_collection)
        self.set_bonds(bonds)
        self.__render_molecule()

    def set_bonds(self, bond_order_collection: Any) -> None:
        n = bond_order_collection.get_system_size()
        for i in range(n - 1):
            for j in range(i + 1, n):
                bond_id = self.__molecule.GetBondId(i, j)
                v = bond_order_collection.get_order(i, j)
                # vtk only supports integer orders
                self.__molecule.SetBondOrder(bond_id, int(round(v)))

    def __update_selector(self) -> None:
        """
        Updates the world tolerance of the class instance that
        selects the labels to display. Labels are located at the centers of atoms,
        and therefore are always hidden by the atom itself. By providing a
        tolerance which is approximately/at least the radius of the atom,
        we show those labels nonetheless.
        """
        self.__selector.SetToleranceWorld(
            self.__molecule_mapper.GetAtomicRadiusScaleFactor()
            * maximum_vdw_radius(self.__molecule)
        )

    def __update_molecule_style_if_necessary(self) -> None:
        """
        Updates the molecule style using from the status manager if the style
        has not been changed by displaying custom atom radii.
        """
        if (
            self.__molecule_mapper.GetAtomicRadiusType()
            == vtkMoleculeMapper.CustomArrayRadius
        ):
            return
        self.__update_molecule_style()

    def __update_molecule_style(self) -> None:
        """
        Change molecule style.
        """
        if self.__settings_status_manager.molecule_style == MoleculeStyle.BallAndStick:
            self.__molecule_mapper.UseBallAndStickSettings()
        elif self.__settings_status_manager.molecule_style == MoleculeStyle.VDWSpheres:
            self.__molecule_mapper.UseVDWSpheresSettings()
        elif (
            self.__settings_status_manager.molecule_style
            == MoleculeStyle.LiquoriceStick
        ):
            self.__molecule_mapper.UseLiquoriceStickSettings()
        elif self.__settings_status_manager.molecule_style == MoleculeStyle.Fast:
            self.__molecule_mapper.UseFastSettings()
        elif (
            self.__settings_status_manager.molecule_style
            == MoleculeStyle.PartialCharges
        ):
            self.__molecule_mapper.UseBallAndStickSettings()
        elif (
            self.__settings_status_manager.molecule_style
            == MoleculeStyle.ForceArrow
        ):
            self.__molecule_mapper.UseBallAndStickSettings()
        else:
            assert False, "Unknown molecule style type."
        self.__update_selector()
        self.__render_molecule()

    def __update_labels_style(self) -> None:
        """
        Change labels style.
        """
        self.__labels.display_labels_style(self.__settings_status_manager.labels_style)
        self.__render_molecule()

    def provide_data(self) -> vtkMolecule:
        """
        Returns the currently displayed molecule.
        """
        return self.__molecule_mapper.GetInput()

    def set_calc_gradient_in_loop(self, calc_gradient_in_loop: bool) -> None:
        """
        Set calc_gradient_in_loop flag in MoleculeInteractorStyle instance.
        """
        return self.__style.set_calc_gradient_in_loop(calc_gradient_in_loop)

    def display_array_via_colors(self, array: vtkDoubleArray) -> None:
        """
        Display the given array via atom colors. The array needs to contain
        exactly one scalar per atom.
        """
        assert (
            array.GetNumberOfValues() == self.__molecule.GetNumberOfAtoms()
        ), "The array needs to provide one scalar per atom."

        self.__display_colorbar_with_range(array.GetValueRange())
        self.__display_colors(self.__colorbar.GetLookupTable().MapScalars(array, 0, 0))

    def __display_colorbar_with_range(self, value_range: Tuple[float, float]) -> None:
        """
        Adds a colorbar with the given range to the display.
        """
        self.__colorbar.SetLookupTable(
            create_symmetric_color_transfer_function(value_range)
        )
        self.__renderer.AddActor2D(self.__colorbar)

    def __display_colors(self, colors: vtkUnsignedCharArray) -> None:
        """
        Display the given colors per atom. The array needs to contain
        exactly one color per atom.
        """
        assert (
            colors.GetNumberOfTuples() == self.__molecule.GetNumberOfAtoms()
        ), "The array needs to provide one color per atom."

        # we need to control the color mapping, otherwise the mapper uses a
        # color map suitable for atomic numbers
        self.__molecule_mapper.SetMapScalars(False)

        colors.SetName("scine_colors")
        self.__molecule.GetVertexData().AddArray(colors)
        self.__molecule_mapper.SetInputArrayToProcess(
            0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_VERTICES, "scine_colors"
        )

    def display_atomic_number_colors(self) -> None:
        """
        Switches the colors back to the default atomic number based colors.
        """
        self.__renderer.RemoveActor2D(self.__colorbar)
        self.__molecule_mapper.SetMapScalars(True)
        self.__molecule_mapper.SetInputArrayToProcess(
            0,
            0,
            0,
            vtkDataObject.FIELD_ASSOCIATION_VERTICES,
            self.__molecule.GetAtomicNumberArrayName(),
        )
        self.__molecule.GetVertexData().RemoveArray("scine_colors")

    def display_array_via_labels(self, array: vtkDoubleArray) -> None:
        """
        Display the given values as labels per atom.
        """
        assert (
            array.GetNumberOfValues() == self.__molecule.GetNumberOfAtoms()
        ), "The array needs to provide one scalar per atom."

        labels = vtkDoubleArray()
        labels.DeepCopy(array)
        labels.SetName("scine_labels")
        self.__molecule.GetVertexData().AddArray(labels)

    def display_style_labels(self) -> None:
        """
        Display the labels per atom as defined by the labels style.
        """
        self.__molecule.GetVertexData().RemoveArray("scine_labels")

    def display_array_via_radii(self, values: vtkDoubleArray) -> None:
        """
        Display the given radii per atom. The radii are rescaled to [0, m], where
        m is the maximum VDW radius of the molecule multiplied by the default atomic
        radius scale factor of the vtkMoleculeMapper.
        """
        assert (
            values.GetNumberOfValues() == self.__molecule.GetNumberOfAtoms()
        ), "The array needs to provide one radius per atom."

        radii = rescale_to_range(
            values,
            (
                0,
                maximum_vdw_radius(self.__molecule)
                * vtkMoleculeMapper().GetAtomicRadiusScaleFactor(),
            ),
        )
        radii.SetName("radii")
        self.__molecule.GetVertexData().AddArray(radii)
        self.__molecule_mapper.SetAtomicRadiusTypeToCustomArrayRadius()

    def display_atomic_number_radii(self) -> None:
        """
        Switches the radii back to the default atomic number based radii.
        """
        self.__update_molecule_style()

    def __render_molecule(self) -> None:
        """
        Render molecule.
        """
        self.__renderer.GetRenderWindow().Render()

    def add_atom_default_position(self, atomic_number: int) -> vtkMolecule:
        """
        Add an atom in a position given by the structural completion functions.
        """
        if len(self.__selected_atoms) == 0 and self.__molecule.GetNumberOfAtoms() > 0:
            self.__settings_status_manager.error_message = (
                "No selected atom, cannot determine position for new atom."
            )
            return

        atoms_to_consider = list(self.__selected_atoms)
        mol = self.__filter.GetOutput()
        for bond_id in range(mol.GetNumberOfBonds()):
            bond = mol.GetBond(bond_id)
            if bond.GetBeginAtomId() == atoms_to_consider[0]:
                atoms_to_consider.append(bond.GetEndAtomId())
            if bond.GetEndAtomId() == atoms_to_consider[0]:
                atoms_to_consider.append(bond.GetBeginAtomId())

        new_molecule = emf.build_molecule_with_new_atom_structural_completion(
            self.__molecule,
            atomic_number,
            atoms_to_consider,
            self.__settings_status_manager,
        )

        self.__plug_in_new_molecule(new_molecule)

    def has_atoms(self) -> bool:
        return bool(self.__molecule.GetNumberOfAtoms() > 0)

    def remove_selected_atoms(self) -> None:
        new_molecule = emf.build_molecule_without_removed_atoms(
            self.__molecule, self.__selected_atoms
        )
        self.__selected_atoms = []
        if not self.__disable_modification:
            self.set_selection(self.__selected_atoms)
        self.__plug_in_new_molecule(new_molecule)

    def append_selection(self, atoms: Optional[List[int]]) -> None:
        """
        Only works if a selection has already been made because of a round-about way to deselect atoms.
        """
        if len(self.__selected_atoms) == 0:
            return
        if atoms:
            for atom in atoms:
                if atom is None or atom in self.__selected_atoms:
                    return
                self.__selected_atoms.append(atom)
        if not self.__disable_modification:
            self.set_selection(self.__selected_atoms)

    def get_atom_collection(self) -> utils.AtomCollection:
        return molecule_to_atom_collection(self.__molecule)

    def get_energy(self, seconds=0.5) -> Optional[float]:
        if self.__energy_status_manager is None:
            return None
        return self.__energy_status_manager.get_latest_energy(seconds)

    def single_point_calculation(self) -> CustomResult:
        if self.__molecule.GetNumberOfAtoms() == 0:
            self.__settings_status_manager.error_message = "Cannot carry out calculation with no loaded molecule"
            return CustomResult()

        # we simply want to create a separate instance of a Scine Calculator to execute a single point calculation
        # basic logic is contained in this function
        def _impl(calculator_args: Tuple[str, str],
                  calculator_settings: Dict[str, Any],
                  bond_display: str,
                  molecule_version: int,
                  molecule: vtkMolecule,
                  results: ListProxy) -> None:

            method_family, program = calculator_args
            calculation_client = ScineCalculatorWrapper(
                method_family, program, hessian_required=False, settings=calculator_settings,
            )
            atoms = molecule_to_atom_collection(molecule)
            try:
                calculation_client.set_bond_orders_flag(bond_display != "distance")
                calculation_client.update_system(molecule_version, [str(e) for e in atoms.elements], atoms.positions)
                # Carry out calculations
                result = calculation_client.calculate_custom_result()
            except RuntimeError as error:
                result = CustomResult()
                result.error_msg = str(error)
            result.make_pickleable()
            results.append(result)

        # we do this ugly multiprocessing hack, because the following scenario is unsafe:
        # creating the first instance of a calculator here, which may load openmpi libraries if available
        # destroying the calculator
        # forking the process that did this later for continuous interactive updates
        # constructing a new calculator that again utilizes openmpi
        # because some references to the originally loaded libraries may still be in memory,
        # this can lead to undefined behavior
        # we avoid this by forking here and doing the single point calculation in a separate process
        with multiprocessing.Manager() as manager:
            default = CustomResult()
            default.make_pickleable()
            results: ListProxy = manager.list([default])

            p = multiprocessing.Process(target=_impl,
                                        args=(self.__settings_status_manager.get_calculator_args(),
                                              self.__settings_status_manager.get_calculator_settings(),
                                              self.__settings_status_manager.bond_display,
                                              self.__molecule_version,
                                              self.__molecule,
                                              results
                                              )
                                        )
            p.start()
            p.join()
            if len(results) <= 1:
                return default
            result = results[1]
            if result is not None:
                if result.error_msg:
                    self.__settings_status_manager.error_message = result.error_msg
                elif result.info_msg:
                    self.__settings_status_manager.info_message = result.info_msg
            else:
                result = default
            return result

    def get_selection(self) -> List[int]:
        return self._atom_selection.get_selection_data()

    def set_selection(self, selection: List[int], color: Optional[Tuple[float, float, float]] = None):
        if color is None:
            self._atom_selection.back_to_default_color()
        else:
            self._atom_selection.change_color(*color)
        self._atom_selection.set_selection(selection)
        self.__selected_atoms = selection
        self.__render_molecule()

    def make_indices_opaque(self, selected_indices: List[int],
                            _exclude_mode: bool = False,
                            _opacity_percent: float = 0.5):
        self._qm_selection.set_selection(selected_indices)
        """
        # we need to control the color mapping, otherwise the mapper uses a
        # color map suitable for atomic numbers
        self.__molecule_mapper.SetMapScalars(False)
        n = self.__molecule.GetNumberOfAtoms()
        atomic_numbers_data = \
            self.__molecule.GetVertexData().GetArray(self.__molecule.GetAtomicNumberArrayName())
        table = vtkPeriodicTable()
        colors = vtkUnsignedCharArray()
        colors.SetName("opacity")
        colors.SetNumberOfComponents(4)
        colors.SetNumberOfTuples(n)
        for i in range(n):
            rgb_percent = table.GetDefaultRGBTuple(int(atomic_numbers_data.GetTuple(i)[0]))
            in_indices: bool = i in selected_indices
            if in_indices:
                this_opacity = 1 if exclude_mode else opacity_percent
            else:
                this_opacity = opacity_percent if exclude_mode else 1
            colors.SetTuple(i, [p * 255 for p in list(rgb_percent) + [this_opacity]])
        self.__molecule.GetVertexData().AddArray(colors)
        self.__molecule_mapper.SetInputArrayToProcess(
            0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_VERTICES, "opacity"
        )
        self.__render_molecule()
        """

    def remove_opacity(self) -> None:
        self._qm_selection.set_selection([])
        """
        self.__molecule_mapper.SetMapScalars(True)
        self.__molecule_mapper.SetInputArrayToProcess(
            0,
            0,
            0,
            vtkDataObject.FIELD_ASSOCIATION_VERTICES,
            self.__molecule.GetAtomicNumberArrayName(),
        )
        self.__molecule.GetVertexData().RemoveArray("opacity")
        self.__render_molecule()
        """

    def __create_force_arrows(self):
        n_atoms = self.__molecule.GetNumberOfAtoms()
        self.__arrow_filter_list = []
        for _id in range(n_atoms):
            force_vector = vtkArrowSource()
            force_vector_mapper = vtkPolyDataMapper()
            transformFilter = vtkTransformPolyDataFilter()
            transformFilter.SetInputConnection(force_vector.GetOutputPort())
            transform = vtkTransform()
            transformFilter.SetTransform(transform)
            transform.Scale(0.0, 0.0, 0.0)
            force_vector_mapper.SetInputConnection(transformFilter.GetOutputPort())
            force_vector_actor = vtkActor()
            force_vector_actor.SetMapper(force_vector_mapper)
            self.__renderer.AddActor(force_vector_actor)
            self.__arrow_filter_list.append(transformFilter)
