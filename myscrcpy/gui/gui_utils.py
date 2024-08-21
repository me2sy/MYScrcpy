# -*- coding: utf-8 -*-
"""
    Gui Utils
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-21 1.3.5 Me2sY
            创建，新增按键映射注入功能，解决不同平台下Code可能不一致问题
"""

__author__ = 'Me2sY'
__version__ = '1.3.5'

__all__ = [
    'inject_dpg_key_mapper', 'inject_pg_key_mapper'
]


from loguru import logger

import dearpygui.dearpygui as dpg
import pygame


from myscrcpy.utils import UnifiedKey, UnifiedKeyMapper


def inject_dpg_key_mapper():
    """
        注入DPG键盘映射表
    :return:
    """

    # Number
    dpg_mapper = {
        str(_): f"K_{_}" for _ in range(10)
    }

    # Numpad
    dpg_mapper.update({
        f"NUMPAD{_}": f"NP_{_}" for _ in range(10)
    })

    # Function Keys
    dpg_mapper.update({
        'TILDE': 'BACKQUOTE',
        'SHIFT': 'L_SHIFT',
        'CONTROL': 'L_CTRL',
        'ALT': 'L_ALT',
        'LSHIFT': 'L_SHIFT',
        'LCONTROL': 'L_CTRL',
        'LALT': 'L_ALT',
        'RSHIFT': 'R_SHIFT',
        'RCONTROL': 'R_CTRL',
        'RALT': 'R_ALT',
        'PLUS': 'EQUALS',
        'OPEN_BRACE': 'L_BRACKET',
        'CLOSE_BRACE': 'R_BRACKET',
        'BACK': 'BACKSPACE',
        'SPACEBAR': 'SPACE',
        'DIVIDE': 'NP_DIVIDE',
        'MULTIPLY': 'NP_MULTIPLY',
        'SUBTRACT': 'NP_MINUS',
        'ADD': 'NP_PLUS',
        'DECIMAL': 'NP_PERIOD',
        'PRIOR': 'PAGE_UP',
        'NEXT': 'PAGE_DOWN',
        'LWIN': 'L_WIN',
        'RWIN': 'R_WIN',
    })

    for key, code in dpg.__dict__.items():
        if key.startswith('mvKey_'):

            _key = key[6:].upper()

            try:
                uk = UnifiedKey[dpg_mapper.get(_key, _key)]
                UnifiedKeyMapper.MAPPER_DPG2UK[code] = uk
                UnifiedKeyMapper.MAPPER_UK2DPG[uk] = code
            except KeyError:
                ...

    logger.success(f"DearPyGui Inject {len(UnifiedKeyMapper.MAPPER_DPG2UK)} Keys.")


def inject_pg_key_mapper():
    """
        注入 Pygame 键盘映射
    :return:
    """
    dp_mapper = {
       f"{_}": f"K_{_}" for _ in range(10)
    }

    dp_mapper.update({
         f"KP_{_}": f"NP_{_}" for _ in range(10)
    })

    dp_mapper.update({
        "LSHIFT": "L_SHIFT",
        "LCTRL": "L_CTRL",
        "LALT": "L_ALT",
        "LGUI": "L_WIN",
        "RSHIFT": "R_SHIFT",
        "RCTRL": "R_CTRL",
        "RALT": "R_ALT",
        "RGUI": "R_WIN",

        "LEFTBRACKET": "L_BRACKET",
        "RIGHTBRACKET": "R_BRACKET",
        "SEMICOLON": "COLON",

        "KP_DIVIDE": "NP_DIVIDE",
        "KP_MULTIPLY": "NP_MULTIPLY",
        "KP_MINUS": "NP_MINUS",
        "KP_PLUS": "NP_PLUS",
        "KP_ENTER": "NP_ENTER",
        "KP_PERIOD": "NP_PERIOD",

        "PAGEUP": "PAGE_UP",
        "PAGEDOWN": "PAGE_DOWN",
    })

    for key, code in pygame.__dict__.items():
        if key.startswith('K_'):
            _key = key[2:].upper()

            try:
                uk = UnifiedKey[dp_mapper.get(_key, _key)]
                UnifiedKeyMapper.MAPPER_PG2UK[code] = uk
                UnifiedKeyMapper.MAPPER_UK2PG[uk] = code

            except KeyError:
                ...

    mouse = {
        UnifiedKey.M_LEFT: pygame.BUTTON_LEFT,
        UnifiedKey.M_RIGHT: pygame.BUTTON_RIGHT,
        UnifiedKey.M_WHEEL: pygame.BUTTON_MIDDLE,
        UnifiedKey.M_WHEEL_UP: pygame.BUTTON_WHEELUP,
        UnifiedKey.M_WHEEL_DOWN: pygame.BUTTON_WHEELDOWN,
    }

    for uk, code in mouse.items():
        UnifiedKeyMapper.MAPPER_PG2UK[code] = uk
        UnifiedKeyMapper.MAPPER_UK2DPG[uk] = code

    logger.success(f"Pygame Inject {len(UnifiedKeyMapper.MAPPER_PG2UK)} Keys.")
