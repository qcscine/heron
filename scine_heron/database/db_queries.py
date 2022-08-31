#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""


def finished_calculations():
    return {"status": {"$in": ["complete", "failed", "analyzed"]}}


def unstarted_calculations():
    return {"status": {"$in": ["new", "hold"]}}
