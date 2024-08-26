#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the energy profile class
"""

from datetime import datetime
from typing import Optional


class EnergyProfilePoint:
    def __init__(
        self, energy: float = 0, elapsed_time: float = 0, time_stamp: Optional[datetime] = None
    ):
        self.energy: float = energy
        self.elapsed_time: float = elapsed_time
        if time_stamp is None:
            self.time_stamp = datetime.now()
        else:
            self.time_stamp = time_stamp
