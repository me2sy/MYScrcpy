# -*- coding: utf-8 -*-
"""
    Keys
    ~~~~~~~~~~~~~~~~~~
    按键定义及转换

    Log:
        2025-05-10 3.2.0 Me2sY  增加部分UnifiedKey Value值

        2024-10-26 1.7.0 Me2sY
            1. 新增Gamepad Report desc
            2. 新增Gamepad 键值

        2024-09-28 1.6.4 Me2sY  新增 Move uk

        2024-09-18 1.6.0 Me2sY  修正 ADB 部分功能键映射

        2024-08-24 1.3.7 Me2sY  从utils中分离，重构结构及功能
"""

__author__ = 'Me2sY'
__version__ = '3.2.0'

__all__ = [
    'ADBKeyCode', 'UHIDKeyCode',
    'UHID_MOUSE_REPORT_DESC', 'UHID_KEYBOARD_REPORT_DESC',
    'UHID_GAMEPAD_REPORT_DESC',
    'UnifiedKey', 'UnifiedKeys',
    'KeyMapper'
]

from dataclasses import dataclass
from functools import cache, partial
from typing import NamedTuple, Mapping, Dict
from enum import IntEnum, unique


@unique
class ADBKeyCode(IntEnum):
    """
        ADB KeyCode
        https://www.kancloud.cn/a739292020/xiake/1286379
    """

    UNKNOWN = 0
    SOFT_L = 1
    SOFT_R = 2
    HOME = 3
    BACK = 4
    CALL = 5
    ENDCALL = 6

    KB_0 = 7
    KB_1 = 8
    KB_2 = 9
    KB_3 = 10
    KB_4 = 11
    KB_5 = 12
    KB_6 = 13
    KB_7 = 14
    KB_8 = 15
    KB_9 = 16
    STAR = 17  # *
    POUND = 18  # #

    KB_UP = 19
    KB_DOWN = 20
    KB_LEFT = 21
    KB_RIGHT = 22

    KB_VOLUME_UP = 24
    KB_VOLUME_DOWN = 25

    POWER = 26
    CAMERA = 27

    KB_A = 29
    KB_B = 30
    KB_C = 31
    KB_D = 32
    KB_E = 33
    KB_F = 34
    KB_G = 35
    KB_H = 36
    KB_I = 37
    KB_J = 38
    KB_K = 39
    KB_L = 40
    KB_M = 41
    KB_N = 42
    KB_O = 43
    KB_P = 44
    KB_Q = 45
    KB_R = 46
    KB_S = 47
    KB_T = 48
    KB_U = 49
    KB_V = 50
    KB_W = 51
    KB_X = 52
    KB_Y = 53
    KB_Z = 54

    KB_COMMA = 55
    KB_PERIOD = 56
    KB_ALT_L = 57
    KB_ALT_R = 58
    KB_SHIFT_L = 59
    KB_SHIFT_R = 60
    KB_TAB = 61
    KB_SPACE = 62
    SYM = 63
    EXPLORER = 64
    ENVELOPE = 65
    KB_ENTER = 66
    KB_BACKSPACE = 67
    KB_BACKQUOTE = 68
    KB_MINUS = 69
    KB_EQUALS = 70
    KB_BRACKET_L = 71
    KB_BRACKET_R = 72
    KB_BACKSLASH = 73
    KB_COLON = 74
    KB_QUOTE = 75
    KB_SLASH = 76
    FOCUS = 80
    MENU = 82
    NOTIFICATION = 83
    SEARCH = 84

    KB_MEDIA_PLAY_PAUSE = 85
    KB_MEDIA_STOP = 86
    KB_MEDIA_NEXT_TRACK = 87
    KB_MEDIA_PREV_TRACK = 88
    KB_MEDIA_GO_BACK = 89
    KB_MEDIA_GO_FRONT = 90

    MIC_MUTE = 91
    KB_PAGE_UP = 92
    KB_PAGE_DOWN = 93
    KB_ESCAPE = 111
    KB_DELETE = 112
    KB_CONTROL_L = 113
    KB_CONTROL_R = 114
    KB_CAPSLOCK = 115
    KB_SCROLLLOCK = 116

    KB_PRINTSCREEN = 120
    KB_PAUSE = 121
    KB_HOME = 122
    KB_END = 123
    KB_INSERT = 124

    KB_F1 = 131
    KB_F2 = 132
    KB_F3 = 133
    KB_F4 = 134
    KB_F5 = 135
    KB_F6 = 136
    KB_F7 = 137
    KB_F8 = 138
    KB_F9 = 139
    KB_F10 = 140
    KB_F11 = 141
    KB_F12 = 142

    KB_NUMLOCK = 143
    KB_NP_0 = 144
    KB_NP_1 = 145
    KB_NP_2 = 146
    KB_NP_3 = 147
    KB_NP_4 = 148
    KB_NP_5 = 149
    KB_NP_6 = 150
    KB_NP_7 = 151
    KB_NP_8 = 152
    KB_NP_9 = 153
    KB_NP_DIVIDE = 154
    KB_NP_MULTIPLY = 155
    KB_NP_MINUS = 156
    KB_NP_PLUS = 157
    KB_NP_PERIOD = 159
    KB_NP_ENTER = 160

    KB_VOLUME_MUTE = 164

    CHANNEL_UP = 166
    CHANNEL_DOWN = 167
    ZOOM_IN = 168
    ZOOM_OUT = 169
    TV = 170
    BOOKMARK = 174
    SETTINGS = 176
    TV_POWER = 177
    APP_SWITCH = 187
    LANGUAGE_SWITCH = 204
    CONTACTS = 207
    CALENDAR = 208
    MUSIC = 209
    CALCULATOR = 210
    ASSIST = 219
    BRIGHTNESS_DOWN = 220
    BRIGHTNESS_UP = 221
    SLEEP = 223
    WAKEUP = 224
    PAIRING = 225
    VOICE_ASSIST = 231
    CAMERA_START = 259
    CUT = 277
    COPY = 278
    PASTE = 279
    ALLAPPS = 284


class UHIDKeyCode(IntEnum):
    """
        UHID Keyboard codes
        https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf
        Table 12: Keyboard/Keypad Page
    """

    # Letters
    KB_A = 4
    KB_B = 5
    KB_C = 6
    KB_D = 7
    KB_E = 8
    KB_F = 9
    KB_G = 10
    KB_H = 11
    KB_I = 12
    KB_J = 13
    KB_K = 14
    KB_L = 15
    KB_M = 16
    KB_N = 17
    KB_O = 18
    KB_P = 19
    KB_Q = 20
    KB_R = 21
    KB_S = 22
    KB_T = 23
    KB_U = 24
    KB_V = 25
    KB_W = 26
    KB_X = 27
    KB_Y = 28
    KB_Z = 29

    # Numbers
    KB_1 = 30
    KB_2 = 31
    KB_3 = 32
    KB_4 = 33
    KB_5 = 34
    KB_6 = 35
    KB_7 = 36
    KB_8 = 37
    KB_9 = 38
    KB_0 = 39

    KB_ENTER = 40
    KB_ESCAPE = 41
    KB_BACKSPACE = 42
    KB_TAB = 43
    KB_SPACE = 44
    KB_MINUS = 45
    KB_EQUALS = 46
    KB_BRACKET_L = 47
    KB_BRACKET_R = 48
    KB_BACKSLASH = 49
    KB_COLON = 51
    KB_QUOTE = 52
    KB_BACKQUOTE = 53
    KB_COMMA = 54
    KB_PERIOD = 55
    KB_SLASH = 56
    KB_CAPSLOCK = 57

    KB_F1 = 58
    KB_F2 = 59
    KB_F3 = 60
    KB_F4 = 61
    KB_F5 = 62
    KB_F6 = 63
    KB_F7 = 64
    KB_F8 = 65
    KB_F9 = 66
    KB_F10 = 67
    KB_F11 = 68
    KB_F12 = 69
    KB_PRINTSCREEN = 70
    KB_SCROLLLOCK = 71
    KB_PAUSE = 72
    KB_INSERT = 73
    KB_HOME = 74
    KB_PAGE_UP = 75
    KB_DELETE = 76
    KB_END = 77
    KB_PAGE_DOWN = 78
    KB_RIGHT = 79
    KB_LEFT = 80
    KB_DOWN = 81
    KB_UP = 82
    KB_NUMLOCK = 83
    KB_NP_DIVIDE = 84
    KB_NP_MULTIPLY = 85
    KB_NP_MINUS = 86
    KB_NP_PLUS = 87
    KB_NP_ENTER = 88

    KB_NP_1 = 89
    KB_NP_2 = 90
    KB_NP_3 = 91
    KB_NP_4 = 92
    KB_NP_5 = 93
    KB_NP_6 = 94
    KB_NP_7 = 95
    KB_NP_8 = 96
    KB_NP_9 = 97
    KB_NP_0 = 98
    KB_NP_PERIOD = 99

    KB_MENU = 101

    KB_F13 = 104
    KB_F14 = 105
    KB_F15 = 106
    KB_F16 = 107
    KB_F17 = 108
    KB_F18 = 109
    KB_F19 = 110
    KB_F20 = 111
    KB_F21 = 112
    KB_F22 = 113
    KB_F23 = 114
    KB_F24 = 115

    KB_HELP = 117
    KB_VOLUME_MUTE = 127
    KB_VOLUME_UP = 128
    KB_VOLUME_DOWN = 129

    KB_CONTROL = 224
    KB_CONTROL_L = 224

    KB_SHIFT = 225  # No This One, Use Left Key
    KB_SHIFT_L = 225

    KB_ALT = 226
    KB_ALT_L = 226

    KB_WIN = 227
    KB_WIN_L = 227

    KB_CONTROL_R = 228
    KB_SHIFT_R = 229
    KB_ALT_R = 230
    KB_WIN_R = 231


UHID_MOUSE_REPORT_DESC = bytearray([
    0x05, 0x01,  # Usage Page (Generic Desktop)
    0x09, 0x02,  # Usage (Mouse)
    0xA1, 0x01,  # Collection (Application)
    0x09, 0x01,  # Usage (Pointer)
    0xA1, 0x00,  # Collection (Physical)
    0x05, 0x09,  # Usage Page (Buttons)
    0x19, 0x01,  # Usage Minimum (1)
    0x29, 0x05,  # Usage Maximum (5)
    0x15, 0x00,  # Logical Minimum (0)
    0x25, 0x01,  # Logical Maximum (1)
    0x95, 0x05,  # Report Count (5)
    0x75, 0x01,  # Report Size (1)
    0x81, 0x02,  # Input (Data, Variable, Absolute): 5 buttons bits
    0x95, 0x01,  # Report Count (1)
    0x75, 0x03,  # Report Size (3)
    0x81, 0x01,  # Input (Constant): 3 bits padding
    0x05, 0x01,  # Usage Page (Generic Desktop)
    0x09, 0x30,  # Usage (X)
    0x09, 0x31,  # Usage (Y)
    0x09, 0x38,  # Usage (Wheel)
    0x15, 0x81,  # Local Minimum (-127)
    0x25, 0x7F,  # Local Maximum (127)
    0x75, 0x08,  # Report Size (8)
    0x95, 0x03,  # Report Count (3)
    0x81, 0x06,  # Input (Data, Variable, Relative): 3 position bytes (X, Y, Wheel)
    0xC0,  # End Collection
    0xC0,  # End Collection
])

UHID_KEYBOARD_REPORT_DESC = bytearray([
    0x05, 0x01,  # Usage Page (Generic Desktop)
    0x09, 0x06,  # Usage (Keyboard)
    0xA1, 0x01,  # Collection (Application)
    0x05, 0x07,  # Usage Page (Key Codes)
    0x19, 0xE0,  # Usage Minimum (224)
    0x29, 0xE7,  # Usage Maximum (231)
    0x15, 0x00,  # Logical Minimum (0)
    0x25, 0x01,  # Logical Maximum (1)
    0x75, 0x01,  # Report Size (1)
    0x95, 0x08,  # Report Count (8)
    0x81, 0x02,  # Input (Data, Variable, Absolute): Modifier byte
    0x75, 0x08,  # Report Size (8)
    0x95, 0x01,  # Report Count (1)
    0x81, 0x01,  # Input (Constant): Reserved byte
    0x05, 0x08,  # Usage Page (LEDs)
    0x19, 0x01,  # Usage Minimum (1)
    0x29, 0x05,  # Usage Maximum (5)
    0x75, 0x01,  # Report Size (1)
    0x95, 0x05,  # Report Count (5)
    0x91, 0x02,  # Output (Data, Variable, Absolute): LED report
    0x75, 0x03,  # Report Size (3)
    0x95, 0x01,  # Report Count (1)
    0x91, 0x01,  # Output (Constant): LED report padding
    0x05, 0x07,  # Usage Page (Key Codes)
    0x19, 0x00,  # Usage Minimum (0)
    0x29, 0x65,  # Usage Maximum (101)
    0x15, 0x00,  # Logical Minimum (0)
    0x25, 0x65,  # Logical Maximum(101)
    0x75, 0x08,  # Report Size (8)
    0x95, 0x06,  # Report Count (6)
    0x81, 0x00,  # Input (Data, Array): Keys
    0xC0  # End Collection
])

UHID_GAMEPAD_REPORT_DESC = bytearray([
    0x05, 0x01,  # Usage Page(Generic Desktop)
    0x09, 0x05,  # Usage(Gamepad)
    0xA1, 0x01,  # Collection(Application)
    0xA1, 0x00,  # Collection(Physical)
    0x05, 0x01,  # Usage Page(Generic Desktop)
    0x09, 0x30,  # Usage (X)   Left stick x
    0x09, 0x31,  # Usage (Y)   Left stick y
    0x09, 0x32,  # Usage (Z)   Right stick x
    0x09, 0x35,  # Usage (Rz)  Right stick y
    0x15, 0x00,  # Logical Minimum(0)
    0x27, 0xFF, 0xFF, 0x00, 0x00,  # Logical Maximum(65535) little - endian
    0x75, 0x10,  # Report Size(16)
    0x95, 0x04,  # Report Count (4)
    0x81, 0x02,  # Input (Data, Variable, Absolute): 4 bytes (X, Y, Z, Rz)
    0x05, 0x02,  # Usage Page(Simulation Controls)
    0x09, 0xC5,  # Usage(Brake)
    0x09, 0xC4,  # Usage(Accelerator)
    0x15, 0x00,  # Logical Minimum(0)
    0x26, 0xFF, 0x7F,  # Logical Maximum(32767)
    0x75, 0x10,  # Report Size(16)
    0x95, 0x02,  # Report Count(2)
    0x81, 0x02,  # Input(Data, Variable, Absolute): 2 bytes(L2, R2)
    0x05, 0x09,  # Usage Page(Buttons)
    0x19, 0x01,  # Usage Minimum(1)
    0x29, 0x10,  # Usage Maximum(16)
    0x15, 0x00,  # Logical Minimum(0)
    0x25, 0x01,  # Logical Maximum(1)
    0x95, 0x10,  # Report Count(16)
    0x75, 0x01,  # Report Size(1)
    0x81, 0x02,  # Input(Data, Variable, Absolute): 16 buttons bits
    0x05, 0x01,  # Usage Page(Generic Desktop)
    0x09, 0x39,  # Usage(Hat switch)
    0x15, 0x01,  # Logical Minimum(1)
    0x25, 0x08,  # Logical Maximum(8)
    0x75, 0x04,  # Report Size(4)
    0x95, 0x01,  # Report Count(1)
    0x81, 0x42,  # Input(Data, Variable, Null State): 4 - bit value
    0xC0,  # End Collection
    0xC0,  # End Collection
])

DEVICE_UNKNOWN = 0
DEVICE_KEYBOARD = 1
DEVICE_MOUSE = 2
DEVICE_ANDROID = 3
DEVICE_GAMEPAD = 4


@dataclass
class UnifiedKey:
    """
        统一按键数据类型
    """

    name: str
    code: int
    device: int
    value: int | str | None = None

    def __hash__(self):
        return hash(self.code)


class UnifiedKeys(NamedTuple):
    """
        Unified Keys
    """

    UK_UNKNOWN = UnifiedKey(name='UNKNOWN', code=-1, device=DEVICE_UNKNOWN)

    # Mouse

    UK_MOUSE_L = UnifiedKey(name='MOUSE_L', code=0, device=DEVICE_MOUSE, value='M_LEFT')
    UK_MOUSE_R = UnifiedKey(name='MOUSE_R', code=1, device=DEVICE_MOUSE, value='M_RIGHT')
    UK_MOUSE_WHEEL = UnifiedKey(name='MOUSE_WHEEL', code=2, device=DEVICE_MOUSE, value='M_WHEEL')
    UK_MOUSE_WHEEL_UP = UnifiedKey(name='MOUSE_WHEEL_UP', code=3, device=DEVICE_MOUSE)
    UK_MOUSE_WHEEL_DOWN = UnifiedKey(name='MOUSE_WHEEL_DOWN', code=4, device=DEVICE_MOUSE)

    # For Mouse Move Action
    UK_MOUSE_MOVE = UnifiedKey(name='MOUSE_MOVE', code=5, device=DEVICE_MOUSE)

    # Keyboard

    UK_KB_BACKSPACE = UnifiedKey(name='KB_BACKSPACE', code=8, device=DEVICE_KEYBOARD, value='BACKSPACE')
    UK_KB_TAB = UnifiedKey(name='KB_TAB', code=9, device=DEVICE_KEYBOARD, value='TAB')

    UK_KB_ENTER = UnifiedKey(name='KB_ENTER', code=13, device=DEVICE_KEYBOARD, value='ENTER')

    UK_KB_SHIFT = UnifiedKey(name='KB_SHIFT', code=16, device=DEVICE_KEYBOARD, value='SHIFT')
    UK_KB_CONTROL = UnifiedKey(name='KB_CONTROL', code=17, device=DEVICE_KEYBOARD, value='CTRL')
    UK_KB_ALT = UnifiedKey(name='KB_ALT', code=18, device=DEVICE_KEYBOARD, value='ALT')
    UK_KB_PAUSE = UnifiedKey(name='KB_PAUSE', code=19, device=DEVICE_KEYBOARD)
    UK_KB_CAPSLOCK = UnifiedKey(name='KB_CAPSLOCK', code=20, device=DEVICE_KEYBOARD)

    UK_KB_ESCAPE = UnifiedKey(name='KB_ESCAPE', code=27, device=DEVICE_KEYBOARD, value='ESCAPE')

    UK_KB_SPACE = UnifiedKey(name='KB_SPACE', code=32, device=DEVICE_KEYBOARD, value='SPACE')
    UK_KB_PAGE_UP = UnifiedKey(name='KB_PAGE_UP', code=33, device=DEVICE_KEYBOARD, value='PAGE_UP')
    UK_KB_PAGE_DOWN = UnifiedKey(name='KB_PAGE_DOWN', code=34, device=DEVICE_KEYBOARD, value='PAGE_DOWN')
    UK_KB_END = UnifiedKey(name='KB_END', code=35, device=DEVICE_KEYBOARD, value='END')
    UK_KB_HOME = UnifiedKey(name='KB_HOME', code=36, device=DEVICE_KEYBOARD, value='HOME')
    UK_KB_LEFT = UnifiedKey(name='KB_LEFT', code=37, device=DEVICE_KEYBOARD, value='LEFT')
    UK_KB_UP = UnifiedKey(name='KB_UP', code=38, device=DEVICE_KEYBOARD, value='UP')
    UK_KB_RIGHT = UnifiedKey(name='KB_RIGHT', code=39, device=DEVICE_KEYBOARD, value='RIGHT')
    UK_KB_DOWN = UnifiedKey(name='KB_DOWN', code=40, device=DEVICE_KEYBOARD, value='DOWN')
    UK_KB_SELECT = UnifiedKey(name='KB_SELECT', code=41, device=DEVICE_KEYBOARD)
    UK_KB_PRINT = UnifiedKey(name='KB_PRINT', code=42, device=DEVICE_KEYBOARD)
    UK_KB_EXECUTE = UnifiedKey(name='KB_EXECUTE', code=43, device=DEVICE_KEYBOARD)
    UK_KB_PRINTSCREEN = UnifiedKey(name='KB_PRINTSCREEN', code=44, device=DEVICE_KEYBOARD)
    UK_KB_INSERT = UnifiedKey(name='KB_INSERT', code=45, device=DEVICE_KEYBOARD, value='INSERT')
    UK_KB_DELETE = UnifiedKey(name='KB_DELETE', code=46, device=DEVICE_KEYBOARD, value='DELETE')
    UK_KB_HELP = UnifiedKey(name='KB_HELP', code=47, device=DEVICE_KEYBOARD)

    # Number
    UK_KB_0 = UnifiedKey(name='KB_0', code=48, device=DEVICE_KEYBOARD, value=0)
    UK_KB_1 = UnifiedKey(name='KB_1', code=49, device=DEVICE_KEYBOARD, value=1)
    UK_KB_2 = UnifiedKey(name='KB_2', code=50, device=DEVICE_KEYBOARD, value=2)
    UK_KB_3 = UnifiedKey(name='KB_3', code=51, device=DEVICE_KEYBOARD, value=3)
    UK_KB_4 = UnifiedKey(name='KB_4', code=52, device=DEVICE_KEYBOARD, value=4)
    UK_KB_5 = UnifiedKey(name='KB_5', code=53, device=DEVICE_KEYBOARD, value=5)
    UK_KB_6 = UnifiedKey(name='KB_6', code=54, device=DEVICE_KEYBOARD, value=6)
    UK_KB_7 = UnifiedKey(name='KB_7', code=55, device=DEVICE_KEYBOARD, value=7)
    UK_KB_8 = UnifiedKey(name='KB_8', code=56, device=DEVICE_KEYBOARD, value=8)
    UK_KB_9 = UnifiedKey(name='KB_9', code=57, device=DEVICE_KEYBOARD, value=9)

    # Letters
    UK_KB_A = UnifiedKey(name='KB_A', code=65, device=DEVICE_KEYBOARD, value='A')
    UK_KB_B = UnifiedKey(name='KB_B', code=66, device=DEVICE_KEYBOARD, value='B')
    UK_KB_C = UnifiedKey(name='KB_C', code=67, device=DEVICE_KEYBOARD, value='C')
    UK_KB_D = UnifiedKey(name='KB_D', code=68, device=DEVICE_KEYBOARD, value='D')
    UK_KB_E = UnifiedKey(name='KB_E', code=69, device=DEVICE_KEYBOARD, value='E')
    UK_KB_F = UnifiedKey(name='KB_F', code=70, device=DEVICE_KEYBOARD, value='F')
    UK_KB_G = UnifiedKey(name='KB_G', code=71, device=DEVICE_KEYBOARD, value='G')
    UK_KB_H = UnifiedKey(name='KB_H', code=72, device=DEVICE_KEYBOARD, value='H')
    UK_KB_I = UnifiedKey(name='KB_I', code=73, device=DEVICE_KEYBOARD, value='I')
    UK_KB_J = UnifiedKey(name='KB_J', code=74, device=DEVICE_KEYBOARD, value='J')
    UK_KB_K = UnifiedKey(name='KB_K', code=75, device=DEVICE_KEYBOARD, value='K')
    UK_KB_L = UnifiedKey(name='KB_L', code=76, device=DEVICE_KEYBOARD, value='L')
    UK_KB_M = UnifiedKey(name='KB_M', code=77, device=DEVICE_KEYBOARD, value='M')
    UK_KB_N = UnifiedKey(name='KB_N', code=78, device=DEVICE_KEYBOARD, value='N')
    UK_KB_O = UnifiedKey(name='KB_O', code=79, device=DEVICE_KEYBOARD, value='O')
    UK_KB_P = UnifiedKey(name='KB_P', code=80, device=DEVICE_KEYBOARD, value='P')
    UK_KB_Q = UnifiedKey(name='KB_Q', code=81, device=DEVICE_KEYBOARD, value='Q')
    UK_KB_R = UnifiedKey(name='KB_R', code=82, device=DEVICE_KEYBOARD, value='R')
    UK_KB_S = UnifiedKey(name='KB_S', code=83, device=DEVICE_KEYBOARD, value='S')
    UK_KB_T = UnifiedKey(name='KB_T', code=84, device=DEVICE_KEYBOARD, value='T')
    UK_KB_U = UnifiedKey(name='KB_U', code=85, device=DEVICE_KEYBOARD, value='U')
    UK_KB_V = UnifiedKey(name='KB_V', code=86, device=DEVICE_KEYBOARD, value='V')
    UK_KB_W = UnifiedKey(name='KB_W', code=87, device=DEVICE_KEYBOARD, value='W')
    UK_KB_X = UnifiedKey(name='KB_X', code=88, device=DEVICE_KEYBOARD, value='X')
    UK_KB_Y = UnifiedKey(name='KB_Y', code=89, device=DEVICE_KEYBOARD, value='Y')
    UK_KB_Z = UnifiedKey(name='KB_Z', code=90, device=DEVICE_KEYBOARD, value='Z')
    UK_KB_WIN_L = UnifiedKey(name='KB_WIN_L', code=91, device=DEVICE_KEYBOARD)
    UK_KB_WIN_R = UnifiedKey(name='KB_WIN_R', code=92, device=DEVICE_KEYBOARD)
    UK_KB_MENU = UnifiedKey(name='KB_MENU', code=93, device=DEVICE_KEYBOARD)

    # Numpad
    UK_KB_NP_0 = UnifiedKey(name='KB_NP_0', code=96, device=DEVICE_KEYBOARD, value=0)
    UK_KB_NP_1 = UnifiedKey(name='KB_NP_1', code=97, device=DEVICE_KEYBOARD, value=1)
    UK_KB_NP_2 = UnifiedKey(name='KB_NP_2', code=98, device=DEVICE_KEYBOARD, value=2)
    UK_KB_NP_3 = UnifiedKey(name='KB_NP_3', code=99, device=DEVICE_KEYBOARD, value=3)
    UK_KB_NP_4 = UnifiedKey(name='KB_NP_4', code=100, device=DEVICE_KEYBOARD, value=4)
    UK_KB_NP_5 = UnifiedKey(name='KB_NP_5', code=101, device=DEVICE_KEYBOARD, value=5)
    UK_KB_NP_6 = UnifiedKey(name='KB_NP_6', code=102, device=DEVICE_KEYBOARD, value=6)
    UK_KB_NP_7 = UnifiedKey(name='KB_NP_7', code=103, device=DEVICE_KEYBOARD, value=7)
    UK_KB_NP_8 = UnifiedKey(name='KB_NP_8', code=104, device=DEVICE_KEYBOARD, value=8)
    UK_KB_NP_9 = UnifiedKey(name='KB_NP_9', code=105, device=DEVICE_KEYBOARD, value=9)

    UK_KB_NP_MULTIPLY = UnifiedKey(name='KB_NP_MULTIPLY', code=106, device=DEVICE_KEYBOARD, value='*')  # *
    UK_KB_NP_PLUS = UnifiedKey(name='KB_NP_PLUS', code=107, device=DEVICE_KEYBOARD, value='+')  # +
    UK_KB_NP_ENTER = UnifiedKey(name='KB_NP_ENTER', code=108, device=DEVICE_KEYBOARD)
    UK_KB_NP_MINUS = UnifiedKey(name='KB_NP_MINUS', code=109, device=DEVICE_KEYBOARD, value='-')  # -
    UK_KB_NP_PERIOD = UnifiedKey(name='KB_NP_PERIOD', code=110, device=DEVICE_KEYBOARD, value='.')  # .
    UK_KB_NP_DIVIDE = UnifiedKey(name='KB_NP_DIVIDE', code=111, device=DEVICE_KEYBOARD, value='/')  # /

    # F1 - F24
    UK_KB_F1 = UnifiedKey(name='KB_F1', code=112, device=DEVICE_KEYBOARD, value='F1')
    UK_KB_F2 = UnifiedKey(name='KB_F2', code=113, device=DEVICE_KEYBOARD, value='F2')
    UK_KB_F3 = UnifiedKey(name='KB_F3', code=114, device=DEVICE_KEYBOARD, value='F3')
    UK_KB_F4 = UnifiedKey(name='KB_F4', code=115, device=DEVICE_KEYBOARD, value='F4')
    UK_KB_F5 = UnifiedKey(name='KB_F5', code=116, device=DEVICE_KEYBOARD, value='F5')
    UK_KB_F6 = UnifiedKey(name='KB_F6', code=117, device=DEVICE_KEYBOARD, value='F6')
    UK_KB_F7 = UnifiedKey(name='KB_F7', code=118, device=DEVICE_KEYBOARD, value='F7')
    UK_KB_F8 = UnifiedKey(name='KB_F8', code=119, device=DEVICE_KEYBOARD, value='F8')
    UK_KB_F9 = UnifiedKey(name='KB_F9', code=120, device=DEVICE_KEYBOARD, value='F9')
    UK_KB_F10 = UnifiedKey(name='KB_F10', code=121, device=DEVICE_KEYBOARD, value='F10')
    UK_KB_F11 = UnifiedKey(name='KB_F11', code=122, device=DEVICE_KEYBOARD, value='F11')
    UK_KB_F12 = UnifiedKey(name='KB_F12', code=123, device=DEVICE_KEYBOARD, value='F12')
    UK_KB_F13 = UnifiedKey(name='KB_F13', code=124, device=DEVICE_KEYBOARD, value='F13')
    UK_KB_F14 = UnifiedKey(name='KB_F14', code=125, device=DEVICE_KEYBOARD, value='F14')
    UK_KB_F15 = UnifiedKey(name='KB_F15', code=126, device=DEVICE_KEYBOARD, value='F15')
    UK_KB_F16 = UnifiedKey(name='KB_F16', code=127, device=DEVICE_KEYBOARD, value='F16')
    UK_KB_F17 = UnifiedKey(name='KB_F17', code=128, device=DEVICE_KEYBOARD, value='F17')
    UK_KB_F18 = UnifiedKey(name='KB_F18', code=129, device=DEVICE_KEYBOARD, value='F18')
    UK_KB_F19 = UnifiedKey(name='KB_F19', code=130, device=DEVICE_KEYBOARD, value='F19')
    UK_KB_F20 = UnifiedKey(name='KB_F20', code=131, device=DEVICE_KEYBOARD, value='F20')
    UK_KB_F21 = UnifiedKey(name='KB_F21', code=132, device=DEVICE_KEYBOARD, value='F21')
    UK_KB_F22 = UnifiedKey(name='KB_F22', code=133, device=DEVICE_KEYBOARD, value='F22')
    UK_KB_F23 = UnifiedKey(name='KB_F23', code=134, device=DEVICE_KEYBOARD, value='F23')
    UK_KB_F24 = UnifiedKey(name='KB_F24', code=135, device=DEVICE_KEYBOARD, value='F24')
    UK_KB_F25 = UnifiedKey(name='KB_F25', code=136, device=DEVICE_KEYBOARD, value='F25')

    UK_KB_NUMLOCK = UnifiedKey(name='KB_NUMLOCK', code=144, device=DEVICE_KEYBOARD)
    UK_KB_SCROLLLOCK = UnifiedKey(name='KB_SCROLLLOCK', code=145, device=DEVICE_KEYBOARD)

    UK_KB_SHIFT_L = UnifiedKey(name='KB_SHIFT_L', code=160, device=DEVICE_KEYBOARD, value='SHIFT_L')
    UK_KB_SHIFT_R = UnifiedKey(name='KB_SHIFT_R', code=161, device=DEVICE_KEYBOARD, value='SHIFT_R')
    UK_KB_CONTROL_L = UnifiedKey(name='KB_CONTROL_L', code=162, device=DEVICE_KEYBOARD, value='CTRL_L')
    UK_KB_CONTROL_R = UnifiedKey(name='KB_CONTROL_R', code=163, device=DEVICE_KEYBOARD, value='CTRL_R')
    UK_KB_ALT_L = UnifiedKey(name='KB_ALT_L', code=164, device=DEVICE_KEYBOARD, value='ALT_L')
    UK_KB_ALT_R = UnifiedKey(name='KB_ALT_R', code=165, device=DEVICE_KEYBOARD, value='ALT_R')

    UK_KB_MENU_L = UnifiedKey(name='KB_MENU_L', code=166, device=DEVICE_KEYBOARD)
    UK_KB_MENU_R = UnifiedKey(name='KB_MENU_R', code=167, device=DEVICE_KEYBOARD)

    UK_KB_VOLUME_MUTE = UnifiedKey(name='KB_VOLUME_MUTE', code=173, device=DEVICE_KEYBOARD)
    UK_KB_VOLUME_DOWN = UnifiedKey(name='KB_VOLUME_DOWN', code=174, device=DEVICE_KEYBOARD)
    UK_KB_VOLUME_UP = UnifiedKey(name='KB_VOLUME_UP', code=175, device=DEVICE_KEYBOARD)

    UK_KB_COLON = UnifiedKey(name='KB_COLON', code=186, device=DEVICE_KEYBOARD, value=';')
    UK_KB_EQUALS = UnifiedKey(name='KB_EQUALS', code=187, device=DEVICE_KEYBOARD, value='=')
    UK_KB_COMMA = UnifiedKey(name='KB_COMMA', code=188, device=DEVICE_KEYBOARD, value=',')
    UK_KB_MINUS = UnifiedKey(name='KB_MINUS', code=189, device=DEVICE_KEYBOARD, value='-')
    UK_KB_PERIOD = UnifiedKey(name='KB_PERIOD', code=190, device=DEVICE_KEYBOARD, value='.')
    UK_KB_SLASH = UnifiedKey(name='KB_SLASH', code=191, device=DEVICE_KEYBOARD, value='/')
    UK_KB_BACKQUOTE = UnifiedKey(name='KB_BACKQUOTE', code=192, device=DEVICE_KEYBOARD, value='`')
    UK_KB_BRACKET_L = UnifiedKey(name='KB_BRACKET_L', code=219, device=DEVICE_KEYBOARD, value='[')
    UK_KB_BACKSLASH = UnifiedKey(name='KB_BACKSLASH', code=220, device=DEVICE_KEYBOARD, value='\\')
    UK_KB_BRACKET_R = UnifiedKey(name='KB_BRACKET_R', code=221, device=DEVICE_KEYBOARD, value=']')
    UK_KB_QUOTE = UnifiedKey(name='KB_QUOTE', code=222, device=DEVICE_KEYBOARD, value="'")

    UK_KB_MEDIA_PLAY_PAUSE = UnifiedKey(name='KB_MEDIA_PLAY_PAUSE', code=300, device=DEVICE_KEYBOARD)
    UK_KB_MEDIA_STOP = UnifiedKey(name='KB_MEDIA_STOP', code=301, device=DEVICE_KEYBOARD)
    UK_KB_MEDIA_PREV_TRACK = UnifiedKey(name='KB_MEDIA_PREV_TRACK', code=302, device=DEVICE_KEYBOARD)
    UK_KB_MEDIA_NEXT_TRACK = UnifiedKey(name='KB_MEDIA_NEXT_TRACK', code=303, device=DEVICE_KEYBOARD)

    # Android

    UK_A_SOFT_L = UnifiedKey(name='A_SOFT_L', code=401, device=DEVICE_ANDROID)
    UK_A_SOFT_R = UnifiedKey(name='A_SOFT_R', code=402, device=DEVICE_ANDROID)
    UK_A_HOME = UnifiedKey(name='A_HOME', code=403, device=DEVICE_ANDROID)
    UK_A_BACK = UnifiedKey(name='A_BACK', code=404, device=DEVICE_ANDROID)
    UK_A_CALL = UnifiedKey(name='A_CALL', code=405, device=DEVICE_ANDROID)
    UK_A_ENDCALL = UnifiedKey(name='A_ENDCALL', code=406, device=DEVICE_ANDROID)

    UK_A_STAR = UnifiedKey(name='A_STAR', code=417, device=DEVICE_ANDROID, value='*')
    UK_A_POUND = UnifiedKey(name='A_POUND', code=418, device=DEVICE_ANDROID, value='#')

    UK_A_POWER = UnifiedKey(name='A_POWER', code=426, device=DEVICE_ANDROID)
    UK_A_CAMERA = UnifiedKey(name='A_CAMERA', code=427, device=DEVICE_ANDROID)

    UK_A_SYM = UnifiedKey(name='A_SYM', code=463, device=DEVICE_ANDROID)
    UK_A_EXPLORER = UnifiedKey(name='A_EXPLORER', code=464, device=DEVICE_ANDROID)
    UK_A_ENVELOPE = UnifiedKey(name='A_ENVELOPE', code=465, device=DEVICE_ANDROID)

    UK_A_FOCUS = UnifiedKey(name='A_FOCUS', code=480, device=DEVICE_ANDROID)  # Camera Focus

    UK_A_MENU = UnifiedKey(name='A_MENU', code=482, device=DEVICE_ANDROID)
    UK_A_NOTIFICATION = UnifiedKey(name='A_NOTIFICATION', code=483, device=DEVICE_ANDROID)
    UK_A_SEARCH = UnifiedKey(name='A_SEARCH', code=484, device=DEVICE_ANDROID)

    UK_A_CHANNEL_UP = UnifiedKey(name='A_CHANNEL_UP', code=566, device=DEVICE_ANDROID)
    UK_A_CHANNEL_DOWN = UnifiedKey(name='A_CHANNEL_DOWN', code=567, device=DEVICE_ANDROID)
    UK_A_ZOOM_IN = UnifiedKey(name='A_ZOOM_IN', code=568, device=DEVICE_ANDROID)
    UK_A_ZOOM_OUT = UnifiedKey(name='A_ZOOM_OUT', code=569, device=DEVICE_ANDROID)
    UK_A_TV = UnifiedKey(name='A_TV', code=570, device=DEVICE_ANDROID)
    UK_A_BOOKMARK = UnifiedKey(name='A_BOOKMARK', code=574, device=DEVICE_ANDROID)

    UK_A_SETTINGS = UnifiedKey(name='A_SETTINGS', code=576, device=DEVICE_ANDROID)
    UK_A_TV_POWER = UnifiedKey(name='A_TV_POWER', code=577, device=DEVICE_ANDROID)

    UK_A_APP_SWITCH = UnifiedKey(name='A_APP_SWITCH', code=587, device=DEVICE_ANDROID)

    UK_A_LANGUAGE_SWITCH = UnifiedKey(name='A_LANGUAGE_SWITCH', code=604, device=DEVICE_ANDROID)

    UK_A_CONTACTS = UnifiedKey(name='A_CONTACTS', code=607, device=DEVICE_ANDROID)
    UK_A_CALENDAR = UnifiedKey(name='A_CALENDAR', code=608, device=DEVICE_ANDROID)
    UK_A_MUSIC = UnifiedKey(name='A_MUSIC', code=609, device=DEVICE_ANDROID)
    UK_A_CALCULATOR = UnifiedKey(name='A_CALCULATOR', code=610, device=DEVICE_ANDROID)

    UK_A_ASSIST = UnifiedKey(name='A_ASSIST', code=619, device=DEVICE_ANDROID)
    UK_A_BRIGHTNESS_DOWN = UnifiedKey(name='A_BRIGHTNESS_DOWN', code=620, device=DEVICE_ANDROID)
    UK_A_BRIGHTNESS_UP = UnifiedKey(name='A_BRIGHTNESS_UP', code=621, device=DEVICE_ANDROID)

    UK_A_SLEEP = UnifiedKey(name='A_SLEEP', code=623, device=DEVICE_ANDROID)
    UK_A_WAKEUP = UnifiedKey(name='A_WAKEUP', code=624, device=DEVICE_ANDROID)
    UK_A_PAIRING = UnifiedKey(name='A_PAIRING', code=625, device=DEVICE_ANDROID)

    UK_A_VOICE_ASSIST = UnifiedKey(name='A_VOICE_ASSIST', code=631, device=DEVICE_ANDROID)

    UK_A_HELP = UnifiedKey(name='A_HELP', code=659, device=DEVICE_ANDROID)

    UK_A_CUT = UnifiedKey(name='A_CUT', code=677, device=DEVICE_ANDROID)
    UK_A_COPY = UnifiedKey(name='A_COPY', code=678, device=DEVICE_ANDROID)
    UK_A_PASTE = UnifiedKey(name='A_PASTE', code=679, device=DEVICE_ANDROID)
    UK_A_ALLAPPS = UnifiedKey(name='A_ALLAPPS', code=684, device=DEVICE_ANDROID)

    UK_GP_S = UnifiedKey(name='GP_S', code=700, device=DEVICE_GAMEPAD, value=1 << 0)
    UK_GP_E = UnifiedKey(name='GP_E', code=701, device=DEVICE_GAMEPAD, value=1 << 1)
    UK_GP_W = UnifiedKey(name='GP_W', code=702, device=DEVICE_GAMEPAD, value=1 << 3)
    UK_GP_N = UnifiedKey(name='GP_N', code=703, device=DEVICE_GAMEPAD, value=1 << 4)
    UK_GP_L1 = UnifiedKey(name='GP_L1', code=704, device=DEVICE_GAMEPAD, value=1 << 6)
    UK_GP_R1 = UnifiedKey(name='GP_R1', code=705, device=DEVICE_GAMEPAD, value=1 << 7)
    UK_GP_BACK = UnifiedKey(name='GP_BACK', code=706, device=DEVICE_GAMEPAD, value=1 << 10)
    UK_GP_START = UnifiedKey(name='GP_START', code=707, device=DEVICE_GAMEPAD, value=1 << 11)
    UK_GP_GUIDE = UnifiedKey(name='GP_GUIDE', code=708, device=DEVICE_GAMEPAD, value=1 << 12)
    UK_GP_LS = UnifiedKey(name='GP_LS', code=709, device=DEVICE_GAMEPAD, value=1 << 13)
    UK_GP_RS = UnifiedKey(name='GP_RS', code=710, device=DEVICE_GAMEPAD, value=1 << 14)

    UK_GP_DP_U = UnifiedKey(name='GP_DP_U', code=720, device=DEVICE_GAMEPAD, value=1)
    UK_GP_DP_D = UnifiedKey(name='GP_DP_D', code=721, device=DEVICE_GAMEPAD, value=5)
    UK_GP_DP_L = UnifiedKey(name='GP_DP_L', code=722, device=DEVICE_GAMEPAD, value=7)
    UK_GP_DP_R = UnifiedKey(name='GP_DP_R', code=723, device=DEVICE_GAMEPAD, value=3)

    UK_GP_DP_UL = UnifiedKey(name='GP_DP_UL', code=724, device=DEVICE_GAMEPAD, value=8)
    UK_GP_DP_UR = UnifiedKey(name='GP_DP_UR', code=725, device=DEVICE_GAMEPAD, value=2)
    UK_GP_DP_DL = UnifiedKey(name='GP_DP_DL', code=726, device=DEVICE_GAMEPAD, value=6)
    UK_GP_DP_DR = UnifiedKey(name='GP_DP_DR', code=727, device=DEVICE_GAMEPAD, value=4)

    @classmethod
    def filter_name(cls, name: str) -> UnifiedKey | None:
        """
            通过名称获取 UnifiedKey
        :param name:
        :return:
        """
        name = name.upper()

        for _ in ['', 'KB_', 'MOUSE_', 'A_']:
            uk = cls.__dict__.get(f"UK_{_}{name}", None)
            if uk:
                return uk
        return None

    @classmethod
    def get_by_code(cls, code: int) -> UnifiedKey:
        """
            通过 Code 获取 UnifiedKey
        :param code:
        :return:
        """
        for k, _ in cls.__dict__.items():
            if k.startswith('UK_'):
                if _.code == code:
                    return _

        return cls.UK_UNKNOWN

    @classmethod
    def get_keyboard_keys(cls) -> Dict[str, UnifiedKey]:
        """
            获取按键表
        :return:
        """
        keys = {}
        for k, _ in cls.__dict__.items():
            if k.startswith('UK_KB'):
                keys[_.name] = _
        return keys


class KeyMapper:
    """
        按键映射
    """

    @classmethod
    def register(cls, key_type_name: str, key_mapper: Mapping[str | int, UnifiedKey]):
        """
            注册键值对
        :param key_type_name:
        :param key_mapper:
        :return:
        """

        _u2t = {}
        _t2u = {}

        # Create Mapping
        for to_code, _uk in key_mapper.items():
            _u2t[_uk.code] = to_code
            _t2u[to_code] = _uk

        setattr(cls, f"_km_uk2{key_type_name}", _u2t)
        setattr(cls, f"_km_{key_type_name}2uk", _t2u)

        @cache
        def f_t2u(_cls, t_code: int | str) -> UnifiedKey:
            """
                通过键值获取UK
            :param _cls:
            :param t_code:
            :return:
            """
            try:
                return getattr(_cls, f"_km_{key_type_name}2uk")[t_code]
            except AttributeError:
                raise RuntimeError(f"Setup {key_type_name} Key Mapper First")
            except KeyError:
                return UnifiedKeys.UK_UNKNOWN

        setattr(cls, f"{key_type_name}2uk", partial(f_t2u, cls))

        @cache
        def f_u2t(_cls, _uk: UnifiedKey) -> str | int | None:
            """
                通过UK获取指定键值
            :param _cls:
            :param _uk:
            :return:
            """
            if _uk is None:
                return None
            try:
                return getattr(_cls, f"_km_uk2{key_type_name}")[_uk.code]
            except AttributeError:
                raise RuntimeError(f"Setup {key_type_name} Key Mapper First")
            except KeyError:
                return None

        setattr(cls, f"uk2{key_type_name}", partial(f_u2t, cls))


def register_adb_code():
    """
        Register ADB Codes
    :return:
    """
    register_dict = {}

    for key in ADBKeyCode:
        uk = UnifiedKeys.filter_name(key.name)
        if uk:
            register_dict[key.value] = uk

    # ADB 修正
    register_dict[ADBKeyCode.KB_CONTROL_L] = UnifiedKeys.UK_KB_CONTROL
    register_dict[ADBKeyCode.KB_SHIFT_L] = UnifiedKeys.UK_KB_SHIFT
    register_dict[ADBKeyCode.KB_ALT_L] = UnifiedKeys.UK_KB_ALT

    KeyMapper.register('adb', register_dict)


register_adb_code()


def register_uhid_code():
    """
        Register UHID Codes
    :return:
    """
    register_dict = {}

    for key in UHIDKeyCode:
        uk = UnifiedKeys.filter_name(key.name)
        if uk:
            register_dict[key.value] = uk

    KeyMapper.register('uhid', register_dict)


register_uhid_code()

if __name__ == '__main__':
    print(UnifiedKeys.get_by_code(50))
