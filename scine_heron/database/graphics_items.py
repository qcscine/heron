#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from typing import Any, List, Union, Optional, Tuple
import numpy as np
import datetime

from PySide2.QtWidgets import (
    QGraphicsPolygonItem,
    QGraphicsEllipseItem,
    QGraphicsTextItem
)
from PySide2.QtGui import QBrush, QPolygon, QFont, QFontMetrics, QPen
from PySide2.QtCore import QPoint
import scine_database as db
import scine_utilities as utils

from scine_heron.utilities import qcolor_by_key


class Structure(QGraphicsEllipseItem):
    def __init__(self, x, y, brush=None, pen=None) -> None:
        # The ellipse is displayed based on its top left corner.
        #  With a size of 20x20 units a shift of -10,-10 centers it.r = 20.0
        r = 20.0
        shift = 10.0

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
    def __init__(self, x, y, brush=None, pen=None,
                 concentration: Union[float, None] = None, cost: Union[float, None] = None) -> None:
        # The ellipse is displayed based on its top left corner.
        #  With a size of 20x20 units a shift of -10,-10 centers it.
        self.r = 20.0
        self.shift = 10.0
        self.concentration: Union[float, None] = concentration
        self.final_concentration: Union[float, None] = None
        self.concentration_flux: Union[float, None] = None
        self.cost: Union[float, None] = cost

        self.allow_scaling = False

        self.x_coord = x
        self.y_coord = y
        super().__init__(self.x_coord - self.shift,
                         self.y_coord - self.shift,
                         self.r, self.r)
        self.created: Union[datetime.datetime, None] = None
        self.db_representation: Any = None
        self.__brush = brush
        self.__current_brush = brush
        self.__pen = pen
        self.__current_pen = pen

        self.reset_brush()
        if pen is not None:
            self.setPen(pen)
        self._mouse_release_function = None
        self._mouse_double_click_function = None
        self._mouse_press_function = None
        self._hover_enter_function = None
        self._hover_leave_function = None
        self._menu_function = None

    def update_size(self):
        scaling = 1.0 if not self.allow_scaling else self.get_scaling()
        tmp_r = self.r * scaling
        tmp_shift = self.shift * scaling
        self.setRect(self.x_coord - tmp_shift, self.y_coord - tmp_shift, tmp_r, tmp_r)

    def get_scaling(self):
        from math import log10
        scaling = 1.0
        if self.concentration is not None:
            concentration = max(self.concentration, 1e-9)
            # Scale the size of the compound according to its concentration.
            # Minimum scaling: 10 % of the original radius.
            # Note that the scaling function is more or less made up and can be changed if required.
            scaling = 1.5 * max(1.0 / (1.0 + 0.5 * abs(log10(concentration))), 0.1)
        elif self.cost is not None:
            cost = min(self.cost, 100)
            if cost == 0.0:
                scaling = 0.6
            else:
                scaling = 5.0 + cost * -0.025
        return scaling

    def add_concentration_tooltip(self):
        cs = [self.concentration, self.final_concentration, self.concentration_flux]
        names = ["c_max", "c_final ", "c_flux "]
        self.setToolTip(f"{names[0]:6} = {cs[0]:.3E}\n"
                        f"{names[1]:8} = {cs[1]:.3E}\n"
                        f"{names[2]:8} = {cs[2]:.3E}")

    def reset_brush(self):
        if self.__brush is not None:
            self.__current_brush = self.__brush
            self.setBrush(self.__brush)
            self.__current_pen = self.__pen
            self.setPen(self.__pen)

    def set_current_brush(self, brush: QBrush):
        self.__current_brush = brush
        self.setBrush(brush)

    def get_current_brush(self):
        return self.__current_brush

    def get_brush(self) -> Union[None, QBrush]:
        return self.__brush

    def get_pen(self) -> Union[None, QPen]:
        return self.__pen

    def set_current_pen(self, pen: QPen):
        self.__current_pen = pen
        self.setPen(pen)

    def get_current_pen(self):
        return self.__current_pen

    def center(self):
        return QPoint(self.x_coord, self.y_coord)

    def set_created(self, created: datetime.datetime):
        self.created = created

    def get_created(self) -> Union[None, datetime.datetime]:
        return self.created

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
    def __init__(self, x, y,
                 flux=None, brush=None, pen=None,
                 invert_direction=False) -> None:

        self.x_coord = x
        self.y_coord = y
        self.ang = 0.0
        # Rot as side indicator
        self.db_representation: Any = None
        self.created: Union[datetime.datetime, None] = None
        self.assigned_es_id: db.ID
        self.spline: Optional[utils.bsplines.TrajectorySpline] = None
        self.barriers: Optional[Tuple[float, float]] = None  # lhs->ts, rhs->ts, in kJ/mol, direction as stored in db
        self.barrierless_type = False
        self.lhs_ids: List[str] = []
        self.rhs_ids: List[str] = []
        self.lhs_types: List[db.CompoundOrFlask] = []
        self.rhs_types: List[db.CompoundOrFlask] = []
        self.energy_difference: Union[None, float] = None
        # Keep track of the relative direction of the step and the reaction.
        self.invert_direction = invert_direction

        self.flux = flux
        self.allow_scaling = False
        poly = self.get_rotated_polygon()
        super().__init__(poly)
        self.__brush = brush
        self.__current_brush = brush
        self.__pen = pen
        self.__current_pen = pen
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
        if self.invert_direction:
            return - self.energy_difference  # pylint: disable=invalid-unary-operand-type
        return self.energy_difference

    def reset_brush(self):
        if self.__brush is not None:
            self.__current_brush = self.__brush
            self.setBrush(self.__brush)
            self.__current_pen = self.__pen
            self.setPen(self.__pen)

    def set_current_brush(self, brush: QBrush):
        self.__current_brush = brush
        self.setBrush(brush)

    def get_current_brush(self):
        return self.__current_brush

    def get_brush(self) -> Union[None, QBrush]:
        return self.__brush

    def get_pen(self) -> Union[None, QPen]:
        return self.__pen

    def set_current_pen(self, pen: QPen):
        self.__current_pen = pen
        self.setPen(pen)

    def get_current_pen(self):
        return self.__current_pen

    def set_barriers(self, barriers: Union[Tuple[float, float], Tuple[None, None]]):
        if None in barriers:
            tmp_barriers = (0.0, 0.0)
        else:
            assert barriers[0] is not None and barriers[1] is not None
            tmp_barriers = barriers
        self.barriers = tmp_barriers

    def get_barriers(self):
        return self.barriers

    def set_created(self, created: datetime.datetime):
        self.created = created

    def get_created(self) -> Union[None, datetime.datetime]:
        return self.created

    def get_flux(self) -> Union[None, float]:
        return self.flux

    def __rot(self, x, y) -> QPoint:
        # Rotation relative to vector relative to (1, 0) - original position
        scaling = self.get_scaling() if self.allow_scaling else 1.0
        x = x * scaling
        y = y * scaling
        org_ang = np.arctan2(y, x)
        norm_xy = np.sqrt(x * x + y * y)
        dx = norm_xy * np.cos(self.ang + org_ang)
        dy = norm_xy * np.sin(self.ang + org_ang)
        # dy *= -1.0 if self.y_coord < 0 else 1.0
        return QPoint(int(self.x_coord + dx), int(self.y_coord - dy))

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

    def outgoing(self) -> QPoint:
        return self.__rot(+15, +0)

    def incoming(self) -> QPoint:
        return self.__rot(-15, +0)

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
    def __init__(self, x, y, path: List[Any], path_rank: int, path_length: float, text="") -> None:
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

        self.path = path
        self.path_rank = path_rank
        self.path_length = path_length
        self.setToolTip("Double click for energy diagram")
        # Function attributes
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
