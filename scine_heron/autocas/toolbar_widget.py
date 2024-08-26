#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from PySide2.QtWidgets import QStyle, QToolBar, QWidget

from scine_heron.autocas.autocas_settings import AutocasSettings
from scine_heron.autocas.signal_handler import SignalHandler


class ToolbarWidget(QToolBar):
    # pylint: disable-next=W0613
    def __init__(
        self, parent: QWidget, signal_handler: SignalHandler, settings: AutocasSettings
    ):
        super().__init__()
        self.signal_handler = signal_handler
        self.autocas_settings = settings

        # self.open_molecule_file = self.addAction(
        #     self.style().standardIcon(QStyle.SP_TitleBarMenuButton),
        #     self.tr(self.__action_padding("Open xyz file")),  # type: ignore
        # )
        # self.open_entanglement_view.triggered.connect(
        #    self.signal_handler.open_entanglement_widget_signal
        # )

        self.start_autocas_calculation = self.addAction(
            self.style().standardIcon(QStyle.SP_MediaPlay),
            self.tr(self.__action_padding("Start Autocas calculation")),  # type: ignore
        )
        self.open_entanglement_view.triggered.connect(
            self.signal_handler.open_entanglement_widget_signal
        )

        self.open_settings_view = self.addAction(
            self.style().standardIcon(QStyle.SP_FileDialogContentsView),
            self.tr(self.__action_padding("Open Settings")),  # type: ignore
        )
        # self.open_entanglement_view.triggered.connect(
        #    self.signal_handler.open_entanglement_widget_signal
        # )

        self.open_filebrowser_view = self.addAction(
            self.style().standardIcon(QStyle.SP_DirHomeIcon),
            self.tr(self.__action_padding("Open File Browser")),  # type: ignore
        )
        # self.open_entanglement_view.triggered.connect(
        #    self.signal_handler.open_entanglement_widget_signal
        # )

        self.open_output_view = self.addAction(
            self.style().standardIcon(QStyle.SP_TrashIcon),
            self.tr(self.__action_padding("Open Output")),  # type: ignore
        )
        # self.open_entanglement_view.triggered.connect(
        #    self.signal_handler.open_entanglement_widget_signal
        # )
        self.open_file_tree = self.addAction(
            self.style().standardIcon(QStyle.SP_TrashIcon),
            self.tr(self.__action_padding("Open File Tree")),  # type: ignore
        )
        self.open_file_tree.triggered.connect(
            self.signal_handler.toggle_file_tree
        )

    @staticmethod
    def __action_padding(annotation: str) -> str:
        return '<p style="color:black !important;">{}</p>'.format(annotation)
