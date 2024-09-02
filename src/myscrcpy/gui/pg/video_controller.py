# -*- coding: utf-8 -*-
"""
    Pygame Video Controller
    ~~~~~~~~~~~~~~~~~~
    Pygame 适配器

    Log:
        2024-08-29 1.4.0 Me2sY  适配新Core/Session架构

        2024-07-31 1.1.1 Me2sY  适配新Controller

        2024-07-28 1.0.0 Me2sY  发布初版

        2024-07-09 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '1.4.0'

__all__ = [
    'PGVideoController'
]

from loguru import logger
import numpy as np
import pygame as pg

from myscrcpy.core import *


class PGVideoController:
    """
        Pygame Video Controller
        为提高性能及刷新频率，采用固定显示大小，剔除旋转、缩放等运算
    """

    def __init__(
            self,
            session: Session
    ):

        self.session = session
        if not self.session.is_video_ready or not self.session.is_control_ready:
            raise RuntimeError('Connect Scrcpy Video And Control First!')

        self.surface_video: pg.Surface = pg.surfarray.make_surface(self.transformed_frame(self.session.va.get_frame()))

    @staticmethod
    def transformed_frame(frame: np.ndarray) -> np.ndarray:
        return np.flipud(np.rot90(frame))

    def load_frame(self):
        try:
            pg.surfarray.blit_array(self.surface_video, self.transformed_frame(self.session.va.get_frame()))
        except ValueError:
            logger.error('Failed to load video frame')

    @property
    def surface(self) -> pg.Surface:
        self.load_frame()
        return self.surface_video
