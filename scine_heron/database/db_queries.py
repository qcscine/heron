#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""


from warnings import warn
warn('This is deprecated, please import the queries from scine_database', DeprecationWarning, stacklevel=2)


def finished_calculations():
    return {"status": {"$in": ["complete", "failed", "analyzed"]}}


def unstarted_calculations():
    return {"status": {"$in": ["new", "hold"]}}
