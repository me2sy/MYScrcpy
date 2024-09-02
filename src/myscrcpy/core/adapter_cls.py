# -*- coding: utf-8 -*-
"""
    适配器基类
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-28 1.4.0 Me2sY  创建，用于V/A/C数据转换
"""

__author__ = 'Me2sY'
__version__ = '1.4.0'

__all__ = [
    'ScrcpyAdapter'
]

from abc import ABCMeta, abstractmethod

from myscrcpy.core.connection import Connection


class ScrcpyAdapter(metaclass=ABCMeta):

    def __init__(self, connection: Connection):
        self.conn = connection
        self.is_running = False
        self.is_ready = False

    @abstractmethod
    def start(self, *args, **kwargs):
        """
            start the adapter
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        """
            close the adapter
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def main_thread(self):
        """
            数据处理主进程
        :return:
        """
        raise NotImplementedError
