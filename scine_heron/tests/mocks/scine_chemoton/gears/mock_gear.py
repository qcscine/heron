#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Mocks for the scine_chemoton.engine module.
"""
from . import Gear


class MockGear(Gear):
    def __init__(self):
        super().__init__()
        self.options = self.Options()

    class Options:
        """
        The options for the BasicCompoundHousekeeping Gear.
        """

        __slots__ = [
            "cycle_time",
            "model",
            "bond_order_job",
        ]

        def __init__(self):
            self.cycle_time = 10
            """
            int
                The minimum number of seconds between two cycles of the Gear.
                Cycles are finished independent of this option, thus if a cycle
                takes longer than the cycle_time will effectively lead to longer
                cycle times and not cause multiple cycles of the same Gear.
            """
            self.model: str = "Model"
            """
            db.Model (Scine::Database::Model)
                The Model used for the bond order calculations.
                The default is: PM6 using Sparrow.
            """
            self.bond_order_job: str = "Job"
            """
            db.Job (Scine::Database::Calculation::Job)
                The Job used for the bond order calculations.
                The default is: the 'scine_bond_orders' order on a single core.
            """
