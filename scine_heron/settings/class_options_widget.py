#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the ClassOptionsWidget class.
"""

from typing import Optional, Dict, Any, List, Callable, Type, TYPE_CHECKING
import inspect

from PySide2.QtGui import QCloseEvent, QKeySequence
from PySide2.QtCore import Qt, QObject
from PySide2.QtWidgets import (
    QVBoxLayout,
    QScrollArea,
    QDialog,
)
from scine_utilities import opt_settings_names, settings_names, ValueCollection

from scine_heron.containers.buttons import TextPushButton
from scine_heron.utilities import write_error_message
from scine_heron.settings.dict_option_widget import DictOptionWidget
from scine_heron.settings.docstring_parser import DocStringParser

if TYPE_CHECKING:
    from scine_database import Model
else:
    from scine_heron.dependencies.optional_import import importer
    Model = importer("scine_database", "Model")


class ClassOptionsWidget(QDialog):
    """
    A popup widget for editing the options of a class or a dictionary.
    This class is basically a wrapper around DictOptionWidget.
    """

    def __init__(
        self,
        options: Any,
        docstring: Optional[Dict[str, str]] = None,
        parent: Optional[QObject] = None,
        add_close_button: bool = True,
        allow_additions: bool = False,
        allow_removal: bool = True,
        addition_suggestions: Optional[List[str]] = None,
        suggestions_by_name: Optional[Dict[str, Dict[str, Callable]]] = None,
        value_type: Optional[Type] = None,
        keys_excluded_from_io: Optional[List[str]] = None,
    ) -> None:
        """
        Constructs the widget, but does not show the pop-up.
        The widget is constructed with the object to be altered by the user and
        some additional parameters concerning the layout and possibilities of the widget.

        Parameters
        ----------
        options : Any
            The object to be altered by the user.
        docstring : Optional[Dict[str, str]], optional
            A dictionary containing the docstrings for the individual attributes
            or key/value pairs. The docstrings are added as tooltips, by default None
        parent : Optional[QObject], optional
            The parent widget, by default None
        add_close_button : bool, optional
            If the pop-up should have a close button, by default True
        allow_additions : bool, optional
            If additional key/value pairs may be added, by default False
        allow_removal : bool, optional
            If key/value pairs are allowed to be removed, by default True
        addition_suggestions : Optional[List[str]], optional
            A list of strings that are suggested for autocompletion for new keys,
            when the user wants to add a key/value pair, by default None
        suggestions_by_name : Optional[Dict[str, Dict[str, Callable]]], optional
            A dictionary of suggestions for sub dictionaries in the created widget
            with the key representing the key to the sub dictionary and the values
            being a dictionary with the keys being the keys of the subdictionary
            and the value being functions to generate the suggestions, by default None
        keys_excluded_from_io : Optional[List[str]], optional
            A list of keys that should be excluded from saving and loading, by default None
        """
        super(ClassOptionsWidget, self).__init__(parent)

        self._options = options
        if isinstance(options, dict) or isinstance(options, ValueCollection):
            self._option_widget = DictOptionWidget(
                self._options,
                parent=self,
                docstring_dict=docstring,
                add_close_button=False,
                allow_additions=allow_additions,
                allow_removal=allow_removal,
                addition_suggestions=addition_suggestions,
                suggestions_by_name=suggestions_by_name,
                value_type=value_type,
                keys_excluded_from_io=keys_excluded_from_io
            )
        else:
            self._option_widget = DictOptionWidget(
                DictOptionWidget.get_attributes_of_object(self._options),
                parent=self,
                docstring_dict=docstring,
                add_close_button=False,
                allow_additions=allow_additions,
                allow_removal=allow_removal,
                addition_suggestions=addition_suggestions,
                suggestions_by_name=suggestions_by_name,
                keys_excluded_from_io=keys_excluded_from_io
            )

        self.setWindowTitle("Options")
        self.setMinimumWidth(350)
        self.setMinimumHeight(200)

        layout = QVBoxLayout()

        self._scroll_area = QScrollArea()
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setWidget(self._option_widget)
        self._scroll_area.setWidgetResizable(True)
        layout.addWidget(self._scroll_area)

        if add_close_button:
            close_button = TextPushButton("Ok", self.reject)
            close_button.setShortcut(QKeySequence("Return"))
            layout.addWidget(close_button)

        self.setLayout(layout)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._update_options()
        super().closeEvent(event)

    def reject(self) -> None:
        self._update_options()
        super().reject()

    def _update_options(self):
        DictOptionWidget.set_attributes_to_object(
            self._options, self._option_widget.get_widget_data()
        )


class ModelOptionsWidget(ClassOptionsWidget):
    """
    A widget that holds a model and allows to manipulate it.
    """

    def __init__(self, parent: Optional[QObject] = None, model: Optional[Model] = None):
        """
        Construct the widget with an optional starting model.

        Parameters
        ----------
        parent : Optional[QObject], optional
            The parent widget, by default None
        model : Optional[Model], optional
            An optional starting model, a simple PM6 model, if none is given, by default None
        """
        model = Model("PM6", "PM6", "") if model is None else model
        super().__init__(options=model, parent=parent, add_close_button=False, allow_additions=False,
                         allow_removal=False)

    @property
    def model(self) -> Model:
        """
        Getter for the underlying model
        """
        self._update_options()
        return self._options

    @model.setter
    def model(self, model: Model) -> None:
        """
        Setter for the underlying model.

        Parameters
        ----------
        model : Model
            The new model
        """
        self._options = model
        self._option_widget.setParent(None)  # type: ignore
        self._option_widget = DictOptionWidget(
            DictOptionWidget.get_attributes_of_object(self._options),
            parent=self.parent(),
            add_close_button=False,
            allow_additions=False,
            allow_removal=False,
        )
        self._scroll_area.setWidget(self._option_widget)


class GeneralSettingsWidget(ClassOptionsWidget):
    """
    A widget that is meant to build Scine calculator and ReaDuct task settings.
    I can also have a button that allows to add default Chemoton settings.
    """

    def __init__(self, parent: Optional[QObject] = None, pre_settings: Optional[Dict[str, Any]] = None,
                 add_chemoton_settings_button: bool = True, add_opt_suggestions: bool = True):
        """
        Construct the widget with some existing settings and if the Chemoton button
        should be added.

        Parameters
        ----------
        parent : Optional[QObject], optional
            The parent widget, by default None
        pre_settings : Optional[Dict[str, Any]], optional
            Some settings to add to the widget already, by default None
        add_chemoton_settings_button : bool, optional
            If the Chemoton settings button should be added, by default True
        add_opt_suggestions : bool, optional
            If the Scine Utilities optimization settings names should be added as suggestions
        """
        settings = {} if pre_settings is None else pre_settings
        names = [s for s in dir(settings_names) if not s.startswith("_")]
        if add_opt_suggestions:
            names += [s for s in dir(opt_settings_names) if not s.startswith("_")]
        super().__init__(options=settings, parent=parent, add_close_button=False, allow_additions=True,
                         addition_suggestions=names)
        if add_chemoton_settings_button:
            self.default_button = TextPushButton("Add default Chemoton NT Settings",
                                                 self.__add_chemoton_defaults)
            self.layout().addWidget(self.default_button)

    def remove_chemoton_button(self):
        """
        remove the button that allows to add Chemoton settings
        """
        self.default_button.setParent(None)  # type: ignore

    @property
    def settings(self) -> ValueCollection:
        """
        Getter for the underlying settings

        Returns
        -------
        ValueCollection
            The settings
        """
        self._options = {}
        self._update_options()
        return ValueCollection(self._options)

    def __add_chemoton_defaults(self) -> None:
        """
        Adds the Chemoton defaults to the settings
        """
        from scine_chemoton.default_settings import default_nt_settings
        self._update_options()
        defaults = default_nt_settings().as_dict()
        for k, v in defaults.items():
            if k not in self._options:
                self._option_widget.add_key_value(k, v)
        self._options = {**self._options, **defaults}


def generate_instance_based_on_potential_widget_input(calling_widget: QObject, cls: type,
                                                      predefined_kwargs: Optional[Dict[str, Any]] = None,
                                                      possible_suggestions: Optional[Dict[str,
                                                                                          Dict[str, Callable]]] =
                                                      None) -> Any:
    """
    Generate an instance of a given class type based on some user input if required

    Parameters
    ----------
    calling_widget : QObject
        The widget that called this function
    cls : type
        The class type to be instantiated
    predefined_kwargs : Optional[Dict[str, Any]], optional
        A dictionary containing the parameter name and the value that should be used for constructing the
        instance instead of asking the user in the widget, by default None
    possible_suggestions : Optional[Dict[str, Dict[str, Callable]]], optional
        Provided suggestions to be propagated to the ClassOptionsWidgets;
        A dictionary of suggestions for sub dictionaries in the created widget
        with the key representing the key to the sub dictionary and the values
        being a dictionary with the keys being the keys of the subdictionary
        and the value being functions to generate the suggestions, by default None

    Notes
    -----
    Currently not thread safe due to written error messages

    Returns
    -------
    Any
        The instance of the class or None if an error occurred
    """
    delete_list = ["self", "args", "kwargs", "_"]
    signature = inspect.signature(cls.__init__)  # type: ignore
    if len(signature.parameters) > 1:
        parameters = signature.parameters.copy()
        for d in delete_list:
            if d in parameters:
                del parameters[d]
        if predefined_kwargs is not None:
            for key in predefined_kwargs:
                if key not in parameters:
                    write_error_message(f"Failed to construct class '{cls.__name__}', "
                                        f"due to wrong predefined argument {key}")
                    return None
                del parameters[key]
            if not parameters:
                # nothing left for the user to decide, all was predefined
                return cls(**predefined_kwargs)
        elif not parameters:
            # can happen if the class was written inheritance friendly with empty arguments
            return cls()
        try:
            parser = DocStringParser()
            doc = parser.get_docstring_for_class_init(cls.__name__, cls)
        except BaseException:
            # print(str(e))
            doc = None  # pylint: disable=bad-option-value
        param_selection = ClassOptionsWidget(parameters, docstring=doc, parent=calling_widget, allow_removal=False,
                                             add_close_button=True, suggestions_by_name=possible_suggestions)
        param_selection.exec_()
        if predefined_kwargs is not None:
            parameters.update(predefined_kwargs)
        if any(isinstance(p, inspect.Parameter) for p in parameters.values()):
            write_error_message(f"Failed to construct class {cls.__name__}")
            return None
        for k, v in parameters.items():
            if isinstance(v, str):
                if v.startswith("[") and v.endswith("]"):
                    str_list = [s.strip() for s in v.replace("[", "").replace("]", "").split(",")]
                    if str_list and not (len(str_list) == 1 and isinstance(str_list[0], str) and not str_list[0]):
                        parameters[k] = str_list
        return cls(**parameters)
    return cls()


# # # Compound Cost Widget probably not wanted here
class CompoundCostOptionsWidget(ClassOptionsWidget):

    def __init__(
        self,
        options: Any,
        parent: QObject,
    ) -> None:
        super(CompoundCostOptionsWidget, self).__init__(options, parent=parent, allow_additions=True,
                                                        allow_removal=True, value_type=float)
        # Allow access to parent
        self.parent: QObject = parent

        # Deactivate buttons from parent and remember state before disabling
        self._buttons_disabled_state: List[bool] = []
        if hasattr(parent, 'buttons_to_deactivate'):
            for button in parent.buttons_to_deactivate:
                self._buttons_disabled_state.append(not button.isEnabled())
                button.setDisabled(True)

        self.setWindowTitle("Start conditions")
        self.setMinimumWidth(400)
        self.setMinimumHeight(200)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._update_options()
        # Enable buttons as before opening this widget
        self._enable_buttons()

        super().closeEvent(event)

    def reject(self) -> None:
        self._update_options()
        # Enable buttons as before opening this widget
        self._enable_buttons()

        # assert self.parent.pathfinder
        if self._options != self.parent.pathfinder.options:
            self.parent._start_conditions = self._options
        super().reject()

    def _enable_buttons(self):
        if hasattr(self.parent, 'buttons_to_deactivate'):
            for button, disable in zip(self.parent.buttons_to_deactivate, self._buttons_disabled_state):
                button.setDisabled(disable)
