#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Tests for the free functions in the molecule_writer module.
"""
import os
import numpy as np

import scine_utilities as su

from scine_heron.molecule.molecule_video import MoleculeVideo
from scine_heron.tests.resources import test_resource_path
from scine_heron.molecule.molecule_widget import MoleculeWidget


def test_frame_set() -> None:
    # reference
    ref = os.path.join(test_resource_path(), "water.trj.xyz")
    ref_traj = su.io.read_trajectory(su.io.TrajectoryFormat.Xyz, ref)
    n = 42
    assert len(ref_traj) > n
    ref_frame = ref_traj[n]
    # testing
    molecule_widget = MoleculeWidget()
    video = MoleculeVideo(None, ref_traj, molecule_widget)
    video.set_frame(n)
    assert video._frame == n
    assert video.slider is not None
    assert video.slider.value() == n
    assert all(all(np.isclose(p, r)) for p, r in zip(video._trajectory[video._frame], ref_frame))
