#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""

import numpy as np
from typing import List, TypeVar

Position = TypeVar("Position")


def collision(
    radius1: float, position1: Position, radius2: float, position2: Position
) -> bool:
    """
    Checks whether 2 spheres collide.
    """
    res = bool(
        ((np.array(position1) - np.array(position2)) ** 2).sum()
        < (radius1 + radius2) ** 2
    )

    return res


def collision_multiple(
    radius: float, position: Position, radii: List[float], positions: List[Position]
) -> bool:
    """
    Checks whether a sphere collides with any sphere in a list.
    """
    return any(collision(radius, position, r, p) for r, p in zip(radii, positions))
