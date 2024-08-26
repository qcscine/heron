#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from multiprocessing import Process, Manager
from multiprocessing.managers import SyncManager
from time import sleep
import typing
import socket
import numpy as np

import scine_utilities as su
from scine_heron.calculators.calculator import ScineCalculatorWrapper
from .mediator_potential import MediatorPotential
from .system import System
from .clientserver import recv_data, send_data


def convert_positions_to_bohr(
        molecule: typing.List[typing.List[typing.Union[float, str]]]
) -> np.ndarray:
    """
    Conversion to bohr (a.u.)
    """
    return np.array([xyz for _, xyz in molecule], dtype=np.float64) * su.BOHR_PER_ANGSTROM


def get_results_to_send(
    mediator_potential: MediatorPotential,
    positions: np.ndarray,
    molecule_version: int,
    natoms: int,
) -> typing.Tuple[
    float,
    np.ndarray,
    typing.Optional[typing.List[float]],
    typing.Optional[np.ndarray],
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
        energy, gradient, charges, bond_orders, molden_input, settings = (
            0.0,
            np.zeros((natoms, 3)),
            None,
            None,
            None,
            {},
        )
    else:
        energy = mediator_potential.get_energy(positions)
        gradient = mediator_potential.get_gradients(positions)
        charges = mediator_potential.get_atomic_charges()
        bond_orders = mediator_potential.bond_orders
        if bond_orders is not None:
            # nd.array is not JSON serializable, so we convert it to a list
            bond_orders = bond_orders.tolist()
        molden_input = mediator_potential.molden_input
        settings = mediator_potential.settings
    return energy, gradient, charges, bond_orders, molden_input, settings


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
    active_mediator_potential = True
    saved_mediator_potential: typing.Optional[MediatorPotential] = None

    last_error = ""
    while True:
        conn, _ = s.accept()
        with conn:
            stop_signal, molecule_version, molecule, calculator_args, settings, mediator_potential_signal, \
                bond_orders_type = recv_data(conn)
            shared_data["stop_signal"] = stop_signal

            if stop_signal:
                break

            if mediator_potential_signal is not None:
                # we received signal to change set switch
                active_mediator_potential = mediator_potential_signal
                shared_data["mediator_potential_signal"] = mediator_potential_signal

            positions = convert_positions_to_bohr(molecule)
            atom_symbols = [atom[0] for atom in molecule]
            with lock:
                shared_data["system"] = System(
                    molecule_version=molecule_version,
                    positions=positions,
                    atom_symbols=atom_symbols,
                    calculator_args=calculator_args,
                    settings=settings,
                )
                shared_data["bond_orders_type"] = bond_orders_type
                mediator_potential = shared_data.get("mediator_potential", None)
                error_msg = shared_data.get("error_msg", last_error)
                info_msg = shared_data.get("info_msg", "")

                if mediator_potential is not None and not active_mediator_potential:
                    # result evaluation relies on the fact that it always happens over the mediator potential class
                    # independent of whether we have a real finished calculation or the mediator
                    # to disable it, we rely on the fact that it was not None, so we once got a result
                    # we evaluate energy, gradients and now remove the class from the shared data
                    # only once a new real calculation was finished, we have a mediator potential again, until then
                    # we just send zeros because we get a None from the shared data again
                    saved_mediator_potential = mediator_potential  # back up in case it is activated again
                    del shared_data["mediator_potential"]
                if mediator_potential is None and active_mediator_potential and saved_mediator_potential is not None:
                    mediator_potential = saved_mediator_potential

            (
                energy,
                gradient,
                charges,
                bond_orders,
                molden_input,
                settings,
            ) = get_results_to_send(
                mediator_potential, positions, molecule_version, len(molecule)
            )

            send_data([energy, gradient.tolist(), charges, bond_orders, molden_input,
                       error_msg, info_msg, settings, mediator_potential_signal],
                      conn,
                      )


def electronic_structure_calculation(
        shared_data: typing.MutableMapping[str, typing.Any],
        lock: typing.ContextManager[None],
) -> None:
    """
    Prepares calculator for Sparrow calculations
    Updates mediator potential whenever new results are available
    """
    calculation_client = None
    prev_mediator_signal = True
    while True:
        try:
            with lock:
                system = shared_data.get("system", None)
                stop_signal = shared_data.get("stop_signal", False)
                mediator_signal = shared_data.get("mediator_potential_signal", True)
                bond_orders_type = shared_data.get("bond_orders_type", "distance")
            if stop_signal:
                break

            if system is None:
                continue

            if calculation_client is None:
                calculation_client = ScineCalculatorWrapper(  # type: ignore
                    *system.calculator_args,
                    hessian_required=mediator_signal,
                    settings=system.settings,
                )

            if prev_mediator_signal != mediator_signal:
                calculation_client.set_hessian_flag(mediator_signal)
                prev_mediator_signal = mediator_signal

            error_msg = ""
            mediator_potential = None
            try:
                calculation_client.set_bond_orders_flag(bond_orders_type != "distance")
                calculation_client.update_system(
                    system.molecule_version, system.atom_symbols, system.positions, system.settings
                )
                # Perform calculations
                result = calculation_client.calculate_custom_result()
            except RuntimeError as error:
                error_msg = str(error)
            else:
                if result:
                    mediator_potential = MediatorPotential(system.molecule_version, result)
                    with lock:
                        shared_data["info_msg"] = result.info_msg
                elif result is not None:
                    error_msg = result.error_msg
            with lock:
                if mediator_potential:
                    shared_data["mediator_potential"] = mediator_potential
                shared_data["error_msg"] = error_msg
        except BrokenPipeError:
            break


def run_server(stop_signal: typing.Callable) -> None:
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

        while all(p.is_alive() for p in [server_process, calculation_process]):
            sleep(0.1)

        if any(p.is_alive() for p in [server_process, calculation_process]):
            sleep(0.5)
            try:
                stop_signal()
            except ConnectionRefusedError:
                pass

        if calculation_process.is_alive():
            server_process.join()
            calculation_process.join()
        else:
            calculation_process.join()
            server_process.join()
