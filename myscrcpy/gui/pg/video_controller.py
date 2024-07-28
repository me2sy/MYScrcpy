# -*- coding: utf-8 -*-
"""
    Pygame Video Controller
    ~~~~~~~~~~~~~~~~~~


    Log:
        2024-07-28 1.0.0 Me2sY
            发布初版

        2024-07-09 0.1.0 Me2sY
            创建

"""

__author__ = 'Me2sY'
__version__ = '1.0.0'

__all__ = [
    'PGVideoController'
]

from loguru import logger
import numpy as np
import pygame as pg

from myscrcpy.device_controller import DeviceController
from myscrcpy.utils import Coordinate


class PGVideoController:
    """
        Pygame Video Controller
        为提高性能及刷新频率，采用固定显示大小，剔除旋转、缩放等运算
    """

    def __init__(
            self,
            device: DeviceController
    ):

        self.device = device
        if not self.device.is_scrcpy_running:
            raise RuntimeError('Connect Scrcpy First!')

        self.vs = device.vs
        self.surface_video: pg.Surface = pg.surfarray.make_surface(self.transformed_frame(self.vs.get_frame()))

    @staticmethod
    def transformed_frame(frame: np.ndarray) -> np.ndarray:
        return np.flipud(np.rot90(frame))

    def load_frame(self):
        try:
            pg.surfarray.blit_array(self.surface_video, self.transformed_frame(self.vs.get_frame()))
        except ValueError:
            logger.error('Failed to load video frame')

    @property
    def surface(self) -> pg.Surface:
        self.load_frame()
        return self.surface_video

    @property
    def coordinate(self) -> Coordinate:
        return self.vs.coordinate
