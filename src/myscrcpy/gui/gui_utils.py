# -*- coding: utf-8 -*-
"""
    Gui Utils
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-10-27 1.7.0 Me2sY  适配 dearpygui 2.X

        2024-08-24 1.3.7 Me2sY  配合utils分离接key_mapper进行改造

        2024-08-21 1.3.5 Me2sY
            创建，新增按键映射注入功能，解决不同平台下Code可能不一致问题
"""

__author__ = 'Me2sY'
__version__ = '1.7.0'

__all__ = [
    'inject_dpg_key_mapper', 'inject_pg_key_mapper'
]


import dearpygui.dearpygui as dpg
import pygame

from myscrcpy.utils.keys import UnifiedKeys, KeyMapper


def inject_dpg_key_mapper():
    """
        注入 Dearpygui 键值表
    :return:
    """

    key_mapper = {
        dpg.mvKey_Return: UnifiedKeys.UK_KB_ENTER,
        dpg.mvKey_CapsLock: UnifiedKeys.UK_KB_CAPSLOCK,
        dpg.mvKey_Spacebar: UnifiedKeys.UK_KB_SPACE,
        dpg.mvKey_Prior: UnifiedKeys.UK_KB_PAGE_UP,
        dpg.mvKey_Next: UnifiedKeys.UK_KB_PAGE_DOWN,
        dpg.mvKey_LWin: UnifiedKeys.UK_KB_WIN_L,
        dpg.mvKey_RWin: UnifiedKeys.UK_KB_WIN_R,
        dpg.mvKey_Apps: UnifiedKeys.UK_KB_MENU,
        dpg.mvKey_Back: UnifiedKeys.UK_KB_BACKSPACE,

        dpg.mvKey_Multiply: UnifiedKeys.UK_KB_NP_MULTIPLY,
        dpg.mvKey_Add: UnifiedKeys.UK_KB_NP_PLUS,
        dpg.mvKey_Subtract: UnifiedKeys.UK_KB_NP_MINUS,
        dpg.mvKey_Decimal: UnifiedKeys.UK_KB_NP_PERIOD,
        dpg.mvKey_Divide: UnifiedKeys.UK_KB_NP_DIVIDE,

        dpg.mvKey_LShift: UnifiedKeys.UK_KB_SHIFT_L,
        dpg.mvKey_RShift: UnifiedKeys.UK_KB_SHIFT_R,
        dpg.mvKey_LControl: UnifiedKeys.UK_KB_CONTROL_L,
        dpg.mvKey_RControl: UnifiedKeys.UK_KB_CONTROL_R,
        dpg.mvKey_Menu: UnifiedKeys.UK_KB_MENU_L,

        dpg.mvKey_Plus: UnifiedKeys.UK_KB_EQUALS,
        dpg.mvKey_Tilde: UnifiedKeys.UK_KB_BACKQUOTE,
        dpg.mvKey_Open_Brace: UnifiedKeys.UK_KB_BRACKET_L,
        dpg.mvKey_Close_Brace: UnifiedKeys.UK_KB_BRACKET_R,

        dpg.mvMouseButton_Left: UnifiedKeys.UK_MOUSE_L,
        dpg.mvMouseButton_Right: UnifiedKeys.UK_MOUSE_R,
        dpg.mvMouseButton_Middle: UnifiedKeys.UK_MOUSE_WHEEL
    }

    register_dict = {}

    for key, code in dpg.__dict__.items():

        if key.startswith('mvKey_') or key.startswith('mvMouseButton_'):

            if code in key_mapper:
                register_dict[code] = key_mapper[code]
                continue

            _key = 'KB_' + key[6:]
            uk = UnifiedKeys.filter_name(_key)
            if uk:
                register_dict[code] = uk
            else:
                _key = _key.replace('NumPad', 'NP_')
                uk = UnifiedKeys.filter_name(_key)
                if uk:
                    register_dict[code] = uk

    KeyMapper.register('dpg', register_dict)


def inject_pg_key_mapper():
    """
        注入 Pygame 键值表
    :return:
    """
    key_mapper = {
        pygame.K_LSHIFT: UnifiedKeys.UK_KB_SHIFT_L,
        pygame.K_RSHIFT: UnifiedKeys.UK_KB_SHIFT_R,
        pygame.K_LCTRL: UnifiedKeys.UK_KB_CONTROL_L,
        pygame.K_RCTRL: UnifiedKeys.UK_KB_CONTROL_R,
        pygame.K_LALT: UnifiedKeys.UK_KB_ALT_L,
        pygame.K_RALT: UnifiedKeys.UK_KB_ALT_R,
        pygame.K_RETURN: UnifiedKeys.UK_KB_ENTER,
        pygame.K_UNKNOWN: UnifiedKeys.UK_UNKNOWN,
        pygame.K_SEMICOLON: UnifiedKeys.UK_KB_COLON,
        pygame.K_LEFTBRACKET: UnifiedKeys.UK_KB_BRACKET_L,
        pygame.K_RIGHTBRACKET: UnifiedKeys.UK_KB_BRACKET_R,
        pygame.K_PAGEUP: UnifiedKeys.UK_KB_PAGE_UP,
        pygame.K_PAGEDOWN: UnifiedKeys.UK_KB_PAGE_DOWN,
        pygame.K_LGUI: UnifiedKeys.UK_KB_WIN_L,
        pygame.K_RGUI: UnifiedKeys.UK_KB_WIN_R,

        pygame.BUTTON_LEFT: UnifiedKeys.UK_MOUSE_L,
        pygame.BUTTON_RIGHT: UnifiedKeys.UK_MOUSE_R,
        pygame.BUTTON_MIDDLE: UnifiedKeys.UK_MOUSE_WHEEL,
        pygame.BUTTON_WHEELUP: UnifiedKeys.UK_MOUSE_WHEEL_UP,
        pygame.BUTTON_WHEELDOWN: UnifiedKeys.UK_MOUSE_WHEEL_DOWN,
    }

    register_dict = {}

    for key, code in pygame.__dict__.items():
        if key.startswith('K_') or key.startswith('BUTTON_'):
            if code in key_mapper:
                register_dict[code] = key_mapper[code]
                continue

            _key = key[2:].upper()
            uk = UnifiedKeys.filter_name(_key)
            if uk:
                register_dict[code] = uk
            else:
                _key = _key.replace('KP_', 'NP_')
                uk = UnifiedKeys.filter_name(_key)
                if uk:
                    register_dict[code] = uk

    KeyMapper.register('pg', register_dict)
