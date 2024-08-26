#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""


class CalculatorSettings:
    def __init__(self) -> None:
        self.method: str = 'PM6'
        self.molecular_charge: int = 0
        self.spin_multiplicity: int = 1
        self.spin_mode: str = 'unrestricted'
        self.self_consistence_criterion: float = 1e-5
        self.scf_mixer: str = 'diis'
