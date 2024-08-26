__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Department of Chemistry and Applied Biosciences, Reiher Group.
See LICENSE.txt for details.
"""

from typing import TYPE_CHECKING, Any, Optional

from PySide2.QtCore import QObject

from scine_heron.autocas.basic_options import BasicOptions

if TYPE_CHECKING:
    Signal = Any
else:
    pass

from PySide2.QtCore import Signal


class OptionsStatusManager(QObject):
    interface_changed_signal = Signal()
    status_bar_update_signal = Signal(str)

    def __init__(self, basic_options: BasicOptions, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.__basic_options = basic_options

    @property
    def basic_options(self) -> BasicOptions:
        """
        Returns the settings.
        """
        return self.__basic_options

    @property
    def error_message(self) -> str:
        """
        Returns the error_message.
        """
        return self.__basic_options.error_message

    @error_message.setter
    def error_message(self, value: str) -> None:
        """
        Sets the contained value. Notifies on change.
        """
        if value == self.__basic_options.error_message or value == "":
            return

        self.__basic_options.error_message = value
        self.status_bar_update_signal.emit(value)
