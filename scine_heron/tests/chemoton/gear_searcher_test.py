#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from scine_heron.chemoton.gear_searcher import GearSearcher


def test_gear_searcher() -> None:
    """
    Check that GearSearcher load gears from scine_chemoton.gears.
    """
    gear_searcher = GearSearcher()

    assert len(gear_searcher.gears) == 1
    assert "Mock Gear" in gear_searcher.gears

    assert len(gear_searcher.module_to_class) == 1
    assert "mock_gear" in gear_searcher.module_to_class
