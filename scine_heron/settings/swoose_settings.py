#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from os import path
from typing import List, Optional, TYPE_CHECKING
import pickle

from PySide2.QtWidgets import (
    QWidget,
    QInputDialog,
)
from PySide2.QtGui import QCloseEvent

import scine_utilities as su

from scine_heron.calculators.hybrid_model_construction import MMParametrizer, QMRegionSelector, SwooseTask
from scine_heron.containers.layouts import VerticalLayout
from scine_heron.containers.buttons import TextPushButton
from scine_heron.io.text_box import yes_or_no_question, pop_up_message
from scine_heron.settings.class_options_widget import ClassOptionsWidget
from scine_heron.settings.settings_status_manager import SettingsStatusManager
from scine_heron.utilities import write_error_message, write_info_message, docstring_dict_from_scine_settings
from scine_heron.dependencies.optional_import import is_imported

if TYPE_CHECKING:
    from scine_heron.database.connection_dialog import DatabaseConnectionDialog
    from scine_database import Manager
else:
    from scine_heron.dependencies.optional_import import importer
    DatabaseConnectionDialog = importer("scine_heron.database.connection_dialog", "DatabaseConnectionDialog")
    Manager = importer("scine_database", "Manager")


class SwooseSettingsWidget(QWidget):

    def __init__(self, parent: Optional[QWidget], settings_status_manager: SettingsStatusManager) -> None:
        super().__init__(parent)
        self.__settings_status_manager = settings_status_manager
        self.__swoose_backup_file = ".swoose_qm_region_backup.pkl"

        # threads
        self.__swoose_parametrize_task: Optional[SwooseTask] = None
        self.__swoose_select_task: Optional[SwooseTask] = None
        self.__setup_param_task()
        self.__setup_qm_selection_task()

        # buttons
        self.__mm_parametrize_button = TextPushButton("Parametrize SFAM", self.__parametrize_sfam)
        self.__mm_parametrize_button.setVisible(False)
        self.__qmmm_selection_button = TextPushButton("Construct QM region", self.__construct_hybrid_model)
        self.__qmmm_selection_button.setVisible(False)
        self.__qmmm_direct_selection_button = TextPushButton("Current selection as QM region",
                                                             self.__specify_current_selection_as_qm_region)
        self.__qmmm_direct_selection_button.setVisible(False)

        # connect settings status manager
        self.__settings_status_manager.hamiltonian_changed.connect(
            self.__determine_hybrid_model_selection_visibility
        )
        self.__settings_status_manager.hamiltonian_changed.connect(
            self.__determine_parametrize_option_visibility
        )

        # layout buttons
        layout = VerticalLayout([
            self.__mm_parametrize_button,
            self.__qmmm_selection_button,
            self.__qmmm_direct_selection_button
        ])
        self.setLayout(layout)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.__swoose_parametrize_task is not None and self.__swoose_parametrize_task.isRunning():
            self.__swoose_parametrize_task.terminate()
            self.__swoose_parametrize_task.wait()
        if self.__swoose_select_task is not None and self.__swoose_select_task.isRunning():
            self.__swoose_select_task.terminate()
            self.__swoose_select_task.wait()
        super().closeEvent(event)

    def __setup_param_task(self) -> None:
        if self.__swoose_parametrize_task is not None:
            if self.__swoose_parametrize_task.isRunning():
                self.__swoose_parametrize_task.terminate()
            self.__swoose_parametrize_task.wait()
        self.__swoose_parametrize_task = SwooseTask(self, MMParametrizer)
        # connect error handling
        self.__swoose_parametrize_task.error_signal.connect(
            write_error_message
        )
        # connect settings handling
        self.__swoose_parametrize_task.send_settings_signal.connect(
            self.__handle_swoose_settings
        )
        # connect results
        self.__swoose_parametrize_task.parametrize_signal.connect(
            self.__handle_parametrize_result
        )

    def __setup_qm_selection_task(self) -> None:
        if self.__swoose_select_task is not None:
            if self.__swoose_select_task.isRunning():
                self.__swoose_select_task.terminate()
            self.__swoose_select_task.wait()
        self.__swoose_select_task = SwooseTask(self, QMRegionSelector)
        # connect error handling
        self.__swoose_select_task.error_signal.connect(
            write_error_message
        )
        # connect settings handling
        self.__swoose_select_task.send_settings_signal.connect(
            self.__handle_swoose_settings
        )
        # connect results
        self.__swoose_select_task.qm_region_signal.connect(
            self.__handle_selection_result
        )

    def __determine_parametrize_option_visibility(self) -> None:
        method_family = self.__settings_status_manager.get_calculator_args()[0]
        mm_methods = ["SFAM", "GAFF"]
        self.__mm_parametrize_button.setVisible(method_family.upper() in mm_methods or '/' in method_family)

    def __determine_hybrid_model_selection_visibility(self) -> None:
        method_family = self.__settings_status_manager.get_calculator_args()[0]
        have_hybrid_model: bool = '/' in method_family
        self.__qmmm_selection_button.setVisible(have_hybrid_model)
        self.__qmmm_direct_selection_button.setVisible(have_hybrid_model)

    def __handle_swoose_settings(self, settings: su.Settings, identifier: str) -> None:
        method_family, program = self.__settings_status_manager.get_calculator_args()
        if su.settings_names.method_family in settings:
            settings[su.settings_names.method_family] = method_family
        if su.settings_names.program in settings:
            settings[su.settings_names.program] = program
        doc_strings = docstring_dict_from_scine_settings(settings)
        widget = ClassOptionsWidget(
            options=settings,
            docstring=doc_strings,
            parent=self,
            allow_removal=False
        )
        widget.exec_()
        for task in [self.__swoose_parametrize_task, self.__swoose_select_task]:
            if task is not None and task.identifier == identifier:
                task.receive_settings_signal.emit(settings)

    def __set_swoose_buttons_enabled(self, value: bool) -> None:
        for button in [self.__mm_parametrize_button, self.__qmmm_selection_button, self.__qmmm_direct_selection_button]:
            button.setEnabled(value)

    def __wrap_db_usage_around_task_start(self, task: SwooseTask, nomen: str, verb: str) -> None:
        self.__set_swoose_buttons_enabled(False)
        if not is_imported(Manager) or not is_imported(DatabaseConnectionDialog):
            # no database available, start direct mode
            task.disable_database()
            task.start()
            return
        db_direct_decision = QInputDialog()
        db_direct_decision.setWindowTitle("Mode decision")
        mode = db_direct_decision.getItem(self,
                                          nomen,
                                          f"Do you want to {verb} directly or via a database?",
                                          ["direct", "database"],
                                          current=0,
                                          editable=False)[0]
        if mode == "database":
            from scine_heron import find_main_window
            main = find_main_window()
            manager = None
            if main is not None:
                credentials = main.toolbar.current_credentials()
                if credentials is not None:
                    manager = Manager()
                    manager.set_credentials(credentials)
            while True:
                connect_dialog = DatabaseConnectionDialog(self, db_manager=manager)
                manager = connect_dialog.get_db_manager()
                if manager is not None and manager.connected:
                    task.enable_database(manager)
                    break
                else:
                    really_no_database = yes_or_no_question(self,
                                                            "Not connected to database. "
                                                            "Do you want to use the direct mode")
                    if really_no_database:
                        break
                    skip = yes_or_no_question(self, f"Do you want to abort the {nomen}")
                    if skip:
                        self.__set_swoose_buttons_enabled(True)
                        return
        else:
            task.disable_database()
        task.start()

    def __parametrize_sfam(self) -> None:
        if self.__swoose_parametrize_task is None:
            self.__setup_param_task()
            assert self.__swoose_parametrize_task is not None
        self.__wrap_db_usage_around_task_start(self.__swoose_parametrize_task, "Parametrization", "parametrize")

    def __construct_hybrid_model(self) -> None:
        if path.exists(self.__swoose_backup_file):
            ans = yes_or_no_question(self, f"Found file '{self.__swoose_backup_file}'. Do you want to load it instead?")
            if ans:
                sele = self.__load_qm_selection()
                self.__handle_selection_result(sele)
                return
            else:
                write_info_message("Ignoring backup file, starting selection from scratch")
        if self.__swoose_select_task is None:
            self.__setup_qm_selection_task()
            assert self.__swoose_select_task is not None
        self.__wrap_db_usage_around_task_start(self.__swoose_select_task, "QM region selection", "select QM region")

    def __handle_parametrize_result(self, result: bool) -> None:
        if result:
            pop_up_message(self, "Finished parametrization")
        else:
            write_error_message("Failed to parametrize structure")
        self.__setup_param_task()
        self.__set_swoose_buttons_enabled(True)

    def __handle_selection_result(self, result: List[int]) -> None:
        from scine_heron.molecular_viewer import get_mol_viewer_tab
        self.__set_swoose_buttons_enabled(True)
        if not result:
            return
        store_message = f"Storing result in '{self.__swoose_backup_file}' in case you want to enter it manually"
        mol_tab = get_mol_viewer_tab(want_atoms_there=True)
        if mol_tab is None:
            write_error_message(f"Got QM region selection, but could not access structure in Molecular Viewer. "
                                f"{store_message}")
            self.__save_qm_selection(result)
            return
        result_string = "["
        split_size = 10
        for i in range(0, str(result).count(',') + 1, split_size):
            result_string += ",".join([str(r) for r in result[i:i + split_size]]) + ",\n"
        result_string += "]"
        answer = yes_or_no_question(self, f"Determined QM region {result}. Do you want to set this in the calculator?")
        if not answer:
            write_info_message(store_message)
            self.__save_qm_selection(result)
            return
        assert mol_tab.mol_widget is not None
        n_atoms = len(mol_tab.mol_widget.get_atom_collection())
        if any(r >= n_atoms for r in result):
            write_error_message(f"Got QM region selection, but it does not fit in the current structure. "
                                f"{store_message}")
            self.__save_qm_selection(result)
            return
        mol_tab.mol_widget.set_selection(result)
        self.__specify_current_selection_as_qm_region()
        self.__setup_qm_selection_task()

    def __save_qm_selection(self, selection: List[int]) -> None:
        with open(self.__swoose_backup_file, "wb") as f:
            pickle.dump(selection, f)

    def __load_qm_selection(self) -> List[int]:
        with open(self.__swoose_backup_file, "rb") as f:
            return pickle.load(f)

    def __specify_current_selection_as_qm_region(self) -> None:
        from scine_heron.molecular_viewer import get_mol_viewer_tab
        mol_tab = get_mol_viewer_tab(want_atoms_there=True)
        if mol_tab is None:
            write_error_message("Could not get selection, no structure present")
            return
        mol_widget = mol_tab.mol_widget
        assert mol_widget is not None
        selection = mol_widget.get_selection()
        if not selection:
            write_error_message("Could not get selection, nothing selected")
            return
        method_family = self.__settings_status_manager.get_calculator_args()[0]
        have_hybrid_model: bool = '/' in method_family
        if not have_hybrid_model:
            write_error_message("No hybrid method family such as 'PM6/SFAM' currently loaded")
            return
        # TODO move Swoose settingsname into settingsnames in utils and use binding instead of naked string
        mol_tab.create_calculator_widget.update_settings({"qm_atoms": selection})
        self.__set_swoose_buttons_enabled(True)
