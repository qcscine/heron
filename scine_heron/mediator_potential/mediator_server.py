#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from multiprocessing import Process, Manager
from multiprocessing.managers import SyncManager
import typing
import socket
import numpy as np

import scine_utilities as su
from .sparrow_client import SparrowClient
from .mediator_potential import MediatorPotential
from .system import System
from .clientserver import recv_data, send_data
from .custom_results import CustomResult


def convert_positions_to_bohr(
    molecule: typing.List[typing.List[typing.Union[float, str]]]
) -> np.ndarray:
    """
    Conversion to bohr (a.u.)
    """
    return (
        np.array([xyz for _, xyz in molecule], dtype=np.float64) * su.BOHR_PER_ANGSTROM
    )


def get_energy_gradient_charges_or_default(
    mediator_potential: MediatorPotential,
    positions: np.ndarray,
    molecule_version: int,
    natoms: int,
) -> typing.Tuple[
    float,
    np.ndarray,
    typing.Optional[typing.List[float]],
    typing.Optional[str],
    typing.Dict[str, typing.Any],
]:
    """
    Computes the energy and the gradient
    given the mediator potential and the positions.
    In case something goes wrong, returns sensible defaults.
    """

    if (
        mediator_potential is None
        or mediator_potential.molecule_version != molecule_version
    ):
        energy, gradient, charges, molden_input, settings = (
            0.0,
            np.zeros((natoms, 3)),
            None,
            None,
            {},
        )
    else:
        energy = mediator_potential.get_energy(positions)
        gradient = mediator_potential.get_gradients(positions)
        charges = mediator_potential.get_atomic_charges()
        molden_input = mediator_potential.molden_input
        settings = mediator_potential.settings
    return energy, gradient, charges, molden_input, settings


def check_method_specific_settings(
    settings: typing.Dict[str, typing.Any]
) -> typing.Tuple[typing.Dict[str, typing.Any], str]:
    error_msg = ""
    if settings["method"] == "DFTB0":
        if "self_consistence_criterion" in settings.keys():
            del settings["self_consistence_criterion"]
        if "scf_mixer" in settings.keys():
            del settings["scf_mixer"]
        if "spin_mode" in settings.keys():
            # Sparrow performs restricted calculations no matter the setting, this guarantees
            # that the displayed setting corresponds to the actual calculation.
            settings["spin_mode"] = "restricted"
    if (settings["method"] == "DFTB2" or settings["method"] == "DFTB3") and settings["scf_mixer"] == "no_mixer":
        settings["scf_mixer"] = "diis"
        error_msg += (
            settings["method"]
            + " requires an SCF accelerator, reset to DIIS."
        )
    return settings, error_msg


def server(
    shared_data: typing.MutableMapping[str, typing.Any],
    lock: typing.ContextManager[None],
) -> None:
    """
    Connects to the client (GUI)
    Receives molecule, settings i.e. updates system
    Sends gradients and energy derived from mediator potential
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 55145))
    s.listen()

    while True:
        conn, _ = s.accept()
        with conn:
            stop_signal, molecule_version, molecule, settings = recv_data(conn)
            shared_data["stop_signal"] = stop_signal

            if stop_signal:
                break

            positions = convert_positions_to_bohr(molecule)
            atom_symbols = [atom[0] for atom in molecule]
            settings, info_msg = check_method_specific_settings(settings)
            error_msg = ""
            with lock:
                shared_data["system"] = System(
                    molecule_version=molecule_version,
                    positions=positions,
                    atom_symbols=atom_symbols,
                    settings=settings,
                )
                mediator_potential = shared_data.get("mediator_potential", None)
                error_msg += shared_data.get("error_msg", "")
                info_msg += shared_data.get("info_msg", "")

            (
                energy,
                gradient,
                charges,
                molden_input,
                settings,
            ) = get_energy_gradient_charges_or_default(
                mediator_potential, positions, molecule_version, len(molecule)
            )

            send_data(
                [energy, gradient.tolist(), charges, molden_input, error_msg, info_msg, settings],
                conn,
            )


def electronic_structure_calculation(
    shared_data: typing.MutableMapping[str, typing.Any],
    lock: typing.ContextManager[None],
) -> None:
    """
    Prepares calculator for Sparrow calculations
    Updates mediator potential whenever new results are available
    If atomic_hessian_switch (hard coded atm), then the atomic hessians are used,
    otherwise, the full hessian is used (slower, but more precise)
    """
    atomic_hessian_switch = True
    sparrow_client = None
    while True:
        with lock:
            system = shared_data.get("system", None)
            stop_signal = shared_data.get("stop_signal", False)
        if stop_signal:
            break

        if system is None:
            continue

        if sparrow_client is None:
            sparrow_client = SparrowClient(
                atomic_hessian_switch,
                system.settings,
                system.molecule_version,
            )
        error_msg = ""
        mediator_potential = None
        result = CustomResult()
        try:
            sparrow_client.update_calculator(
                system.positions, system.atom_symbols, system.settings
            )
            # Perform sparrow calculations
            result = sparrow_client.calculate_gradients()
        except RuntimeError as error:
            error_msg = str(error)
        else:
            if result:
                mediator_potential = MediatorPotential(system.molecule_version, result)
                shared_data["info_msg"] = result.info_msg
        with lock:
            if mediator_potential:
                shared_data["mediator_potential"] = mediator_potential
            shared_data["error_msg"] = error_msg


def run_server() -> None:
    with Manager() as manager:
        assert isinstance(manager, SyncManager)

        shared_data: typing.MutableMapping[str, typing.Any] = manager.dict()
        lock = manager.Lock()

        server_process = Process(target=server, args=(shared_data, lock))
        server_process.start()

        calculation_process = Process(
            target=electronic_structure_calculation, args=(shared_data, lock)
        )
        calculation_process.start()

        for process in [server_process, calculation_process]:
            process.join()
