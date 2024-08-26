#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from scine_heron.chemoton.class_searcher import ChemotonClassSearcher
from scine_chemoton import gears
from scine_chemoton.gears.scheduler import Scheduler


def test_gear_searcher() -> None:
    """
    Check that ChemotonClassSearcher load gears from scine_chemoton.gears.
    """
    gear_searcher = ChemotonClassSearcher(gears.Gear)

    assert len(gear_searcher) > 10
    print(list(gear_searcher.keys()))
    assert "Scheduler" in gear_searcher.keys()

    assert len(gear_searcher.module_to_class) > 10
    assert "scheduler" in gear_searcher.module_to_class

    blacked_gear_searcher = ChemotonClassSearcher(gears.Gear, black_list=[Scheduler])
    assert len(blacked_gear_searcher) > 10
    assert "Scheduler" not in blacked_gear_searcher.keys()
