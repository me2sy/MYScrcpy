# -*- coding: utf-8 -*-
"""
    Dearpygui Video Controller
    ~~~~~~~~~~~~~~~~~~~~~~~~~~
    视频控制器，用于将RGB Frame 转为 DPG raw_texture

    Log:
        2024-07-31 1.1.1 Me2sY  适配新Controller

        2024-07-28 1.0.0 Me2sY  发布初版

        2024-07-23 0.1.1 Me2sY  适配 scrcpy-server-2.5

        2024-06-28 0.1.0 Me2sY  创建，形成Controller 统一处理 Resize Rotation等事件后的重绘制工作
"""

__author__ = 'Me2sY'
__version__ = '1.1.1'

__all__ = [
    'DpgVideoController'
]

import numpy as np
import dearpygui.dearpygui as dpg

from myscrcpy.controller import DeviceController
from myscrcpy.utils import Coordinate, Param


class DpgVideoController:
    """
        Dearpygui Video Controller
    """

    def __init__(
            self,
            device: DeviceController,
            max_height: int = -1, max_width: int = -1,
            coord_changed_callback=None
    ):

        self.device = device
        if not self.device.is_scrcpy_running:
            raise RuntimeError('Connect Scrcpy First!')

        self.vsc = device.vsc
        self.frame = None
        self.raw_texture_value = None

        self.coord_frame = Coordinate(0, 0)
        self.coord_draw = self.coord_frame

        self.max_height = max_height
        self.max_width = max_width

        self.tag_texture = dpg.generate_uuid()

        self.draw_tags = set()
        self.callbacks = set()

        self.is_pause = False

        self.load_frame()

        if coord_changed_callback:
            self.callbacks.add(coord_changed_callback)

    def _init_texture(self):
        """
            初始化 Texture
        :return:
        """
        try:
            dpg.delete_item(self.tag_texture)
        except SystemError:
            pass

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                tag=self.tag_texture, **self.coord_frame.d,
                default_value=self.raw_texture_value, format=dpg.mvFormat_Float_rgb
            )

    @staticmethod
    def to_raw_texture_value(frame: np.ndarray) -> np.ndarray:
        """
            输出一维 float RGB
        :param frame:
        :return:
        """
        return np.true_divide(frame.ravel().astype(np.float32), 255.0)

    def load_frame(self):
        """
            加载Frame，检测Coordinate变化
        :return:
        """
        self.frame = self.vsc.get_frame() if not self.is_pause else self.frame
        self.raw_texture_value = self.to_raw_texture_value(self.frame)

        h, w, d = self.frame.shape
        _c = Coordinate(width=w, height=h)

        if self.coord_frame != _c:

            if self.coord_frame.rotation != _c.rotation:
                # Update Device Info
                self.device.update_rotation(_c.rotation)

            self.coord_frame = _c
            self.coord_draw = self.coord_frame.get_max_coordinate(self.max_width, self.max_height)
            self.coord_changed()
        else:
            dpg.set_value(self.tag_texture, self.raw_texture_value)

    def loop(self):
        """
            循环以更新画面
        :return:
        """
        self.load_frame()

    def coord_changed(self):
        """
            屏幕坐标变化事件（旋转等）
        :return:
        """

        # Reset Texture
        self._init_texture()

        # update registered items
        self.update_draw_items()

        # callback
        for callback in self.callbacks:
            callback(self)

    def register_changed_callback(self, callback_func):
        """
            注册变化事件回调函数
        :param callback_func:
        :return:
        """
        self.callbacks.add(callback_func)

    def update_draw_items(self):
        """
            更新已注册的绘制item
        :return:
        """
        for _ in self.draw_tags:
            _type = dpg.get_item_type(_)
            if _type == 'mvAppItemType::mvDrawImage':
                dpg.configure_item(
                    _,
                    texture_tag=self.tag_texture,
                    pmax=self.coord_draw,
                )
            elif _type == 'mvAppItemType::mvDrawlist':
                dpg.configure_item(
                    _,
                    **self.coord_draw.d
                )

    def resize_handler(self, sender, app_data, user_data):
        """
            Resize 处理器
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        fix_coord = Coordinate(-16, -32)

        if user_data and isinstance(user_data, dict):
            fix_coord = user_data.get('fix_coord', fix_coord)

        _w = dpg.get_item_width(app_data)
        _h = dpg.get_item_height(app_data)

        self.resize(Coordinate(_w, _h) + fix_coord)

    def resize(self, coord: Coordinate = None):
        """
            Resize Items
        :param coord:
        :return:
        """
        self.coord_draw = coord
        self.update_draw_items()

    @staticmethod
    def _pop_kwargs(d: dict, kwarg: str, default):
        d.setdefault(kwarg, default)
        return d.pop(kwarg)

    def draw_image(self, parent=None, **kwargs):
        _tag = self._pop_kwargs(kwargs, 'tag', dpg.generate_uuid())
        _max_height = self._pop_kwargs(kwargs, 'max_height', self.max_height)
        _max_width = self._pop_kwargs(kwargs, 'max_width', self.max_width)

        _coord = self.coord_frame.get_max_coordinate(_max_width, _max_height)

        parent = dpg.last_container() if parent is None else parent

        dpg.draw_image(self.tag_texture, parent=parent, pmin=[0, 0], pmax=_coord, tag=_tag, **kwargs)

        self.draw_tags.add(_tag)

        if dpg.get_item_type(parent) == 'mvAppItemType::mvDrawLayer':
            parent = dpg.get_item_parent(parent)

        self.draw_tags.add(parent)
        dpg.configure_item(parent, **_coord.d)

    def reset(self):
        """
            恢复初始显示比例
            通过设置coord_frame为新值，触发loop中检测机制，以此进行重置
        :return:
        """
        self.coord_frame = Coordinate(-3 if self.coord_frame.rotation == Param.ROTATION_VERTICAL else -1, -2)

    def set_pause(self, is_pause: bool):
        """
            设置暂停状态
        :param is_pause:
        :return:
        """
        self.is_pause = is_pause

    def to_touch_d(self, mouse_pos) -> dict:
        return {
            **self.coord_frame.to_point(
                self.coord_draw.to_scale_point(*mouse_pos)
            ).d,
            **self.coord_frame.d
        }
