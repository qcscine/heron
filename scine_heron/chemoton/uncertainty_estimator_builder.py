#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import Optional, List

from PySide2.QtCore import QObject
from PySide2.QtWidgets import (
    QDialog,
    QLabel,
    QCheckBox,
)
from scine_heron.containers.without_wheel_event import NoWheelDoubleSpinBox
from scine_chemoton.utilities.model_combinations import ModelCombination
from scine_chemoton.utilities.place_holder_model import construct_place_holder_model
from scine_chemoton.utilities.uncertainties import (
    UncertaintyEstimator, ConstantUncertainty, ModelCombinationBasedUncertaintyEstimator, ZeroUncertainty
)

from scine_heron.chemoton.uncertainty_tuple import UncertaintyTuple
from scine_heron.chemoton.model_combination_builder import ModelCombinationBuilder
from scine_heron.containers.layouts import VerticalLayout, HorizontalLayout
from scine_heron.settings.class_options_widget import DictOptionWidget


class UncertaintyEstimatorBuilder(QDialog):
    def __init__(self, option: UncertaintyEstimator, parent: Optional[QObject] = None):
        """
        Build the options object for the uncertainty estimator.
        """
        super().__init__(parent)
        self._uncertainty_list: List[UncertaintyTuple] = [UncertaintyTuple(
            ModelCombination(construct_place_holder_model()), ConstantUncertainty((0.0, 0.0)),
            ConstantUncertainty((0.0, 0.0)))
        ]
        use_default_zero = True
        if isinstance(option, ModelCombinationBasedUncertaintyEstimator):
            uncertainties_for_models = option.get_model_uncertainties()
            if uncertainties_for_models:
                if not all(isinstance(t[1], ConstantUncertainty) and isinstance(t[2], ConstantUncertainty)
                           for t in uncertainties_for_models):
                    raise ValueError("Only constant uncertainties are supported in Heron at the moment.")
                self._uncertainty_list = [UncertaintyTuple(t[0], t[1], t[2]) for t in uncertainties_for_models]
                use_default_zero = False
        self._disclaimer_widget = QLabel("Only constant uncertainties are supported in Heron at the moment.\n"
                                         "Use a Python script directly for more sophisticated uncertainty\n"
                                         "quantification.", parent=parent)
        self._use_default_zero_uncertainty = QCheckBox("Assume zero uncertainties for all models", parent=parent)
        self._use_default_zero_uncertainty.toggled.connect(self.__box_check_function)  # pylint: disable=no-member

        self._label = "Uncertainties"
        options = {self._label: self._uncertainty_list}
        self.dict_option_widget = DictOptionWidget(options, parent=parent)
        self._uncertainty_list_widget, self._getter_function\
            = self.dict_option_widget.construct_widget_based_on_type(self._uncertainty_list, self._label)

        layout = VerticalLayout([
            self._disclaimer_widget,
            self._use_default_zero_uncertainty,
            self._uncertainty_list_widget
        ])
        self.setLayout(layout)
        self._use_default_zero_uncertainty.setChecked(use_default_zero)

    def __box_check_function(self) -> None:
        self._uncertainty_list_widget.setVisible(not self._use_default_zero_uncertainty.isChecked())

    def get_uncertainty_estimator(self):
        if self._use_default_zero_uncertainty.isChecked():
            return ZeroUncertainty()
        uncertainty_tuple_list = [t.get_tuple() for t in self._getter_function()]
        return ModelCombinationBasedUncertaintyEstimator(uncertainty_tuple_list)


class UncertaintyBuilder(QDialog):
    def __init__(self, option: UncertaintyTuple, parent: Optional[QObject] = None):
        """
        Build the widget for an element of a list of uncertainties. This is required by the uncertainty estimator.
        """
        super().__init__(parent)
        assert isinstance(option, UncertaintyTuple)
        self._model_combination = option.model_combination
        self._free_energy_uncertainty = option.free_energy_uncertainty
        self._activation_uncertainty = option.activation_energy_uncertainty
        self._model_combination_label = QLabel("Model combination")
        self._model_combination_widget = ModelCombinationBuilder(self._model_combination)
        self._free_energy_uncertainty_label = QLabel("Free Energy Uncertainty (in J/mol)")
        if (not isinstance(self._free_energy_uncertainty, ConstantUncertainty)
                or not isinstance(self._activation_uncertainty, ConstantUncertainty)):
            raise ValueError("Only constant uncertainties are supported in Heron at the moment.")
        self._free_energy_uncertainty_widget = ConstantUncertaintyBuilder(self._free_energy_uncertainty, parent)
        self._activation_uncertainty_label = QLabel("Activation Energy Uncertainty (in J/mol)")
        self._activation_uncertainty_widget = ConstantUncertaintyBuilder(self._activation_uncertainty, parent)

        layout = VerticalLayout([
            self._model_combination_label,
            self._model_combination_widget,
            self._free_energy_uncertainty_label,
            self._free_energy_uncertainty_widget,
            self._activation_uncertainty_label,
            self._activation_uncertainty_widget
        ])
        self.setLayout(layout)

    def get_uncertainty_tuple(self) -> UncertaintyTuple:
        return UncertaintyTuple(self._model_combination_widget.get_model_combination(),
                                self._free_energy_uncertainty_widget.get_uncertainty(),
                                self._activation_uncertainty_widget.get_uncertainty())


class ConstantUncertaintyBuilder(QDialog):
    def __init__(self, option: ConstantUncertainty, parent: Optional[QObject] = None):
        """
        Build a widget for a constant uncertainty object.
        """
        super().__init__(parent)
        self._label = "uncertainty_bounds"

        lower, upper = option.get_uncertainty_bounds()
        maximum = 999999
        self._lower_edit = NoWheelDoubleSpinBox(parent=parent)
        self._lower_edit.setMinimum(0.0)
        self._lower_edit.setMaximum(maximum)
        self._lower_edit.setSingleStep(0.01)
        self._lower_edit.setDecimals(2)
        self._lower_edit.setValue(lower)

        self._upper_edit = NoWheelDoubleSpinBox(parent=parent)
        self._upper_edit.setMinimum(0.0)
        self._upper_edit.setMaximum(maximum)
        self._upper_edit.setSingleStep(0.01)
        self._upper_edit.setDecimals(2)
        self._upper_edit.setValue(upper)

        self._layout = HorizontalLayout([
            self._lower_edit,
            self._upper_edit
        ])
        self.setLayout(self._layout)

    def get_uncertainty(self) -> ConstantUncertainty:
        return ConstantUncertainty((self._lower_edit.value(), self._upper_edit.value()))
