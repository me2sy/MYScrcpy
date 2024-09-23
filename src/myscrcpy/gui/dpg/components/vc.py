# -*- coding: utf-8 -*-
"""
    Video/Control Component
    ~~~~~~~~~~~~~~~~~~~~~~~

    Log:
        2024-09-23 1.6.0 Me2sY  优化部分方法

        2024-09-12 1.5.10 Me2sY 支持Extensions

        2024-09-08 1.5.7 Me2sY  更新图像解析算法

        2024-09-05 1.5.4 Me2sY  优化CPU占用

        2024-09-01 1.4.2 Me2sY  配合右键手势控制功能，添加显示layer

        2024-08-29 1.4.0 Me2sY  适配新架构

        2024-08-15 1.3.0 Me2sY  发布初版

        2024-08-11 0.1.2 Me2sY  完成功能开发

        2024-08-10 0.1.1 Me2sY  分离
"""

__author__ = 'Me2sY'
__version__ = '1.6.0'

__all__ = [
    'VideoController', 'CPMVC'
]

import threading
from typing import Callable

import av
import dearpygui.dearpygui as dpg
from loguru import logger
import numpy as np


from myscrcpy.utils import Coordinate, ScalePoint, ScalePointR
from myscrcpy.gui.dpg.components.component_cls import *


class VideoController:
    """
        视频控制器 控制 Raw Texture
        解析视频流，并写入至 raw_texture
        视频旋转时发起旋转信号
    """

    def __init__(self, default_rgb_color: int = 0):
        """
            RawTexture 控制器
        :param default_rgb_color:
        """
        self.tag_texture = dpg.generate_uuid()

        self.default_rgb_color = default_rgb_color

        self.coord_frame = Coordinate(0, 0)

        self.resize_callbacks = set()

    @staticmethod
    def create_default_frame(coordinate, rgb_color: int = 0) -> np.ndarray:
        """
            创建初始化页面
            RGB 3D uint8 0...255
        :param coordinate:
        :param rgb_color: 0..255
        :return: RGB uint8 0..255
        """
        return np.full((coordinate.height, coordinate.width, 3), rgb_color, dtype=np.uint8)

    @staticmethod
    def create_default_av_video_frame(coordinate, rgb_color: int = 0) -> av.VideoFrame:
        """
            创建 av.VideoFrame
            2024-09-05 1.5.4 适配新版本
        :param coordinate:
        :param rgb_color: 0..255
        :return:
        """
        return av.VideoFrame.from_ndarray(
            array=np.full((coordinate.height, coordinate.width, 3), rgb_color, dtype=np.uint8), format='rgb24'
        )

    def to_raw_texture_value(self, frame: av.VideoFrame) -> np.ndarray:
        """
            输出 1D float32 RGB 0..1
            重写该函数以实现更多图像处理
        :param frame:
        :return:
        """
        # 2024-09-05 1.5.4 Me2sY
        # Issue #6
        # 经查 DPG 绘图使用 rgb float32 0..1 1D
        # av.to_ndarray 为 rgb uint8 0..255 3D
        # 需进行 dtype 1D化 及 归一化
        # 1200x752 4ms to float32

        # try:
        #     self.u2f[:] = frame.reformat(format='rgb24').planes[0]
        # except:
        #     self.u2f[:] = frame.to_ndarray(format='rgb24').astype(np.float32).ravel()
        # return self.u2f / 255.0

        # 2024-09-07 1.5.7 Me2sY 时间相差不多，读取安全性高
        return frame.to_ndarray(format='rgb24').ravel() / np.float32(255)

    def _init_texture(self, coord_frame: Coordinate):
        """
            初始化 Texture
        :param coord_frame: 尺寸
        :return:
        """

        if dpg.does_item_exist(self.tag_texture):
            dpg.delete_item(self.tag_texture)

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(**coord_frame.d, tag=self.tag_texture, format=dpg.mvFormat_Float_rgb, default_value=[])

        self.coord_frame = coord_frame

    def load_frame(self, frame: av.VideoFrame):
        """
            加载 Frame
        """
        # 2024-09-05 1.5.4 Me2sY
        # 改用 av.VideoFrame

        _c = Coordinate(width=frame.width, height=frame.height)

        if _c != self.coord_frame:
            # 尺寸变化
            # 旋转 或 重连
            _old = self.coord_frame
            self._init_texture(_c)
            self._callback_frame_resize(_old, _c)

        # 2024-09-06 1.5.4 Me2sY 零星加载失败情况

        try:
            dpg.set_value(self.tag_texture, self.to_raw_texture_value(frame))
        except Exception as e:
            logger.error(f"VC load_frame error -> {e}")

    def _callback_frame_resize(self, old_coord: Coordinate, new_coord: Coordinate):
        """
            frame resize callback
        :param old_coord:
        :param new_coord:
        :return:
        """
        for callback in self.resize_callbacks:
            threading.Thread(target=callback, args=(self.tag_texture, old_coord, new_coord)).start()

    def register_resize_callback(self, callback: Callable[[str | int, Coordinate, Coordinate], None]):
        """
            注册 Resize Callback
        :param callback:
        :return:
        """
        self.resize_callbacks.add(callback)

    def reset(self):
        self.coord_frame = Coordinate(0, 0)


class CPMVC(Component):
    """
        Video/Control 组件
    """

    DEFAULT_CONTAINER_ADD_METHOD = dpg.add_group
    init_max_height = 800
    init_max_width = 1200

    @property
    def coord_draw(self) -> Coordinate:
        return self._coord_draw

    def get_coord_draw(self) -> Coordinate:
        return self._coord_draw

    def is_hovered(self) -> bool:
        return dpg.is_item_hovered(self.tag_dl)

    def spr(self) -> ScalePointR:
        return self._coord_draw.to_scale_point_r(*dpg.get_drawing_mouse_pos())

    @property
    def scale_point(self) -> ScalePoint:
        return self._coord_draw.to_scale_point(*dpg.get_drawing_mouse_pos())

    def to_scale_point(self, x, y) -> ScalePoint:
        return self._coord_draw.to_scale_point(x, y)

    def setup_inner(self, *args, **kwargs):
        self.tags = set()
        self._coord_draw = Coordinate(0, 0)
        self.tag_dl = dpg.add_drawlist(**self._coord_draw.d)
        self.tag_layer_0 = dpg.add_draw_layer(parent=self.tag_dl)
        self.tag_layer_1 = dpg.add_draw_layer(parent=self.tag_dl)
        self.tag_layer_2 = dpg.add_draw_layer(parent=self.tag_dl)
        self.tag_layer_track = dpg.add_draw_layer(parent=self.tag_dl)
        self.tag_layer_msg = dpg.add_draw_layer(parent=self.tag_dl)
        self.tag_layer_sec_point = dpg.add_draw_layer(parent=self.tag_dl)

    def register_layer(self) -> int | str:
        """
            注册 layer
        :return:
        """
        _tag_layer = dpg.add_draw_layer(parent=self.tag_dl)
        self.tags.add(_tag_layer)
        return _tag_layer

    def clear_drawlist(self):
        """
            清除注册页面
        :return:
        """
        for _ in self.tags:
            if dpg.does_item_exist(_):
                dpg.delete_item(_)

    def draw_layer(self, layer_tag, *args, clear: bool = True, **kwargs):
        """
            绘制图层
        """
        if layer_tag == self.tag_layer_0:
            raise ValueError(f'Video Layer is ReadOnly.')

        if clear:
            dpg.delete_item(layer_tag, children_only=True)
            return

        for _ in args:
            _(parent=layer_tag)

    def update(self, init_max_height: int = 800, init_max_width: int = 1200):
        self.init_max_height = init_max_height
        self.init_max_width = init_max_width

    def init_image(self, texture: int | str, coord: Coordinate, auto_fix: bool = True) -> Coordinate:
        """
            初始化 Image
        """

        if dpg.does_item_exist(self.tag_layer_0):
            dpg.delete_item(self.tag_layer_0, children_only=True)

        # 限制初始画面大小，避免手机竖屏导致的窗口高度过高
        if auto_fix:
            coord = coord.get_max_coordinate(max_width=self.init_max_width, max_height=self.init_max_height)

        self.tag_image = dpg.draw_image(texture_tag=texture, pmin=(0, 0), pmax=coord, parent=self.tag_layer_0)

        return self.resize(coord)

    def resize(self, coord: Coordinate, texture_tag: int | str | None = None) -> Coordinate:
        """
            Resize coord and texture
        :param coord:
        :param texture_tag:
        :return:
        """

        if not hasattr(self, 'tag_image') or coord == self._coord_draw:
            return coord
        else:
            self._coord_draw = coord

        try:
            update_cfg = {}
            if texture_tag:
                update_cfg['texture_tag'] = texture_tag
            dpg.configure_item(self.tag_image, pmax=coord, **update_cfg)
        except Exception as e:
            logger.error(f"Update Image Error => {e}")

        try:
            dpg.configure_item(self.tag_dl, **coord.d)
        except Exception as e:
            logger.error(f"Resize drawlist Error -> {e}")

        return coord
