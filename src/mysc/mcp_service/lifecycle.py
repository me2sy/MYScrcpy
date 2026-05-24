# -*- coding: utf-8 -*-
"""
    lifecycle
    ~~~~~~~~~~~~~~~~~~

    在守护线程里跑 uvicorn，把 FastMCP 的 streamable_http_app 挂上去。
    GUI on_stop 时翻 should_exit 实现优雅关闭；即使没翻，daemon 线程
    也会随主进程一起结束。
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = ['start_in_thread', 'stop', 'is_running', 'current_port']

import threading
from typing import Optional

import uvicorn

from mysc.mcp_service.server import build_mcp


_thread: Optional[threading.Thread] = None
_server: Optional[uvicorn.Server] = None
_port: Optional[int] = None


def is_running() -> bool:
    return _thread is not None and _thread.is_alive()


def current_port() -> Optional[int]:
    return _port


def start_in_thread(host: str = '0.0.0.0', port: int = 16165, log_level: str = 'warning') -> int:
    """启动 MCP server（streamable-http）守护线程，返回实际监听端口。
    若已在运行则直接返回当前端口（幂等）。
    """
    global _thread, _server, _port
    if is_running():
        return _port

    mcp = build_mcp()
    app = mcp.streamable_http_app()

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level=log_level,
        # uvicorn 默认会注册 SIGTERM/SIGINT handler，跑在子线程里这会失败；关掉。
        lifespan='on',
    )
    server = uvicorn.Server(config)
    # 子线程里 install_signal_handlers 必须为 False
    server.install_signal_handlers = lambda: None

    def _run():
        server.run()

    thread = threading.Thread(target=_run, name='MCP-Server', daemon=True)
    thread.start()

    _thread = thread
    _server = server
    _port = port
    return port


def stop(timeout: float = 3.0) -> None:
    """优雅关闭。daemon 线程进程退出时也会自动死，这里仅尽量优雅。"""
    global _thread, _server, _port
    if _server is not None:
        _server.should_exit = True
    if _thread is not None:
        _thread.join(timeout=timeout)
    _thread = None
    _server = None
    _port = None
