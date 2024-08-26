#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from scine_chemoton.gears.scheduler import Scheduler
from scine_heron.settings.docstring_parser import DocStringParser


class MockClass:
    """
    Just for testing.

    Here is also a docstring.
    """

    def __init__(self, arg: int, fake_argument: Scheduler) -> None:
        """
        Construct it.
        With lots of docs.

        Parameters
        ----------
        arg : int
            Some description
        fake_argument : Scheduler
            Another description text
            over multiple lines.
        """


def test_doc_string_parser() -> None:
    """
    Check that DocStringParser load attribute Docstrings.
    """
    parser = DocStringParser()
    gear = Scheduler()

    docstring_dict = parser.get_docstring_for_object_attrs(Scheduler.__name__, gear.options)

    assert len(docstring_dict) >= 2
    assert "job_counts" in docstring_dict
    assert "job_priorities" in docstring_dict

    assert "Dict[str, int]\n" in docstring_dict["job_counts"]
    assert "Dict[str, int]\n" in docstring_dict["job_priorities"]


def test_doc_string_parser_init() -> None:
    parser = DocStringParser()
    inst = MockClass(None, None)  # type: ignore

    docstring_dict = parser.get_docstring_for_instance_init(MockClass.__name__, inst)

    assert len(docstring_dict) == 2
    assert "cycle_time" not in docstring_dict
    assert "arg" in docstring_dict
    assert "Some description" in docstring_dict["arg"]
    assert "Scheduler" not in docstring_dict["arg"]

    assert "fake_argument" in docstring_dict
    assert "Scheduler" in docstring_dict["fake_argument"]
    assert "Another description text" in docstring_dict["fake_argument"]
    assert "over multiple lines" in docstring_dict["fake_argument"]
