#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from abc import ABC, abstractmethod
from copy import deepcopy
from time import sleep
from typing import Any, List, Optional, Union, TYPE_CHECKING, Type, Dict

from PySide2.QtCore import QThread
from PySide2.QtWidgets import QWidget

if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


import scine_database as db
import scine_utilities as su
import scine_swoose as swoose  # noqa # pylint: disable=import-error

from scine_heron.molecular_viewer import MolecularViewerWidget, get_mol_viewer_tab


class _SwooseWrapper(ABC):

    def __init__(self) -> None:
        self.errors: List[str] = []
        self._db_manager: Optional[db.Manager] = None
        self._mol_tab: Optional[MolecularViewerWidget] = None
        self._instance: Union[swoose.QmRegionSelector, swoose.Parametrizer, None] = None

    def _get_excluded_settings(self) -> List[str]:
        excluded_settings = [
            "qm_region_center_atoms",
            "ref_data_mode",
            "yaml_settings_file_path",
        ]
        if not self.db_available():
            excluded_settings.extend([
                "database_host",
                "database_name",
                "database_port",
                "database_sleep_time",
                "reuse_database",
            ])
        return excluded_settings

    def _get_default_modified_settings(self) -> Dict[str, Any]:
        if not self.db_available():
            return {}
        assert self._db_manager is not None  # just linting, proper check in method
        credentials = self._db_manager.get_credentials()
        return {
            "database_host": credentials.hostname,
            "database_name": credentials.database_name,
            "database_port": credentials.port
        }

    def identifier(self) -> str:
        return self._instance.__class__.__name__

    @abstractmethod
    def failed_result(self) -> Union[List[int], bool]:
        pass

    @abstractmethod
    def sanity_check(self) -> Union[List[int], bool]:
        pass

    @abstractmethod
    def task(self) -> Union[List[int], bool]:
        pass

    def get_settings(self) -> su.Settings:
        if self._instance is None:
            return su.Settings("none", {})
        shown_settings = deepcopy(self._instance.settings)
        for excluded in self._get_excluded_settings():
            if excluded in shown_settings:
                del shown_settings[excluded]
        for key, value in self._get_default_modified_settings().items():
            shown_settings[key] = value
        return shown_settings

    def set_settings(self, settings: su.Settings) -> None:
        if self._instance is None:
            return
        self._instance.settings.update(settings)

    def _reload_mol_tab(self):
        self._mol_tab = self._mol_view_wrap()

    def _mol_view_wrap(self) -> Optional[MolecularViewerWidget]:
        tab = get_mol_viewer_tab(want_atoms_there=True, message_container=self.errors)
        return tab

    def enable_database(self, db_manager: db.Manager) -> None:
        self._db_manager = db_manager
        if not db_manager.connected:
            try:
                self._db_manager.connect()
            except RuntimeError as e:
                self.errors.append(str(e))

    def disable_database(self) -> None:
        self._db_manager = None

    def db_available(self) -> bool:
        return self._db_manager is not None and self._db_manager.connected


class SwooseTask(QThread):

    # signals that this threads sends to main display for result of Swoose Task
    parametrize_signal = Signal(bool)
    qm_region_signal = Signal(list)

    # technical reasons
    error_signal = Signal(str)  # error message cannot be displayed from thread
    send_settings_signal = Signal(su.Settings, str)  # pop-up for settings cannot safely be displayed from thread
    receive_settings_signal = Signal(su.Settings)

    def __init__(self, parent: Optional[QWidget], swoose_wrapper: Type):
        super().__init__(parent)
        self._swoose_wrapper: _SwooseWrapper = swoose_wrapper()
        self.identifier = self._swoose_wrapper.identifier()
        self._settings: Optional[su.Settings] = None

    def enable_database(self, db_manager: db.Manager) -> None:
        self._swoose_wrapper.enable_database(db_manager)
        self._error_check()

    def disable_database(self) -> None:
        self._swoose_wrapper.disable_database()

    def _error_check(self, additional_error: str = "") -> None:
        if self._swoose_wrapper.errors:
            for error in self._swoose_wrapper.errors:
                self.error_signal.emit(error)
        if additional_error:
            self.error_signal.emit(additional_error)
            self._send_result(self._swoose_wrapper.failed_result())

    def _send_result(self, result: Union[List[int], bool]) -> None:
        if isinstance(result, list):
            self.qm_region_signal.emit(result)
        elif isinstance(result, bool):
            self.parametrize_signal.emit(result)
        else:
            raise NotImplementedError(f"Unknown Swoose result {result}")

    def run(self):
        try:
            sane_result = self._swoose_wrapper.sanity_check()
            if not sane_result:
                self._error_check()
                self._send_result(self._swoose_wrapper.failed_result())
                self.exit(1)
            self._wait_for_settings()
            if self._settings is None:
                self._error_check(additional_error="Could not get settings")
                self.exit(0)
            self._swoose_wrapper.set_settings(self._settings)
            result = self._swoose_wrapper.task()
        except Exception as e:  # pylint: disable=broad-except
            self._error_check(additional_error=str(e))
        else:
            self._error_check()
            self._send_result(result)
        self.exit(0)

    def _stop_waiting(self, settings: su.Settings) -> None:
        self._settings = settings
        self.receive_settings_signal.disconnect(self._stop_waiting)

    def _wait_for_settings(self) -> None:
        settings = self._swoose_wrapper.get_settings()
        self.receive_settings_signal.connect(self._stop_waiting)
        self.send_settings_signal.emit(settings, self.identifier)
        while self._settings is None:
            sleep(0.1)


class QMRegionSelector(_SwooseWrapper):

    def __init__(self):
        super().__init__()
        self._instance = swoose.QmRegionSelector()

    def _get_excluded_settings(self) -> List[str]:
        return super()._get_excluded_settings() + ["qm_region_center_atoms"]

    def _get_default_modified_settings(self) -> Dict[str, Any]:
        return {**super()._get_default_modified_settings(),
                **{
                    "cutting_probability": 0.6,
                    "qm_region_min_size": 40,
                    "qm_region_max_size": 60,
                    "ref_max_size": 80,
                    "tol_percentage_sym_score": 99.0
        }}

    def failed_result(self) -> List[int]:
        return []

    def sanity_check(self) -> Union[List[int], bool]:
        self._reload_mol_tab()
        selection = self._get_mol_tab_atom_selection()
        if not selection:
            return []
        return True

    def task(self) -> Union[List[int], bool]:
        self._reload_mol_tab()
        selection = self._get_mol_tab_atom_selection()
        if not selection:
            return []
        self._set_hardcoded_settings(selection)
        tab = get_mol_viewer_tab(True)
        assert isinstance(tab, MolecularViewerWidget)
        assert tab.mol_widget is not None
        atoms = tab.mol_widget.get_atom_collection()
        calculator = tab.create_calculator_widget.get_calculator()
        calculator.structure = atoms
        assert calculator.name() == "QMMM"
        assert isinstance(self._instance, swoose.QmRegionSelector) and self._mol_tab is not None \
            and self._mol_tab.mol_widget is not None
        self._instance.set_underlying_calculator(calculator)
        self._instance.generate_qm_region(self._mol_tab.mol_widget.get_atom_collection())
        return self._instance.get_qm_region_indices()

    def _get_mol_tab_atom_selection(self) -> List[int]:
        if self._mol_tab is None:
            self.errors.append("Cannot construct QM region")
            return []
        mol_widget = self._mol_tab.mol_widget
        if mol_widget is None or not mol_widget.has_atoms():
            self.errors.append("Cannot construct QM region")
            return []
        selection = mol_widget.get_selection()
        if not selection:
            self.errors.append("No selection, please select one nucleus to start the QM region construction "
                               "around this atom")
            return []
        return selection

    def _set_hardcoded_settings(self, selection: List[int]) -> None:
        if self._instance is None:
            return
        mode = "database" if self.db_available() else "direct"
        self._instance.settings["ref_data_mode"] = mode
        self._instance.settings["qm_region_center_atoms"] = selection


class MMParametrizer(_SwooseWrapper):

    def __init__(self):
        super().__init__()
        self._instance = swoose.Parametrizer()

    def _get_excluded_settings(self) -> List[str]:
        return super()._get_excluded_settings() + ["ref_data_generation_only"]

    def _get_default_modified_settings(self) -> Dict[str, Any]:
        return {**super()._get_default_modified_settings(),
                **{
                    "reference_program": "sparrow",
                    "mm_parameter_file": "Parameters.dat",
                    "mm_connectivity_file": "Connectivity.dat",
        }}

    def failed_result(self) -> bool:
        return False

    def sanity_check(self) -> Union[List[int], bool]:
        self._reload_mol_tab()
        if self._mol_tab is None:
            self.errors.append("Cannot parametrize")
            return False
        mol_widget = self._mol_tab.mol_widget
        if mol_widget is None or not mol_widget.has_atoms():
            self.errors.append("Cannot parametrize")
            return False
        return True

    def task(self) -> Union[List[int], bool]:
        self._reload_mol_tab()
        if self._mol_tab is None:
            self.errors.append("Cannot parametrize")
            return False
        mol_widget = self._mol_tab.mol_widget
        if mol_widget is None or not mol_widget.has_atoms():
            self.errors.append("Cannot parametrize")
            return False
        self._set_hardcoded_settings()
        assert isinstance(self._instance, swoose.Parametrizer)
        self._instance.parametrize_mm(mol_widget.get_atom_collection())
        return True

    def _set_hardcoded_settings(self) -> None:
        if self._instance is None:
            return
        mode = "database" if self.db_available() else "direct"
        self._instance.settings["ref_data_mode"] = mode
