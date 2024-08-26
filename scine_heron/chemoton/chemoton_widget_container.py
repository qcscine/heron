#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from functools import partial
from threading import Thread
from time import sleep
from typing import Any, List, Optional, Callable, Tuple
import pickle

from PySide2.QtWidgets import (
    QWidget,
    QScrollArea,
    QGridLayout,
    QVBoxLayout,
    QStyle,
)
from PySide2.QtCore import Qt, QObject, QThread
from PySide2.QtGui import QCloseEvent

from scine_database import Manager, Model
from scine_utilities import ValueCollection

from scine_chemoton.filters.aggregate_filters import \
    AggregateFilter
from scine_chemoton.filters.reactive_site_filters import \
    ReactiveSiteFilter
from scine_chemoton.filters.further_exploration_filters import \
    FurtherExplorationFilter
from scine_chemoton.filters.elementary_step_filters import ElementaryStepFilter
from scine_chemoton.filters.reaction_filters import ReactionFilter
from scine_chemoton.gears.network_refinement.enabling import (
    AggregateEnabling, ReactionEnabling, EnableCalculationResults
)
from scine_chemoton.gears.network_refinement.disabling import ReactionDisabling, StepDisabling
from scine_chemoton.filters.structure_filters import StructureFilter
from scine_chemoton.utilities.datastructure_transfer import make_picklable

from scine_heron.containers.tab_widget import TabWidget
from scine_heron.containers.start_stop_widget import StartStopWidget
from scine_heron.chemoton.class_searcher import ChemotonClassSearcher
from scine_heron.settings.class_options_widget import ModelOptionsWidget, GeneralSettingsWidget
from scine_heron.settings.docstring_parser import DocStringParser
from scine_heron.chemoton.filter_builder import FilterBuilder
from scine_heron.io.file_browser_popup import get_load_file_name, get_save_file_name
from scine_heron.toolbar.io_toolbar import HeronToolBar
from scine_heron.utilities import write_error_message, write_info_message, clear_status_bar
import scine_heron.io.json_pickle_wrap as json_wrap


class ChemotonWidgetContainer(QWidget):
    """
    Container Widget for StartStopWidgets in a grid view.
    This represents the whole Chemoton tab.
    """

    def __init__(self, parent: Optional[QObject], db_manager: Manager, wanted_classes: List[Any],
                 widget_creators: List[Callable], cls_black_list: Optional[List[type]] = None) -> None:
        """
        Construct the container.
        This specifies the database we are working on and the classes we can work with.

        Parameters
        ----------
        parent : Optional[QObject]
            The parent widget
        db_manager : Manager
            The Scine Database Manager
        wanted_classes : List[Any]
            The classes we want to work with, subclasses are automatically included
        widget_creators : List[Callable]
            The functions that can create widgets for the classes
        cls_black_list : Optional[List[type]], optional
            Specify classes that we don't want to be shown / selected, by default None

        Raises
        ------
        RuntimeError
            If the number of classes and the number of creators don't match
        """
        QWidget.__init__(self, parent)
        self.db_manager = db_manager
        self.class_searchers = [ChemotonClassSearcher(cls, black_list=cls_black_list) for cls in wanted_classes]
        self.doc_string_parser = DocStringParser()
        self._joiner: Optional[EngineJoiner] = None
        self._delete_join_threads: List[Thread] = []

        if len(wanted_classes) != len(widget_creators):
            raise RuntimeError("InternalError, invalid input")

        # take care of model and filters
        self._model_builder = ModelOptionsWidget()
        self._filter_builder = FilterBuilder()
        self._settings_builder = GeneralSettingsWidget()
        self._init_argument_builder_tabs = TabWidget(parent=self)
        self._init_argument_builder_tabs.addTab(self._model_builder, "Model")
        self._init_argument_builder_tabs.addTab(self._filter_builder, "Filter")
        self._init_argument_builder_tabs.addTab(self._settings_builder, "General Settings")
        self._init_argument_builder_tabs.setMaximumWidth(500)

        # generate the widgets to build widgets
        self.__add_chemoton_widgets = [creator(self, self.db_manager, searcher)
                                       for searcher, creator in zip(self.class_searchers, widget_creators)]

        # create widget for scroll area
        scroll_area_content = QWidget()
        self._scroll_area_content_layout = QVBoxLayout()
        # add toolbar
        self._toolbar = HeronToolBar()
        # play button
        self._play = self._toolbar.shortened_add_action(QStyle.SP_MediaPlay, "Start exploration",
                                                        "Ctrl+M", lambda: self._start_stop_all(True))
        self._stop = self._toolbar.shortened_add_action(QStyle.SP_MediaPause, "Stop exploration",
                                                        "Ctrl+R", lambda: self._start_stop_all(False))
        self._toolbar.shortened_add_action(
            QStyle.SP_DialogOpenButton, "Load Exploration Setup", "Ctrl+O", self._load_file
        )
        self._toolbar.shortened_add_action(
            QStyle.SP_DialogSaveButton, "Save Exploration Setup", "Ctrl+S", self._save_file
        )
        self._toggle_sound_action = self._toolbar.shortened_add_action(QStyle.SP_MediaVolumeMuted,
                                                                       "Mute/Unmute sounds",
                                                                       "Ctrl+P",
                                                                       self._toggle_sound)
        self.sound_allowed = False
        self._play.setCheckable(True)
        self._stop.setCheckable(True)
        self.is_blocked = False
        self._scroll_area_content_layout.addWidget(self._toolbar)
        # add holder of all the created widgets
        self.created_chemoton_widgets: List[StartStopWidget] = []
        self._created_chemoton_widgets_holder = QWidget()
        self.__created_chemoton_widgets_layout = QGridLayout()
        self._created_chemoton_widgets_holder.setLayout(self.__created_chemoton_widgets_layout)
        # finish scroll area content
        self._scroll_area_content_layout.addWidget(self._created_chemoton_widgets_holder)
        scroll_area_content.setLayout(self._scroll_area_content_layout)

        # create scroll area
        self._scroll_area = QScrollArea()
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setWidget(scroll_area_content)
        self._scroll_area.setWidgetResizable(True)

        # fill total grid layout of the tab
        self._grid_layout = QGridLayout()
        self._grid_layout.addWidget(self._init_argument_builder_tabs, 0, 0)
        self._grid_layout.addWidget(self._scroll_area, 0, 1)
        for i, widget in enumerate(self.__add_chemoton_widgets, 1):
            self._grid_layout.addWidget(widget, 1, i)

        self._max_widgets_per_row = 3
        self.setLayout(self._grid_layout)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Clean up before we are closed
        """
        if self._joiner is not None:
            self._joiner.wait()
        for thread in self._delete_join_threads:
            thread.join()
        for widget in self.created_chemoton_widgets:
            widget.start_stop(stop_all=True)
        for widget in self.created_chemoton_widgets:
            widget.join(force_join=True)
        super().closeEvent(event)

    def _toggle_sound(self) -> None:
        self.sound_allowed = not self.sound_allowed
        self._toggle_sound_action.setIcon(
            self.style().standardIcon(QStyle.SP_MediaVolume)
            if self.sound_allowed
            else self.style().standardIcon(QStyle.SP_MediaVolumeMuted)
        )

    def _pre_io_operations(self) -> None:
        """
        Possible operations that we may want to do before we do disc I/O operations.
        Nothing currently implemented, but child classes can override this.
        """

    def _post_io_operations(self) -> None:
        """
        Possible operations that we may want to do after we do disc I/O operations.
        Nothing currently implemented, but child classes can override this.
        """

    def add_widget(self, chemoton_widget: StartStopWidget, predefined_position: bool = False) -> None:
        """
        Adds a new widget to the grid layout.

        Parameters
        ----------
        chemoton_widget : StartStopWidget
            The new widget
        predefined_position : bool, optional
            If the widget should be simply added or placed at a special position, by default False
            This addition is currently not implemented, but has to be done by child class.
            In this case, only the doc strings are set and the delete button is connected.
        """
        # connect functionalities
        chemoton_widget.set_docstring_dict(self.doc_string_parser)
        if chemoton_widget.button_delete is not None:
            chemoton_widget.button_delete.clicked.connect(  # pylint: disable=no-member
                partial(self.delete_widget, chemoton_widget)
            )
        if predefined_position:
            return
        # add widget
        count = len(self.created_chemoton_widgets)
        row = count // self._max_widgets_per_row
        column = count % self._max_widgets_per_row

        self.created_chemoton_widgets.append(chemoton_widget)
        self.__created_chemoton_widgets_layout.addWidget(chemoton_widget, row, column)

    def delete_widget(self, chemoton_widget: StartStopWidget) -> int:
        """
        Deletes a widget from the grid layout.

        Parameters
        ----------
        chemoton_widget : StartStopWidget
            The widget to be deleted

        Returns
        -------
        int
            The index of the deleted widget
        """
        idx = self.created_chemoton_widgets.index(chemoton_widget)
        self.created_chemoton_widgets.pop(idx)
        chemoton_widget.stop_class_if_working()
        self._delete_join_threads.append(Thread(target=chemoton_widget.join, kwargs={'force_join': True}))
        self._delete_join_threads[-1].start()

        chemoton_widget.setAttribute(Qt.WA_DeleteOnClose)
        chemoton_widget.close()
        chemoton_widget.setParent(None)  # type: ignore
        for widget in self.created_chemoton_widgets:
            self.__created_chemoton_widgets_layout.removeWidget(widget)

        # add remaining widgets
        n_widgets = len(self.created_chemoton_widgets)
        for i in range(n_widgets):
            row = i // self._max_widgets_per_row
            column = i % self._max_widgets_per_row
            self.__created_chemoton_widgets_layout.addWidget(self.created_chemoton_widgets[i], row, column)

        return idx

    def get_filters(self) -> Tuple[AggregateFilter, ReactiveSiteFilter, FurtherExplorationFilter, StructureFilter,
                                   ElementaryStepFilter, ReactionFilter, AggregateEnabling, AggregateFilter,
                                   ReactionEnabling, ReactionFilter, EnableCalculationResults, ReactionDisabling,
                                   StepDisabling]:
        """
        Returns the filters that are currently set.

        Returns
        -------
        Tuple[AggregateFilter, ReactiveSiteFilter, FurtherExplorationFilter, StructureFilter, ElementaryStepFilter,
                ReactionFilter, AggregateEnabling, AggregateFilter, ReactionEnabling, ReactionFilter,
                ReactionDisabling, StepDisabling]
            The filters as a tuple
        """
        return self._filter_builder.get_filters()

    def get_model(self) -> Model:
        """
        Return the current model.

        Returns
        -------
        Model
            The current model
        """
        return self._model_builder.model

    def get_settings(self) -> ValueCollection:
        """
        Returns the current settings.

        Returns
        -------
        ValueCollection
            The current settings
        """
        return ValueCollection(self._settings_builder.settings)

    def _start_stop_all(self, start: bool, force_join: bool = False) -> None:
        """
        Start or stop all widgets depending on the input.
        Stopping them also takes care of joining forked processes.

        Parameters
        ----------
        start : bool
            Whether we should start (True) or stop (False) all widgets
        force_join : bool, optional
            Propagates argument to engine, whether we should join also engines
            that have not been working, by default False
        """
        if not self.created_chemoton_widgets:
            write_error_message("You have not created any engines, yet")
            return
        if self.is_blocked:
            write_error_message("Currently in the process of stopping all engines, please be patient")
            return
        if start and force_join:
            write_error_message("Internal error, conflicting inputs")
            return
        button = self._play if start else self._stop
        button.setChecked(True)
        for widget in self.created_chemoton_widgets:
            if start:
                widget.start_stop(start_all=True)
            else:
                widget.start_stop(stop_all=True)
        # additional loop for shutdown to collect processes
        if not start:
            self.is_blocked = True
            self._joiner = EngineJoiner(self, force_join)
            self._joiner.start()
        button.setChecked(False)

    def _toggle_button(self, start: bool):
        """
        Toggle our play or stop button to signal interaction.

        Parameters
        ----------
        start : bool
            Whether we should toggle the play (True) or stop (False) button.
        """
        if start:
            self._play.toggle()
        else:
            self._stop.toggle()

    def _load_file(self) -> None:
        """
        Loads a widget setup from file.
        """
        filename = get_load_file_name(self, "exploration", ["json", "pickle", "pkl"])
        if filename is None:
            return
        self._pre_io_operations()
        if filename.suffix == ".json":
            with open(filename, "r") as f:
                data = f.read()
            save_object = json_wrap.decode(data)
        else:
            with open(filename, "rb") as f:
                save_object = pickle.load(f)
        self._unpack_save_object(save_object)
        self._post_io_operations()

    def _save_file(self, force_join: bool = True) -> None:
        """
        Write current widget setup to file.
        This requires to stop all widgets first, hence may take some time.
        """
        if not self.created_chemoton_widgets:
            write_error_message("You have not created anything, yet")
            return
        filename = get_save_file_name(self, "exploration", ["json", "pickle", "pkl"])
        if filename is None:
            return
        write_info_message("Stopping all engines, this may take some time...", timer=1_000_000_000)
        self._start_stop_all(start=False, force_join=force_join)
        # wait for all engines to be joined
        while self.is_blocked:
            sleep(0.1)
        clear_status_bar()
        self._pre_io_operations()
        write_info_message("Writing to disk")
        save_object = self._generate_save_object()
        try:
            if filename.suffix == ".json":
                encoded = json_wrap.encode(save_object)
                with open(filename, "w") as f:
                    f.write(encoded)
            else:
                with open(filename, "wb") as f:
                    pickle.dump(save_object, f)
        except BaseException as e:
            write_error_message(f"Error while saving: {e}")
        self._post_io_operations()

    def _generate_save_object(self) -> List[List[Any]]:
        """
        Puts all current widgets into one objects from which the widgets can be
        reconstructed.

        Returns
        -------
        List[List[Any]]
            The save object
        """
        save_object: List[List[Any]] = []
        for widget in self.created_chemoton_widgets:
            init_arguments = [type(widget)] + widget.init_arguments[:]
            save_object.append(init_arguments)
        save_object.append([self.get_model()])
        save_object = make_picklable(save_object)
        return save_object

    def _unpack_save_object(self, save_object: List[List[Any]]) -> None:
        """
        The inverse of _generate_save_object.

        Parameters
        ----------
        save_object : List[List[Any]]
            The object holding the reconstructed widget information.
        """
        model = save_object.pop(-1)[0]
        assert isinstance(model, Model)
        self._model_builder.model = model
        for init_arguments in save_object:
            cls = init_arguments.pop(0)
            for arg in init_arguments:
                if hasattr(arg, "initialize_collections"):
                    arg.initialize_collections(self.db_manager)
            inst = cls(*init_arguments)
            self.add_widget(inst)


class EngineJoiner(QThread):
    """
    A thread that joins all engines.
    """

    def __init__(self, parent: ChemotonWidgetContainer, force_join: bool = False):
        """
        Construct the thread.

        Parameters
        ----------
        parent : ChemotonWidgetContainer
            The container that holds all widgets that should be joined.
        force_join : bool, optional
            Whether engines should be joined also if they were not working, by default False
        """
        super().__init__(parent)
        self.container = parent
        self._force = force_join

    def run(self):
        """
        The thread's main loop, which joins all engines.
        """
        for widget in self.container.created_chemoton_widgets:
            widget.join(self._force)
        self.container.is_blocked = False
        self.exit(0)
