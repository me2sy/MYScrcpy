# -*- coding: utf-8 -*-
"""
    __init__.py
    ~~~~~~~~~~~~~~~~~~
    
    Log:
        2025-05-10 3.2.0 Me2sY  定板

        2025-04-09 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '3.2.0'

__all__ = [
    'StoredConfig', 'MYColor', 'FONT_ZH', 'MYCombineColors',
    'MYStyledButton',
    'IntInput', 'create_snack', 'KeyMapper'
]

from dataclasses import dataclass
from enum import Enum
import string
from typing import ClassVar, Any

from kivy.core.window import Keyboard
from kivy.metrics import sp
from kivy.storage.dictstore import DictStore
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText

from myscrcpy.utils import Param, UnifiedKeys, KeyMapper


@dataclass
class StoredConfig:
    """
        可存储配置
    """

    # 继承并定义StorageKey
    _STORAGE_KEY: ClassVar[str]
    _dict_store: DictStore
    _belongs: str | None

    @staticmethod
    def key(storage_key: str, belongs: str | None = None) -> str:
        """
            生成存储键值
        :param storage_key:
        :param belongs:
        :return:
        """
        if belongs:
            return f'{belongs}-{storage_key}'
        else:
            return f'{storage_key}'

    @classmethod
    def load(cls, dict_store: DictStore, belongs: str = None, reset: bool = False, defaults: dict[Any, Any] = None):
        """
            加载默认配置
        :param dict_store:
        :param belongs: 归属配置，针对不同设备获情况
        :param reset: 重置
        :param defaults:
        :return:
        """
        _key = cls.key(cls._STORAGE_KEY, belongs)
        if reset or not dict_store.exists(_key):
            values = {key: value for key, value in cls.__dict__.items() if not key.startswith('_')}
            values.update(defaults or {})
            dict_store.put(_key, **values)
        return cls(_dict_store=dict_store, _belongs=belongs, **dict_store.get(_key))

    def save(self):
        """
            保存
        :return:
        """
        self._dict_store.put(
            self.key(self._STORAGE_KEY, self._belongs),
            **{key: value for key, value in self.__dict__.items() if not key.startswith('_')}
        )

@dataclass(frozen=True)
class MYColor:
    """
        统一色彩
    """
    black = 'black'
    white = 'white'
    red = '#ff6b81'

    green = '#7bed9f'
    blue = '#1e90ff'
    grey = '#e2e2e2'
    yellow = '#f1c40f'
    orange = '#ffa502'

    button_vol = (1, .753, .314, 1)
    button_camera = (.863, .969, .173, 1)
    button_screen = (.471, .91, .949, 1)


class MYCombineColors(Enum):
    """
        Button 配色
    """
    black = (MYColor.black, MYColor.white)
    white = (MYColor.white, MYColor.black)
    red = (MYColor.red, MYColor.white)
    green = (MYColor.green, MYColor.black)
    blue = (MYColor.blue, MYColor.black)
    grey = (MYColor.grey, MYColor.black)
    yellow = (MYColor.yellow, MYColor.black)
    orange = (MYColor.orange, MYColor.black)


# 注册中文字体，替代原Roboto
FONT_ZH = 'Roboto'

from kivy.core.text import LabelBase
LabelBase.register(
    name=FONT_ZH,
    fn_regular=(Param.PATH_LIBS / 'notosans.ttf').__str__(),
    fn_bold=(Param.PATH_LIBS / 'notosans_bold.ttf').__str__()
)


class MYStyledButton(Button):

    DEFAULT_STYLE = MYCombineColors.grey

    def __init__(self, style: MYCombineColors = None, user_data: Any = None, **kwargs):
        """
            自定义按钮，支持颜色及中文显示
        :param kwargs:
        """
        super(MYStyledButton, self).__init__(**kwargs)
        self.background_normal = ''
        style = self.DEFAULT_STYLE if style is None else style
        self.background_color = style.value[0]
        self.color = style.value[1]
        self.font_name = FONT_ZH
        self.user_data = user_data
        self.font_size = sp(13)


class IntInput(TextInput):
    """
        Int TextInput
    """
    def insert_text(self, substring, from_undo=False):
        if substring in string.digits:
            return super().insert_text(substring, from_undo=from_undo)


def create_snack(msg: str, color: MYCombineColors = None, duration: float=2., **kwargs) -> MDSnackbar:
    """
        创建简单提示框
    :param msg:
    :param color:
    :param duration: 持续时间
    :param kwargs:
    :return:
    """
    default = dict(y=sp(40), pos_hint={"center_x": 0.5}, size_hint_x=0.5, duration=duration)
    default.update(kwargs)

    text = MDSnackbarText(text=msg)
    if color:
        text.theme_text_color = 'Custom'
        text.text_color = color.value[1]

    sb = MDSnackbar(text, **default)
    if color:
        sb.background_color = color.value[0]

    return sb


# 注册 kivy 按键 至 KeyMapper
# Kivy使用 pygame 键位键值

key_mapper = {}

for key, code in Keyboard.keycodes.items():
    _key = {
        'rshift': 'SHIFT_R',
        'lctrl': 'CONTROL_L',
        'rctrl': 'CONTROL_R',
        'alt-gr': 'ALT_R',
        'pageup': 'PAGE_UP',
        'pagedown': 'PAGE_DOWN',
        'numpaddecimal': 'NP_PERIOD',
        'numpaddivide': 'NP_DIVIDE',
        'numpadmul': 'NP_MULTIPLY',
        'numpadsubstract': 'NP_MINUS',
        'numpadadd': 'NP_PLUS',
        'numpadenter': 'NP_ENTER',
        'spacebar': 'SPACE',
        '[': 'BRACKET_L',
        ']': 'KB_BRACKET_R',
        ';': 'KB_COLON',
        '=': 'KB_EQUALS',
        '-': 'KB_MINUS',
        '/': 'KB_SLASH',
        '`': 'KB_BACKQUOTE',
        '\\': 'KB_BACKSLASH',
        "'": 'KB_QUOTE',
        ',': 'KB_COMMA',
        '.': 'KB_PERIOD'
    }.get(key, key)

    if _key.startswith('numpad'):
        _key = 'NP_' + _key[-1]

    uks = UnifiedKeys.filter_name(_key)
    if uks:
        key_mapper[code] = uks

KeyMapper.register('ky', key_mapper)
