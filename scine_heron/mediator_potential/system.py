#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the System class.
"""

import typing
import numpy


class System:
    # This class contains the current positions and elements of the system
    # Only altered by the server process, only read by the sparrow process
    # All in atomic units

    def __init__(
        self,
        molecule_version: int,
        positions: numpy.ndarray,
        atom_symbols: typing.List[str],
        settings: typing.Dict[str, typing.Any],
    ):
        self.__molecule_version = molecule_version
        self.__positions = positions
        self.__atom_symbols = atom_symbols
        self.__settings = settings

    @property
    def molecule_version(self) -> int:
        return self.__molecule_version

    @property
    def positions(self) -> numpy.ndarray:
        return self.__positions

    @property
    def atom_symbols(self) -> typing.List[str]:
        return self.__atom_symbols

    @property
    def settings(self) -> typing.Dict[str, typing.Any]:
        return self.__settings
