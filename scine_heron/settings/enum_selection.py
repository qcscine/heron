#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from enum import Enum
from typing import Type, Optional

from PySide2.QtCore import QObject
from scine_heron.containers.combo_box import ComboBox


class EnumSelectionBox(ComboBox):
    """
    A combo box that can be constructed with a ChemotonClassSearcher to include all its
    held classes as selectable items and split them based on its module information.
    """

    def __init__(self, parent: Optional[QObject], enum_type: Type[Enum], add_none: bool = False) -> None:
        """
        Construct the widget that allows to select any member of the Enum type

        Parameters
        ----------
        parent : QObject
            The parent widget
        enum_type : Type
            The enum type to select from, class must inherit from Enum
        add_none : bool, optional
            If 'None' should be added as an option to the combo box, by default False
        """
        self.enum_values = list(enum_type.__members__.values())
        if not self.enum_values:
            raise ValueError(f"Enum type {enum_type.__name__} has no members")

        ComboBox.__init__(self, parent=parent, values=list(enum_type.__members__.keys()), header=enum_type.__name__,
                          add_none=add_none)

    def get_value(self) -> Enum:
        """
        Returns the selected enum value
        """
        current_text = self.currentText().lower()
        for value in self.enum_values:
            if value.name.lower() == current_text:
                return value
        raise ValueError(f"Could not find enum value for {current_text}")
