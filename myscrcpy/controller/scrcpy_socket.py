# -*- coding: utf-8 -*-
"""
    Scrcpy Socket
    ~~~~~~~~~~~~~~~~~~
    基础类

    Log:
        2024-07-30 1.1.0 Me2sY 从原有结构中抽离,形成发布初版

"""

__author__ = 'Me2sY'
__version__ = '1.1.0'

__all__ = [
    'ScrcpySocket'
]


from abc import ABCMeta, abstractmethod
import socket
import struct


class ScrcpySocket(metaclass=ABCMeta):
    """
        ScrcpySocket ABCMeta
        Scrcpy server 2.5
    """
    @abstractmethod
    def close(self):
        """
            Stop Running and Close Socket
        :return:
        """
        raise NotImplementedError

    def __init__(
            self,
            conn: socket.socket | None = None,
            **kwargs
    ):
        self._conn: socket.socket | None = conn
        self.is_running = conn is not None and isinstance(conn, socket.socket)

    def setup_socket_connection(self, conn: socket.socket):
        self._conn = conn
        self.is_running = True
        return self

    def decode_packet(self) -> bytes:
        """
            当 设置 send_frame_meta = True时，解析数据包
            为降低延迟，暂时关闭send_frame_meta
        """
        self._conn.recv(8)
        (size, ) = struct.unpack('>I', self._conn.recv(4))
        data = self._conn.recv(int(size))
        return data
