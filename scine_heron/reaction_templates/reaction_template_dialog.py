#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional, List

from PySide2.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QFileDialog,
    QLineEdit
)
from PySide2.QtCore import QObject

from scine_heron.reaction_templates.reaction_template_storage import ReactionTemplateStorage
from scine_heron.utilities import (
    color_axis,
    color_figure,
    get_font,
    get_primary_line_color,
    get_secondary_line_color,
    get_color_by_key,
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from networkx import Graph, spring_layout
import numpy as np


class RTGraphCanvas(FigureCanvasQTAgg):
    def __init__(self, width=5, height=4):
        self.fig = Figure(figsize=(width, height))
        self.ax1 = self.fig.add_subplot(1, 1, 1)
        color_figure(self.fig)
        self.font = get_font()
        color_axis(self.ax1)
        self.ax1.axis('off')
        super(RTGraphCanvas, self).__init__(self.fig)

    def plot_graph(self, graph: Graph, mapping: dict) -> None:
        self.ax1.clear()

        fixed_pos = {
            0: (-0.05, 0.0),
            1: (+0.05, 0.0)
        }
        r_mol = 0.1
        n_lhs_mol = len(mapping['lhs']['mol'])
        tmp_space = np.linspace(-np.pi / 4, np.pi / 4, n_lhs_mol + 2)
        for i, mol in enumerate(mapping['lhs']['mol']):
            angle = tmp_space[i + 1]
            x = -r_mol * np.cos(angle) - 0.05
            y = -r_mol * np.sin(angle)
            fixed_pos[mol] = (x, y)
        n_rhs_mol = len(mapping['rhs']['mol'])
        tmp_space = np.linspace(-np.pi / 4, np.pi / 4, n_rhs_mol + 2)
        for i, mol in enumerate(mapping['rhs']['mol']):
            angle = tmp_space[i + 1]
            x = r_mol * np.cos(angle) + 0.05
            y = r_mol * np.sin(angle)
            fixed_pos[mol] = (x, y)
        r_frag = 0.2
        lhs_frag_bounds = np.linspace(-np.pi / 4, np.pi / 4, n_lhs_mol + 1)
        for i, mol in enumerate(mapping['lhs']['frag']):
            tmp_space = np.linspace(lhs_frag_bounds[i], lhs_frag_bounds[i + 1], len(mol) + 2)
            for j, frag in enumerate(mol):
                angle = tmp_space[j + 1]
                x = -r_frag * np.cos(angle) - 0.05
                y = -r_frag * np.sin(angle)
                fixed_pos[frag] = (x, y)
        rhs_frag_bounds = np.linspace(-np.pi / 4, np.pi / 4, n_rhs_mol + 1)
        for i, mol in enumerate(mapping['rhs']['frag']):
            tmp_space = np.linspace(rhs_frag_bounds[i], rhs_frag_bounds[i + 1], len(mol) + 2)
            for j, frag in enumerate(mol):
                angle = tmp_space[j + 1]
                x = r_frag * np.cos(angle) + 0.05
                y = r_frag * np.sin(angle)
                fixed_pos[frag] = (x, y)
        r_atom = 0.35
        for i, mol in enumerate(mapping['lhs']['atoms']):
            atom_bounds = np.linspace(lhs_frag_bounds[i], lhs_frag_bounds[i + 1], len(mol) + 1)
            for j, frag in enumerate(mol):
                tmp_space = np.linspace(atom_bounds[j], atom_bounds[j + 1], len(frag) + 2)
                for k, atom in enumerate(frag):
                    angle = tmp_space[k + 1]
                    x = -r_atom * np.cos(angle) - 0.05
                    y = -r_atom * np.sin(angle)
                    fixed_pos[atom] = (x, y)
        for i, mol in enumerate(mapping['rhs']['atoms']):
            atom_bounds = np.linspace(rhs_frag_bounds[i], rhs_frag_bounds[i + 1], len(mol) + 1)
            for j, frag in enumerate(mol):
                tmp_space = np.linspace(atom_bounds[j], atom_bounds[j + 1], len(frag) + 2)
                for k, atom in enumerate(frag):
                    angle = tmp_space[k + 1]
                    x = r_atom * np.cos(angle) + 0.05
                    y = r_atom * np.sin(angle)
                    fixed_pos[atom] = (x, y)
        pos = spring_layout(graph, dim=2, seed=42, k=0.1, pos=fixed_pos, fixed=fixed_pos.keys())

        for u, v in graph.edges():
            w = graph.get_edge_data(u, v)['weight']
            if w < 5 or w == 8:
                color = get_secondary_line_color()
            elif w in [6, 7]:
                color = get_color_by_key('reactionColor')
            else:
                color = get_primary_line_color()
            linestyle = 'solid'
            if w in [6, 8]:
                linestyle = ':'
            self.ax1.plot(*np.array([(pos[u], pos[v]), ]).T, linestyle=linestyle, color=color, zorder=0)
        # edge_xyz = np.array([(pos[u], pos[v]) for u, v in graph.edges()])

        # # Plot the edges
        # for vizedge in edge_xyz:
        #     self.ax1.plot(*vizedge.T, color=get_primary_line_color(), zorder=0)

        # Plot the nodes, one type at a time
        reaction = np.array([pos[0], pos[1]])
        tmp = []
        for mol in (mapping['lhs']['mol'] + mapping['rhs']['mol']):
            tmp.append(pos[mol])
        molecules = np.array(tmp)
        tmp = []
        for mol in (mapping['lhs']['frag'] + mapping['rhs']['frag']):
            for frag in mol:
                tmp.append(pos[frag])
        fragments = np.array(tmp)
        tmp = []
        atom_indices = []
        for mol in (mapping['lhs']['atoms'] + mapping['rhs']['atoms']):
            for frag in mol:
                for atom in frag:
                    tmp.append(pos[atom])
                    atom_indices.append(atom)
        atoms = np.array(tmp)
        self.ax1.scatter(*reaction.T, s=300, c=get_color_by_key('reactionColor'), zorder=1)
        for p in reaction:
            self.ax1.text(
                p[0], p[1], 'R',
                horizontalalignment='center', verticalalignment='center',
                size='medium', color=get_color_by_key('primaryTextColor'),
            )
        self.ax1.scatter(*molecules.T, s=300, c=get_color_by_key('compoundColor'), zorder=1)
        for p in molecules:
            self.ax1.text(
                p[0], p[1], 'M',
                horizontalalignment='center', verticalalignment='center',
                size='medium', color=get_color_by_key('primaryTextColor'),
            )
        self.ax1.scatter(*fragments.T, s=300, c=get_color_by_key('structureColor'), zorder=1)
        for p in fragments:
            self.ax1.text(
                p[0], p[1], 'F',
                horizontalalignment='center', verticalalignment='center',
                size='medium', color=get_color_by_key('primaryTextColor'),
            )
        self.ax1.scatter(*atoms.T, s=400, c=get_secondary_line_color(), zorder=1)
        for i, p in zip(atom_indices, atoms):
            self.ax1.text(
                p[0], p[1], graph.nodes[i]['at'],
                horizontalalignment='center', verticalalignment='center',
                size='medium', color=get_color_by_key('primaryTextColor'),
            )
        self.ax1.axis('off')
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()


class TemplateTreeWidget(QTreeWidget):
    def __init__(self, parent: QObject):
        QTreeWidget.__init__(self, parent)

    # def contextMenuEvent(self, event):
    #     self.currentItem().contextMenuEvent(event)


class TemplateTreeWidgetItem(QTreeWidgetItem):

    def __init__(self, parent: QObject, info: List[str]):
        QTreeWidgetItem.__init__(self, parent, info, type=QTreeWidgetItem.UserType)
        self.id_string_list = [info]
        self.item_type = info


class ReactionTemplateDialog(QWidget):
    def __init__(
            self, parent: QWidget,
            storage: ReactionTemplateStorage,
            window_title: str = "Reaction Template Storage",
    ) -> None:
        super(ReactionTemplateDialog, self).__init__(parent)
        self.setWindowTitle(window_title)

        # Class members for storage of data
        self.__storage = storage

        # Class members for widgets
        self.__layout = QVBoxLayout()
        self.__button_box = QWidget()
        self.__button_box_layout = QHBoxLayout()
        self.__button_clear = QPushButton("Clear Storage")
        self.__button_add = QPushButton("Add From File")
        self.__button_load = QPushButton("Load From File")
        self.__button_save = QPushButton("Save To File")

        self.__browsing_box = QWidget()
        self.__browsing_box_layout = QHBoxLayout()
        self.__template__tree = QTreeWidget(self)
        self.__template__tree.setColumnCount(1)
        self.__template__tree.setHeaderHidden(True)
        self.__template__tree.itemClicked.connect(self.__focus_graph)  # pylint: disable=no-member
        self.__template__tree.itemActivated.connect(self.__focus_graph)  # pylint: disable=no-member
        self.__graph_canvas = RTGraphCanvas()

        # Create layout and add widgets
        self.__button_box_layout.addWidget(self.__button_clear)
        self.__button_box_layout.addWidget(self.__button_add)
        self.__button_box_layout.addWidget(self.__button_load)
        self.__button_box_layout.addWidget(self.__button_save)

        self.__button_box.setLayout(self.__button_box_layout)
        self.__layout.addWidget(self.__button_box)

        self.__searchbar = QLineEdit()
        self.__searchbar.textChanged.connect(self.update_tree_view)  # pylint: disable=no-member
        self.__layout.addWidget(self.__searchbar)

        self.__browsing_box_layout.addWidget(self.__template__tree)
        self.__browsing_box_layout.addWidget(self.__graph_canvas)

        self.__browsing_box.setLayout(self.__browsing_box_layout)
        self.__layout.addWidget(self.__browsing_box)

        # Connect functions to buttons and widgets
        self.__button_clear.clicked.connect(self.__press_clear)  # pylint: disable=no-member
        self.__button_add.clicked.connect(self.__press_add)  # pylint: disable=no-member
        self.__button_load.clicked.connect(self.__press_load)  # pylint: disable=no-member
        self.__button_save.clicked.connect(self.__press_save)  # pylint: disable=no-member

        # Set dialog layout
        self.setLayout(self.__layout)
        self.update_tree_view()

    def update_tree_view(self):
        self.__template__tree.clear()
        self.__tree_items = []
        for rt_id in self.__storage.get_template_ids():
            search_string = self.__searchbar.text().strip()
            if search_string and search_string not in rt_id:
                continue
            base_item = TemplateTreeWidgetItem(self.__template__tree, [f"{rt_id}"])
            self.__tree_items.append(base_item)
        if self.__tree_items:
            self.__focus_graph(self.__tree_items[0], None)
        self.__template__tree.insertTopLevelItems(0, self.__tree_items)

    def __press_clear(self) -> None:
        self.__storage.clear()
        self.update_tree_view()

    def __get_reaction_template_database_file(self) -> Optional[str]:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open File"),  # type: ignore[arg-type]
            "",
            self.tr("Reaction Template Database (*rtdb.pickle.obj)"),  # type: ignore[arg-type]
        )
        if filename:
            return str(filename)
        return None

    def __press_add(self) -> None:
        filename = self.__get_reaction_template_database_file()
        if filename:
            self.__storage.add_database(filename)
            self.update_tree_view()

    def __press_load(self) -> None:
        filename = self.__get_reaction_template_database_file()
        if filename:
            self.__storage.load_database(filename)
            self.update_tree_view()

    def __press_save(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Open File"),  # type: ignore[arg-type]
            "",
            self.tr("Reaction Template Database (*rtdb.pickle.obj)"),  # type: ignore[arg-type]
        )
        if filename:
            self.__storage.save_database(filename)

    def __draw_rt_graph(self, rt_id: str) -> None:
        template = self.__storage.get_template(rt_id)
        if template:
            graph, mapping = template.get_networkx_graph()
            self.__graph_canvas.plot_graph(graph, mapping)

    def __focus_graph(self, item: TemplateTreeWidgetItem, _):
        rt_id = item.id_string_list[0][0]
        self.__draw_rt_graph(rt_id)
