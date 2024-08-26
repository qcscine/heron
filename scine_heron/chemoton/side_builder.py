#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional
import scine_database as db

from PySide2.QtCore import QObject
from scine_heron.containers.combo_box import BaseBox


class SideBuilder(BaseBox):
    """
    Selection for the database Side enum.
    """

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent=parent)
        self.addItems(["BOTH", "LHS", "RHS"])
        self.sides = {
            "BOTH": db.Side.BOTH,
            "LHS": db.Side.LHS,
            "RHS": db.Side.RHS,
        }

    def get_side(self) -> db.Side:
        assert self.currentText()
        return self.sides[self.currentText()]
