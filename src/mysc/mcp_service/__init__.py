# -*- coding: utf-8 -*-
"""
    mcp_service
    ~~~~~~~~~~~~~~~~~~

    通过 MCP（streamable-http）把 Android 设备暴露给 LLM。
    底层使用 uiautomator2，提供语义化 UI 树 + 截屏 + 控制工具。

    与 GUI 的关系：作为守护线程随 GUI 启动，进程退出时一并销毁。
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = ['start_in_thread', 'stop', 'is_running', 'current_port']

from mysc.mcp_service.lifecycle import (
    start_in_thread, stop, is_running, current_port,
)
