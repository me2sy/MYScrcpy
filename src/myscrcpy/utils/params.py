# -*- coding: utf-8 -*-
"""
    Params
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-09-02 1.5.2 Me2sY  Pypi发布

        2024-08-24 1.3.7 Me2sY  从utils中抽离
"""

__author__ = 'Me2sY'
__version__ = '1.5.2'

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
    AUTHOR = 'Me2sY'
    VERSION = '1.5.6'
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

    # Scrcpy
    SCRCPY_SERVER_VER = '2.6.1'
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
