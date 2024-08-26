#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import scine_utilities as su
import numpy as np


@dataclass
class CustomResult:
    result: su.Results = field(default_factory=su.Results)
    energy: float = field(default=0.0, init=False)
    gradients: Optional[np.ndarray] = field(default=None, init=False)
    hessian: np.ndarray = field(init=False)
    positions: Optional[np.ndarray] = field(default=None)
    atomic_charges: Optional[List[float]] = field(init=False)
    bond_orders: Optional[np.ndarray] = field(init=False)
    molden_input: str = field(default="")
    error_msg: str = field(default="")
    info_msg: str = field(default="")
    settings: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.result.successful_calculation is None:
            self.successful = False
            return self
        if not self.result.successful_calculation:
            return CustomResult()
        self.energy: float = self.result.energy
        self.gradients: np.ndarray = self.result.gradients
        self.hessian: np.ndarray = self._construct_hessian()
        self.atomic_charges: List[float] = self.result.atomic_charges
        self.bond_orders: np.ndarray = self._construct_bond_matrix()
        self.successful: bool = self.result.successful_calculation is not None and self.result.successful_calculation

    def _construct_hessian(self) -> Optional[np.ndarray]:
        if self.result.atomic_hessian is not None and self.result.atomic_charges is not None:
            size = len(self.result.atomic_charges)
            # Convert list of atomic hessians to block-diagonal pos. definite approx. hessian
            atomic_hessians = self.result.atomic_hessian.get_atomic_hessians()
            new_atomic_hessians = []
            for atomic_hessian in atomic_hessians:
                eigvals, eigvecs = np.linalg.eig(atomic_hessian)
                new_eigvals = abs(eigvals)
                new_atomic_hessians.append(eigvecs @ np.diag(new_eigvals) @ eigvecs.T)
            new_hessian = np.zeros((3 * size, 3 * size,))
            for i in range(size):
                new_hessian[i * 3: i * 3 + 3, i * 3: i * 3 + 3] = new_atomic_hessians[i]
        elif self.result.hessian is not None:
            hessian = self.result.hessian
            # Make hessian pos. definite
            eigvals, eigvecs = np.linalg.eig(hessian)
            new_eigvals = abs(eigvals)
            new_hessian = eigvecs @ np.diag(new_eigvals) @ eigvecs.T
        else:
            new_hessian = None
        return new_hessian

    def _construct_bond_matrix(self) -> Optional[np.ndarray]:
        if self.result.bond_orders is not None:
            return self.result.bond_orders.matrix.toarray()
        return None

    def __bool__(self):
        return self.successful

    def make_pickleable(self):
        self.result = None
