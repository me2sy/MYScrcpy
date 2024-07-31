# -*- coding: utf-8 -*-
"""
    控制窗口
    ~~~~~~~~~~~~~~~~~~
    pygame框架下设备控制窗口，适用于低延迟需求应用。

    Log:
         2024-07-31 1.1.1 Me2sY 切换新controller

         2024-07-28 1.0.0 Me2sY 发布初版

"""

__author__ = 'Me2sY'
__version__ = '1.1.1'

__all__ = [
    'PGControlWindow', 'run'
]

import pathlib

import pygame

from myscrcpy.controller import DeviceController
from myscrcpy.gui.pg.tp_adapter import TouchProxyAdapter
from myscrcpy.gui.pg.video_controller import PGVideoController

from myscrcpy.utils import Param


class PGControlWindow:
    """
        pygame 控制窗口
        为提高性能及刷新频率，采用固定显示大小，剔除旋转、缩放等运算
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
        pygame.display.set_caption(f"{Param.PROJECT_NAME} - {Param.AUTHOR}")
        pygame.display.set_icon(pygame.image.load(Param.PATH_STATICS_ICON))

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

    from loguru import logger
    import easygui

    from myscrcpy.controller import DeviceFactory, VideoSocketController, ControlSocketController, AudioSocketController
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
        dev.connect(
            vsc=VideoSocketController(max_size=size),
            asc=AudioSocketController(),
            csc=ControlSocketController()
        )
        PGControlWindow().run(
            dev, None, pathlib.Path(file_path)
        )
    dev.close()


if __name__ == '__main__':
    run()
