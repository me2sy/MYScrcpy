# -*- coding: utf-8 -*-
"""
    utils
    ~~~~~~~~~~~~~~~~~~


    Log:
        2024-07-28 1.0.0 Me2sY  发布

        2024-07-25 0.2.1 Me2sY
            1.UnifiedKeyMapper 新增 uk2scrcpy 方法，用于支持scrcpy uhid keyboard
            2.新增 ADBKeyCode 用于adb key event

        2024-07-09 0.2.0 Me2sY
            1.项目重构，去除路径方法，新增Param类存储变量
            2.改用 path.home路径存储配置文件

        2024-07-07 0.1.5 Me2sY  UnifiedKeyMapper 新增 pg2uk 同时使用@cache 加速转换

        2024-06-29 0.1.4 Me2sY
            1.Coordinate 新增部分方法
            2.新增 Action

        2024-06-19 0.1.3 Me2sY  新增 UnifiedKey, UnifiedKeyMapper 统一各类按键码

        2024-06-10 0.1.2 Me2sY  新增 ScalePoint Coordinate Vector

        2024-06-06 0.1.1 Me2sY  改造 适配Dearpygui

        2024-06-01 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '1.0.0'

__all__ = [
    'Param',
    'CfgHandler',
    'Point', 'ScalePoint', 'Coordinate',
    'Action',
    'UnifiedKey', 'UnifiedKeyMapper',
    'ADBKeyCode'
]

import pathlib
import json
from enum import IntEnum, unique
from typing import NamedTuple
from functools import cache


PROJECT_NAME = 'myscrcpy'
AUTHOR = 'Me2sY'


def project_path() -> pathlib.Path:
    for _ in pathlib.Path(__file__).resolve().parents:
        if _.name == PROJECT_NAME:
            return _


class Param:
    """
        参数
    """

    PROJECT_NAME = PROJECT_NAME
    AUTHOR = AUTHOR

    PROJECT_PATH = project_path()

    PATH_CONFIGS = PROJECT_PATH.joinpath('configs')
    PATH_CONFIGS.mkdir(parents=True, exist_ok=True)

    PATH_STATICS = PROJECT_PATH.joinpath('static')
    PATH_STATICS.mkdir(parents=True, exist_ok=True)
    PATH_STATICS_ICON = PATH_STATICS.joinpath('myscrcpy.ico')

    PATH_LIBS = PROJECT_PATH.joinpath('libs')
    PATH_LIBS.mkdir(parents=True, exist_ok=True)

    PATH_TPS = pathlib.Path.home().joinpath(f".{PROJECT_NAME}").joinpath('tps')
    PATH_TPS.mkdir(parents=True, exist_ok=True)

    PATH_TEMP = pathlib.Path.home().joinpath(f".{PROJECT_NAME}").joinpath('temp')
    PATH_TEMP.mkdir(parents=True, exist_ok=True)

    ROTATION_VERTICAL = 0
    ROTATION_HORIZONTAL = 1

    # dpg
    INT_LEN_WIN_TITLE_HEIGHT = 19
    INT_LEN_WIN_BORDER = 8


class CfgHandler:
    """
        TPS Configuration Handler
    """

    @classmethod
    def load(cls, config_path: pathlib.Path) -> dict:
        return json.load(config_path.open('r'))

    @classmethod
    def save(cls, config_path: pathlib.Path, config: dict) -> None:
        json.dump(config, config_path.open('w'), indent=4)


@unique
class Action(IntEnum):
    """
        按键事件
    """
    DOWN = 0
    RELEASE = 1
    MOVE = 2
    ROLL = 3


@unique
class ADBKeyCode(IntEnum):

    HOME = 3
    BACK = 4
    POWER = 26
    MENU = 82

    ENTER = 66
    BACKSPACE = 67
    ESCAPE = 111

    N0 = 7
    N1 = 8
    N2 = 9
    N3 = 10
    N4 = 11
    N5 = 12
    N6 = 13
    N7 = 14
    N8 = 15
    N9 = 16


@unique
class UnifiedKey(IntEnum):

    SETKEY = -1

    M_LEFT = 0
    M_RIGHT = 1
    M_WHEEL = 2
    M_WHEEL_UP = 3
    M_WHEEL_DOWN = 4

    NP_DIVIDE = 20      # /
    NP_MULTIPLY = 21    # *
    NP_MINUS = 22       # -
    NP_PLUS = 23        # +
    NP_ENTER = 24       # Enter
    NP_PERIOD = 25      # .

    NP_0 = 30
    NP_1 = 31
    NP_2 = 32
    NP_3 = 33
    NP_4 = 34
    NP_5 = 35
    NP_6 = 36
    NP_7 = 37
    NP_8 = 38
    NP_9 = 39

    K_0 = 40
    K_1 = 41
    K_2 = 42
    K_3 = 43
    K_4 = 44
    K_5 = 45
    K_6 = 46
    K_7 = 47
    K_8 = 48
    K_9 = 49

    A = 60
    B = 61
    C = 62
    D = 63
    E = 64
    F = 65
    G = 66
    H = 67
    I = 68
    J = 69
    K = 70
    L = 71
    M = 72
    N = 73
    O = 74
    P = 75
    Q = 76
    R = 77
    S = 78
    T = 79
    U = 80
    V = 81
    W = 82
    X = 83
    Y = 84
    Z = 85

    F1 = 91
    F2 = 92
    F3 = 93
    F4 = 94
    F5 = 95
    F6 = 96
    F7 = 97
    F8 = 98
    F9 = 99
    F10 = 100
    F11 = 101
    F12 = 102

    ESCAPE = 130
    BACKQUOTE = 131
    TAB = 132
    L_SHIFT = 133
    L_CTRL = 134
    L_WIN = 135
    L_ALT = 136
    SPACE = 137
    R_ALT = 138
    R_WIN = 139
    R_CTRL = 140
    R_SHIFT = 141
    RETURN = 142
    COMMA = 143         # ,
    PERIOD = 144        # .
    SLASH = 145         # /
    COLON = 146         # ;
    QUOTE = 147         # '
    L_BRACKET = 148     # [
    R_BRACKET = 149     # ]
    BACKSLASH = 150     # \
    MINUS = 151         # -
    EQUALS = 152        # =
    BACKSPACE = 153
    INSERT = 154
    DELETE = 155
    HOME = 156
    END = 157
    PAGE_UP = 158
    PAGE_DOWN = 159
    UP = 160
    DOWN = 161
    LEFT = 162
    RIGHT = 163


class UnifiedKeyMapper:
    """
        Unified Key Mapper
        转换 dpg pg 事件代码 为 统一按键代码
    """

    cfg = CfgHandler.load(Param.PATH_CONFIGS.joinpath('key_mapper.json'))

    MAPPER_PG = {v: k for k, v in cfg['pg'].items()}
    MAPPER_DPG = {v: k for k, v in cfg['dpg'].items()}

    @classmethod
    @cache
    def dpg2uk(cls, dpg_code: int) -> UnifiedKey:
        """
            dpg key code to union keycode Enum
        :return:
        """
        try:
            return UnifiedKey[cls.MAPPER_DPG[int(dpg_code)]]
        except KeyError:
            print(f"DPG KEYCODE {dpg_code} is not in mapper!")
            return UnifiedKey(-1)

    @classmethod
    @cache
    def pg2uk(cls, pg_code: int) -> UnifiedKey:
        """
            dpg key code to UnionKey Enum
        :param pg_code:
        :return:
        """
        try:
            return UnifiedKey[cls.MAPPER_PG[int(pg_code)]]
        except KeyError:
            print(f"PG KEYCODE {pg_code} is not in mapper!")
            return UnifiedKey(-1)

    @classmethod
    @cache
    def uk2pg(cls, unified_key: UnifiedKey) -> int:
        """
            unified key code to pygame key code
        :param unified_key:
        :return:
        """
        return cls.cfg['pg'][unified_key.name]

    @classmethod
    @cache
    def uk2uhidkey(cls, unified_key: UnifiedKey) -> int:
        """
            unified key code to scrcpy scancode
        :param unified_key:
        :return:
        """
        return cls.cfg['uhidkey'][unified_key.name]



class Point(NamedTuple):
    """
        坐标点
    """
    x: int
    y: int

    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Point') -> 'Point':
        return Point(self.x - other.x, self.y - other.y)

    @property
    def d(self) -> dict:
        return self._asdict()


class ScalePoint(NamedTuple):
    """
        比例点
    """
    x: float
    y: float

    def __add__(self, other: 'ScalePoint') -> 'ScalePoint':
        return ScalePoint(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'ScalePoint') -> 'ScalePoint':
        return ScalePoint(self.x - other.x, self.y - other.y)

    def __mul__(self, scale: float) -> 'ScalePoint':
        return ScalePoint(self.x * scale, self.y * scale)


class Coordinate(NamedTuple):
    """
        坐标系
    """
    width: int
    height: int

    def __repr__(self):
        return f'w:{self.width}, h:{self.height} {"Up" if self.rotation == Param.ROTATION_VERTICAL else "Right"}'

    def __add__(self, other: 'Coordinate') -> 'Coordinate':
        return Coordinate(self.width + other.width, self.height + other.height)

    def __sub__(self, other: 'Coordinate') -> 'Coordinate':
        return Coordinate(self.width - other.width, self.height - other.height)

    def __mul__(self, scale: float) -> 'Coordinate':
        if 0 < scale:
            return Coordinate(round(self.width * scale), round(self.height * scale))
        else:
            raise ValueError(f"Scale value {scale} is not valid")

    def to_point(self, scale_point: ScalePoint) -> Point:
        return Point(round(scale_point.x * self.width), round(scale_point.y * self.height))

    def to_scale_point(self, x: int, y: int) -> ScalePoint:
        return ScalePoint(x / self.width, y / self.height)

    @property
    def rotation(self) -> int:
        return Param.ROTATION_VERTICAL if self.height >= self.width else Param.ROTATION_HORIZONTAL

    @property
    def max_size(self) -> int:
        return max(self.width, self.height)

    @property
    def min_size(self) -> int:
        return min(self.width, self.height)

    @property
    def d(self) -> dict:
        return self._asdict()

    def w2h(self, width: float) -> float:
        return width / self.width * self.height

    def h2w(self, height: float) -> float:
        return height / self.height * self.width

    def get_max_coordinate(self, max_width: int = 0, max_height: int = 0) -> 'Coordinate':
        """
            获取限制下最大坐标系
        :param max_width:
        :param max_height:
        :return:
        """

        scale_w = max_width / self.width
        scale_h = max_height / self.height

        if scale_w <= 0 < scale_h:
            _scale = min(scale_h, 1)

        elif scale_w > 0 >= scale_h:
            _scale = min(scale_w, 1)

        elif scale_w > 0 and scale_h > 0:
            _scale = min(scale_h, scale_w, 1)

        else:
            _scale = 1

        return self * _scale
