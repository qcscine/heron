#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides pooling functions for Animator.
"""
import socket
import numpy as np
from typing import Tuple, List, Any, NamedTuple, Dict, Optional
from scine_heron.mediator_potential import clientserver


class GradientCalculationResult(NamedTuple):
    """
    The results of a Sparrow calculation.
    """

    gradients: np.ndarray
    energy: float
    atomic_charges: Optional[List[float]]
    settings: Dict[str, Any]
    bond_orders: Optional[np.ndarray]
    error_msg: str
    info_msg: str
    molden_input: str


def calculate_gradient(
    parameters: Tuple[
        int, List[Tuple[str, Tuple[float, float, float]]], Tuple[str, str], Dict[str, Any], bool, str
    ]
) -> GradientCalculationResult:
    molecule_version, molecule, calculator_args, settings, mediator_potential_signal, bond_type = parameters
    stop_signal = False
    new_settings = settings
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect(("127.0.0.1", 55145))
            clientserver.send_data(
                data=[
                    stop_signal,
                    molecule_version,
                    molecule,
                    calculator_args,
                    settings,
                    mediator_potential_signal,
                    bond_type,
                ],
                socket=s,
            )
            (
                energy,
                gradients,
                charges,
                bond_orders,
                molden_input,
                error_msg,
                info_msg,
                new_settings,
                mediator_potential_signal
            ) = clientserver.recv_data(connection=s)
        except ConnectionError:
            energy, gradients, charges, bond_orders, molden_input, error_msg, info_msg = (
                0.0,
                np.zeros(shape=(len(molecule), 3)),
                None,
                None,
                None,
                "",
                "",
            )
        if new_settings != settings:
            settings = new_settings
        if bond_orders is not None:
            # nd.array is not JSON serializable, so we convert it back from a list
            bond_orders = np.array(bond_orders)
    return GradientCalculationResult(
        gradients=np.array(gradients),
        energy=energy,
        settings=settings,
        atomic_charges=charges,
        bond_orders=bond_orders,
        error_msg=error_msg,
        info_msg=info_msg,
        molden_input=molden_input,
    )
