#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
import sys

from .mocks import scine_heron_haptic_mock as haptic_mock
from .mocks import animator_pooling_functions_mock as apf

sys.modules["scine_heron_haptic"] = haptic_mock
sys.modules["scine_heron.molecule.animator_pooling_functions"] = apf
