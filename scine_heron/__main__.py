#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""

import os.path
import sys
import argparse
import pathlib
import signal
import typing

from PySide2.QtWidgets import QApplication
from PySide2.QtGui import QIcon
from qt_material import apply_stylesheet, get_theme

from .main_window import MainWindow
from scine_heron.resources import resource_path
import scine_heron.config as config


def parse_command_line_arguments() -> argparse.Namespace:
    """
    Parses the "--file" command line argument and returns it.
    """
    parser = argparse.ArgumentParser(description="SCINE User Interface")
    parser.add_argument(
        "-f", "--file", help="load molecule from FILE", type=pathlib.Path, default=None,
    )
    parser.add_argument(
        "-p", "--port", help="SCINE database port", type=int, default=27017,
    )
    parser.add_argument(
        "-n",
        "--name",
        help="SCINE database name",
        type=str,
        default="default",
    )
    parser.add_argument(
        "-i",
        "--ip",
        help="SCINE database IP or hostname",
        type=str,
        default="localhost",
    )
    parser.add_argument(
        "-m", "--mode", help="choose dark or light mode", type=str, default="dark"
    )
    return parser.parse_args()


def main() -> None:
    """
    Starts the molecule viewer application.
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    application = QApplication(sys.argv)
    application.setWindowIcon(QIcon(os.path.join(resource_path(), 'heron_logo.png')))

    arguments = parse_command_line_arguments()
    theme_path = os.path.join(resource_path(), f'theme_{arguments.mode}.xml')
    if os.path.exists(theme_path):
        apply_stylesheet(
            application,
            theme=theme_path,
            invert_secondary=True,
        )
        config.COLORS = get_theme(theme_path)
    else:
        raise RuntimeError(f'Failed to load theme at `{theme_path}`')
    filename = typing.cast(typing.Optional[pathlib.Path], arguments.file)

    window = MainWindow(file_name=filename)
    window.set_database_credentials(arguments.name, arguments.ip, arguments.port)
    window.show()  # type: ignore[no-untyped-call]
    application.exec_()


if __name__ == "__main__":
    main()
