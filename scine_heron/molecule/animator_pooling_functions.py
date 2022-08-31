#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
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
    error_msg: str
    info_msg: str
    molden_input: str


def calculate_gradient(
    parameters: Tuple[int, List[Tuple[str, Tuple[float, float, float]]], Dict[str, Any]]
) -> GradientCalculationResult:
    molecule_version, molecule, settings = parameters
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
                    settings,
                ],
                socket=s,
            )
            (
                energy,
                gradients,
                charges,
                molden_input,
                error_msg,
                info_msg,
                new_settings,
            ) = clientserver.recv_data(connection=s)
        except ConnectionError:
            energy, gradients, charges, molden_input, error_msg, info_msg = (
                0.0,
                np.zeros(shape=(len(molecule), 3)),
                None,
                None,
                "",
                "",
            )
        if new_settings != settings:
            settings = new_settings
    return GradientCalculationResult(
        gradients=np.array(gradients),
        energy=energy,
        settings=settings,
        atomic_charges=charges,
        error_msg=error_msg,
        info_msg=info_msg,
        molden_input=molden_input,
    )
