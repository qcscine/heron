#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from scine_heron.chemoton.docstring_parser import DocStringParser
from scine_heron.tests.mocks.scine_chemoton.gears.mock_gear import MockGear


def test_doc_string_parser() -> None:
    """
    Check that DocStringParser load attribute Docstrings.
    """
    parser = DocStringParser()
    gear = MockGear()

    docstring_dict = parser.get_docstring_for_object_attrs("MockGear", gear.options)

    assert len(docstring_dict) == 3
    assert "cycle_time" in docstring_dict
    assert "model" in docstring_dict
    assert "bond_order_job" in docstring_dict

    assert docstring_dict["cycle_time"] == (
        "int\n"
        "    The minimum number of seconds between two cycles of the Gear.\n"
        "    Cycles are finished independent of this option, thus if a cycle\n"
        "    takes longer than the cycle_time will effectively lead to longer\n"
        "    cycle times and not cause multiple cycles of the same Gear."
    )

    assert docstring_dict["model"] == (
        "db.Model (Scine::Database::Model)\n"
        "    The Model used for the bond order calculations.\n"
        "    The default is: PM6 using Sparrow."
    )

    assert docstring_dict["bond_order_job"] == (
        "db.Job (Scine::Database::Calculation::Job)\n"
        "    The Job used for the bond order calculations.\n"
        "    The default is: the 'scine_bond_orders' order on a single core."
    )
