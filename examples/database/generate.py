#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
import scine_database as db
from scine_chemoton.tests import test_database_setup as db_setup

"""
This script generates a small 'fake' reaction network database
on the 'localhost', with port 27017 and name 'many_reactions'.
All structures in the database will be the same water molecule.
The database generated is very shallow and unphysical.
It is mainly used for unit tests and debugging purposes.
"""

if __name__ == '__main__':
    n_compounds = 50
    n_reactions = 3000
    max_r_per_c = 300
    max_n_products_per_r = 2
    max_n_educts_per_r = 2
    max_s_per_c = 1
    max_steps_per_r = 1
    barrier_limits = (0.1, 2000.0)
    n_inserts = 1
    n_flasks = 100
    manager = db_setup.get_random_db(
        n_compounds,
        n_flasks,
        n_reactions,
        max_r_per_c,
        "many_reactions",
        max_n_products_per_r,
        max_n_educts_per_r,
        max_s_per_c,
        max_steps_per_r,
        barrier_limits,
        n_inserts,
    )

