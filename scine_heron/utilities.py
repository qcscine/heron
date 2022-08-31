#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""

from PySide2.QtGui import (
    QGuiApplication,
    QClipboard,
    QBrush,
    QPen,
    QColor,
)
from PySide2.QtCore import Qt
from datetime import datetime
import scine_heron.config as config
from typing import Any, Dict, Tuple


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


def get_primary_line_color():
    return config.COLORS['primaryLineColor']


def get_secondary_line_color():
    return config.COLORS['secondaryLineColor']


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
    mongo_time = str(time).split(" ")[0] + "T{:02d}:{:02d}Z".format(time.hour, time.minute)
    return {'_lastmodified': {'$gt': {"$date": mongo_time}}}
