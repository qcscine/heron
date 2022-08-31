#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
import os
import signal
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional

from PySide2.QtWidgets import QApplication, QMainWindow, QWidget
from qt_material import apply_stylesheet, get_theme
import scine_utilities as su

import scine_heron.config as config
from scine_heron.molecule.molecule_video import MainVideo
from scine_heron.resources import resource_path

from ._version import __version__  # noqa: F401


def find_main_window() -> Optional[QMainWindow]:
    # Global function to find the (open) QMainWindow in application
    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            return widget
    return None


def get_core_tab(tab_identifier: str) -> Optional[QWidget]:
    main = find_main_window()
    if main is None:
        return None
    return main.get_tab(tab_identifier)


def view_trajectory_cli() -> None:
    parser = ArgumentParser(description='Enter filepath of trajectory')
    parser.add_argument(
        "file", help="load trajectory from file", type=Path, default=None,
    )
    parser.add_argument(
        "-m", "--mode", help="choose dark or light mode", type=str, default="dark"
    )
    args = parser.parse_args()
    theme_path = Path(os.path.join(resource_path(), f'theme_{args.mode}.xml'))
    view_trajectory_from_file(args.file, theme_path)


def view_trajectory_from_file(trajectory_path: Path, theme_path: Optional[Path] = None) -> None:
    p = trajectory_path
    ending = p.suffix
    if ending == ".bin":
        traj = su.io.read_trajectory(su.io.TrajectoryFormat.Binary, str(p.expanduser()))
    elif ending == ".xyz":
        traj = su.io.read_trajectory(su.io.TrajectoryFormat.Xyz, str(p.expanduser()))
    else:
        raise RuntimeError(f"Unsupported file type for trajectory {ending}")
    view_trajectory(traj, theme_path)


def view_trajectory(trajectory: su.MolecularTrajectory, theme_path: Optional[Path] = None) -> None:
    if theme_path is None:
        theme_path = Path(os.path.join(resource_path(), 'theme_dark.xml'))
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    application = QApplication()
    if os.path.exists(str(theme_path)):
        apply_stylesheet(
            application,
            theme=theme_path,
            invert_secondary=True,
        )
        config.COLORS = get_theme(theme_path)
    window = MainVideo(trajectory)
    window.show()
    application.exec_()
