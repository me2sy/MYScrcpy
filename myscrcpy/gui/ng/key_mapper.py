# -*- coding: utf-8 -*-
"""
    For Nicegui Keymapper
    ~~~~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-22 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = ['ng2uk']


from myscrcpy.utils import UnifiedKey

# number
key_mapper = {
    f"{_}": UnifiedKey[f"K_{_}"] for _ in range(10)
}

# keys
key_mapper.update({

    'ENTER': UnifiedKey.RETURN,

    'SHIFTLEFT': UnifiedKey.L_SHIFT,
    'SHIFTRIGHT': UnifiedKey.R_SHIFT,

    'CONTROLLEFT': UnifiedKey.L_CTRL,
    'CONTROLRIGHT': UnifiedKey.R_CTRL,

    'ALTLEFT': UnifiedKey.L_ALT,
    'ALTRIGHT': UnifiedKey.R_ALT,

    'EQUAL': UnifiedKey.EQUALS,
    'SEMICOLON': UnifiedKey.COLON,

    "BRACKETLEFT": UnifiedKey.L_BRACKET,
    "BRACKETRIGHT": UnifiedKey.R_BRACKET,
    'ARROWUP': UnifiedKey.UP,
    'ARROWDOWN': UnifiedKey.DOWN,
    'ARROWLEFT': UnifiedKey.LEFT,
    'ARROWRIGHT': UnifiedKey.RIGHT,
    'PAGEUP': UnifiedKey.PAGE_UP,
    'PAGEDOWN': UnifiedKey.PAGE_DOWN,

    'NP_ADD': UnifiedKey.NP_PLUS,
    'NP_SUBTRACT': UnifiedKey.NP_MINUS,
    'NP_DECIMAL': UnifiedKey.NP_PERIOD,

})


def ng2uk(key_code: str) -> UnifiedKey:
    """
        Convert Nicegui keycode to UnifiedKey
    :param key_code:
    :return:
    """

    key_code = key_code.upper()
    if key_code.startswith('KEY'):
        key_code = key_code[3:]

    elif key_code.startswith('NUMPAD'):
        key_code = 'NP_' + key_code[6:]

    elif key_code.startswith('DIGIT'):
        key_code = 'K_' + key_code[5:]

    try:
        return UnifiedKey[key_code.upper()]
    except:
        try:
            return key_mapper[key_code.upper()]
        except KeyError:
            return UnifiedKey.SETKEY
