__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox,
                               QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QSpinBox, QVBoxLayout)


class OpenMolcasOptionsPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("OpenMolcas Interface Options")
        self.__layout = QGridLayout()
        self.__add_options()

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        # pylint: disable-next=E1101
        self.buttonBox.accepted.connect(self.accept)
        # pylint: disable-next=E1101
        self.buttonBox.rejected.connect(self.reject)
        self.__layout.addWidget(self.buttonBox, 1, 0, alignment=Qt.AlignCenter)

        self.setLayout(self.__layout)

    def __add_options(self):
        project_name_edit = QLineEdit(self)
        molcas_binary_location_edit = QLineEdit(self)
        molcas_flags_edit = QLineEdit(self)
        molcas_max_memory_edit = QSpinBox(self)
        molcas_scratch_dir_edit = QLineEdit(self)
        molcas_dumping_edit = QCheckBox(self)
        molcas_max_processes = QSpinBox(self)
        molcas_max_processes.setMinimum(1)

        layout = QHBoxLayout()
        sub_layout = QVBoxLayout()
        sub_layout.addWidget(QLabel("Project Name"))
        sub_layout.addWidget(QLabel("Binary Location"))
        sub_layout.addWidget(QLabel("<< pymolcas >> Flags"))
        sub_layout.addWidget(QLabel("Max Memory [MB]"))
        sub_layout.addWidget(QLabel("Scratch Location"))
        sub_layout.addWidget(QLabel("Dumping"))
        sub_layout.addWidget(QLabel("Max Processes"))
        layout.addLayout(sub_layout)
        sub_layout = QVBoxLayout()
        sub_layout.addWidget(project_name_edit)
        sub_layout.addWidget(molcas_binary_location_edit)
        sub_layout.addWidget(molcas_flags_edit)
        sub_layout.addWidget(molcas_max_memory_edit)
        sub_layout.addWidget(molcas_scratch_dir_edit)
        sub_layout.addWidget(molcas_dumping_edit)
        sub_layout.addWidget(molcas_max_processes)
        layout.addLayout(sub_layout)
        self.__layout.addLayout(layout, 0, 0)
