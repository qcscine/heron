#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from typing import Any, List, Union, Optional
import numpy as np

from PySide2.QtWidgets import (
    QGraphicsPolygonItem,
    QGraphicsEllipseItem,
    QGraphicsTextItem
)
from PySide2.QtGui import QBrush, QPolygon, QFont, QFontMetrics
from PySide2.QtCore import QPoint
import scine_database as db
import scine_utilities as utils

from scine_heron.utilities import qcolor_by_key


class Structure(QGraphicsEllipseItem):
    def __init__(self, x, y, brush=None, pen=None) -> None:
        # The ellipse is displayed based on its top left corner.
        #  With a size of 20x20 units a shift of -10,-10 centers it.
        super().__init__(x - 10, y - 10, 20, 20)
        self.x_coord = x
        self.y_coord = y
        self.db_representation: Any = None
        self.__brush = brush
        self.reset_brush()
        if pen is not None:
            self.setPen(pen)
        self._mouse_release_function = None
        self._mouse_double_click_function = None
        self._mouse_press_function = None
        self._hover_enter_function = None
        self._hover_leave_function = None
        self._menu_function = None

    def reset_brush(self):
        if self.__brush is not None:
            self.setBrush(self.__brush)

    def set_brush(self, brush: QBrush):
        self.__brush = brush
        self.setBrush(brush)

    def center(self):
        return QPoint(self.x_coord, self.y_coord)

    def bind_mouse_release_function(self, func):
        self._mouse_release_function = func

    def bind_mouse_press_function(self, func):
        self._mouse_press_function = func

    def bind_mouse_double_click_function(self, func):
        self._mouse_double_click_function = func

    def bind_hover_enter_function(self, func):
        self._hover_enter_function = func

    def bind_hover_leave_function(self, func):
        self._hover_leave_function = func

    def bind_menu_function(self, func):
        self._menu_function = func

    def mouseDoubleClickEvent(self, event):
        if self._mouse_double_click_function is not None:
            self._mouse_double_click_function(event, self)

    def mousePressEvent(self, event):
        if self._mouse_press_function is not None:
            self._mouse_press_function(event, self)

    def mouseReleaseEvent(self, event):
        if self._mouse_release_function is not None:
            self._mouse_release_function(event, self)

    def hoverEnterEvent(self, event):
        if self._hover_enter_function is not None:
            self._hover_enter_function(event, self)

    def hoverLeaveEvent(self, event):
        if self._hover_leave_function is not None:
            self._hover_leave_function(event, self)

    def contextMenuEvent(self, event):
        if self._menu_function is not None:
            self._menu_function(event, self)


class Compound(QGraphicsEllipseItem):
    def __init__(self, x, y, brush=None, pen=None, concentration: Union[float, None] = None) -> None:
        # The ellipse is displayed based on its top left corner.
        #  With a size of 20x20 units a shift of -10,-10 centers it.
        r = 20.0
        shift = 10.0
        self.concentration: Union[float, None] = concentration
        scaling = self.get_scaling()
        r *= scaling
        shift *= scaling

        super().__init__(x - shift, y - shift, r, r)
        self.x_coord = x
        self.y_coord = y
        self.db_representation: Any = None
        self.__brush = brush
        self.reset_brush()
        if pen is not None:
            self.setPen(pen)
        self._mouse_release_function = None
        self._mouse_double_click_function = None
        self._mouse_press_function = None
        self._hover_enter_function = None
        self._hover_leave_function = None
        self._menu_function = None

    def get_scaling(self):
        from math import log10
        scaling = 1.0
        if self.concentration is not None:
            concentration = max(self.concentration, 1e-9)
            # Scale the size of the compound according to its concentration.
            # Minimum scaling: 10 % of the original radius.
            # Note that the scaling function is more or less made up and can be changed if required.
            scaling = 1.5 * max(1.0 / (1.0 + 0.5 * abs(log10(concentration))), 0.1)
        return scaling

    def reset_brush(self):
        if self.__brush is not None:
            self.setBrush(self.__brush)

    def set_brush(self, brush: QBrush):
        self.__brush = brush
        self.setBrush(brush)

    def center(self):
        return QPoint(self.x_coord, self.y_coord)

    def bind_mouse_release_function(self, func):
        self._mouse_release_function = func

    def bind_mouse_press_function(self, func):
        self._mouse_press_function = func

    def bind_mouse_double_click_function(self, func):
        self._mouse_double_click_function = func

    def bind_hover_enter_function(self, func):
        self._hover_enter_function = func

    def bind_hover_leave_function(self, func):
        self._hover_leave_function = func

    def bind_menu_function(self, func):
        self._menu_function = func

    def mouseDoubleClickEvent(self, event):
        if self._mouse_double_click_function is not None:
            self._mouse_double_click_function(event, self)

    def mousePressEvent(self, event):
        if self._mouse_press_function is not None:
            self._mouse_press_function(event, self)

    def mouseReleaseEvent(self, event):
        if self._mouse_release_function is not None:
            self._mouse_release_function(event, self)

    def hoverEnterEvent(self, event):
        if self._hover_enter_function is not None:
            self._hover_enter_function(event, self)

    def hoverLeaveEvent(self, event):
        if self._hover_leave_function is not None:
            self._hover_leave_function(event, self)

    def contextMenuEvent(self, event):
        if self._menu_function is not None:
            self._menu_function(event, self)


class Reaction(QGraphicsPolygonItem):
    def __init__(self, x, y, flux=None, brush=None, pen=None, ang: float = 0, rot=0) -> None:

        self.x_coord = x
        self.y_coord = y
        self.ang = ang
        self.rot = rot
        self.db_representation: Any = None
        self.structure: Optional[utils.AtomCollection] = None
        self.spline: Optional[utils.bsplines.TrajectorySpline] = None
        self.lhs_ids: List[str] = []
        self.rhs_ids: List[str] = []
        self.lhs_types: List[db.CompoundOrFlask] = []
        self.rhs_types: List[db.CompoundOrFlask] = []
        self.energy_difference: Union[None, float] = None
        # Keep track of the relative direction of the step and the reaction.
        self.invert_sign_of_difference: bool = False
        self.flux = flux
        poly = self.get_rotated_polygon()
        super().__init__(poly)
        self.__brush = brush
        self.reset_brush()
        if pen is not None:
            self.setPen(pen)
        self._mouse_release_function = None
        self._mouse_double_click_function = None
        self._mouse_press_function = None
        self._hover_enter_function = None
        self._hover_leave_function = None
        self._menu_function = None

    def get_scaling(self) -> float:
        from math import log10
        scaling = 1.0
        if self.flux is not None:
            flux = max(self.flux, 1e-9)
            scaling = max(1.0 / (1.0 + 0.5 * abs(log10(min(flux, 1.0)))), 0.1)
        return scaling

    def get_energy_difference(self) -> Union[None, float]:
        if not self.energy_difference:
            return None
        if self.invert_sign_of_difference:
            return - self.energy_difference  # pylint: disable=invalid-unary-operand-type
        return self.energy_difference

    def reset_brush(self):
        if self.__brush is not None:
            self.setBrush(self.__brush)

    def set_brush(self, brush: QBrush):
        self.__brush = brush
        self.setBrush(brush)

    def __rot(self, x, y) -> QPoint:
        scaling = self.get_scaling()
        x = x * scaling
        y = y * scaling
        old = np.arctan2(x, y) + np.pi / 2.0
        radius = np.sqrt(x * x + y * y)
        dx = radius * np.cos(self.ang + old)
        dy = radius * np.sin(self.ang + old)
        return QPoint(int(self.x_coord + dx), int(self.y_coord + dy))

    def get_rotated_polygon(self) -> QPolygon:
        poly = QPolygon(
            [
                self.__rot(-15, +0),
                self.__rot(-5, +10),
                self.__rot(-5, +5),
                self.__rot(+5, +5),
                self.__rot(+5, +10),
                self.__rot(+15, +0),
                self.__rot(+5, -10),
                self.__rot(+5, -5),
                self.__rot(-5, -5),
                self.__rot(-5, -10),
                self.__rot(-15, +0),
            ]
        )
        return poly

    def rhs(self) -> QPoint:
        if self.rot == 1:
            return self.__rot(15, +0)
        else:
            return self.__rot(-15, +0)

    def lhs(self) -> QPoint:
        if self.rot == 1:
            return self.__rot(-15, +0)
        else:
            return self.__rot(15, +0)

    def update_angle(self, angle) -> None:
        self.ang = angle
        poly = self.get_rotated_polygon()
        self.setPolygon(poly)

    def bind_mouse_release_function(self, func) -> None:
        self._mouse_release_function = func

    def bind_mouse_press_function(self, func) -> None:
        self._mouse_press_function = func

    def bind_mouse_double_click_function(self, func) -> None:
        self._mouse_double_click_function = func

    def bind_hover_enter_function(self, func) -> None:
        self._hover_enter_function = func

    def bind_hover_leave_function(self, func) -> None:
        self._hover_leave_function = func

    def mouseDoubleClickEvent(self, event) -> None:
        if self._mouse_double_click_function is not None:
            self._mouse_double_click_function(event, self)

    def bind_menu_function(self, func):
        self._menu_function = func

    def mousePressEvent(self, event) -> None:
        if self._mouse_press_function is not None:
            self._mouse_press_function(event, self)

    def mouseReleaseEvent(self, event) -> None:
        if self._mouse_release_function is not None:
            self._mouse_release_function(event, self)

    def hoverEnterEvent(self, event) -> None:
        if self._hover_enter_function is not None:
            self._hover_enter_function(event, self)

    def hoverLeaveEvent(self, event) -> None:
        if self._hover_leave_function is not None:
            self._hover_leave_function(event, self)

    def contextMenuEvent(self, event):
        if self._menu_function is not None:
            self._menu_function(event, self)


class Pathinfo(QGraphicsTextItem):
    def __init__(self, x, y, text="") -> None:
        super().__init__(text)
        self.x_coord = x
        self.y_coord = y
        self.center()
        self.text = text
        self.font_size = 30
        self.font_family = 'Arial'
        self.setFont(QFont(self.font_family, self.font_size))
        self.setDefaultTextColor(qcolor_by_key("primaryTextColor"))
        font_metrics = QFontMetrics(QFont(self.font_family, self.font_size))
        # Y position such that two line text is centered at line break
        self.setPos(x, y - 1 * self.font_size - int(0.5 * font_metrics.lineSpacing()))
        # Funciton attributes
        self._mouse_release_function = None
        self._mouse_double_click_function = None
        self._mouse_press_function = None
        self._hover_enter_function = None
        self._hover_leave_function = None
        self._menu_function = None

    def center(self):
        return QPoint(self.x_coord, self.y_coord)

    def bind_mouse_release_function(self, func) -> None:
        self._mouse_release_function = func

    def bind_mouse_press_function(self, func) -> None:
        self._mouse_press_function = func

    def bind_mouse_double_click_function(self, func) -> None:
        self._mouse_double_click_function = func

    def bind_hover_enter_function(self, func) -> None:
        self._hover_enter_function = func

    def bind_hover_leave_function(self, func) -> None:
        self._hover_leave_function = func

    def mouseDoubleClickEvent(self, event) -> None:
        if self._mouse_double_click_function is not None:
            self._mouse_double_click_function(event, self)

    def bind_menu_function(self, func):
        self._menu_function = func

    def mousePressEvent(self, event) -> None:
        if self._mouse_press_function is not None:
            self._mouse_press_function(event, self)

    def mouseReleaseEvent(self, event) -> None:
        if self._mouse_release_function is not None:
            self._mouse_release_function(event, self)

    def hoverEnterEvent(self, event) -> None:
        if self._hover_enter_function is not None:
            self._hover_enter_function(event, self)

    def hoverLeaveEvent(self, event) -> None:
        if self._hover_leave_function is not None:
            self._hover_leave_function(event, self)

    def contextMenuEvent(self, event):
        if self._menu_function is not None:
            self._menu_function(event, self)
