#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Any, List, Sequence, Tuple, Union

from PySide2.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QSizePolicy, QWidget

from scine_utilities import AtomCollection

import scine_heron.config as config
from scine_heron.styling.delegates import CustomLightDelegate
from scine_heron.molecular_viewer import get_mol_viewer_tab
from scine_heron.utilities import write_info_message, copy_text_to_clipboard


class TreeWidget(QTreeWidget):
    """
    Wrapper around the standard QTreeWidget that holds a TreeWidgetItem and
    propagates some camera information and focus actions.
    """

    def __init__(self, parent: QWidget):
        from .current_selection import SelectionTab
        super().__init__(parent)
        self._parent: SelectionTab = parent
        self.itemClicked.connect(self.focus)  # pylint: disable=no-member
        self.itemActivated.connect(self.focus)  # pylint: disable=no-member
        self.setMinimumHeight(250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()
        if config.MODE in config.LIGHT_MODES:
            self.setItemDelegate(CustomLightDelegate())

    def insertTopLevelItems(self, index: int, items: Sequence) -> None:
        super().insertTopLevelItems(index, items)
        self._parent.reset_camera()

    def contextMenuEvent(self, event):
        self.currentItem().contextMenuEvent(event)

    def focus(self, item: QTreeWidgetItem, _: Any) -> None:
        self._parent.display_atoms_with_sites(item.atoms, item.indices)


class TreeWidgetItem(QTreeWidgetItem):
    """
    A wrapper around the standard QTreeWidgetItem that holds the name, a structure, and reactive indices.
    It is meant to be plugged into the TreeWidget.
    """

    def __init__(self, parent: Union[TreeWidget, QTreeWidgetItem], info: List[str], atoms: AtomCollection,
                 indices: List[int]) -> None:
        """
        Construct the item

        Parameters
        ----------
        parent : Union[TreeWidget, QTreeWidgetItem]
            Should be the TreeWidget or another TreeWidgetItem, not generic
            (not possible currently because of backwards compatibility)
        info : List[str]
            The information to be displayed in the tree, from which the type and name are extracted
        atoms : AtomCollection
            The structure
        indices : List[int]
            The reactive sites of the structure
        """
        super().__init__(parent, info, type=QTreeWidgetItem.UserType)
        self._parent = parent
        assert len(info) == 1
        self.item_type = info[0].split('(')[0].strip()
        id_string = info[0].split('(')[1][:-1]
        self.names: Tuple[str, ...] = tuple([s.strip() for s in id_string.split("-")])
        self.atoms = atoms
        self.indices = indices

    def contextMenuEvent(self, event):
        menu = QMenu()
        show_in_mol_view = menu.addAction('Move to Interactive')
        show_all_reactive_sites = menu.addAction('Display all reactive sites')
        copy_names = menu.addAction('Copy ID')
        _ = menu.addAction('Close Menu')
        action = menu.exec_(event.globalPos())  # type: ignore
        if action == show_in_mol_view:
            tab = get_mol_viewer_tab(want_atoms_there=False)
            if tab is not None:
                tab.update_molecule(atoms=self.atoms)
                tab.mol_widget.set_selection(self.indices)
        elif action == show_all_reactive_sites:
            self.show_all_sites()
        elif action == copy_names:
            copy_text_to_clipboard("-".join(self.names))

    def show_all_sites(self):
        """
        Combine all reactive sites of individual complexes and display them all at once (with deduplication).
        This is useful to get a quick overview of the reactive sites of a structure to possibly adapt the
        selection.
        """
        if not self.indices:
            write_info_message("No reactive sites")
            return
        if "Structure" in self.item_type:
            self._parent.show_all_sites()
        else:
            # none structure item should hold all indices as indices
            self._parent.focus(self, None)

    def focus(self, item: QTreeWidgetItem, _: Any) -> None:
        self._parent.focus(item, _)
