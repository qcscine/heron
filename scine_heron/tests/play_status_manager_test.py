#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Contains the tests for the PlayStatusManager class.
"""


import pytest
from scine_heron.molecule.play_status_manager import PlayStatusManager


class Counters:
    """
    Counts the on- and off-signals.
    """

    def __init__(self, manager: PlayStatusManager) -> None:
        """
        Connects to the provided manager to count the
        signals it emits.
        """
        self.on_signals = 0
        self.off_signals = 0

        manager.on_signal.connect(self.handle_on)
        manager.off_signal.connect(self.handle_off)

    def handle_on(self) -> None:
        """
        Increments the number of on-signals.
        """
        self.on_signals += 1

    def handle_off(self) -> None:
        """
        Increments the number of off-signals.
        """
        self.off_signals += 1


@pytest.fixture(name="manager")  # type: ignore[misc]
def create_manager() -> PlayStatusManager:
    """
    Creates a default PlayStatusManager.
    """
    return PlayStatusManager()


@pytest.fixture(name="counters")  # type: ignore[misc]
def create_counters(manager: PlayStatusManager) -> Counters:
    """
    Creates an instance of Counters connected to `manager`.
    """
    return Counters(manager)


def test_start_yields_on_status(manager: PlayStatusManager) -> None:
    """
    Asserts that starting the manager yields the status "on".
    """
    manager.start()

    assert manager.is_on()


def test_start_signals(manager: PlayStatusManager, counters: Counters) -> None:
    """
    Asserts that starting the manager signals if the status changes.
    """
    manager.start()

    assert counters.on_signals == 1


def test_by_default_is_off(manager: PlayStatusManager) -> None:
    """
    Asserts that manager has the status "off" by default.
    """
    assert not manager.is_on()


def test_stop_turns_off(manager: PlayStatusManager) -> None:
    """
    Asserts that stopping the manager yields the status "off".
    """

    manager.start()
    manager.stop()

    assert not manager.is_on()


def test_stop_signals(manager: PlayStatusManager, counters: Counters) -> None:
    """
    Asserts that stopping the manager signals if the status changes.
    """
    manager.start()
    manager.stop()

    assert counters.off_signals == 1
