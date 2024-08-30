# -*- coding: utf-8 -*-
"""
    控制窗口
    ~~~~~~~~~~~~~~~~~~
    pygame框架下设备控制窗口，适用于低延迟需求应用。

    Log:
        2024-08-29 1.4.0 Me2sY  适配Session

        2024-08-26 1.3.7 Me2sY  适配Core架构，去除Run

        2024-07-31 1.1.1 Me2sY  切换新controller

        2024-07-28 1.0.0 Me2sY  发布初版

"""

__author__ = 'Me2sY'
__version__ = '1.4.0'

__all__ = [
    'PGControlWindow'
]

import pathlib

import pygame

from myscrcpy.core import *
from myscrcpy.gui.pg.tp_adapter import TouchProxyAdapter
from myscrcpy.gui.pg.video_controller import PGVideoController

from myscrcpy.utils import Param, Coordinate


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
            session: Session,
            device: AdvDevice,
            coord: Coordinate,
            cfg_path: pathlib.Path,
            fps: int = 120,
            *args, **kwargs
    ):
        """
            启动控制窗口
        :param session: Session
        :param device: AdvDevice
        :param coord:
        :param cfg_path:
        :param fps:
        :param args:
        :param kwargs:
        :return:
        """

        pgv = PGVideoController(session)
        self.tpa = TouchProxyAdapter(session, device, coord, cfg_path)

        pygame.init()
        pygame.display.init()

        main_surface = pygame.display.set_mode(coord)
        pygame.display.set_caption(f"{Param.PROJECT_NAME} - {Param.AUTHOR}")
        pygame.display.set_icon(pygame.image.load(Param.PATH_STATICS_ICON))

        clock = pygame.time.Clock()

        pygame.event.set_allowed([
            pygame.QUIT,
            pygame.KEYDOWN, pygame.KEYUP,
            pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
            pygame.MOUSEMOTION
        ])

        # 2024-08-30 Me2sY
        # 重启音频，尽量保证同步，建议使用 Flac
        # 肯定有细微延迟，最好设备使用有线/蓝牙耳机等

        if session.is_audio_ready:
            session.aa.stop()
            session.aa.start(session.adb_device)

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
