# -*- coding: utf-8 -*-
"""
    GUI 入口
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-30 1.4.0 Me2sY  适配 Session/Connection 架构

        2024-08-19 1.3.3 Me2sY  去除 opencv 缩小程序包

        2024-08-15 1.3.0 Me2sY  新版本GUI

        2024-08-05 1.2.0 Me2sY  适配新分体架构

        2024-07-28 1.0.0 Me2sY
            发布初版
"""

__author__ = 'Me2sY'
__version__ = '1.4.0'

__all__ = []

from loguru import logger

try:
    import click
    import dearpygui
    import pygame
except ImportError:
    logger.warning('You need to install click, dearpygui, pygame before using.')
    raise ImportError


from myscrcpy.gui.dpg.window import start_dpg_adv


@click.command()
def cmd():
    start_dpg_adv()


if __name__ == '__main__':
    cmd()
