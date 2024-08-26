#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from collections import UserDict
from typing import Dict, Any
from PySide2.QtWidgets import QWidget

import scine_database as db
import scine_utilities as su

from scine_heron.settings.dict_option_widget import DictOptionWidget


class TestClass:
    """
    Test class the used to check set_attributes_to_object and get_attributes_to_object methods.
    """

    attr1: str = ""
    attr2: int = 2


class InheritanceTest(UserDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data["user"] = "defined"


def test_set_attributes_to_object() -> None:
    parent = QWidget()
    dict_widget = DictOptionWidget(parent=parent, options={})

    o = TestClass()

    assert o.attr1 == ""
    assert o.attr2 == 2

    attr_dict: Dict[str, Any] = {"attr1": "Not empty string", "attr2": 42}

    dict_widget.set_attributes_to_object(o, attr_dict)

    assert o.attr1 == "Not empty string"
    assert o.attr2 == 42


def test_get_attributes_to_object() -> None:
    parent = QWidget()
    dict_widget = DictOptionWidget(parent=parent, options={})

    o = TestClass()

    attr_dict = dict_widget.get_attributes_of_object(o)

    # contains only 2 attributes
    assert len(attr_dict.keys()) == 2

    assert "attr1" in attr_dict
    assert o.attr1 == attr_dict["attr1"]
    assert "attr2" in attr_dict
    assert o.attr2 == attr_dict["attr2"]


def test_get_widget_data() -> None:
    parent = QWidget()
    empty_widget = DictOptionWidget(parent=parent, options={})
    assert empty_widget.get_widget_data() == {}

    sub_dict = {'a': 1, 'b': 0.2, 'c': "str", 'd': True, 'e': [0, 50]}

    dict_example = {
        "int": 1,
        "float": 0.2,
        "str": "str",
        "bool": True,
        "int_list": [0, 20],
        "float_list": [0.1, 20.53],
        "str_list": ["3534ed5", "953egf"],
        "sub_dict": sub_dict,
        "value_coll": su.ValueCollection(sub_dict),
        "model": db.Model("a", "b", "c"),
        "job": db.Job("sleep"),
        "user": InheritanceTest(sub_dict),
    }
    filled_widget = DictOptionWidget(parent=parent, options=dict_example)
    dict_from_widget = filled_widget.get_widget_data()
    assert len(dict_example) == len(dict_from_widget)

    for key in dict_example.keys():
        assert dict_example[key] == dict_from_widget[key]


def test_recursive_get_widget_data() -> None:
    parent = QWidget()
    empty_widget = DictOptionWidget(parent=parent, options={})
    assert empty_widget.get_widget_data() == {}

    dict_example = {"first level": {"second level": {"third level": "recursive"}}}
    filled_widget = DictOptionWidget(parent=parent, options=dict_example)
    dict_from_widget = filled_widget.get_widget_data()

    assert len(dict_example) == len(dict_from_widget)
    assert "first level" in dict_from_widget
    assert "second level" in dict_from_widget["first level"]
    assert "third level" in dict_from_widget["first level"]["second level"]
    assert dict_from_widget["first level"]["second level"]["third level"] == "recursive"
