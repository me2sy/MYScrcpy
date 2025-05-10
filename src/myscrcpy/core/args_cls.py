# -*- coding: utf-8 -*-
"""
    连接配置基类
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2025-05-10 3.2.0 Me2sY  定版

        2024-08-28 1.4.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '3.2.0'

__all__ = [
    'ScrcpyConnectArgs'
]

from dataclasses import dataclass, asdict


@dataclass
class ScrcpyConnectArgs:

    is_activate: bool = True

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
