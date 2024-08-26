#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
from time import sleep
from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Qt
import pytest

from scine_database.test_database_setup import get_clean_db
from scine_chemoton import gears

try:
    db_manager = get_clean_db()
except RuntimeError:
    pass


@pytest.mark.slow  # type: ignore[misc]
@pytest.mark.skipif('db_manager' not in globals(),
                    reason="requires a running database")
def test_container_init(qtbot) -> None:
    from scine_heron.chemoton.chemoton_widget import EngineWidget
    from scine_heron.chemoton.create_chemoton_widget import CreateEngineWidget
    from scine_heron.chemoton.chemoton_widget_container import ChemotonWidgetContainer

    parent = QWidget()
    chemoton_widget = ChemotonWidgetContainer(parent, db_manager, [gears.Gear], [CreateEngineWidget])

    model = chemoton_widget.get_model()
    assert model.method_family

    assert chemoton_widget.get_filters()

    assert len(chemoton_widget.created_chemoton_widgets) == 0

    creator = chemoton_widget._grid_layout.itemAtPosition(1, 1).widget()
    assert isinstance(creator, CreateEngineWidget)

    creator.chemoton_class.setCurrentText("   Scheduler")
    creator.button_add.click()

    assert len(chemoton_widget.created_chemoton_widgets) == 1
    widget = chemoton_widget.created_chemoton_widgets[0]
    assert isinstance(widget, EngineWidget)
    assert isinstance(widget.gear, gears.scheduler.Scheduler)

    assert widget.engine.get_number_of_gear_loops() == 0

    with qtbot.waitSignal(widget.single_run_finished, raising=True):
        widget.button_single.click()
    sleep(1)

    qtbot.mouseClick(widget.button_start_stop, Qt.MouseButton.LeftButton)

    sleep(1)
    assert widget.is_running()

    qtbot.mouseClick(widget.button_start_stop, Qt.MouseButton.LeftButton)
    sleep(1)
    assert not widget.is_running()

    creator.button_add.click()
    assert len(chemoton_widget.created_chemoton_widgets) == 2

    chemoton_widget._play.toggle()
    sleep(1)
    chemoton_widget._stop.toggle()
    sleep(1)
    for w in chemoton_widget.created_chemoton_widgets:
        assert isinstance(w, EngineWidget)
    chemoton_widget.close()
