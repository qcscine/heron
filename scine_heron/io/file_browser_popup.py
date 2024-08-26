#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from pathlib import Path
from os import path
from typing import Callable, Optional, List
from PySide2.QtWidgets import QFileDialog, QWidget

from scine_heron.utilities import write_error_message, write_info_message


def _valid_extension(file_name: Path, allowed_extensions: List[str]) -> bool:
    checked_extensions = [f'.{e}' if not e.startswith('.') else e for e in allowed_extensions]
    if file_name.suffix not in checked_extensions:
        write_error_message(f"Unsupported file extension '{file_name.suffix}', allowed are {checked_extensions}")
        return False
    return True


def get_load_file_name(parent: QWidget, default_name: str, valid_extensions: List[str],
                       validator: Optional[Callable[[Path], bool]] = None) -> Optional[Path]:
    """
    Ask the user to provide the name of the file to be loaded with a QFileDialog.

    Parameters
    ----------
    parent : QWidget
        The parent widget for the QFileDialog
    default_name : str
        The default name of the file
    valid_extensions : List[str]
        Valid file extensions without leading '.'
    validator : Optional[Callable[[Path], bool]]
        An optional callable that carries out additional sanity checks on the file name
        and returns if it is valid (true) or not, by default None

    Notes
    -----
    * Not thread safe
    * A return value of None means that something was wrong, error or info has been written to the statusbar

    Returns
    -------
    Path
        The file name as a Path object
    """
    if not valid_extensions:
        valid_extensions = ["*"]
    filename, _ = QFileDialog.getOpenFileName(
        parent,
        parent.tr("Open File"),  # type: ignore[arg-type]
        default_name + "." + valid_extensions[0],
        parent.tr(f"{default_name} ({' *.'.join(['', *valid_extensions])[1:]})"),  # type: ignore[arg-type]
        # explanation last line: valid_extension = ["pkl", "json"] --> string after default_name = (*.pkl *json)
    )
    if not filename:
        write_info_message("Aborted loading")
        return None
    filename = Path(filename)
    if not path.exists(filename):
        write_error_message(f"File {filename} does not exist!")
        return None
    if not _valid_extension(filename, valid_extensions):
        return None
    if validator is not None and not validator(filename):
        return None
    return filename


def get_save_file_name(parent: QWidget, default_name: str, valid_extensions: List[str],
                       validator: Optional[Callable[[Path], bool]] = None) -> Optional[Path]:
    """
    Ask the user to provide the name of a file that should be written based on a QFileDialog.

    Parameters
    ----------
    parent : QWidget
        The parent widget for the QFileDialog
    default_name : str
        The default name of the file
    valid_extensions : List[str]
        Valid file extensions without leading '.'
    validator : Optional[Callable[[Path], bool]]
        An optional callable that carries out additional sanity checks on the file name
        and returns if it is valid (true) or not, by default None

    Notes
    -----
    * Not thread safe
    * A return value of None means that something was wrong, error or info has been written to the statusbar

    Returns
    -------
    Path
        The file name as a Path object
    """
    if not valid_extensions:
        valid_extensions = ["*"]
    filename, _ = QFileDialog.getSaveFileName(
        parent,
        parent.tr("Save File"),  # type: ignore[arg-type]
        default_name + "." + valid_extensions[0],
        parent.tr(f"{default_name} ({' *.'.join(['', *valid_extensions])[1:]})"),  # type: ignore[arg-type]
    )
    if not filename:
        write_info_message("Aborted saving")
        return None
    filename = Path(filename)
    if not _valid_extension(filename, valid_extensions):
        return None
    if validator is not None and not validator(filename):
        return None
    return filename
