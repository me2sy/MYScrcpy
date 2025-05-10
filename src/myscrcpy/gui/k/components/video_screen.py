# -*- coding: utf-8 -*-
"""
    video_screen
    ~~~~~~~~~~~~~~~~~~
    
    Log:
        2025-05-10 3.2.0 Me2sY  定版

        2025-04-23 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '3.2.0'

__all__ = [
    "VideoScreen",
]

from kivy.graphics import Color, Rectangle
from kivymd.uix.screen import MDScreen

from myscrcpy.utils import ROTATION_VERTICAL


class VideoScreen(MDScreen):

    def __init__(self, name: str, **kwargs):
        """
            Video 视频Screen
        :param name:
        :param kwargs:
        """
        super(VideoScreen, self).__init__(name=name, **kwargs)

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.video_rect = Rectangle(size=self.size)

        self.bind(size=self.update_rect)
        self.rotation = ROTATION_VERTICAL

    def update_rect(self, instance, value):
        """
            更新 Video Panel 位置及大小
        :param instance:
        :param value:
        :return:
        """
        self.video_rect.size = instance.size

    def update_frame(self, texture):
        """
            更新 Frame
        :param texture:
        :return:
        """
        self.video_rect.texture = texture

    def set_no_connected(self):
        """
            无视频连接 显示触摸板
        :return:
        """
        with self.canvas:
            Color(1, 1, 1, 0)
            self.video_rect = Rectangle(size=(99999, 99999))
