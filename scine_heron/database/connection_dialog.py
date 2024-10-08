#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from typing import Optional
from PySide2.QtCore import QObject
from PySide2.QtWidgets import (
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QDialog,
    QLabel,
    QMessageBox,
)
from scine_database import Manager

from scine_heron.io.text_box import yes_or_no_question
from scine_heron.utilities import write_error_message, write_info_message


class DatabaseConnectionDialog(QDialog):
    def __init__(self, parent: Optional[QObject] = None, db_manager=None) -> None:
        super(DatabaseConnectionDialog, self).__init__(parent)
        self.setWindowTitle("Connect to Database")

        # Prep manager
        self.db_manager = db_manager
        default_ip = "127.0.0.1"
        default_port = "27017"
        default_db_name = "default"
        if self.db_manager is None:
            self.db_manager = Manager()
        elif self.db_manager.has_credentials():
            # Use current values
            c = self.db_manager.get_credentials()
            default_ip = c.hostname
            default_port = str(c.port)
            default_db_name = c.database_name

        # Create widgets
        self.ip_label = QLabel("Server IP:")
        self.port_label = QLabel("Server Port:")
        self.name_label = QLabel("Database Name:")
        self.ip = QLineEdit(default_ip)
        self.port = QLineEdit(default_port)
        self.port.setMaxLength(5)
        self.name = QLineEdit(default_db_name)
        self.button_connect = QPushButton("Connect")
        self.button_disconnect = QPushButton("Disconnect")
        self.button_wipe = QPushButton("Wipe")
        self.button_close = QPushButton("Close")

        # Create layout and add widgets
        layout = QVBoxLayout()
        layout.setObjectName("Connect to Database")
        layout.addWidget(self.ip_label)
        layout.addWidget(self.ip)
        layout.addWidget(self.port_label)
        layout.addWidget(self.port)
        layout.addWidget(self.name_label)
        layout.addWidget(self.name)
        layout.addWidget(self.button_connect)
        layout.addWidget(self.button_disconnect)
        layout.addWidget(self.button_wipe)
        layout.addWidget(self.button_close)
        # Set dialog layout
        self.setLayout(layout)
        self.button_connect.clicked.connect(self.connect_manager)  # pylint: disable=no-member
        self.button_disconnect.clicked.connect(self.disconnect_manager)  # pylint: disable=no-member
        self.button_wipe.clicked.connect(self.wipe_db)  # pylint: disable=no-member
        if not self.db_manager.is_connected():
            self.button_disconnect.setEnabled(self.db_manager.is_connected())
            self.button_wipe.setEnabled(self.db_manager.is_connected())
        self.button_close.clicked.connect(self.close)  # pylint: disable=no-member

    def connect_manager(self) -> None:
        import scine_database as db

        credentials = db.Credentials(
            self.ip.text(), int(self.port.text()), self.name.text()
        )
        if credentials != self.db_manager.get_credentials():
            self.db_manager.set_credentials(credentials)
        try:
            self.db_manager.connect()
            if not self.db_manager.has_collection("calculations"):
                ans = yes_or_no_question(self, f"The database {self.name.text()} holds no collections. Create it")
                if ans:
                    self.db_manager.init()
                else:
                    self.db_manager.disconnect()
                    write_error_message("Database not connected")
            self.button_disconnect.setEnabled(self.db_manager.is_connected())
            self.button_wipe.setEnabled(self.db_manager.is_connected())
            self.close()
        except Exception as e:  # pylint: disable=broad-except
            error_dialog = QMessageBox(parent=self)
            error_dialog.setWindowTitle("Error: Database Connection")
            c = self.db_manager.get_credentials()
            if c.port > 65535:
                error_dialog.setText("Invalid Port Number")
            else:
                error_dialog.setText(str(e))
            error_dialog.exec()
        except BaseException as e:
            raise RuntimeError("Caught unknown error in SCINE DB wrapper.") from e

    def disconnect_manager(self) -> None:
        self.db_manager.disconnect()
        self.button_disconnect.setEnabled(False)
        self.button_wipe.setEnabled(False)

    def wipe_db(self) -> None:
        answer = yes_or_no_question(self,
                                    f"Are you sure you want to delete everything in the database '{self.name.text()}'")
        if not answer:
            write_info_message(f"Aborted deletion of {self.name.text()}")
            return
        self.db_manager.wipe()
        self.db_manager.init()

    def get_db_manager(self) -> Manager:
        self.exec_()
        return self.db_manager
