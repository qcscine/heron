#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from typing import Union

import scine_database as db


def get_compound_or_flask(a_id: db.ID, a_type: db.CompoundOrFlask, compound_collection: db.Collection,
                          flask_collection: db.Collection) -> Union[db.Compound, db.Flask]:
    if a_type == db.CompoundOrFlask.FLASK:
        return db.Flask(a_id, flask_collection)
    return db.Compound(a_id, compound_collection)


def aggregate_type_from_string(a_type_str: str) -> db.CompoundOrFlask:
    if a_type_str == "compound":
        return db.CompoundOrFlask.COMPOUND
    return db.CompoundOrFlask.FLASK
