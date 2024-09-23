# -*- coding: utf-8 -*-
"""
    Extension ABC
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-09-18 1.6.0 Me2sY  废弃，将于下一个版本移除

        2024-09-12 1.0.0 Me2sY
            创建，用于实现扩展
"""

__author__ = 'Me2sY'
__version__ = '1.6.0'

__all__ = [
    'ExtRunEnv', 'MYScrcpyExtension'
]

from abc import abstractmethod, ABCMeta
from dataclasses import dataclass

from myscrcpy.core import AdvDevice
from myscrcpy.core.session import Session
from myscrcpy.gui.dpg.components.vc import CPMVC


@dataclass
class ExtRunEnv:
    """
        通过run函数回传当前运行环境
    """

    # Adv Device
    adv_device: AdvDevice

    # Run Session
    session: Session

    # Window Main
    window: 'WindowMain'

    # VideoController
    vc: CPMVC

    # Pad Tag
    tag_pad: str | int


class MYScrcpyExtension(metaclass=ABCMeta):
    """
        扩展基类
        通过继承该类，实现自定义扩展
    """
    @staticmethod
    def register(*args, **kwargs):
        """
            注册类
        :return:
        """
        raise NotImplementedError()

    @abstractmethod
    def run(self, ext_run_evn: ExtRunEnv, *args, **kwargs):
        """
            执行方法，初始化实例后，自动调用该函数
        :param ext_run_evn:
        :param args:
        :param kwargs:
        :return:
        """
        ...

    @abstractmethod
    def stop(self):
        """
            停止方法，Windows Disconnect是调用该方法
        :return:
        """
        ...
