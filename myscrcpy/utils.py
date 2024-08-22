# -*- coding: utf-8 -*-
"""
    utils
    ~~~~~~~~~~~~~~~~~~
    工具类

    Log:
        2024-08-22 1.3.6 Me2sY  新增部分 ADB Key Code

        2024-08-21 1.3.5 Me2sY
            1. 重构 UnifiedKeyMapper 去除配置文件加载，采用注入方式，解决不同平台下Code不同问题
            2. 新增部分Code

        2024-08-15 1.2.1 Me2sY
            1.新增 ValueRecord、ValueManager，使用TinyDB进行全局配置、属性配置及值管理
            2.新增 部分Code及方法

        2024-08-05 1.2.0 Me2sY  升级 Scrcpy Server 2.6.1

        2024-08-02 1.1.3 Me2sY  新增媒体控制键代码

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
__version__ = '1.3.6'

__all__ = [
    'Param',
    'CfgHandler',
    'Point', 'ScalePoint', 'Coordinate',
    'Action',
    'UnifiedKey', 'UnifiedKeyMapper',
    'ADBKeyCode',
    'ValueRecord', 'ValueManager'
]

import base64
import pickle
import pathlib
import json
from enum import IntEnum, unique
from typing import NamedTuple, Any
from functools import cache
from dataclasses import dataclass

from tinydb import TinyDB, Query

PROJECT_NAME = 'myscrcpy'
AUTHOR = 'Me2sY'


def project_path() -> pathlib.Path:
    """
        获取项目根目录
    :return:
    """
    for _ in pathlib.Path(__file__).resolve().parents:
        if _.name == PROJECT_NAME:
            return _


class Param:
    """
        参数
    """

    PROJECT_NAME = PROJECT_NAME
    AUTHOR = AUTHOR
    VERSION = '1.3.5'
    EMAIL = 'me2sy@outlook.com'
    GITHUB = 'https://github.com/Me2sY/myscrcpy'

    PROJECT_PATH = project_path()

    PATH_STATICS = PROJECT_PATH.joinpath('static')
    PATH_STATICS.mkdir(parents=True, exist_ok=True)
    PATH_STATICS_ICON = PATH_STATICS.joinpath('myscrcpy.ico')
    PATH_STATICS_ICONS = PATH_STATICS / 'icons'

    PATH_LIBS = PROJECT_PATH.joinpath('libs')
    PATH_LIBS.mkdir(parents=True, exist_ok=True)

    PATH_TPS = pathlib.Path.home().joinpath(f".{PROJECT_NAME}").joinpath('tps')
    PATH_TPS.mkdir(parents=True, exist_ok=True)

    PATH_TEMP = pathlib.Path.home().joinpath(f".{PROJECT_NAME}").joinpath('temp')
    PATH_TEMP.mkdir(parents=True, exist_ok=True)

    PATH_CONFIGS = pathlib.Path.home().joinpath(f".{PROJECT_NAME}").joinpath('configs')
    PATH_CONFIGS.mkdir(parents=True, exist_ok=True)

    ROTATION_VERTICAL = 0
    ROTATION_HORIZONTAL = 1

    # dpg
    INT_LEN_WIN_TITLE_HEIGHT = 19
    INT_LEN_WIN_BORDER = 8

    # Scrcpy
    SCRCPY_SERVER_VER = '2.6.1'
    PATH_SCRCPY_TEMP = '/data/local/tmp/scrcpy-server'
    PATH_SCRCPY_SERVER_JAR = PATH_LIBS.joinpath(f"scrcpy-server")
    SCRCPY_SERVER_START_CMD = [
        f'CLASSPATH={PATH_SCRCPY_TEMP}',
        'app_process',
        '/',
        'com.genymobile.scrcpy.Server',
        SCRCPY_SERVER_VER,
        'log_level=info',
        'tunnel_forward=true',
        'send_frame_meta=false',
        'stay_awake=true',
    ]


class CfgHandler:
    """
        Configuration Handler
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
    """
        ADB KeyCode
    """
    HOME = 3
    BACK = 4
    POWER = 26
    MENU = 82
    NOTIFICATION = 83
    APP_SWITCH = 187

    ESCAPE = 111
    SETTINGS = 176

    # Media
    V_UP = 24
    V_DOWN = 25
    V_MUTE = 164

    M_PLAY = 85
    M_NEXT = 87
    M_PREV = 88

    CAMERA = 27
    FOCUS = 80
    ZOOM_IN = 168
    ZOOM_OUT = 169

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

    UP = 19
    DOWN = 20
    LEFT = 21
    RIGHT = 22

    COMMA = 55
    PERIOD = 56

    L_ALT = 57
    L_SHIFT = 59
    R_ALT = 58
    R_SHIFT = 60

    TAB = 61
    SPACE = 62
    ENTER = 66
    BACKSPACE = 67
    GRAVE = 68
    MINUS = 69
    EQUALS = 70
    L_BRACKET = 71
    R_BRACKET = 72
    BACKSLASH = 73
    COLON = 74
    QUOTE = 75
    SLASH = 76
    PLUS = 81

    DELETE = 112
    END = 123
    INSERT = 124

    F1 = 131
    F2 = 132
    F3 = 133
    F4 = 134
    F5 = 135
    F6 = 136
    F7 = 137
    F8 = 138
    F9 = 139
    F10 = 140
    F11 = 141
    F12 = 142


@unique
class UnifiedKey(IntEnum):
    """
        统一按键编码
        实现 Pygame DearPyGui 等按键统一
    """

    SETKEY = -1

    M_LEFT = 0
    M_RIGHT = 1
    M_WHEEL = 2
    M_WHEEL_UP = 3
    M_WHEEL_DOWN = 4

    NP_DIVIDE = 20  # /
    NP_MULTIPLY = 21  # *
    NP_MINUS = 22  # -
    NP_PLUS = 23  # +
    NP_ENTER = 24  # Enter
    NP_PERIOD = 25  # .

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
    F13 = 103
    F14 = 104
    F15 = 105
    F16 = 106
    F17 = 107
    F18 = 108
    F19 = 109
    F20 = 110
    F21 = 111
    F22 = 112
    F23 = 113
    F24 = 114
    F25 = 115

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
    COMMA = 143  # ,
    PERIOD = 144  # .
    SLASH = 145  # /
    COLON = 146  # ;
    QUOTE = 147  # '
    L_BRACKET = 148  # [
    R_BRACKET = 149  # ]
    BACKSLASH = 150  # \
    MINUS = 151  # -
    EQUALS = 152  # =
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

    PAUSE = 164
    VOLUME_MUTE = 165
    VOLUME_DOWN = 166
    VOLUME_UP = 167
    MEDIA_PLAY_PAUSE = 168
    MEDIA_STOP = 169
    MEDIA_PREV_TRACK = 170
    MEDIA_NEXT_TRACK = 171
    APPS = 172

    NUMLOCK = 173
    SCROLLLOCK = 174
    PRINT = 175


UHIDKEYS = {
    # Numpad
    84: "NP_DIVIDE",
    85: "NP_MULTIPLY",
    86: "NP_MINUS",
    87: "NP_PLUS",
    88: "NP_ENTER",
    99: "NP_PERIOD",
    98: "NP_0",
    89: "NP_1",
    90: "NP_2",
    91: "NP_3",
    92: "NP_4",
    93: "NP_5",
    94: "NP_6",
    95: "NP_7",
    96: "NP_8",
    97: "NP_9",

    # Number
    39: "K_0",
    30: "K_1",
    31: "K_2",
    32: "K_3",
    33: "K_4",
    34: "K_5",
    35: "K_6",
    36: "K_7",
    37: "K_8",
    38: "K_9",

    4: "A",
    5: "B",
    6: "C",
    7: "D",
    8: "E",
    9: "F",
    10: "G",
    11: "H",
    12: "I",
    13: "J",
    14: "K",
    15: "L",
    16: "M",
    17: "N",
    18: "O",
    19: "P",
    20: "Q",
    21: "R",
    22: "S",
    23: "T",
    24: "U",
    25: "V",
    26: "W",
    27: "X",
    28: "Y",
    29: "Z",

    58: "F1",
    59: "F2",
    60: "F3",
    61: "F4",
    62: "F5",
    63: "F6",
    64: "F7",
    65: "F8",
    66: "F9",
    67: "F10",
    68: "F11",
    69: "F12",

    40: "RETURN",
    41: "ESCAPE",
    42: "BACKSPACE",
    43: "TAB",
    44: "SPACE",
    45: "MINUS",
    46: "EQUALS",
    47: "L_BRACKET",
    48: "R_BRACKET",
    49: "BACKSLASH",
    51: "COLON",
    52: "QUOTE",
    53: "BACKQUOTE",
    54: "COMMA",
    55: "PERIOD",
    56: "SLASH",

    71: "SCROLLLOCK",
    72: "PAUSE",
    73: "INSERT",
    74: "HOME",
    75: "PAGE_UP",
    76: "DELETE",
    77: "END",
    78: "PAGE_DOWN",
    79: "RIGHT",
    80: "LEFT",
    81: "DOWN",
    82: "UP",

    101: "APPS",

    104: "F14",
    105: "F15",
    106: "F16",
    107: "F17",
    108: "F18",
    109: "F19",
    110: "F20",
    111: "F21",
    112: "F22",
    113: "F23",
    114: "F24",

    127: "VOLUME_MUTE",
    128: "VOLUME_UP",
    129: "VOLUME_DOWN",

    224: "L_CTRL",
    225: "L_SHIFT",
    226: "L_ALT",
    227: "L_WIN",
    228: "R_CTRL",
    229: "R_SHIFT",
    230: "R_ALT",
    231: "R_WIN",

    258: "MEDIA_NEXT_TRACK",
    259: "MEDIA_PREV_TRACK",
    260: "MEDIA_STOP",
    261: "MEDIA_PLAY_PAUSE",
}


class UnifiedKeyMapper:
    """
        Unified Key Mapper
        转换 dpg pg 事件代码 为 统一按键代码
    """

    # 2024-08-21 Me2sY  不再读取固定配置文件，由包进行注入，解决打包及不同平台Code不同问题

    MAPPER_PG2UK = {}
    MAPPER_UK2PG = {}

    MAPPER_DPG2UK = {}
    MAPPER_UK2DPG = {}

    MAPPER_UK2UHID = {
        UnifiedKey[name]: code for code, name in UHIDKEYS.items()
    }

    @classmethod
    @cache
    def dpg2uk(cls, dpg_code: int) -> UnifiedKey:
        """
            dpg key code to union keycode Enum
        :return:
        """
        return cls.MAPPER_DPG2UK.get(int(dpg_code), UnifiedKey(-1))

    @classmethod
    @cache
    def uk2dpg(cls, unified_key: UnifiedKey) -> int:
        """
            unified_key to dpg key
        :param unified_key:
        :return:
        """
        return cls.MAPPER_UK2DPG.get(unified_key, -1)

    @classmethod
    @cache
    def pg2uk(cls, pg_code: int) -> UnifiedKey:
        """
            pygame key code to UnionKey Enum
        :param pg_code:
        :return:
        """
        return cls.MAPPER_PG2UK.get(int(pg_code), UnifiedKey(-1))

    @classmethod
    @cache
    def uk2pg(cls, unified_key: UnifiedKey) -> int:
        """
            unified key code to pygame key code
        :param unified_key:
        :return:
        """
        return cls.MAPPER_UK2PG.get(unified_key, -1)

    @classmethod
    @cache
    def uk2uhidkey(cls, unified_key: UnifiedKey) -> int:
        """
            unified key code to scrcpy scancode
        :param unified_key:
        :return:
        """
        return cls.MAPPER_UK2UHID.get(unified_key, 0)


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

    def fix_height(self, raw_coordinate: 'Coordinate') -> 'Coordinate':
        """
            Width不变，以Width适配raw_coordinate下新坐标系
        """
        return Coordinate(
            self.width,
            round(self.width / raw_coordinate.width * raw_coordinate.height)
        )

    def fix_width(self, raw_coordinate: 'Coordinate') -> 'Coordinate':
        """
            Height不变，以Height适配raw_coordinate下新坐标系
        """
        return Coordinate(
            round(self.height / raw_coordinate.height * raw_coordinate.width),
            self.height
        )


VR_TYPE_RAW = 1
VR_TYPE_OBJ = 0
PICKLE_PROTOCOL = 4


@dataclass
class ValueRecord:
    """
        值记录
    """

    _key: str
    _conditions: dict | None
    _value: Any
    _type: int

    @classmethod
    def encode(cls, key: str, value: Any, conditions: Any = None) -> 'ValueRecord':
        _type, _value = cls.encode_value(value)
        return cls(_key=key, _conditions=conditions, _value=value, _type=_type)

    @classmethod
    def encode_value(cls, value: Any) -> (Any, int):
        """
            格式化值
        """
        _type = VR_TYPE_RAW
        try:
            json.dumps(value)
        except TypeError:
            value = base64.urlsafe_b64encode(pickle.dumps(value, protocol=PICKLE_PROTOCOL)).decode('utf-8')
            _type = VR_TYPE_OBJ

        return _type, value

    @property
    def value(self) -> Any:
        """
            真实值
        """
        if self._type:
            return self._value
        else:
            return pickle.loads(base64.urlsafe_b64decode(self._value.encode('utf-8')))

    def save(self, td):
        """
            格式化保存
        """
        cond = Query()['k'] == self._key
        if self._conditions:
            cond = cond & (Query()['c'] == self._conditions)
        self._type, self._value = self.encode_value(self._value)
        td.upsert(
            document={
                'k': self._key,
                'c': self._conditions,
                'v': self._value,
                't': self._type
            },
            cond=cond
        )


class ValueManager:
    """
        Value Manager
    """

    db = TinyDB(Param.PATH_CONFIGS / f"{Param.PROJECT_NAME}.json", indent=4)
    t_global = db.table('t_global')

    @classmethod
    def get_global(cls, key: str, default_value: Any = None) -> Any:
        """
            获取全局属性
        """
        r = cls.t_global.search(Query()['k'] == key)
        if r:
            return r[0]['v']
        else:
            return default_value

    @classmethod
    def set_global(cls, key: str, value: dict) -> None:
        """
            设置全局属性
        """
        cls.t_global.upsert({'k': key, 'v': value}, Query()['k'] == key)

    @classmethod
    def del_global(cls, key: str) -> None:
        """
            删除全局属性
        """
        cls.t_global.remove(Query()['k'] == key)

    def __init__(self, part_name: str):
        self.part_name = part_name

        self.t_part = self.__class__.db.table(f"t_part_{self.part_name}")

    def set_value(self, key: str, value: Any, conditions: Any = None) -> ValueRecord:
        """
            设置值
        """
        vr = ValueRecord.encode(key, value, conditions)
        vr.save(self.t_part)
        return vr

    def update_value(self, value_record: ValueRecord):
        """
            更新值
        """
        value_record.save(self.t_part)

    def get_records(self, key: str, conditions: Any = None) -> Any:
        """
            获取记录列表
        """
        cond = Query()['k'] == key
        if conditions:
            cond = cond & (Query()['c'] == conditions)

        vrs = []
        for _ in self.t_part.search(cond=cond):
            vrs.append(
                ValueRecord(_key=_['k'], _value=_['v'], _type=_['t'], _conditions=_.get('c', None))
            )

        return vrs

    def get_value(self, key: str, conditions: Any = None, default_value: Any = None):
        """
            获取属性值
        """
        vrs = self.get_records(key, conditions)
        if vrs:
            return vrs[0].value
        else:
            return default_value
