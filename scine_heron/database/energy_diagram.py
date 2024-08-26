#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from typing import Optional
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


class EnergyDiagram(object):
    """
    This class has been derived and adapted from https://github.com/giacomomarchioro/PyEnergyDiagrams.
    """

    # --- Energy profile diagram---
    # This is a simple script to plot energy profile diagram using matplotlib.
    # autopep8: off
    # E|          4__       # noqa: W605,W1401
    # n|   2__    /  \      # noqa: W605,W1401
    # e|1__/  \__/5   \     # noqa: W605,W1401
    # r|  3\__/       6\__  # noqa: W605,W1401
    # g|
    # y|
    # autopep8: on

    def __init__(self, aspect='equal'):
        # plot parameters
        self.ratio = 1.6181
        self.dimension = 'auto'
        self.space = 'auto'
        self.offset = 'auto'
        self.offset_ratio = 0.02
        self.color_bottom_text = 'black'
        self.aspect = aspect
        self.round_energies_at_digit = "keep all digits"
        self.top_text_fontsize = "medium"
        self.bottom_text_fontsize = "medium"
        self.right_text_fontsize = "medium"
        self.left_text_fontsize = "medium"
        # data
        self.pos_number = 0
        self.energies = []
        self.positions = []
        self.colors = []
        self.alphas = []
        self.top_texts = []
        self.bottom_texts = []
        self.left_texts = []
        self.right_texts = []
        self.links = []
        self.arrows = []
        self.electons_boxes = []
        self.level_linestyles = []
        self.level_linewidths = []
        # matplotlib figure handlers
        self.fig = None
        self.ax = None

    def add_level(self, energy, bottom_text='', position=None, color='k', alpha=1.0,
                  top_text='Energy', right_text='', left_text='', linestyle='solid',
                  linewidth=1):
        """
        Method of ED class
        This method add a new energy level to the plot.

        Parameters
        ----------
        energy : int
                 The energy of the level in Kcal mol-1
        bottom_text  : str
                The text on the bottom of the level (label of the level)
                (default '')
        position  : str
                The position of the level in the plot. Keep it empty to add
                the level on the right of the previous level use 'last' as
                argument for adding the level to the last position used
                for the level before.
                An integer can be used for adding the level to an arbitrary
                position.
                (default  None)
        color  : str
                Color of the level  (default  'k')
        alpha  : float
                Transparency of the level (default  1.0)
        top_text  : str
                Text on the top of the level. By default it will print the
                energy of the level. (default  'Energy')
        right_text  : str
                Text at the right of the level. (default  '')
        left_text  : str
                Text at the left of the level. (default  '')
        linestyle  : str
                The linestyle of the level, one of the following values:
                'solid', 'dashed', 'dashdot', 'dotted' (default  'solid')




        Returns
        -------
        Append to the class data all the information regarding the level added
        """

        if position is None:
            position = self.pos_number + 1
            self.pos_number += 1
        elif isinstance(position, (int, float)):
            pass
        elif position == 'last' or position == 'l':
            position = self.pos_number
        else:
            raise ValueError(
                "Position must be None or 'last' (abr. 'l') or in case an integer or float specifing the position. " +
                "It was: %s" % position)
        if top_text == 'Energy':
            if self.round_energies_at_digit == "keep all digits":
                top_text = energy
            else:
                top_text = round(energy, self.round_energies_at_digit)

        link = []
        self.colors.append(color)
        self.alphas.append(alpha)
        self.energies.append(energy)
        self.positions.append(position)
        self.top_texts.append(top_text)
        self.bottom_texts.append(bottom_text)
        self.left_texts.append(left_text)
        self.right_texts.append(right_text)
        self.links.append(link)
        self.level_linestyles.append(linestyle)
        self.level_linewidths.append(linewidth)
        self.arrows.append([])

    def add_arrow(self, start_level_id, end_level_id):
        """
        Method of ED class
        Add a arrow between two energy levels using IDs of the level. Use
        self.plot(show_index=True) to show the IDs of the levels.

        Parameters
        ----------
        start_level_id : int
                 Starting level ID
        end_level_id : int
                 Ending level ID

        Returns
        -------
        Append arrow to self.arrows

        """
        self.arrows[start_level_id].append(end_level_id)

    def add_link(self, start_level_id, end_level_id,
                 color='k',
                 ls='--',
                 linewidth=1,
                 alpha=1.0
                 ):
        """
        Method of ED class
        Add a link between two energy levels using IDs of the level. Use
        self.plot(show_index=True) to show the IDs of the levels.

        Parameters
        ----------
        start_level_id : int
                 Starting level ID
        end_level_id : int
                 Ending level ID
        color : str
                color of the line
        ls : str
                line styple e.g. -- , ..
        linewidth : int
                line width
        alpha : float
                alpha

        Returns
        -------
        Append link to self.links

        """
        self.links[start_level_id].append((end_level_id, ls, linewidth, color, alpha))

    def plot(self, show_IDs=False, ylabel="Electronic Energy / kJ mol$^{-1}$", ax: Optional[plt.Axes] = None,
             ylimits=None):
        """
        Method of ED class
        Plot the energy diagram. Use show_IDs=True for showing the IDs of the
        energy levels and allowing an easy linking.

        Parameters
        ----------
        show_IDs : bool
            show the IDs of the energy levels
        ylabel : str
            The label to use on the left-side axis. "El. Energy / $kJ$ $mol^{-1}$" by default.
        ax : plt.Axes
            The axes to plot onto. If not specified, a Figure and Axes will be
            created for you.

        Returns
        -------
        fig (plt.figure) and ax (fig.add_subplot())
        """

        # Create a figure and axis if the user didn't specify them.
        if not ax:
            self.fig = plt.figure()
            self.ax = self.fig.add_subplot(111, aspect=self.aspect)
        # Otherwise register the axes and figure the user passed.
        else:
            self.ax = ax
            self.fig = ax.figure

            # Constrain the target axis to have the proper aspect ratio
            self.ax.set_aspect(self.aspect)

        self.ax.set_ylabel(ylabel)
        # self.ax.axes.get_xaxis().set_visible(False)
        self.ax.set_xticks([])
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_visible(False)

        self.__auto_adjust()

        data = list(zip(self.energies,  # 0
                        self.positions,  # 1
                        self.bottom_texts,  # 2
                        self.top_texts,  # 3
                        self.colors,  # 4
                        self.right_texts,  # 5
                        self.left_texts,  # 6
                        self.level_linestyles,  # 7
                        self.level_linewidths,  # 8
                        self.alphas)  # 9
                    )
        for level in data:
            start = level[1] * (self.dimension + self.space)
            self.ax.plot([start, start + self.dimension], [level[0], level[0]],
                         color=level[4],
                         alpha=level[9],
                         linestyle=level[7],
                         linewidth=level[8],
                         solid_capstyle='butt')
            self.ax.text(start + self.dimension / 2.,  # X
                         level[0] + self.offset,  # Y
                         level[3],  # self.top_texts
                         horizontalalignment='center',
                         verticalalignment='bottom',
                         fontsize=self.top_text_fontsize)

            self.ax.text(start + self.dimension,  # X
                         level[0],  # Y
                         level[5],  # self.right_text
                         horizontalalignment='left',
                         verticalalignment='center',
                         color=self.color_bottom_text,
                         fontsize=self.left_text_fontsize)

            self.ax.text(start,  # X
                         level[0],  # Y
                         level[6],  # self.left_text
                         horizontalalignment='right',
                         verticalalignment='center',
                         color=self.color_bottom_text,
                         fontsize=self.right_text_fontsize)

            self.ax.text(start + self.dimension / 2.,  # X
                         level[0] - self.offset * 1.5,  # Y
                         level[2],  # self.bottom_text
                         horizontalalignment='center',
                         verticalalignment='top',
                         color=self.color_bottom_text,
                         fontsize=self.bottom_text_fontsize)
        if show_IDs:
            # for showing the ID allowing the user to identify the level
            for ind, level in enumerate(data):
                start = level[1] * (self.dimension + self.space)
                self.ax.text(start, level[0] + self.offset, str(ind),
                             horizontalalignment='right', color='red')

        for idx, arrow in enumerate(self.arrows):
            # by Kalyan Jyoti Kalita: put arrows between to levels
            # x1, x2   y1, y2
            for i in arrow:
                start = self.positions[idx] * (self.dimension + self.space)
                x1 = start + 0.5 * self.dimension
                x2 = start + 0.5 * self.dimension
                y1 = self.energies[idx]
                y2 = self.energies[i]
                gap = y1 - y2
                gapnew = '{0:.2f}'.format(gap)
                middle = y1 - 0.5 * gap  # warning: this way works for negative HOMO/LUMO energies
                self.ax.annotate("", xy=(x1, y1), xytext=(x2, middle), arrowprops=dict(
                    color='green', width=2.5, headwidth=5))
                self.ax.annotate(gapnew, xy=(x2, y2), xytext=(x1, middle), color='green',
                                 arrowprops=dict(width=2.5, headwidth=5, color='green'),
                                 bbox=dict(boxstyle='round', fc='white'),
                                 ha='center', va='center')

        for idx, link in enumerate(self.links):
            # here we connect the levels with the links
            # x1, x2   y1, y2
            for i in link:
                # i is a tuple: (end_level_id,ls,linewidth,color,alpha)
                start = self.positions[idx] * (self.dimension + self.space)
                x1 = start + self.dimension
                x2 = self.positions[i[0]] * (self.dimension + self.space)
                y1 = self.energies[idx]
                y2 = self.energies[i[0]]
                line = Line2D([x1, x2], [y1, y2],
                              ls=i[1],
                              linewidth=i[2],
                              color=i[3],
                              alpha=i[4])
                self.ax.add_line(line)

        if ylimits is not None:
            self.ax.set_ylim(ylimits)
        else:
            self.ax.xaxis.set_label_coords(0.5, -0.2)

    def __auto_adjust(self):
        """
        Method of ED class
        This method use the ratio to set the best dimension and space between
        the levels.

        Affects
        -------
        self.dimension
        self.space
        self.offset

        """
        # Max range between the energy
        energy_variation = abs(max(self.energies) - min(self.energies))
        if self.dimension == 'auto' or self.space == 'auto':
            # Unique positions of the levels
            unique_positions = float(len(set(self.positions)))
            space_for_level = energy_variation * self.ratio / unique_positions
            self.dimension = space_for_level * 0.7
            self.space = space_for_level * 0.3

        if self.offset == 'auto':
            self.offset = energy_variation * self.offset_ratio
