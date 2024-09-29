# -*- coding: utf-8 -*-
"""
    GUI 入口
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-09-29 1.6.4 Me2sY  新增 指定插件加载路径功能

        2024-09-02 1.5.0 Me2sY  pypi 发布版本

        2024-08-30 1.4.0 Me2sY  适配 Session/Connection 架构

        2024-08-19 1.3.3 Me2sY  去除 opencv 缩小程序包

        2024-08-15 1.3.0 Me2sY  新版本GUI

        2024-08-05 1.2.0 Me2sY  适配新分体架构

        2024-07-28 1.0.0 Me2sY
            发布初版
"""

__author__ = 'Me2sY'
__version__ = '1.6.4'

__all__ = []

import pathlib

import click
from loguru import logger

try:
    import dearpygui
    import pygame
except ImportError:
    logger.warning('Use pip install myscrcpy[gui] before using.')
    raise ImportError

from myscrcpy.gui.dpg.window import start_dpg_adv


@click.command()
@click.option('--ext_dev_path', type=click.Path(
    exists=True, file_okay=False, dir_okay=True, resolve_path=True, path_type=pathlib.Path
), default=None)
def run(ext_dev_path):
    start_dpg_adv(ext_dev_path)


if __name__ == '__main__':
    run()
