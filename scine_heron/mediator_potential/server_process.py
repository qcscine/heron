#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Provides the ServerProcess class.
"""

import socket
from typing import Optional
from multiprocessing import Process
from scine_heron.mediator_potential.mediator_server import run_server
from .clientserver import send_data


class ServerProcess:
    def __init__(self) -> None:
        self.is_server_running = False
        self.__server_process: Optional[Process] = None

    def start(self) -> None:
        if self.__server_process is None:
            self.__server_process = Process(target=run_server, args=())
            self.__server_process.start()

    @staticmethod
    def __send_stop_signal() -> None:
        stop_signal = True
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("127.0.0.1", 55145))
            send_data(data=[stop_signal, None, None, None], socket=s)

    def stop(self) -> None:
        if self.__server_process is not None:
            self.__send_stop_signal()
            self.__server_process.join()
            self.__server_process = None
