# -*- coding: utf-8 -*-
"""
    更新器
    ~~~~~~~~~~~~~~~~~~
    用于 dpg update frame

    Log:
        2024-07-28 1.0.0 Me2sY  发布初版

        2024-06-04 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '1.0.0'

__all__ = ['LoopRegister']


class LoopRegister:
    """
        注册器，将需要在loop中循环的函数，在此处注册
    """

    UPDATE_FUNCTIONS = set()
    TPF_FUNC = None

    @classmethod
    def register(cls, func):
        cls.UPDATE_FUNCTIONS.add(func)

    @classmethod
    def unregister(cls, func):
        cls.UPDATE_FUNCTIONS.discard(func)

    @classmethod
    def func_call_loop(cls):
        for func in cls.UPDATE_FUNCTIONS:
            func()
        cls.TPF_FUNC()

    @classmethod
    def register_tpf(cls, tpf_func):
        cls.TPF_FUNC = tpf_func
