#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Tests for the Animator class.
"""

import typing
import pytest
from PySide2.QtCore import QTimer, QEventLoop
from PySide2.QtWidgets import QApplication
from scine_heron.molecule.animator import Animator
if typing.TYPE_CHECKING:
    Signal = typing.Any
else:
    from PySide2.QtCore import Signal


class Counter:
    """
    Counts the calls to update.
    """

    def __init__(self) -> None:
        self.value = 0

    def update(self, value: int) -> None:
        """
        Increments the `updated` member.
        """
        self.value = value


@pytest.fixture(name="counter")  # type: ignore[misc]
def create_counter() -> Counter:
    """
    Creates a Counter instance.
    """
    return Counter()


def provide_data(counter: Counter) -> int:
    return counter.value


def apply_results(counter: Counter, result: int, _time_interval: float) -> None:
    counter.update(result)


def increment(value: int) -> int:
    return value + 1


@pytest.fixture(name="animator")  # type: ignore[misc]
def create_animator(counter: Counter) -> Animator:
    """
    Creates an animator instances that calls
    `counter.update` to update.
    """
    animator = Animator(
        increment,
        lambda: provide_data(counter),
        lambda results, time_interval: apply_results(counter, results, time_interval),
    )
    return animator


def wait_until_signal(
    signal: Signal, upper_limit_ms: typing.Optional[int] = None
) -> None:
    """
    Waits until the provided `signal` is triggered, or a provided
    upper limit is reached.
    """
    loop = QEventLoop()
    signal.connect(loop.quit)

    if upper_limit_ms is not None:
        timer = QTimer()
        timer.setInterval(upper_limit_ms)
        timer.timeout.connect(loop.quit)  # pylint: disable=no-member
        timer.start()

    loop.exec_()


def test_does_nothing_by_default(
    _app: QApplication, counter: Counter, animator: Animator
) -> None:
    """
    The animator does not update by default.
    """
    wait_until_signal(animator.render_signal, 100)

    assert counter.value == 0


def test_start_triggers_update_and_render(
    _app: QApplication, counter: Counter, animator: Animator
) -> None:
    """
    The animator updates once start is called.
    """
    animator.start()

    wait_until_signal(animator.render_signal)

    assert counter.value == 1


def test_start_triggers_update_and_render_twice(
    _app: QApplication, counter: Counter, animator: Animator
) -> None:
    """
    The animator updates twice after start is called.
    """
    animator.start()

    wait_until_signal(animator.render_signal)
    wait_until_signal(animator.render_signal)

    assert counter.value == 2


def test_no_longer_updates_after_stop(
    _app: QApplication, counter: Counter, animator: Animator
) -> None:
    """
    The animator stops updating when stop is called.
    """
    animator.start()

    wait_until_signal(animator.render_signal)
    animator.stop()
    wait_until_signal(animator.render_signal, 100)

    assert counter.value == 1
