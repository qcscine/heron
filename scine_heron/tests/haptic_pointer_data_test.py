#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from scine_heron.haptic import haptic_pointer_data as hpd

from box import Box


def test_haptic_pointer_vtkpolydata_check() -> None:

    haptic_pd = hpd.HapticPointerData()

    pos = Box(x=4, y=3, z=-1)

    haptic_pd.update_pointer_position(pos)

    center_data = haptic_pd.get_center_data()
    pos_to_check = center_data.GetPoints().GetPoint(0)

    assert pos_to_check == (4, 3, -1)


def test_haptic_pointer_data_position_property() -> None:

    haptic_pointer_d = hpd.HapticPointerData()

    pos = Box(x=4, y=3, z=-1)

    haptic_pointer_d.update_pointer_position(pos)

    pos_to_check = haptic_pointer_d.position

    assert pos_to_check == (4, 3, -1)
