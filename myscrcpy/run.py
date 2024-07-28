# -*- coding: utf-8 -*-
"""
    GUI 入口
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-07-28 1.0.0 Me2sY
            发布初版

"""

__author__ = 'Me2sY'
__version__ = '1.0.0'

__all__ = []

import click

from myscrcpy.gui.dpg.window_devices import main
from myscrcpy.gui.pg.window_control import run


@click.command()
@click.option('-g', '--gamemode', is_flag=True, default=False, help='直接进入控制模式')
def cmd(gamemode):
    if gamemode:
        run()
    else:
        main()


if __name__ == '__main__':
    cmd()
