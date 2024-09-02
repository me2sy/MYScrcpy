# -*- coding: utf-8 -*-
"""
    myscrcpy.core
    ~~~~~~~~~~~~~~~~~~
    核心库
    连接 Scrcpy 基础核心， 包括 Connection 连接管理类 / Session 连接状态类 / AdvDevice 设备管理
    V/A/C Adapter等

    Log:
        2024-08-29 1.4.0 Me2sY  重构，新增 Connection Session

        2024-08-25 1.3.7 Me2sY  重构，架构上支持多视频、音频连接
"""

__author__ = 'Me2sY'
__version__ = '1.4.0'

__all__ = [
    # Connection
    'Connection',
    
    # Video
    'CameraArgs', 'VideoArgs',
    'VideoAdapter',

    # Audio
    'AudioArgs', 'AudioAdapter',

    # Control
    'KeyboardWatcher',
    'ControlArgs', 'ControlAdapter',

    # Session
    'Session',

    # Device
    'DeviceInfo', 'PackageInfo',
    'AdvDevice', 'DeviceFactory',
]

from myscrcpy.core.connection import *
from myscrcpy.core.video import *
from myscrcpy.core.audio import *
from myscrcpy.core.control import *
from myscrcpy.core.session import *
from myscrcpy.core.device import *
