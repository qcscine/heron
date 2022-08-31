#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the energy profile class
"""


class EnergyProfilePoint:
    def __init__(
        self, energy: float = 0, elapsed_time: float = 0, time_interval: float = 0
    ):
        self.energy: float = energy
        self.elapsed_time: float = elapsed_time
        self.time_interval: float = time_interval
