#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the ClassOptionsWidget class.
"""

from typing import Optional, List, TYPE_CHECKING, Tuple

from PySide2.QtCore import QObject
from PySide2.QtWidgets import (
    QLabel,
    QDialog,
    QWidget,
)

from scine_heron.containers.buttons import TextPushButton
from scine_heron.containers.combo_box_tab_widget import ComboBoxTabWidget
from scine_heron.containers.combo_box import ComboBox
from scine_heron.containers.layouts import VerticalLayout, HorizontalLayout
from scine_heron.dependencies.optional_import import is_imported, importer
from scine_heron.utilities import vertical_scroll_area_wrap

if TYPE_CHECKING:
    from scine_chemoton.steering_wheel.datastructures import GearOptions
    from scine_chemoton.gears.elementary_steps.trial_generator import TrialGenerator
    from scine_chemoton.gears import Gear
    from scine_heron.chemoton.class_searcher import ChemotonClassSearcher
    from scine_heron.chemoton.chemoton_widget import construct_all_possible_gears
else:
    GearOptions = importer("scine_chemoton.steering_wheel.datastructures", "GearOptions")
    TrialGenerator = importer("scine_chemoton.gears.elementary_steps.trial_generator", "TrialGenerator")
    Gear = importer("scine_chemoton.gears", "Gear")
    ChemotonClassSearcher = importer("scine_heron.chemoton.class_searcher", "ChemotonClassSearcher")
    construct_all_possible_gears = importer("scine_heron.chemoton.chemoton_widget", "construct_all_possible_gears")


class SingleGearOptionsWidget(QWidget):

    def __init__(self, gear_option: Tuple[Gear.Options, Optional[TrialGenerator.Options]],
                 name: str, parent: QWidget) -> None:
        from scine_heron.settings.dict_option_widget import DictOptionWidget

        super().__init__(parent=parent)
        self._parent = parent
        self._content_dict = {
            'Gear.Options': gear_option[0],
        }
        if gear_option[1] is not None:
            self._content_dict['TrialGenerator.Options'] = gear_option[1]

        content_widget = QWidget(parent=self)
        content_widget.setLayout(VerticalLayout([
            TextPushButton("Remove this option", lambda: self._parent.remove_tab(name), parent=self),
            DictOptionWidget(
                self._content_dict,
                parent=self,
                add_close_button=False,
                allow_additions=False,
                allow_removal=False,
                show_border=True,
            ),
        ]))
        self.setLayout(VerticalLayout([vertical_scroll_area_wrap(content_widget)]))


class GearOptionsWidget(ComboBoxTabWidget):
    """
    A popup widget for editing the options of a class or a dictionary.
    This class is basically a wrapper around DictOptionWidget.
    """

    def __init__(
            self,
            gear_options: Optional[GearOptions] = None,
            allowed_gears: Optional[List[Gear]] = None,
            parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent=parent)
        if not is_imported(ChemotonClassSearcher):
            raise ImportError("ChemotonClassSearcher could not be imported.")

        self._layout.insertWidget(1, TextPushButton("Add new option to set", self._add_option, parent=self))
        if gear_options is None:
            gear_options = GearOptions()
        self._gear_options = gear_options
        if allowed_gears is None:
            allowed_gears = construct_all_possible_gears()
        self._allowed_gears = allowed_gears
        self._chemoton_gear_searcher = ChemotonClassSearcher(Gear)

    def get_options(self) -> GearOptions:
        return self._gear_options

    def _add_option(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Add option")
        gear_sele = ComboBox(parent=dialog, values=[g.name for g in self._allowed_gears], header="Gear", add_none=False)
        index_sele = ComboBox(parent=dialog, values=[str(i) for i in range(9)] + ['None'], header="Index")
        index_sele.setToolTip("Specify the index position of the gear starting at zero,"
                              "or 'None' to affect all gears of that type.")
        layout = VerticalLayout()
        layout.add_layouts([
            HorizontalLayout([QLabel("Gear: "), gear_sele]),
            HorizontalLayout([QLabel("Specify index position"), index_sele]),
        ])
        layout.add_widgets([
            TextPushButton("Cancel", dialog.reject),
            TextPushButton("Add", dialog.accept),
        ])
        dialog.setLayout(layout)
        if dialog.exec_():
            gear_name = gear_sele.currentText()
            # pick the first gear with that name
            gear = next(g for g in self._allowed_gears if g.name == gear_name)
            index_str = index_sele.currentText()
            if index_str.lower() == "none":
                index: Optional[int] = None
            else:
                index = int(index_str)
            self._gear_options += [(gear, index)]
            name = f"{gear.name}, {index}"
            single_option = SingleGearOptionsWidget(self._gear_options[(gear.name, index)], name, parent=self)
            self.add_tab(name, single_option)


class GearOptionsBuilderButtonWrapper(TextPushButton):

    def __init__(self, gear_options: Optional[GearOptions], allowed_gears: Optional[List[Gear]] = None,
                 parent: Optional[QObject] = None):
        super().__init__("Specify gear options", self.execute, parent=parent)
        if gear_options is None:
            gear_options = GearOptions()
        self._options = gear_options
        self._allowed_gears = allowed_gears

    def execute(self) -> None:
        builder = GearOptionsWidget(gear_options=self._options, allowed_gears=self._allowed_gears, parent=self)
        dialog = QDialog(self)
        dialog.setWindowTitle("Specify gear options")
        layout = VerticalLayout([
            builder,
            TextPushButton("Finished", dialog.accept),
        ])
        dialog.setLayout(layout)
        dialog.exec_()
        self._options = builder.get_options()

    def get_options(self) -> GearOptions:
        return self._options
