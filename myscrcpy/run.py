# -*- coding: utf-8 -*-
"""
    GUI 入口
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-15 1.3.0 Me2sY  新版本GUI

        2024-08-05 1.2.0 Me2sY  适配新分体架构

        2024-07-28 1.0.0 Me2sY
            发布初版
"""

__author__ = 'Me2sY'
__version__ = '1.3.0'

__all__ = []

from loguru import logger

try:
    import click
    import dearpygui
    import pygame
    import easygui
    import cv2
except ImportError:
    logger.warning('You need to install click, dearpygui, pygame, easygui, opencv-python before using.')
    raise ImportError


# from myscrcpy.gui.dpg.window_devices import start_devices_window
from myscrcpy.gui.pg.window_control import run
from myscrcpy.gui.dpg_adv.window import start_dpg_adv

@click.command()
@click.option('-g', '--gamemode', is_flag=True, default=False, help='直接进入控制模式')
def cmd(gamemode):
    if gamemode:
        run()
    else:
        start_dpg_adv()


if __name__ == '__main__':
    cmd()
