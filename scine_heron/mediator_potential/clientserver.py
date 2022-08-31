#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Functions that abstract sending and receiving data
between a server and a client.
The data is now serialized using json.
"""
import json
import struct
import typing
from socket import socket as Socket


def send_data(data: typing.Any, socket: Socket) -> None:
    """
    Serialise and send data through a socket.
    The size of the dataset is prepended to the real data,
    so that the receiver knows how large is the dataset.
    Retry until it is done.
    """
    serialized = json.dumps(data)
    raw_data = bytes(serialized, encoding="utf-8")
    sizeinfo = struct.pack("!i", len(raw_data))  # Sending an integer

    socket.sendall(sizeinfo)
    socket.sendall(raw_data)


def recv_data(connection: Socket) -> typing.Any:
    """
    Read data from a socket.
    It is expected that the first datum that comes out
    will be the size of the data sent through.
    """
    buf = bytearray()
    while len(buf) < 4:
        buf += connection.recv(4 - len(buf))
    (size_to_receive,) = struct.unpack("!i", buf)
    size_received = 0
    data_received = bytearray()
    while len(data_received) < size_to_receive:
        chunksize = min(4096, size_to_receive - size_received)
        data_received += connection.recv(chunksize)
    data_decoded = data_received.decode("utf-8")

    return json.loads(data_decoded)
