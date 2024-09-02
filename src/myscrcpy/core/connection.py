# -*- coding: utf-8 -*-
"""
    Connection
    ~~~~~~~~~~~~~~~~~~
    连接类，用于创建 Scrcpy 连接，连接状态管理、自动重连等

    Log:
        2024-08-28 1.4.0 Me2sY
            1.创建
            2.优化server启动逻辑，使用clean降低错误发生，同时不同线程推送不同server文件，确保clean不会误删文件
"""

__author__ = 'Me2sY'
__version__ = '1.4.0'

__all__ = [
    'Connection'
]

import random
from socket import socket
import threading
import time

from adbutils import AdbDevice, Network, AdbConnection, AdbError
from loguru import logger

from myscrcpy.utils import Param


class Connection:
    """
        连接类，用于创建 Scrcpy 连接，状态管理等
    """

    def __init__(self, args, retry_n: int = 3):
        """
            初始化连接参数
        :param args: Scrcpy Connect Args
        :param retry_n: 连接重试次数
        """

        self.args = args

        self._stream: AdbConnection | None = None
        self.socket: socket | None = None

        self.scid = self.random_scid()

        self.is_connected = False
        self.retry_n = retry_n

    def __del__(self):
        self.is_connected = False
        if self._stream is not None and not self._stream.closed:
            try:
                self._stream.close()
            except:
                ...

    @staticmethod
    def random_scid() -> str:
        """
            创建随机 scid，避免抢夺链接
        :return:
        """
        return str(random.randint(0, 5)) + ''.join([hex(random.randint(1,15))[-1] for _ in range(7)])

    def disconnect(self):
        """
            关闭连接
        :return:
        """
        if self.is_connected and self._stream is not None and not self._stream.closed:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(e)
            try:
                self._stream.close()
            except:
                ...

        self.is_connected = False
        self.scid = self.random_scid()

    @staticmethod
    def clean(func):
        """
            重置
        :param func:
        :return:
        """
        def wrapper(self, *args, **kwargs):
            if self.is_connected:
                self.disconnect()
            return func(self, *args, **kwargs)

        return wrapper

    @clean
    def connect(
            self, adb_device: AdbDevice, extra_cmd: list = None, timeout: int = 5,
            read_stream: bool = True,
            _retry_n: int = 0
    ) -> bool:
        """
            连接至 Scrcpy，建立重连机制。
        :param adb_device: ADB设备
        :param extra_cmd: 附加命令
        :param timeout: 连接超时时间
        :param read_stream: 读取stream回传信息
        :param _retry_n: 已重试测试，用于重试，不建议赋值
        :return:
        """

        if _retry_n > self.retry_n:
            return False

        # 2024-08-30 Me2sY  修复 因 clean导致的 scrcpy-server 自动删除问题，采用每个进程独立scrcpy-server_SCID
        push_path = Param.PATH_SCRCPY_PUSH + f"_{self.scid}"
        adb_device.sync.push(Param.PATH_SCRCPY_SERVER_JAR_LOCAL, push_path)

        extra_cmd = [] if extra_cmd is None else extra_cmd
        cmd = Param.SCRCPY_SERVER_START_CMD + self.args.to_args() + extra_cmd + [f"scid={self.scid}"]
        cmd[0] = cmd[0] + push_path

        # logger.debug(f"Adb Run => {cmd}")

        # 设备执行 app_process
        try:
            self._stream = adb_device.shell(cmd, stream=True, timeout=timeout)
        except AdbError as e:
            logger.error(f"Make Stream Error, Retrying... ERROR => {e}")
            return self.connect(adb_device, extra_cmd, timeout, read_stream, _retry_n + 1)

        wait_ms = 10
        _conn = None
        for _ in range(timeout * 1000 // wait_ms):
            try:
                # 创建 forward 连接
                _conn = adb_device.create_connection(Network.LOCAL_ABSTRACT, f"scrcpy_{self.scid}")
                break
            except AdbError as e:
                time.sleep(wait_ms / 1000)

        if _conn is None:
            logger.error('Failed to Create Socket. Reconnect')
            return self.connect(adb_device, extra_cmd, timeout, read_stream, _retry_n + 1)
        else:
            if _conn.recv(1) != b'\x00':
                logger.error('Dummy Data Error! Reconnect')
                return self.connect(adb_device, extra_cmd, timeout, read_stream, _retry_n + 1)

        # Device Name
        _device_name = _conn.recv(64).decode('utf-8').rstrip('\x00')

        self.socket = _conn
        self.is_connected = True

        # 现实 Scrcpy Server 回传运行信息
        if read_stream:
            threading.Thread(target=self._thread_load_stream, args=(_device_name,)).start()

        return True

    def _thread_load_stream(self, device_name: str):
        """
            读取 Scrcpy Server 回传信息
        :return:
        """
        msg = ''
        while self.is_connected and not self._stream.closed:
            try:
                w = self._stream.read_string(1)
                if w == b'':
                    logger.warning(f"Stream Lost Connection")
                    break
                if w == '\n':
                    logger.info(f"{device_name:<32} => {msg}")
                    msg = ''
                else:
                    msg += w
            except AdbError:
                break
            except ConnectionAbortedError:
                break
            except Exception as e:
                logger.error(f"{device_name:<32} Stream Exception => {e}")

    def recv(self, buf_size) -> bytes:
        """
            self.socket.recv
        :param buf_size:
        :return:
        """
        if self.is_connected:
            return self.socket.recv(buf_size)
        else:
            return b''

    def send(self, buf_data: bytes):
        """
            self.socket.send
        :param buf_data: control bytes
        :return:
        """
        if self.is_connected:
            self.socket.send(buf_data)
