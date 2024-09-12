# -*- coding: utf-8 -*-
"""
    CrossLine Class
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-09-12 1.0.0 Me2sY
            十字线绘制插件
"""

__author__ = 'Me2sY'
__version__ = '1.0.0'

__all__ = [
    'Crossline'
]

import dearpygui.dearpygui as dpg

# 继承 MYScrcpyExtension 类 并重新相应方法
# ExtRunEnv 传入实际功能
from myscrcpy.extensions import MYScrcpyExtension, ExtRunEnv


class Crossline(MYScrcpyExtension):
    """
        十字线插件
    """

    @staticmethod
    def register(*args, **kwargs):
        return Crossline()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.layer = dpg.generate_uuid()

        self.is_draw = False

    def run(self, ext_run_evn: ExtRunEnv, *args, **kwargs):
        """
            程序入口
        :param ext_run_evn:
        :param args:
        :param kwargs:
        :return:
        """
        self.ext_run_env = ext_run_evn
        self.draw_pad()
        self.layer = ext_run_evn.vc.register_layer()

        with dpg.handler_registry() as self.tag_hr:
            dpg.add_mouse_move_handler(callback=self.draw_cross)

    def stop(self):
        """
            停止进程
        :return:
        """
        dpg.delete_item(self.layer)
        dpg.delete_item(self.tag_hr)

    def draw_cross(self, sender, app_data):
        """
            绘制十字线
        :param sender:
        :param app_data:
        :return:
        """
        try:
            dpg.delete_item(self.layer, children_only=True)
        except Exception:
            ...

        if self.is_draw and dpg.is_item_hovered(self.ext_run_env.vc.tag_dl):
            x, y = dpg.get_drawing_mouse_pos()
            w, h = dpg.get_item_rect_size(self.ext_run_env.vc.tag_dl)

            dpg.draw_line(
                [x, 0], [x, h], parent=self.layer, color=dpg.get_value(self.tag_cp)
            )
            dpg.draw_line(
                [0, y], [w, y], parent=self.layer, color=dpg.get_value(self.tag_cp)
            )
            dpg.set_value(self.tag_info, f"x/w:{x:.0f}/{w} \n y/h:{y:.0f}/{h} \n Scale:{x/w:>.4f}:{y/h:>.4f}")


    def switch(self, sender, app_data):
        """
            切换开关
        :param sender:
        :param app_data:
        :return:
        """
        self.is_draw = app_data
        if not self.is_draw:
            dpg.delete_item(self.layer, children_only=True)

    def draw_pad(self):
        """
            绘制面板
        :return:
        """

        # 绘制控制面板，设置 parent = ExtRunEnv.tag_pad
        with dpg.collapsing_header(label='CrossLine', parent=self.ext_run_env.tag_pad):
            dpg.add_checkbox(label='Draw', default_value=self.is_draw, callback=self.switch)
            self.tag_info = dpg.add_text('')
            self.tag_cp = dpg.add_color_picker()
