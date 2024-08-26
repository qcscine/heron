#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional
from copy import deepcopy
from PySide2.QtCore import QObject
from PySide2.QtWidgets import (
    QDialog,
    QLabel
)

from scine_chemoton.utilities.model_combinations import ModelCombination

from scine_heron.containers.layouts import VerticalLayout
from scine_heron.settings.class_options_widget import ModelOptionsWidget


class ModelCombinationBuilder(QDialog):
    def __init__(self, options: ModelCombination, parent: Optional[QObject] = None):
        """
        Define a model combination.
        """
        super().__init__(parent=parent)
        # widgets
        self._electronic_label = QLabel("Model for electronic energies")
        self._electronic_model_widget = ModelOptionsWidget(parent=parent, model=options.electronic_model)
        self._hessian_label = QLabel("Model for free energy corrections")
        self._hessian_model_widget = ModelOptionsWidget(parent=parent, model=options.hessian_model)
        # layout
        layout = VerticalLayout([
            self._electronic_label,
            self._electronic_model_widget,
            self._hessian_label,
            self._hessian_model_widget])
        self.setLayout(layout)

    def get_model_combination(self) -> ModelCombination:
        model_combination = ModelCombination(
            deepcopy(self._electronic_model_widget.model),
            deepcopy(self._hessian_model_widget.model)
        )
        return model_combination
