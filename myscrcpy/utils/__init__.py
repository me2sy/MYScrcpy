# -*- coding: utf-8 -*-
"""
    utils
    ~~~~~~~~~~~~~~~~~~
    工具类

    Log:
        2024-08-25 1.4.0 Me2sY 新增 ScalePointR

        2024-08-24 1.3.7 Me2sY 随着项目的发展，原utils过于臃肿与繁重，遂将Utils分离，方便后期扩展。
"""

__author__ = 'Me2sY'
__version__ = '1.4.0'

__all__ = [
    # Params
    'project_path', 'Param', 'Action',

    # Keys
    'ADBKeyCode', 'UHIDKeyCode', 'UHID_MOUSE_REPORT_DESC', 'UHID_KEYBOARD_REPORT_DESC',
    'UnifiedKey', 'UnifiedKeys', 'KeyMapper',

    # Vector
    'ROTATION_VERTICAL', 'ROTATION_HORIZONTAL',
    'Point', 'ScalePoint', 'ScalePointR',
    'Coordinate',

    # Config manager
    'CfgHandler',
    'ValueRecord', 'ValueManager'
]

from myscrcpy.utils.params import *
from myscrcpy.utils.keys import *
from myscrcpy.utils.vector import *
from myscrcpy.utils.config_manager import *
