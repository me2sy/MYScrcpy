# -*- coding: utf-8 -*-
"""
    For Nicegui Keymapper
    ~~~~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-30 0.1.1 Me2sY  适配新架构

        2024-08-22 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '0.1.1'

__all__ = ['ng2uk']


from myscrcpy.utils import UnifiedKeys, UnifiedKey


key_mapper = {}

key_mapper.update({
    'ENTER': UnifiedKeys.UK_KB_ENTER,

    'SHIFTLEFT': UnifiedKeys.UK_KB_SHIFT_L,
    'SHIFTRIGHT': UnifiedKeys.UK_KB_SHIFT_R,

    'CONTROLLEFT': UnifiedKeys.UK_KB_CONTROL_L,
    'CONTROLRIGHT': UnifiedKeys.UK_KB_CONTROL_R,

    'ALTLEFT': UnifiedKeys.UK_KB_ALT_L,
    'ALTRIGHT': UnifiedKeys.UK_KB_ALT_R,

    'EQUAL': UnifiedKeys.UK_KB_EQUALS,
    'SEMICOLON': UnifiedKeys.UK_KB_COLON,

    "BRACKETLEFT": UnifiedKeys.UK_KB_BRACKET_L,
    "BRACKETRIGHT": UnifiedKeys.UK_KB_BRACKET_R,
    'ARROWUP': UnifiedKeys.UK_KB_UP,
    'ARROWDOWN': UnifiedKeys.UK_KB_DOWN,
    'ARROWLEFT': UnifiedKeys.UK_KB_LEFT,
    'ARROWRIGHT': UnifiedKeys.UK_KB_RIGHT,
    'PAGEUP': UnifiedKeys.UK_KB_PAGE_UP,
    'PAGEDOWN': UnifiedKeys.UK_KB_PAGE_DOWN,

    'NP_ADD': UnifiedKeys.UK_KB_NP_PLUS,
    'NP_SUBTRACT': UnifiedKeys.UK_KB_NP_MINUS,
    'NP_DECIMAL': UnifiedKeys.UK_KB_NP_PERIOD,
})


def ng2uk(key_code: str) -> UnifiedKey:
    """
        Convert Nicegui keycode to UnifiedKey
    :param key_code:
    :return:
    """

    key_code = key_code.upper()
    if key_code.startswith('KEY'):
        key_code = 'KB_' + key_code[3:]

    elif key_code.startswith('NUMPAD'):
        key_code = 'KB_NP_' + key_code[6:]

    elif key_code.startswith('DIGIT'):
        key_code = 'KB_' + key_code[5:]

    try:
        uk = UnifiedKeys.filter_name(key_code.upper())
        if uk is None:
            raise KeyError
        else:
            return uk
    except:
        try:
            return key_mapper[key_code.upper()]
        except KeyError:
            return UnifiedKeys.UK_UNKNOWN
