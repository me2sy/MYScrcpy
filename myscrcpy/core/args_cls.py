# -*- coding: utf-8 -*-
"""
    连接配置基类
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-28 1.4.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '1.4.0'

__all__ = [
    'ScrcpyConnectArgs'
]

from dataclasses import dataclass, asdict


@dataclass
class ScrcpyConnectArgs:

    def __init__(self, *args, **kwargs):
        ...

    def to_args(self) -> list:
        """
            生成 scrcpy 连接参数
        :return:
        """
        raise NotImplementedError

    @classmethod
    def load(cls, **kwargs):
        """
            加载方法
        :param kwargs:
        :return:
        """
        return cls(**kwargs)

    def dump(self) -> dict:
        """
            转储方法
        :return:
        """
        return asdict(self)
