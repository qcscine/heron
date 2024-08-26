__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

# import typing
# from functools import partial
# from typing import Any, Callable, Dict, List, Tuple
#
# if typing.TYPE_CHECKING:
#     Signal = typing.Any
# else:
#     pass
#
#
# from PySide2.QtCore import QParallelAnimationGroup, QSize, Qt
# from PySide2.QtWidgets import (QComboBox, QDialog, QDockWidget, QFrame,
#                                QGridLayout, QHBoxLayout, QLabel, QLineEdit,
#                                QPushButton, QScrollArea, QSpinBox, QToolButton,
#                                QTreeWidget, QTreeWidgetItem, QVBoxLayout,
#                                QWidget, QDoubleSpinBox, QRadioButton, QCheckBox)
#
# from scine_heron.autocas.autocas_settings import AutocasSettings
# from scine_heron.autocas.basic_options import Interfaces
# from scine_heron.autocas.open_molcas_popup import OpenMolcasOptionsPopup
# from scine_heron.autocas.options_status_manager import OptionsStatusManager
# from scine_heron.autocas.signal_handler import SignalHandler
# from scine_heron.settings.settings import LabelsStyle, MoleculeStyle
# from scine_heron.status_manager import Status, StatusManager
#
# import os
#
#
# class OptionsWidget(QDockWidget):
#     def __init__(
#         self,
#         parent,
#         # options_status_manager: OptionsStatusManager,
#         signal_handler: SignalHandler,
#         autocas_settings: AutocasSettings,
#     ):
#         QDockWidget.__init__(self, "")
#
#         self.signal_handler = signal_handler
#         self.autocas_settings = autocas_settings
#
#         self.setFeatures(QDockWidget.NoDockWidgetFeatures)
#         self.__dockedWidget = QWidget(self)
#         self.setWidget(self.__dockedWidget)
#         self.__layout = QVBoxLayout()
#         self.__dockedWidget.setLayout(self.__layout)
#         self.__layout.setAlignment(Qt.AlignTop)
#
#         self.molecular_options = MolecularOptionsWidget(self, self.signal_handler, self.autocas_settings)
#         self.__layout.addWidget(self.molecular_options)
#         self.molecular_options.molecular_options()
#
#         self.molecular_options = MolecularOptionsWidget(self, self.signal_handler, self.autocas_settings)
#         self.__layout.addWidget(self.molecular_options)
#         self.molecular_options.molecular_options()
#
#         self.initial_orbital_options = InitialOrbitalOptionsWidget(self, self.signal_handler, self.autocas_settings)
#         self.__layout.addWidget(self.initial_orbital_options)
#         self.initial_orbital_options.initial_orbital_options()
#         # self.autocas_options()
#         # self.molcas_options()
#         # self.initial_orbital_options()
#         # self.initial_dmrg_options()
#         # self.final_calculation_options()
#
#     def basic_options(self):
#         pass
#
#
# class MolecularOptionsWidget(QWidget):
#     def __init__(self, parent, signal_handler, autocas_settings):
#         QWidget.__init__(self, parent)
#         self.layout = QGridLayout()
#         self.layout.setColumnMinimumWidth(0, 100)
#         self.layout.setColumnMinimumWidth(1, 100)
#         self.layout.setColumnMinimumWidth(2, 100)
#         self.layout.setColumnMinimumWidth(3, 100)
#         self.layout.setColumnMinimumWidth(4, 100)
#         self.layout.setColumnMinimumWidth(5, 200)
#         self.layout.setColumnMinimumWidth(6, 100)
#
#         self.layout.setRowMinimumHeight(0, 60)
#         self.layout.setRowMinimumHeight(1, 60)
#         self.layout.setRowMinimumHeight(2, 60)
#         self.layout.setRowMinimumHeight(3, 60)
#         self.layout.setRowMinimumHeight(4, 60)
#
#         self.basis_label = QLabel("Basis Set")
#         self.basis_label.setMaximumWidth(100)
#         self.basis_set_edit = QLineEdit(self)
#         self.basis_set_edit.setText("cc-pvdz")
#         self.basis_set_edit.setMaximumSize(100, 40)
#
#         self.charge_label = QLabel("Charge")
#         self.charge_label.setMaximumWidth(100)
#         self.charge_edit = QSpinBox()
#         self.charge_edit.setValue(0)
#         self.charge_edit.setMaximumSize(100, 40)
#
#         self.spin_multiplicity_label = QLabel("Spin Multiplicity")
#         self.spin_multiplicity_label.setMaximumWidth(200)
#         self.spin_multiplicity_edit = QSpinBox()
#         self.spin_multiplicity_edit.setValue(1)
#         self.spin_multiplicity_edit.setMinimum(1)
#         self.spin_multiplicity_edit.setMaximumWidth(100)
#
#         self.number_of_roots_label = QLabel("Number Of Roots")
#         self.number_of_roots_label.setMaximumWidth(100)
#         self.number_of_roots_edit = QSpinBox()
#         self.number_of_roots_edit.setValue(1)
#         self.number_of_roots_edit.setMinimum(1)
#
#         self.double_d_shell_label = QLabel("Include double d-shell")
#         self.double_d_shell_label.setMaximumWidth(100)
#         self.double_d_shell = QCheckBox()
#         self.double_d_shell.setChecked(True)
#         self.setLayout(self.layout)
#
#     def molecular_options(self):
#         # self.__layout.addWidget(QLabel("Molecular Settings"))
#         self.layout.addWidget(self.basis_label, 0, 0, 0, 1)
#         self.layout.addWidget(self.basis_set_edit, 0, 1, 0, 2)
#
#         self.layout.addWidget(self.charge_label, 0, 3, 0, 4)
#         self.layout.addWidget(self.charge_edit, 0, 4, 0, 5)
#
#         self.layout.addWidget(self.spin_multiplicity_label, 0, 5, 0, 6)
#         self.layout.addWidget(self.spin_multiplicity_edit, 0, 6, 0, 7)
#
#         # self.layout.addWidget(self.number_of_roots_label, 1, 0, 1, 1)
#         # self.layout.addWidget(self.number_of_roots_edit, 1, 1, 1, 2)
#         #
#         # self.layout.addWidget(self.double_d_shell_label, 1, 2, 1, 3)
#         # self.layout.addWidget(self.double_d_shell, 1, 3, 1, 4)
#         self.setLayout(self.layout)
#
#
# class InitialOrbitalOptionsWidget(QWidget):
#     def __init(self, parent, signal_handler, autocas_settings):
#         self.uhf = QCheckBox()
#         self.uhf.setChecked(False)
#
#     def initial_orbital_options(self):
#         self.__layout.addWidget(QLabel("Initial Orbital Settings"))
#
#         layout = QHBoxLayout()
#         sub_layout = QVBoxLayout()
#         sub_layout.addWidget(QLabel("Unrestricted"))
#         layout.addLayout(sub_layout)
#         sub_layout = QVBoxLayout()
#         sub_layout.addWidget(uhf)
#         layout.addLayout(sub_layout)
#         self.__layout.addLayout(layout)
#
#
# class MolcasOptionsWidget(QWidget):
#     def __init(self, parent, signal_handler, autocas_settings):
#         self.molcas_project_name = QLineEdit(self)
#         self.molcas_project_name.setText("autocas")
#
#         self.molcas_dump = QCheckBox()
#         self.molcas_dump.setChecked(True)
#
#         self.molcas_work_dir = QLineEdit(self)
#         self.molcas_work_dir.setText(os.getcwd() + "/test")
#
#         self.cholesky = QCheckBox()
#         self.cholesky.setChecked(True)
#
#     def molcas_options(self):
#         self.__layout.addWidget(QLabel("Molcas Settings"))
#
#         layout = QHBoxLayout()
#         sub_layout = QVBoxLayout()
#         sub_layout.addWidget(QLabel("Project Name"))
#         sub_layout.addWidget(QLabel("Enable Dump"))
#         sub_layout.addWidget(QLabel("Work Dir"))
#         sub_layout.addWidget(QLabel("Enable Cholesky decomposition"))
#         layout.addLayout(sub_layout)
#         sub_layout = QVBoxLayout()
#         sub_layout.addWidget(molcas_project_name)
#         sub_layout.addWidget(molcas_dump)
#         sub_layout.addWidget(molcas_work_dir)
#         sub_layout.addWidget(cholesky)
#         layout.addLayout(sub_layout)
#         self.__layout.addLayout(layout)
#
#
# class InitialDMRGOptions(QWidget):
#     def __init(self, parent, signal_handler, autocas_settings):
#         self.method = QComboBox()
#         self.method.addItems(["DMRG-CI", "DMRG-SCF"])
#
#         self.bond_dimension = QSpinBox()
#         self.bond_dimension.setMaximum(6000)
#         self.bond_dimension.setMinimum(1)
#         self.bond_dimension.setValue(250)
#
#         self.n_sweeps = QSpinBox()
#         self.n_sweeps.setValue(5)
#         self.n_sweeps.setMinimum(1)
#
#         self.fiedler_ordering = QCheckBox()
#         self.fiedler_ordering.setChecked(True)
#
#         self.large_cas = QCheckBox()
#         self.large_cas.setChecked(False)
#
#         self.n_large_cas_orbitals = QSpinBox()
#         self.n_large_cas_orbitals.setMinimum(1)
#         self.n_large_cas_orbitals.setValue(10)
#
#     def initial_dmrg_options(self):
#         self.__layout.addWidget(QLabel("Initial DMRG Settings"))
#
#         layout = QHBoxLayout()
#         sub_layout = QVBoxLayout()
#         sub_layout.addWidget(QLabel("Method"))
#         sub_layout.addWidget(QLabel("Bond dimension"))
#         sub_layout.addWidget(QLabel("Number of Sweeps"))
#         sub_layout.addWidget(QLabel("Fiedler Ordering"))
#         sub_layout.addWidget(QLabel("Enable Large CAS Protocol"))
#         sub_layout.addWidget(QLabel("Number of orbitals per sub-CAS"))
#         layout.addLayout(sub_layout)
#         sub_layout = QVBoxLayout()
#         sub_layout.addWidget(method)
#         sub_layout.addWidget(bond_dimension)
#         sub_layout.addWidget(n_sweeps)
#         sub_layout.addWidget(fiedler_ordering)
#         sub_layout.addWidget(large_cas)
#         sub_layout.addWidget(n_large_cas_orbitals)
#         layout.addLayout(sub_layout)
#         self.__layout.addLayout(layout)
#
#
# class FinalCalculationOptions(QWidget):
#     def __init(self, parent, signal_handler, autocas_settings):
#         self.method = QComboBox()
#         self.method.addItems(["DMRG-CI", "DMRG-SCF", "CASSCF", "CASCI"])
#
#         self.bond_dimension = QSpinBox()
#         self.bond_dimension.setMaximum(6000)
#         self.bond_dimension.setMinimum(1)
#         self.bond_dimension.setValue(2000)
#
#         self.n_sweeps = QSpinBox()
#         self.n_sweeps.setValue(20)
#         self.n_sweeps.setMinimum(1)
#
#         self.fiedler_ordering = QCheckBox()
#         self.fiedler_ordering.setChecked(True)
#
#         self.post_method = QComboBox()
#         self.post_method.addItems(["CASPT2", "NEVPT2"])
#
#         self.ipea = QDoubleSpinBox()
#         self.ipea.setValue(0.0)
#
#     def final_calculation_options(self):
#         self.__layout.addWidget(QLabel("Final Calculation Settings"))
#
#         layout = QHBoxLayout()
#         sub_layout = QVBoxLayout()
#         sub_layout.addWidget(QLabel("Method"))
#         sub_layout.addWidget(QLabel("Bond dimension"))
#         sub_layout.addWidget(QLabel("Number of Sweeps"))
#         sub_layout.addWidget(QLabel("Fiedler Ordering"))
#         sub_layout.addWidget(QLabel("Post CAS method"))
#         sub_layout.addWidget(QLabel("IPEA-Shift"))
#         layout.addLayout(sub_layout)
#         sub_layout = QVBoxLayout()
#         sub_layout.addWidget(method)
#         sub_layout.addWidget(bond_dimension)
#         sub_layout.addWidget(n_sweeps)
#         sub_layout.addWidget(fiedler_ordering)
#         sub_layout.addWidget(post_method)
#         sub_layout.addWidget(ipea)
#         layout.addLayout(sub_layout)
#         self.__layout.addLayout(layout)
#
#
# class AutoCASOptions(QWidget):
#     def __init(self, parent, signal_handler, autocas_settings):
#         self.plateau_values = QSpinBox(self)
#         self.plateau_values.setValue(10)
#
#         self.threshold_step = QDoubleSpinBox()
#         self.threshold_step.setValue(0.01)
#
#         self.weak_correlation_threshold = QDoubleSpinBox()
#         self.weak_correlation_threshold.setValue(0.02)
#
#         self.single_reference_threshold = QDoubleSpinBox()
#         self.single_reference_threshold.setValue(0.14)
#
#     def autocas_options(self):
#         self.__layout.addWidget(QLabel("AutoCAS Settings"))
#
#         plateau_values = QSpinBox(self)
#         plateau_values.setValue(10)
#
#         threshold_step = QDoubleSpinBox()
#         threshold_step.setValue(0.01)
#
#         weak_correlation_threshold = QDoubleSpinBox()
#         weak_correlation_threshold.setValue(0.02)
#
#         single_reference_threshold = QDoubleSpinBox()
#         single_reference_threshold.setValue(0.14)
#
#         layout = QHBoxLayout()
#         sub_layout = QVBoxLayout()
#         sub_layout.addWidget(QLabel("Required values for a plateau"))
#         sub_layout.addWidget(QLabel("Step size for a plateau"))
#         sub_layout.addWidget(QLabel("Weak correlation threshold"))
#         sub_layout.addWidget(QLabel("Single reference threshold"))
#         layout.addLayout(sub_layout)
#         sub_layout = QVBoxLayout()
#         sub_layout.addWidget(plateau_values)
#         sub_layout.addWidget(threshold_step)
#         sub_layout.addWidget(weak_correlation_threshold)
#         sub_layout.addWidget(single_reference_threshold)
#         layout.addLayout(sub_layout)
#         self.__layout.addLayout(layout)
#
#
# class PlotOptions(QWidget):
#     def __init(self, parent, signal_handler, autocas_settings):
#         self.basis_set_edit = QLineEdit(self)
#         self.basis_set_edit.setText("cc-pvdz")
#
#         self.charge_edit = QSpinBox()
#         self.charge_edit.setValue(0)
#         self.charge_edit.setMinimum(-100000)
#
#         self.spin_multiplicity_edit = QSpinBox()
#         self.spin_multiplicity_edit.setValue(1)
#         self.spin_multiplicity_edit.setMinimum(1)
#
#         self.number_of_roots_edit = QSpinBox()
#         self.number_of_roots_edit.setValue(1)
#         self.number_of_roots_edit.setMinimum(1)
#
#     def plot_options(self):
#         self.__layout.addWidget(QLabel("Initial Orbital Settings"))
#
#         layout = QHBoxLayout()
#         sub_layout = QVBoxLayout()
#         sub_layout.addWidget(QLabel("Basis Set"))
#         sub_layout.addWidget(QLabel("Charge"))
#         sub_layout.addWidget(QLabel("Spin Multiplicity"))
#         sub_layout.addWidget(QLabel("Number Of Roots"))
#         layout.addLayout(sub_layout)
#         sub_layout = QVBoxLayout()
#         sub_layout.addWidget(basis_set_edit)
#         sub_layout.addWidget(charge_edit)
#         sub_layout.addWidget(spin_multiplicity_edit)
#         sub_layout.addWidget(number_of_roots_edit)
#         layout.addLayout(sub_layout)
#         self.__layout.addLayout(layout)
#
#         # self.setFeatures(QDockWidget.NoDockWidgetFeatures)
#         #
#         # self.__dockedWidget = QWidget(self)
#         # self.setWidget(self.__dockedWidget)
#         #
#         # self.__layout = QVBoxLayout()
#         # self.__dockedWidget.setLayout(self.__layout)
#         # self.__layout.setAlignment(Qt.AlignTop)
#         #
#         # # self.__options_status_manager = options_status_manager
#         #
#         # self.__widgets_dict: Dict[str, Any] = {}
#         # self.__widget_height = 30
#         # self.__widget_width = 130
#         #
#         # self.__enabled = StatusManager(True)
#         #
#         # self.__add_interface_option(
#         #     "Interface",
#         #     [Interfaces.OpenMolcas.value],  # , Interfaces.Serenity.value],
#         #     self.__update_interface,
#         #     Interfaces.OpenMolcas.value,
#         #     enabled=self.__enabled,
#         # )
#         # self.__add_system_options_at_layout(enabled=self.__enabled)
#
#     # def button_clicked(self, s):
#     #     open_molcas_popup = OpenMolcasOptionsPopup(self)
#     #     open_molcas_popup.exec_()
#     #
#     # def __add_interface_option(
#     #     self,
#     #     option_name: str,
#     #     all_values: List[str],
#     #     update: Callable[[List[str], int], None],
#     #     default_value: str,
#     #     enabled: Status[bool],
#     # ) -> None:
#     #     combo_box = self.__add_combo_box_at_layout(option_name, option_name, all_values)
#     #     combo_box.currentIndexChanged.connect(partial(update, all_values))
#     #     combo_box.setCurrentIndex(all_values.index(default_value))
#     #     enabled.changed_signal.connect(combo_box.setEnabled)
#     #
#     #     self.interface_options = QPushButton("Advanced Options")
#     #     self.__layout.addWidget(self.interface_options)
#     #     self.interface_options.clicked.connect(self.button_clicked)
#     #
#     # def __add_system_options_at_layout(self, enabled: Status[bool]):
#     #     basis_set_edit = QLineEdit(self)
#     #     basis_set_edit.setText("cc-pvdz")
#     #
#     #     charge_edit = QSpinBox()
#     #     charge_edit.setValue(0)
#     #     charge_edit.setMinimum(-100000)
#     #
#     #     spin_multiplicity_edit = QSpinBox()
#     #     spin_multiplicity_edit.setValue(1)
#     #     spin_multiplicity_edit.setMinimum(1)
#     #
#     #     number_of_roots_edit = QSpinBox()
#     #     number_of_roots_edit.setValue(1)
#     #     number_of_roots_edit.setMinimum(1)
#     #
#     #     layout = QHBoxLayout()
#     #     sub_layout = QVBoxLayout()
#     #     sub_layout.addWidget(QLabel("Basis Set"))
#     #     sub_layout.addWidget(QLabel("Charge"))
#     #     sub_layout.addWidget(QLabel("Spin Multiplicity"))
#     #     sub_layout.addWidget(QLabel("Number Of Roots"))
#     #     layout.addLayout(sub_layout)
#     #     sub_layout = QVBoxLayout()
#     #     sub_layout.addWidget(basis_set_edit)
#     #     sub_layout.addWidget(charge_edit)
#     #     sub_layout.addWidget(spin_multiplicity_edit)
#     #     sub_layout.addWidget(number_of_roots_edit)
#     #     layout.addLayout(sub_layout)
#     #     self.__layout.addLayout(layout)
#     #
#     # def __update_interface(self, all_values: List[str], index: int) -> None:
#     #     """
#     #     Update molecule style.
#     #     """
#     #     self.__options_status_manager.interface = Interfaces(all_values[index])
#     #
#     # def __add_combo_box_at_layout(
#     #     self,
#     #     setting_name: str,
#     #     setting_key: str,
#     #     all_values: List[str],
#     # ) -> QComboBox:
#     #     """
#     #     Add QComboBox widget.
#     #     setting_name is a setting display name.
#     #     setting_key is a setting name in sparrow.
#     #     all_values is a list of valid values.
#     #     """
#     #     combo_box = QComboBox()
#     #     combo_box.addItems(all_values)
#     #     combo_box.setFixedSize(QSize(self.__widget_width, self.__widget_height + 1))
#     #
#     #     #   self.__widgets_dict[setting_key] = combo_box
#     #
#     #     layout = QHBoxLayout()
#     #     layout.addWidget(QLabel(setting_name))
#     #     layout.addWidget(combo_box)
#     #     self.__layout.addLayout(layout)
#     #
#     #     return combo_box
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#     #
#
# # class SectionExpandButton(QPushButton):
# #     def __init__(self, item, text="", parent=None):
# #         super().__init__(text, parent)
# #         self.section = item
# #         self.clicked.connect(self.on_clicked)
# #
# #     def on_clicked(self):
# #         if self.section.isExpanded():
# #             self.section.setExpanded(False)
# #         else:
# #             self.section.setExpanded(True)
# #
# #
# # class OptionsWidget_bck(QDialog):
# #     def __init__(
# #         self,
# #         parent: QWidget,
# #         signal_handler: SignalHandler,
# #         autocas_settings: AutocasSettings,
# #     ):
# #         super().__init__()
# #         self.signal_handler = signal_handler
# #         self.autocas_settings = autocas_settings
# #         self.tree = QTreeWidget()
# #         self.tree.setHeaderHidden(True)
# #         layout = QVBoxLayout()
# #         layout.addWidget(self.tree)
# #         self.setLayout(layout)
# #         # self.tree.setIndentation(0)
# #
# #         self.sections: List[Tuple[QWidget, str]] = []
# #         self.define_sections()
# #         self.add_sections()
# #
# #     def add_sections(self):
# #         """adds a collapsible sections for every
# #         (title, widget) tuple in self.sections
# #         """
# #         for (title, widget) in self.sections:
# #             button1 = self.add_button(title)
# #             section1 = self.add_widget(button1, widget)
# #             button1.addChild(section1)
# #
# #     def define_sections(self):
# #         """reimplement this to define all your sections
# #         and add them as (title, widget) tuples to self.sections
# #         """
# #         widget = QFrame(self.tree)
# #         layout = QHBoxLayout(widget)
# #         layout.addWidget(
# #             OrbitalOption(self, self.signal_handler, self.autocas_settings)
# #         )
# #         # layout.addWidget(QLabel("Bla"))
# #         # layout.addWidget(QLabel("Blubb"))
# #         self.sections.append(("Hartree-Fock", widget))
# #         self.sections.append(("DMRG", widget))
# #
# #     def add_button(self, title):
# #         """creates a QTreeWidgetItem containing a button
# #         to expand or collapse its section
# #         """
# #         item = QTreeWidgetItem()
# #         self.tree.addTopLevelItem(item)
# #         self.tree.setItemWidget(item, 0, SectionExpandButton(item, text=title))
# #         return item
# #
# #     def add_widget(self, button, widget):
# #         """creates a QWidgetItem containing the widget,
# #         as child of the button-QWidgetItem
# #         """
# #         section = QTreeWidgetItem(button)
# #         section.setDisabled(True)
# #         self.tree.setItemWidget(section, 0, widget)
# #         return section
# #
# #
# # class OrbitalOption(QDockWidget):
# #     def __init__(self, parent, signal_handler, autocas_settings):
# #         super().__init__()
# #         self.setFeatures(QDockWidget.NoDockWidgetFeatures)
# #
# #         self.__dockedWidget = QWidget(self)
# #         self.setWidget(self.__dockedWidget)
# #
# #         self.__layout = QVBoxLayout()
# #         self.__dockedWidget.setLayout(self.__layout)
# #         self.__layout.setAlignment(Qt.AlignTop)
