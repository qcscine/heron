#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from datetime import datetime, timedelta
from os import path
from pkgutil import iter_modules
from typing import Any, Dict, Tuple, Optional, List

from PySide2.QtGui import (
    QGuiApplication,
    QClipboard,
    QBrush,
    QPen,
    QColor,
)
from PySide2.QtMultimedia import QMediaPlayer, QMediaContent
from PySide2.QtWidgets import (
    QScrollArea,
    QWidget,
    QSizePolicy
)
from PySide2.QtCore import Qt, QUrl

import scine_utilities as su

import scine_heron.config as config
from scine_heron.statusbar.status_bar import StatusBar


def copy_text_to_clipboard(text: str):
    clipboard = QGuiApplication.clipboard()
    clipboard.setText(text)
    if clipboard.supportsSelection():
        clipboard.setText(text, QClipboard.Selection)


def color_axis(axis):
    axis.xaxis.label.set_color(config.COLORS['primaryTextColor'])
    axis.yaxis.label.set_color(config.COLORS['primaryTextColor'])
    axis.tick_params(labelcolor=config.COLORS['primaryTextColor'])
    axis.set_facecolor(config.COLORS['secondaryLightColor'])
    axis.spines['bottom'].set_color(config.COLORS['primaryTextColor'])
    axis.spines['top'].set_color(config.COLORS['primaryTextColor'])
    axis.spines['right'].set_color(config.COLORS['primaryTextColor'])
    axis.spines['left'].set_color(config.COLORS['primaryTextColor'])


def get_font():
    return {"color": config.COLORS['primaryTextColor']}


def color_figure(figure):
    figure.patch.set_facecolor(config.COLORS['secondaryLightColor'])


def get_primary_line_color() -> str:
    return config.COLORS['primaryLineColor']


def get_secondary_line_color() -> str:
    return config.COLORS['secondaryLineColor']


def get_primary_light_color() -> str:
    return config.COLORS['primaryLightColor']


def get_secondary_light_color() -> str:
    return config.COLORS['secondaryLightColor']


def hex_to_qcolor(hex: str) -> QColor:
    return QColor(*(hex_to_rgb_base_255(hex)))


def hex_to_rgb_base_1(hex: str) -> Tuple[float, ...]:
    return tuple(x / 255.0 for x in hex_to_rgb_base_255(hex))


def hex_to_rgb_base_255(hex: str) -> Tuple[int, ...]:
    hex = hex.strip('#')
    assert len(hex) == 6
    return tuple(int(hex[i:i + 2], 16) for i in (0, 2, 4))


def qcolor_by_key(key: str) -> QColor:
    return hex_to_qcolor(config.COLORS[key])


def get_color_by_key(key: str) -> str:
    return config.COLORS[key]


def build_pen(
    color: QColor,
    style: Qt.PenStyle = Qt.PenStyle.SolidLine,
    join_style: Qt.PenJoinStyle = Qt.PenJoinStyle.RoundJoin,
    width: int = 1
) -> QPen:
    pen = QPen()
    pen.setStyle(style)
    pen.setJoinStyle(join_style)
    pen.setColor(color)
    pen.setWidth(width)
    return pen


def build_brush(fill: QColor, style: Qt.BrushStyle = Qt.BrushStyle.SolidPattern) -> QBrush:
    brush = QBrush()
    brush.setColor(fill)
    brush.setStyle(style)
    return brush


def datetime_to_query(time: datetime) -> Dict[str, Any]:
    return {'_lastmodified': {'$gt': {"$date": int(time.timestamp() * 1000)}}}


def _status_bar_impl() -> Optional[StatusBar]:
    from scine_heron import find_main_window
    from scine_heron.main_window import MainWindow
    main = find_main_window()
    if main is None or not isinstance(main, MainWindow):
        return None
    return main.get_status_bar()


def write_info_message(message: str, timer: Optional[int] = 10000) -> None:
    status_bar = _status_bar_impl()
    if status_bar is not None:
        status_bar.update_status(message, timer)


def write_error_message(message: str, timer: Optional[int] = 10000) -> None:
    status_bar = _status_bar_impl()
    if status_bar is not None:
        status_bar.update_error_status(message, timer)


def clear_status_bar() -> None:
    status_bar = _status_bar_impl()
    if status_bar is not None:
        status_bar.clear_message()


def vertical_scroll_area_wrap(content: QWidget) -> QScrollArea:
    scroll_area = QScrollArea()
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll_area.setWidget(content)
    scroll_area.setWidgetResizable(True)
    scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    return scroll_area


def construct_sound(sound: str) -> QMediaPlayer:
    from scine_heron import resource_path
    player = QMediaPlayer()
    player.setMedia(QMediaContent(QUrl.fromLocalFile(path.join(resource_path(), "sounds", f"{sound}.mp3"))))
    player.setVolume(100)
    return player


def docstring_dict_from_scine_settings(settings: su.Settings) -> Dict[str, str]:
    result = {}
    for key in settings.as_dict():
        result[key] = settings.descriptor_collection[key].property_description
    return result


def thread_safe_error(message: str, message_container: Optional[List[str]]):
    if message_container is None:
        write_error_message(message)
    else:
        message_container.append(message)


def module_available(module_name: str) -> bool:
    return module_name in (name for _, name, _ in iter_modules())


def timedelta_string(t: timedelta) -> str:
    """
    Custom string conversion for timedelta to get rid of microseconds from default __str__
    """
    new_t = t - timedelta(microseconds=t.microseconds)
    return str(new_t)
