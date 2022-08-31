#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
import sys
import traceback

from PySide2.QtCore import QObject, Signal, QRunnable, Slot

"""
Implemented according to:
https://www.pythonguis.com/tutorials/multithreading-pyside-applications-qthreadpool/
"""


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported Signals
    -----------------

    finished :: Signal
        No data
    error :: Signal
        tuple (exctype, value, traceback.format_exc() )
    result :: Signal
        object data returned from processing, anything
    progress :: Signal
        int indicating % progress
    running :: Signal
        bool indicating if thread is running
    """

    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int)
    running = Signal(bool)


class Worker(QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    Parameters
    ----------
    callback :: function
        The function callback to run on this worker thread. Supplied args and
        kwargs will be passed through to the runner.
    args
        Arguments to pass to the callback function
    kwargs
        Keywords to pass to the callback function
    """

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.running

    @Slot()  # type: ignore
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except BaseException:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done
