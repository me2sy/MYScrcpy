# -*- coding: utf-8 -*-
"""
    Params
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-10-24 1.7.0 Me2sY  适配 Scrcpy 2.7.0

        2024-09-29 1.6.4 Me2sY  新增 Action 分类

        2024-09-18 1.6.0 Me2sY  重构 Extensions 体系

        2024-09-12 1.5.10 Me2sY 新增 Extensions

        2024-09-10 1.5.9 Me2sY  新增文件管理器相关路径

        2024-09-02 1.5.2 Me2sY  Pypi发布

        2024-08-24 1.3.7 Me2sY  从utils中抽离
"""

__author__ = 'Me2sY'
__version__ = '1.7.0'

__all__ = [
    'project_path',
    'Param', 'Action'
]


from enum import IntEnum, unique
import pathlib


PROJECT_NAME = 'myscrcpy'


def project_path() -> pathlib.Path:
    """
        获取项目根目录
    :return:
    """
    for _ in pathlib.Path(__file__).resolve().parents:
        if _.name == PROJECT_NAME:
            return _


class Param:
    """
        参数
    """

    PROJECT_NAME = PROJECT_NAME
    AUTHOR = __author__
    VERSION = __version__
    EMAIL = 'me2sy@outlook.com'
    GITHUB = 'https://github.com/Me2sY/myscrcpy'

    PROJECT_PATH = project_path()

    PATH_STATICS = PROJECT_PATH.joinpath('static')
    PATH_STATICS.mkdir(parents=True, exist_ok=True)
    PATH_STATICS_ICON = PATH_STATICS.joinpath('myscrcpy.ico')
    PATH_STATICS_ICONS = PATH_STATICS / 'icons'

    PATH_LIBS = PROJECT_PATH.joinpath('libs')
    PATH_LIBS.mkdir(parents=True, exist_ok=True)

    PATH_TPS = pathlib.Path.home().joinpath(f".{PROJECT_NAME}").joinpath('tps')
    PATH_TPS.mkdir(parents=True, exist_ok=True)

    PATH_TEMP = pathlib.Path.home().joinpath(f".{PROJECT_NAME}").joinpath('temp')
    PATH_TEMP.mkdir(parents=True, exist_ok=True)

    PATH_CONFIGS = pathlib.Path.home().joinpath(f".{PROJECT_NAME}").joinpath('configs')
    PATH_CONFIGS.mkdir(parents=True, exist_ok=True)

    PATH_DOWNLOAD = pathlib.Path.home().joinpath(f".{PROJECT_NAME}").joinpath('download')
    PATH_DOWNLOAD.mkdir(parents=True, exist_ok=True)

    PATH_EXTENSIONS = pathlib.Path.home().joinpath(f".{PROJECT_NAME}").joinpath(f'extensions')
    PATH_EXTENSIONS.mkdir(parents=True, exist_ok=True)

    PATH_EXTENSIONS_LOCAL = PROJECT_PATH.joinpath('extensions')
    PATH_EXTENSIONS_LOCAL.mkdir(parents=True, exist_ok=True)

    # 设备基础位置
    PATH_DEV_BASE = pathlib.PurePosixPath('/storage/emulated/0/')
    PATH_DEV_PUSH = PATH_DEV_BASE / PROJECT_NAME
    PATH_DEV_SCREENSHOT = PATH_DEV_BASE / 'DCIM'
    OPEN_MAX_SIZE = 1024 * 1024 * 100  # 100 MB

    # Scrcpy
    SCRCPY_SERVER_VER = '2.7'
    SCRCPY_SERVER_NAME = f"scrcpy-server"
    PATH_SCRCPY_SERVER_JAR_LOCAL = PATH_LIBS.joinpath(f"{SCRCPY_SERVER_NAME}")
    PATH_SCRCPY_PUSH = f"/data/local/tmp/{SCRCPY_SERVER_NAME}"

    SCRCPY_SERVER_START_CMD = [
        'CLASSPATH=',
        'app_process',
        '/',
        'com.genymobile.scrcpy.Server',
        SCRCPY_SERVER_VER,
        'log_level=warn',
        'tunnel_forward=true',
        'send_frame_meta=false',
        'stay_awake=true',
    ]


@unique
class Action(IntEnum):
    """
        按键事件
    """
    DOWN = 0
    RELEASE = 1
    MOVE = 2
    ROLL = 3
    DRAG = 4
    DB_CLICK = 5

    PRESSED = 6
