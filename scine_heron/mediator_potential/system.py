#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the System class.
"""

from typing import Any, Dict, List, Tuple
from numpy import ndarray


class System:
    # This class contains the current positions and elements of the system
    # Only altered by the server process, only read by the sparrow process
    # All in atomic units

    def __init__(
        self,
        molecule_version: int,
        positions: ndarray,
        atom_symbols: List[str],
        calculator_args: Tuple[str, str],
        settings: Dict[str, Any],
    ):
        self.__molecule_version = molecule_version
        self.__positions = positions
        self.__atom_symbols = atom_symbols
        self.__calculator_args = calculator_args
        self.__settings = settings

    @property
    def molecule_version(self) -> int:
        return self.__molecule_version

    @property
    def positions(self) -> ndarray:
        return self.__positions

    @property
    def atom_symbols(self) -> List[str]:
        return self.__atom_symbols

    @property
    def settings(self) -> Dict[str, Any]:
        return self.__settings

    @property
    def calculator_args(self) -> Tuple[str, str]:
        return self.__calculator_args
