#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
from scine_heron.mediator_potential import clientserver
import pytest
from hypothesis import strategies as st
from hypothesis import given
from string import printable

from box import Box
from typing import Any, Tuple, Generator

import socket
from socket import socket as Socket


class SocketPairMock:
    """
    A pair of two mock sockets that can be used to mock
    an already configured pair of socket
    (e.g., a socket that has been already created and connected,
    and a socket generated by the accept() method on a listening socket)

    The mock sockets implement only 'recv' and 'sendall',
    but can be easily expanded.

    Only A->B communication is used.
    """

    def __init__(self) -> None:
        self._data = [bytearray(), bytearray()]
        # The second bytearray could be used
        # to implement B -> A communication.

    def get_socketA(self) -> Box:
        def sendall(data: bytes) -> None:
            self._data[0].extend(data)

        _socket = Box()
        _socket.sendall = sendall

        return _socket

    def get_socketB(self) -> Box:
        def recv(size: int) -> bytes:
            res = self._data[0][:size]
            self._data[0] = self._data[0][size:]
            return res

        _socket = Box()
        _socket.recv = recv

        return _socket


@pytest.mark.slow  # type: ignore[misc]
@given(
    data_to_send=st.recursive(
        st.none() | st.booleans() | st.floats(allow_nan=False) | st.text(printable),
        lambda children: st.lists(children)
        | st.dictionaries(st.text(printable), children),
    )
)
def test_sendrecv_pair_mock(data_to_send: Any) -> None:
    """
    Test that the data sent is received correctly,
    using mocks for the socket objects.
    The random data generation is based on
    https://hypothesis.readthedocs.io/en/latest/data.html#recursive-data
    """
    socket_pair = SocketPairMock()
    socketA, connection = socket_pair.get_socketA(), socket_pair.get_socketB()

    # Note: mocking a socket with a Box
    clientserver.send_data(data_to_send, socketA)

    # Note: mocking a socket with a Box
    received_data = clientserver.recv_data(connection)

    assert received_data == data_to_send


@pytest.fixture(name="socket_pair", scope="session")  # type: ignore[misc]
def get_socket_pair() -> Generator[Tuple[Socket, Socket], None, None]:
    """
    Sets up two sockets so that "sendall" and "recv" can be used on them.
    """
    PORT = 55148
    HOST = "127.0.0.1"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((HOST, PORT))
            connection, _address = server.accept()
            with connection:
                yield (connection, client)


@pytest.mark.slow  # type: ignore[misc]
@given(
    data_to_send=st.recursive(
        st.none() | st.booleans() | st.floats(allow_nan=False) | st.text(printable),
        lambda children: st.lists(children)
        | st.dictionaries(st.text(printable), children),
    )
)
def test_sendrecv_pair_real(
    data_to_send: Any, socket_pair: Tuple[Socket, Socket]
) -> None:
    """
    Test that the data sent is received correctly,
    using real sockets.
    The random data generation is based on
    https://hypothesis.readthedocs.io/en/latest/data.html#recursive-data
    """
    connection, client = socket_pair
    clientserver.send_data(data_to_send, client)
    received_data = clientserver.recv_data(connection)

    assert received_data == data_to_send