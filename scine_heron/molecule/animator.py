#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the class Animator.
"""

from typing import Any, Optional, Callable, TypeVar, TYPE_CHECKING
from concurrent.futures import ProcessPoolExecutor, Executor
from PySide2.QtCore import QObject, QTimer
from .play_status_manager import PlayStatusManager
if TYPE_CHECKING:
    Signal = Any
else:
    from PySide2.QtCore import Signal


class Animator(QObject):
    """
    Animates an entity by updating it in intervals.
    """

    render_signal = Signal()

    S = TypeVar("S")
    T = TypeVar("T")

    def __init__(
        self,
        update: Callable[[S], T],
        provide_args: Callable[[], S],
        apply_results: Callable[[T, float], None],
        pool: Executor = ProcessPoolExecutor(1),
        parent: Optional[QObject] = None,
        interval: int = 1000 // 60,
    ):
        """
        Create an animator by providing an `update` function that is
        intended to be called every `interval` ms. The calls
        to `update` are submitted to `pool`.
        """
        super().__init__(parent)

        self.__update = update
        self.__provide_args = provide_args
        self.__apply_results = apply_results

        self.__pool = pool

        self.__timer = QTimer()
        self.__timer.setInterval(interval)
        self.__timer.timeout.connect(self.__tick)  # pylint: disable=no-member

        self.__status_manager = PlayStatusManager()
        self.__status_manager.on_signal.connect(self.__timer.start)
        self.__status_manager.off_signal.connect(self.__timer.stop)

    def __tick(self) -> None:
        """
        Blocks further signals from the timer and submits an update.
        """
        self.__timer.blockSignals(True)

        try:
            future = self.__pool.submit(self.__update, self.__provide_args())
            future.add_done_callback(self.__callback)
        except Exception as exception:
            self.__timer.blockSignals(False)
            raise exception

    def __callback(self, calculation_result) -> None:
        """
        Called when an update finished. Unblocks the timer signals
        and emits a `render_signal`.
        """
        try:
            self.__apply_results(
                calculation_result.result(), self.__timer.interval() / 1000,
            )
        finally:
            self.render_signal.emit()
            self.__timer.blockSignals(False)

    def stop(self) -> None:
        """
        Stops the animation.
        """
        self.__status_manager.stop()

    def start(self) -> None:
        """
        Starts the animation.
        """
        self.__status_manager.start()

    @property
    def running(self) -> bool:
        return self.__status_manager.is_on()
