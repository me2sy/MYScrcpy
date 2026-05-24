# -*- coding: utf-8 -*-
"""
    device
    ~~~~~~~~~~~~~~~~~~

    u2 设备懒连接 + 缓存。每个工具调用先 `get_device(serial)`，
    避免在 GUI 启动时阻塞等 atx-agent 初始化。
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = ['get_device', 'list_serials', 'reset_cache']

import threading
from typing import Optional

import uiautomator2 as u2


_lock = threading.Lock()
_cache: dict[str, u2.Device] = {}


def list_serials() -> list[str]:
    """列出所有当前 ADB 在线设备的 serial。"""
    from adbutils import adb
    return [d.serial for d in adb.device_list()]


def get_device(serial: Optional[str] = None) -> u2.Device:
    """获取（必要时建立）u2 Device 句柄。
    serial=None 时使用第一台 ADB 在线设备。
    """
    key = serial or '__default__'
    with _lock:
        dev = _cache.get(key)
        if dev is not None:
            return dev

        if serial is None:
            serials = list_serials()
            if not serials:
                raise RuntimeError('No ADB device connected')
            serial = serials[0]
            key = serial

        dev = u2.connect(serial)
        _cache[key] = dev
        if serial != '__default__':
            _cache['__default__'] = dev
        return dev


def reset_cache() -> None:
    """清空缓存（设备拔插或显式重连时调用）。"""
    with _lock:
        _cache.clear()
