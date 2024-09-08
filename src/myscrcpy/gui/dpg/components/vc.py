# -*- coding: utf-8 -*-
"""
    Video/Control Component
    ~~~~~~~~~~~~~~~~~~~~~~~

    Log:
        2024-09-08 1.5.7 Me2sY  更新图像解析算法

        2024-09-05 1.5.4 Me2sY  优化CPU占用

        2024-09-01 1.4.2 Me2sY  配合右键手势控制功能，添加显示layer

        2024-08-29 1.4.0 Me2sY  适配新架构

        2024-08-15 1.3.0 Me2sY  发布初版

        2024-08-11 0.1.2 Me2sY  完成功能开发

        2024-08-10 0.1.1 Me2sY  分离
"""

__author__ = 'Me2sY'
__version__ = '1.5.7'

__all__ = [
    'VideoController', 'CPMVC'
]

import threading

import av
import dearpygui.dearpygui as dpg
from loguru import logger
import numpy as np


from myscrcpy.utils import Coordinate, ScalePoint, ScalePointR
from myscrcpy.gui.dpg.components.component_cls import *


class VideoController:
    """
        视频控制器
        解析视频流，并写入至 raw_texture
        视频旋转时发起旋转信号
    """

    def __init__(
            self,
            default_rgb_color: int = 0
    ):
        self.tag_texture = dpg.generate_uuid()

        self.default_rgb_color = default_rgb_color

        self.coord_frame = Coordinate(0, 0)

        self.resize_callbacks = set()
        self.rotation_callbacks = set()

    @staticmethod
    def create_default_frame(coordinate, rgb_color: int = 0) -> np.ndarray:
        """
            创建初始化页面
            RGB 3D uint8 0...255
        """
        return np.full((coordinate.height, coordinate.width, 3), rgb_color, dtype=np.uint8)

    @staticmethod
    def create_default_av_video_frame(coordinate, rgb_color: int = 0) -> av.VideoFrame:
        """
            创建 av.VideoFrame
            2024-09-05 1.5.4 适配新版本
        :param coordinate:
        :param rgb_color:
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

    def _init_texture(
            self,
            frame_coord: Coordinate,
            default_value: np.ndarray | None = None
    ):
        """
            初始化 Texture
        :return:
        """
        try:
            dpg.delete_item(self.tag_texture)
        except SystemError:
            pass

        with dpg.texture_registry(show=False):
            # 2024-09-05 Me2sY dynamic 效果并不太好
            # 需要使用 float_rgba 增加计算量
            #
            # dpg.add_dynamic_texture(
            #     tag=self.tag_texture, **frame_coord.d,
            #     default_value=default_value if default_value is not None else self.create_default_frame(
            #         frame_coord, self.default_rgb_color
            #     )
            # )

            dpg.add_raw_texture(
                tag=self.tag_texture, **frame_coord.d, format=dpg.mvFormat_Float_rgb,
                default_value=default_value if default_value is not None else (
                        self.create_default_frame(
                            frame_coord, self.default_rgb_color
                        ).astype(np.float32).ravel() / 255.0)
            )

    def load_frame(self, frame: av.VideoFrame):
        """
            加载 Frame
        """
        # 2024-09-05 1.5.4 Me2sY
        # 改用 av.VideoFrame
        # h, w, d = frame.shape
        # _c = Coordinate(width=w, height=h)

        _c = Coordinate(width=frame.width, height=frame.height)

        if _c != self.coord_frame:

            # float32 容器 用于快速转换
            # 较 .astype 单帧节约 2ms
            self.u2f = np.empty(_c.width * _c.height * 3, dtype=np.float32)
            self._init_texture(_c, self.to_raw_texture_value(frame))
            if self.coord_frame.rotation != _c.rotation:
                self._frame_rotation(self.coord_frame, _c)

            self._frame_resize(self.coord_frame, _c)

            self.coord_frame = _c

        # 2024-09-06 1.5.4 Me2sY 零星加载失败情况
        try:
            dpg.set_value(self.tag_texture, self.to_raw_texture_value(frame))
        except:
            ...

    def _frame_rotation(self, old_coord: Coordinate, new_coord: Coordinate):
        for _ in self.rotation_callbacks:
            threading.Thread(target=_, args=(self.tag_texture, old_coord, new_coord)).start()

    def _frame_resize(self, old_coord: Coordinate, new_coord: Coordinate):
        for _ in self.resize_callbacks:
            threading.Thread(target=_, args=(self.tag_texture, old_coord, new_coord)).start()

    def register_resize_callback(self, callback):
        self.resize_callbacks.add(callback)

    def register_rotation_callback(self, callback):
        self.rotation_callbacks.add(callback)

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
        self._coord_draw = Coordinate(1, 1)
        with dpg.drawlist(**self._coord_draw.d) as self.tag_dl:
            with dpg.draw_layer() as self.tag_layer_0:
                ...
            with dpg.draw_layer() as self.tag_layer_1:
                ...
            with dpg.draw_layer(label='cross') as self.tag_layer_2:
                ...
            with dpg.draw_layer(label='right_track') as self.tag_layer_track:
                ...
            with dpg.draw_layer(label='right_msg') as self.tag_layer_msg:
                ...
            with dpg.draw_layer(label='right_sec_point') as self.tag_layer_sec_point:
                ...

    def draw_layer(self, layer_tag, *args, clear: bool = True, **kwargs):
        """
            绘制图层
        """
        if layer_tag == self.tag_layer_0:
            raise ValueError(f'Video Layer is ReadOnly.')

        if clear:
            dpg.delete_item(layer_tag, children_only=True)

        for _ in args:
            _(parent=layer_tag)

    def update(self, init_max_height: int = 800, init_max_width: int = 1200):
        self.init_max_height = init_max_height
        self.init_max_width = init_max_width

    def init_image(self, texture: int | str, coord: Coordinate, auto_fix: bool = True) -> Coordinate:
        """
            初始化 Image
        """

        try:
            dpg.delete_item(self.tag_layer_0, children_only=True)
        except:
            pass

        # 限制初始画面大小，避免手机竖屏导致的窗口高度过高
        if auto_fix:
            coord = coord.get_max_coordinate(max_width=self.init_max_width, max_height=self.init_max_height)

        self.tag_image = dpg.draw_image(texture_tag=texture, pmin=(0, 0), pmax=coord, parent=self.tag_layer_0)

        return self.update_frame(coord)

    def update_frame(self, coord: Coordinate, texture_tag: int | str | None = None) -> Coordinate:
        """
            根据Texture更新组件配置
        """

        if not hasattr(self, 'tag_image') or coord == self._coord_draw:
            return coord

        try:
            update_cfg = {}
            if texture_tag:
                update_cfg['texture_tag'] = texture_tag
            dpg.configure_item(self.tag_image, pmax=coord, **update_cfg)
        except Exception as e:
            logger.error(f"Update Image Error => {e}")

        try:
            dpg.configure_item(self.tag_dl, **coord.d)
        except:
            pass

        self._coord_draw = coord

        return coord
