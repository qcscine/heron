#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Any, Optional, Dict, Set, TYPE_CHECKING, Tuple

from PySide2.QtWidgets import (
    QWidget,
    QMenu,
    QLineEdit,
    QLabel,
    QVBoxLayout,
    QDialog,
    QScrollArea,
)
from PySide2.QtCore import Qt, QObject
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal

from scine_utilities import AtomCollection
from scine_utilities import core, io, settings_names

from scine_heron.calculators.create_calculator_widget import CreateCalculatorWidget
from scine_heron.calculators.calculator import CalculatorLoadingFailed
from scine_heron.containers.buttons import TextPushButton
from scine_heron.containers.layouts import HorizontalLayout, VerticalLayout
from scine_heron.io.text_box import yes_or_no_question
from scine_heron.io.file_browser_popup import get_load_file_name
from scine_heron.containers.collapsible_list import CollapsibleList, CollapsibleListItem
from scine_heron.molecule.molecule_widget import MoleculeWidget
from scine_heron.molecular_viewer import get_mol_viewer_tab
from scine_heron.settings.dict_option_widget import DictOptionWidget
from scine_heron.utilities import write_info_message


class CalculatorContainer(QWidget):
    """
    Container Widget to handle ReaDuct systems / Scine Calculators
    """
    default_name = "enumeration"
    new_system_added = Signal(str)

    def __init__(self, parent: Optional[QObject]) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout()
        self._layout.setAlignment(Qt.AlignTop)

        self._default_method_family = "PM6"
        self._default_program = "Any"
        self._general_settings: Dict[str, Any] = {}
        self._names: Set[str] = set()

        # calc name
        self.name_edit = QLineEdit(self.default_name)
        name_layout = HorizontalLayout([QLabel("Name:"), self.name_edit])
        self._layout.addLayout(name_layout)

        # buttons
        self.molecular_viewer_add_button = TextPushButton("Add from molecular viewer", self.add_from_viewer)
        file_add_button = TextPushButton("Add from file", self.add_from_file)
        settings_button = TextPushButton("Default Settings", self.show_settings_widget)
        self._layout.addLayout(HorizontalLayout([self.molecular_viewer_add_button, file_add_button, settings_button]))

        # tree
        self._layout.addWidget(QLabel("Existing Systems:"))
        self.tree = CalculatorListWidget(self)
        self._scroll_area = QScrollArea()
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setWidget(self.tree)
        self._scroll_area.setMinimumHeight(350)
        self._layout.addWidget(self._scroll_area)

        # viewer
        self._layout.addStretch()
        self._mol_widget = MoleculeWidget(parent=self, disable_modification=True)
        self._layout.addWidget(self._mol_widget)

        self.setLayout(self._layout)

    def get_systems(self) -> Dict[str, core.Calculator]:
        systems = {}
        for item in self.tree:
            systems[item.name] = item.get_calculator()
        return systems

    def get_augmented_systems(self) -> Dict[str, Tuple[str, str, core.Calculator]]:
        systems = {}
        for item in self.tree:
            method_family, program = item.get_calculator_args()
            systems[item.name] = (method_family, program, item.get_calculator())
        return systems

    def focus(self):
        item = self.tree.current_item()
        self._scroll_area.ensureWidgetVisible(item)
        self._scroll_area.updateGeometry()
        if item is not None:
            structure = item.get_structure()
            if structure is not None:
                self._mol_widget.update_molecule(atoms=structure)
                self.updateGeometry()

    def show_settings_widget(self):
        frame = QDialog(self)
        method_family_edit = QLineEdit(self._default_method_family)
        mf_layout = HorizontalLayout([QLabel("Method family:"), method_family_edit])
        program_edit = QLineEdit(self._default_program)
        program_layout = HorizontalLayout([QLabel("Program:"), program_edit])
        method_family_edit.returnPressed.connect(program_edit.setFocus)  # pylint: disable=no-member
        method_family_edit.returnPressed.connect(program_edit.selectAll)  # pylint: disable=no-member
        suggestions = [s for s in dir(settings_names) if not s.startswith("_")]
        settings_widget = DictOptionWidget(options=self._general_settings, parent=frame,
                                           add_close_button=False, allow_additions=True,
                                           addition_suggestions=suggestions)
        settings_widget.setMinimumHeight(200)
        layout = VerticalLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.add_layouts([mf_layout, program_layout])
        layout.add_widgets([
            QLabel("Settings for all new calculators:"),
            settings_widget,
            TextPushButton("Ok", frame.reject)
        ])
        frame.setLayout(layout)
        frame.exec_()
        self._default_method_family = method_family_edit.text()
        self._default_program = program_edit.text()
        self._general_settings = settings_widget.get_widget_data()

    def _determine_name(self) -> str:
        name_line = self.name_edit.text()
        if name_line != self.default_name:
            return name_line
        return str(len(self.tree))

    def add_item(self, method_family: str, program: str, atoms: AtomCollection, settings: Dict[str, Any],
                 name: Optional[str] = None):
        if name is None:
            name = self._determine_name()
        if name in self._names:
            replace_name = yes_or_no_question(self, f"System '{name}' does already exist. Do you want to replace it")
            if replace_name:
                write_info_message(f"Replacing {name}")
                item = self.tree.get_item_by_name(name)
                if item is None:
                    raise RuntimeError(f"Internal name management error with {name} and {self._names}")
                self.tree.remove_widget(item)
            else:
                write_info_message("No system was added")
                return
        else:
            self._names.add(name)
        try:
            content = CreateCalculatorWidget(method_family=method_family, program=program, atoms=atoms,
                                             settings=settings)
            new_item = CollapsibleCalculatorListItem(self.tree, name, content)
        except CalculatorLoadingFailed:
            self._names.remove(name)
        else:
            self.tree.add_widget(new_item)
            self.tree.set_current_item(new_item)
            self.focus()
            self.new_system_added.emit(name)

    def add_from_viewer(self) -> None:
        tab = get_mol_viewer_tab(want_atoms_there=True)
        if tab is None or tab.mol_widget is None:
            return
        mol_viewer_calculator_edit = tab.create_calculator_widget
        atoms = tab.mol_widget.get_atom_collection()  # ensures that we get the current atoms
        method_family = mol_viewer_calculator_edit.method_family_edit.text()
        program = mol_viewer_calculator_edit.program_edit.text()
        if method_family != self._default_method_family or program != self._default_program:
            write_info_message("Taking method family and program from molecular viewer")
        mol_viewer_settings = mol_viewer_calculator_edit.get_settings()
        if any(default_key in mol_viewer_settings for default_key in self._general_settings.keys()):
            write_info_message("Duplicate keys in given defaults and molecular viewer. Given defaults overrule")
        settings = {**mol_viewer_calculator_edit.get_settings(), **self._general_settings}  # type: ignore
        self.add_item(method_family=method_family, program=program, atoms=atoms, settings=settings)

    def add_from_file(self) -> None:
        filename = get_load_file_name(self, "Structure", ["xyz", "mol", "pdb"])
        if filename is None:
            return
        atoms, bonds = io.read(str(filename))
        self.add_item(self._default_method_family, self._default_program, atoms, self._general_settings)
        if not bonds.empty():
            self._mol_widget.set_bonds(bonds)


class CollapsibleCalculatorListItem(CollapsibleListItem):

    def __init__(self, parent: QWidget, name: str, content: CreateCalculatorWidget) -> None:  # for typing
        super().__init__(parent, name, content)
        self.content = content

    def get_calculator_args(self):
        return self.content.get_calculator_args()

    def get_calculator(self):
        return self.content.get_calculator()

    def get_structure(self):
        return self.content.get_structure()

    def contextMenuEvent(self, event):
        menu = QMenu()
        show_in_mol_view = menu.addAction('Move to Molecular Viewer')
        _ = menu.addAction('Close Menu')
        action = menu.exec_(event.globalPos())  # type: ignore
        if action == show_in_mol_view:
            tab = get_mol_viewer_tab(want_atoms_there=False)
            if tab is not None:
                atoms = self.content.get_structure()
                if atoms is not None:
                    tab.update_molecule(atoms=atoms)
                    tab.layout().replaceWidget(tab.create_calculator_widget, self.content)


class CalculatorListWidget(CollapsibleList):

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self._widgets: Dict[str, CollapsibleCalculatorListItem] = {}
