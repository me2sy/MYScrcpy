# -*- coding: utf-8 -*-
"""
    各种插件功能类
    ~~~~~~~~~~~~~~~~~~
    单独形成module，解决循环引用问题

    Log:
        2024-09-29 1.6.4 Me2sY 创建
"""

__author__ = 'Me2sY'
__version__ = '1.6.4'

__all__ = [
    'KeyInfo', 'MouseGestureInfo', 'ActionCallbackParam'
]

from dataclasses import dataclass, field
from typing import Any

from myscrcpy.utils import Action, UnifiedKey


@dataclass
class KeyInfo:
    """
        按键信息
    """
    name: str
    space: int
    uk_name: str
    desc: str = ''

    @property
    def vm_name(self) -> str:
        return f"keys.{self.name}"


@dataclass
class MouseGestureInfo:
    """
        鼠标手势信息
    :return:
    """
    name: str
    space: int
    gestures: str
    desc: str = ''

    @property
    def vm_name(self) -> str:
        return f"gestures.{self.name}"


@dataclass
class ActionCallbackParam:
    """
        回调传递参数
    """
    action: Action
    uk: UnifiedKey
    is_first: bool = True
    action_data: Any = None
    app_data: Any = None
    user_data: Any = None
    kwargs: dict = field(default_factory=dict)
