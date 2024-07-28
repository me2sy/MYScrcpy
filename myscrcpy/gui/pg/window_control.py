# -*- coding: utf-8 -*-
"""
    控制窗口
    ~~~~~~~~~~~~~~~~~~


    Log:
         2024-07-28 1.0.0 Me2sY
            发布初版

"""

__author__ = 'Me2sY'
__version__ = '1.0.0'

__all__ = [
    'PGControlWindow'
]

import pathlib

import pygame

from myscrcpy.device_controller import DeviceController
from myscrcpy.gui.pg.tp_adapter import TouchProxyAdapter
from myscrcpy.gui.pg.video_controller import PGVideoController

from myscrcpy.utils import Param


class PGControlWindow:
    """
        pygame 控制窗口
    """

    def __init__(self):
        self.tpa: TouchProxyAdapter | None = None
        self.is_running = False

    def reload_cfg(self, cfg_path: pathlib.Path):
        if self.tpa:
            self.tpa.load_cfg(cfg_path)

    def run(
            self,
            device: DeviceController,
            creator,
            cfg_path: pathlib.Path,
            fps: int = 120,
            *args, **kwargs
    ):
        """
            启动控制窗口
        :param device:
        :param creator:
        :param cfg_path:
        :param fps:
        :param args:
        :param kwargs:
        :return:
        """
        pgv = PGVideoController(device)
        self.tpa = TouchProxyAdapter(device, pgv.coordinate, cfg_path)

        pygame.init()
        pygame.display.init()

        main_surface = pygame.display.set_mode(pgv.coordinate)
        pygame.display.set_caption('MyScrcpy - Me2sY')
        pygame.display.set_icon(pygame.image.load(Param.PATH_STATICS.joinpath('myscrcpy.ico')))

        clock = pygame.time.Clock()

        pygame.event.set_allowed([
            pygame.QUIT,
            pygame.KEYDOWN, pygame.KEYUP,
            pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
            pygame.MOUSEMOTION
        ])

        self.is_running = True

        while self.is_running:

            main_surface.blit(pgv.surface, (0, 0))
            pygame.display.update()

            for event in pygame.event.get(
                    [
                        pygame.QUIT,
                        pygame.KEYUP, pygame.KEYDOWN,
                        pygame.MOUSEBUTTONUP, pygame.MOUSEBUTTONDOWN,
                        pygame.MOUSEMOTION
                    ]
            ):
                if event.type == pygame.QUIT or event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.is_running = False
                    break

                else:
                    self.tpa.event_handler(event)

            self.tpa.loop_event_handler()
            clock.tick(fps)

        pygame.quit()


def run():
    from pathlib import Path

    from loguru import logger
    import easygui
    from myscrcpy.device_controller import DeviceFactory
    from myscrcpy.utils import Param

    devices = DeviceFactory.init_all_devices()

    if len(devices) > 1:

        choice = easygui.choicebox(
            'Choose a device',
            'Devices',
            list(devices.keys())
        )
        dev = devices[choice]

    else:
        dev = devices[list(devices.keys())[0]]

    size = easygui.integerbox('max_size', 'Video Max Size', dev.coordinate.max_size, upperbound=99999)
    if size is None or size <= 0:
        dev.close()
        return

    file_path = easygui.fileopenbox(
        'Choose a tp config',
        'Open',
        default=Param.PATH_TPS.__str__() + '\\'
    )
    logger.info(f'Opening {Param.PATH_TPS.__str__()}')
    logger.info(f'file_path: {file_path}')

    if file_path is not None and size > 0:
        dev.connect_to_scrcpy(size, screen_on=True)
        PGControlWindow().run(
            dev, None, Path(file_path)
        )
    dev.close()
