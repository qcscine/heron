#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from hypothesis import given, assume
from hypothesis import strategies as st
from typing import List
from scine_heron.edit_molecule.collision import collision, collision_multiple


def test_collision_yes() -> None:
    radius1 = 1
    radius2 = 2

    position1 = (0, 0, 0)
    position2 = (1, 2, 1)

    assert collision(radius1, position1, radius2, position2)


def test_collision_no() -> None:
    radius1 = 1
    radius2 = 2

    position1 = (-1, 0, 0)
    position2 = (1, 2, 1.01)

    assert not collision(radius1, position1, radius2, position2)


# Packed
@given(
    st.lists(
        st.lists(st.floats(-0.4, 0.4), min_size=3, max_size=3), min_size=1, max_size=5
    )
)
def test_collision_multiple_yes(positions: List[List[float]]) -> None:
    r = 0.2
    position = (0, 0, 0)
    radii = [r for _ in positions]
    assume(any(collision(r, position, r, p) for p in positions))
    assert collision_multiple(r, position, radii, positions)  # type: ignore[misc]


# Sparse
@given(
    st.lists(st.lists(st.floats(-1, 1), min_size=3, max_size=3), min_size=1, max_size=5)
)
def test_collision_multiple_no(positions: List[List[float]]) -> None:
    r = 0.2
    position = (0, 0, 0)
    radii = [r for _ in positions]
    assume(not any(collision(r, position, r, p) for p in positions))
    assert not collision_multiple(r, position, radii, positions)  # type: ignore[misc]
