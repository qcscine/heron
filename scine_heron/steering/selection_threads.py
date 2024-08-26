#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from collections import defaultdict
from threading import Event
from typing import Optional, List, Any, Dict, Tuple, TYPE_CHECKING

import numpy as np
from PySide2.QtCore import QThread
from PySide2.QtWidgets import QWidget

from scine_database import Manager, Credentials, Compound, Structure
from scine_utilities import AtomCollection
from scine_chemoton.steering_wheel.datastructures import ProtocolEntry, SelectionResult
from scine_chemoton.steering_wheel.network_expansions import (
    NetworkExpansion,
    GiveWholeDatabaseWithModelResult
)
from scine_chemoton.gears.conformers.brute_force import BruteForceConformers
from scine_chemoton.gears.elementary_steps import ElementaryStepGear

if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


class UnimolecularCoordinates:
    """
    This class mitigates any problems when sending the coordinates as a signal with optional types and defaultdict.
    """

    def __init__(self, data: Dict[str,
                                  Dict[str,
                                       Optional[List[Tuple[List[List[Tuple[int, int]]], int]]]]]) -> None:
        self.data = data


class BimolecularCoordinates:
    """
    This class mitigates any problems when sending the coordinates as a signal with optional types and defaultdict.
    """

    def __init__(self, data: Dict[str,
                                  Dict[str,
                                       Dict[Tuple[List[Tuple[int, int]], int],
                                            List[Tuple[np.ndarray, np.ndarray, float, float]]
                                            ]
                                       ]
                                  ]) -> None:
        self.data = data


class CoordinateThread(QThread):  # no ABC because of QThread

    info_message_signal = Signal(str)
    error_message_signal = Signal(str)
    loop_signal = Signal()
    final_count_signal = Signal(int)

    def __init__(self, parent: QWidget, credentials: Credentials, potential_next_step: NetworkExpansion,
                 selection: SelectionResult) -> None:
        super().__init__(parent=parent)
        self._manager = Manager()
        self._credentials = credentials
        self._selection = selection
        self._manager.set_credentials(credentials)
        self._manager.connect()
        self._potential_next_step = potential_next_step
        self._potential_next_step.protocol = []
        self._compound_collection = self._manager.get_collection("compounds")
        self._structure_collection = self._manager.get_collection("structures")
        self._was_stopped = Event()

    def _setup_step(self) -> None:
        self._potential_next_step.dry_setup_protocol(self._credentials, self._selection)

    def _cleanup(self):
        self._potential_next_step.protocol = []
        if self._manager is not None:
            self._manager.disconnect()
            self._manager = None

    def run(self):
        try:
            self._setup_step()
            self._run_impl()
        except BaseException as e:
            self.error_message_signal.emit(str(e))  # pylint: disable=no-member
            self.final_count_signal.emit(0)  # pylint: disable=no-member
        finally:
            self._cleanup()
            self.exit(0)

    def _run_impl(self) -> None:
        raise NotImplementedError("This method needs to be implemented in a subclass")

    def terminate(self):
        for p in self._potential_next_step.protocol:
            if not isinstance(p, ProtocolEntry):
                continue
            p.terminate()
        self._cleanup()
        super().terminate()

    def stop(self):
        self._was_stopped.set()
        for p in self._potential_next_step.protocol:
            if not isinstance(p, ProtocolEntry):
                continue
            p.engine.stop()
        for p in self._potential_next_step.protocol:
            if not isinstance(p, ProtocolEntry):
                continue
            p.engine.join()


class UnimolecularThread(CoordinateThread):
    """
    """

    single_structure_no_sites_signal = Signal(str, AtomCollection)
    coordinates_signal = Signal(UnimolecularCoordinates)

    def _run_impl(self) -> None:
        """
        Queries for the unimolecular coordinates and emits the results.
        """
        total: Dict[str,
                    Dict[str,
                         Optional[List[Tuple[List[List[Tuple[int, int]]], int]]]]] \
            = defaultdict(lambda: defaultdict(list))
        if isinstance(self._potential_next_step, GiveWholeDatabaseWithModelResult):
            # loop over db
            model = self._potential_next_step.options.model
            for compound in self._compound_collection.iterate_all_compounds():
                self.loop_signal.emit()  # pylint: disable=no-member
                compound.link(self._compound_collection)
                if self._was_stopped.is_set():
                    break
                for sid in compound.get_structures():
                    structure = Structure(sid, self._structure_collection)
                    if structure.get_model() == model:
                        self.single_structure_no_sites_signal.emit(  # pylint: disable=no-member
                            f"Compound ({str(sid)})", structure.get_atoms()
                        )
                        break
            self.final_count_signal.emit(0)  # pylint: disable=no-member
            return
        for entry in self._potential_next_step.protocol:
            if not isinstance(entry, ProtocolEntry):
                continue
            if isinstance(entry.gear, ElementaryStepGear):
                entry.gear.disable_caching()
                uni_result = entry.gear.unimolecular_coordinates(
                    self._credentials, self.loop_signal.emit  # pylint: disable=no-member
                )
                if self._was_stopped.is_set():
                    break
                for cid, sub_dict in uni_result.items():
                    for sid, coords in sub_dict.items():
                        if sid in total[cid]:
                            total[cid][sid] += coords
                        else:
                            total[cid][sid] = coords
            elif isinstance(entry.gear, BruteForceConformers):
                if total:
                    self.info_message_signal.emit(  # pylint: disable=no-member
                        "Cannot show conformer generation + reaction trials, only showing conformer generation"
                    )
                entry.gear.clear_cache()
                count = 0
                for cid in entry.gear.valid_compounds():
                    self.loop_signal.emit()  # pylint: disable=no-member
                    compound = Compound(cid, self._compound_collection)
                    centroid = Structure(compound.get_centroid(), self._structure_collection)
                    self.single_structure_no_sites_signal.emit(f"Compound ({str(cid)})",  # pylint: disable=no-member
                                                               centroid.get_atoms())
                    count += 1
                self.final_count_signal.emit(count)  # pylint: disable=no-member
                return
        if self._was_stopped.is_set():
            self.final_count_signal.emit(0)  # pylint: disable=no-member
        else:
            self.coordinates_signal.emit(UnimolecularCoordinates(total))  # pylint: disable=no-member
        self._cleanup()
        self.exit(0)


class BimolecularThread(CoordinateThread):

    coordinates_signal = Signal(BimolecularCoordinates)

    def _run_impl(self) -> None:
        """
        Queries for the bimolecular coordinates and emits the results.
        """

        total: Dict[str,
                    Dict[str,
                         Dict[Tuple[List[Tuple[int, int]], int],
                              List[Tuple[np.ndarray, np.ndarray, float, float]]
                              ]
                         ]
                    ] \
            = defaultdict(lambda: defaultdict(dict))
        for entry in self._potential_next_step.protocol:
            if not isinstance(entry, ProtocolEntry):
                continue
            if isinstance(entry.gear, ElementaryStepGear):
                entry.gear.disable_caching()
                bi_result = entry.gear.bimolecular_coordinates(
                    self._credentials, self.loop_signal.emit  # pylint: disable=no-member
                )
                for cid, sub_dict in bi_result.items():
                    for sid, coords in sub_dict.items():
                        for key, complexes in coords.items():
                            if key in total[cid][sid]:
                                total[cid][sid][key] += complexes
                            else:
                                total[cid][sid][key] = complexes
        if self._was_stopped.is_set():
            self.final_count_signal.emit(0)  # pylint: disable=no-member
        else:
            self.coordinates_signal.emit(BimolecularCoordinates(total))  # pylint: disable=no-member
        self._cleanup()
        self.exit(0)
