# -*- coding: utf-8 -*-
"""
    面板组件
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-29 1.4.0 Me2sY
            1.适配新架构
            2.新增部分功能按键

        2024-08-15 1.3.0 Me2sY  发布初版

        2024-08-13 0.1.2 Me2sY
            1.整合ADB Key Event 功能至Switch Pad
            2.新增 Icon按钮

        2024-08-10 0.1.1 Me2sY  分离
"""

__author__ = 'Me2sY'
__version__ = '1.4.0'

__all__ = [
    'CPMNumPad', 'CPMControlPad',
    'CPMSwitchPad'
]

from typing import Callable

import dearpygui.dearpygui as dpg

from myscrcpy.utils import ADBKeyCode
from myscrcpy.gui.dpg.components.component_cls import Component


class CPMPad(Component):
    """
        控制面板
    """

    DEFAULT_CONTAINER_ADD_METHOD = dpg.add_group

    def __init__(self, callback: Callable = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._callback = callback

    def callback(self, user_data):
        if self._callback:
            self._callback(user_data)

    def update(self, callback: Callable, *args, **kwargs):
        self._callback = callback
        return self


class CPMNumPad(CPMPad):
    """
        数字键盘
        使用 ADB Key event 实现
    """
    def setup_inner(self, *args, **kwargs):
        def show_input(value):
            if value == ADBKeyCode.KB_BACKSPACE:
                dpg.set_value(self.tag_ipt, dpg.get_value(self.tag_ipt)[:-1])
            elif value == ADBKeyCode.KB_ENTER:
                dpg.set_value(self.tag_ipt, '')
            else:
                dpg.set_value(self.tag_ipt, dpg.get_value(self.tag_ipt) + '*')

        btn_cfg = dict(width=25, height=25, callback=lambda s, a, u: self.callback(u) or show_input(u))
        self.tag_ipt = dpg.add_input_text(width=-1, enabled=False)
        for i in range(3):
            with dpg.group(horizontal=True):
                for j in range(1, 4):
                    bn = i * 3 + j
                    dpg.add_button(label=f"{bn}", user_data=ADBKeyCode[f"KB_{bn}"], **btn_cfg)

        with dpg.group(horizontal=True):
            dpg.add_button(label="|<-", user_data=ADBKeyCode.KB_BACKSPACE, **btn_cfg)
            dpg.add_button(label="0", user_data=ADBKeyCode.KB_0, **btn_cfg)
            dpg.add_button(label="OK", user_data=ADBKeyCode.KB_ENTER, **btn_cfg)

    def clear(self):
        dpg.set_value(self.tag_ipt, '')


class CPMControlPad(CPMPad):
    """
        控制面板
        # TODO 2024-08-15 Me2sY ADB Shell功能 调试功能等
    """

    def callback(self, user_data):
        code = dpg.get_value(self.tag_ipt)
        super().callback(code)
        if self._callback:
            dpg.set_value(self.tag_msg, f"{code} Send")

    def setup_inner(self, *args, **kwargs):
        self.tag_msg = dpg.add_text(f"Send KeyCode")
        self.tag_ipt = dpg.add_input_int(min_value=0, max_value=999, on_enter=True, width=-1)
        dpg.add_button(label='send', height=35, width=-1, callback=self.callback)


class CPMSwitchPad(CPMPad):
    """
        开关/ADB控制 面板
    """

    WIDTH = 38

    @classmethod
    def default_container(cls, parent=None):
        return cls.create_container(dpg.add_child_window, parent, border=False, width=cls.WIDTH, no_scrollbar=True)

    def switch_show(self, sender):
        """
            开关
        """
        self.status = not self.status
        self._switch_show_callback(self.status)
        dpg.configure_item(self.tag_ib_switch, texture_tag=self.icon_map[self.status])

    def setup_inner(self, icons, *args, **kwargs):

        self.status = False
        self.icon_map = {
            True: icons['lp_close'],
            False: icons['lp_open']
        }

        btn_icon_cfg = dict(height=30, width=30, callback=lambda s, a, u: self.callback(u))

        dpg.add_image_button(icons['power'], user_data=ADBKeyCode.POWER, **btn_icon_cfg)
        dpg.add_spacer(height=3)

        dpg.add_image_button(icons['switch'], user_data=ADBKeyCode.APP_SWITCH, **btn_icon_cfg)
        dpg.add_separator()
        dpg.add_image_button(icons['home'], user_data=ADBKeyCode.HOME, **btn_icon_cfg)
        dpg.add_separator()
        dpg.add_image_button(icons['back'], user_data=ADBKeyCode.BACK, **btn_icon_cfg)
        dpg.add_separator()
        dpg.add_image_button(icons['notification'], user_data=ADBKeyCode.NOTIFICATION, **btn_icon_cfg)
        dpg.add_image_button(icons['settings'], user_data=ADBKeyCode.SETTINGS, **btn_icon_cfg)
        dpg.add_spacer(height=3)
        self.tag_ib_switch = dpg.add_image_button(
            self.icon_map[self.status], height=30, width=30, callback=self.switch_show
        )
        dpg.add_spacer(height=3)

        with dpg.child_window(no_scrollbar=True, border=False, width=self.WIDTH):
            dpg.add_image_button(icons['play'], user_data=ADBKeyCode.KB_MEDIA_PLAY_PAUSE, **btn_icon_cfg)
            dpg.add_image_button(icons['p_next'], user_data=ADBKeyCode.KB_MEDIA_NEXT_TRACK, **btn_icon_cfg)
            dpg.add_image_button(icons['p_pre'], user_data=ADBKeyCode.KB_MEDIA_PREV_TRACK, **btn_icon_cfg)
            dpg.add_separator()
            dpg.add_image_button(icons['mic_off'], user_data=ADBKeyCode.MIC_MUTE, **btn_icon_cfg)
            dpg.add_image_button(icons['vol_off'], user_data=ADBKeyCode.KB_VOLUME_MUTE, **btn_icon_cfg)
            dpg.add_image_button(icons['vol_up'], user_data=ADBKeyCode.KB_VOLUME_UP, **btn_icon_cfg)
            dpg.add_image_button(icons['vol_down'], user_data=ADBKeyCode.KB_VOLUME_DOWN, **btn_icon_cfg)
            dpg.add_separator()
            dpg.add_image_button(icons['camera'], user_data=ADBKeyCode.CAMERA, **btn_icon_cfg)
            dpg.add_image_button(icons['zoom_in'], user_data=ADBKeyCode.ZOOM_IN, **btn_icon_cfg)
            dpg.add_image_button(icons['zoom_out'], user_data=ADBKeyCode.ZOOM_OUT, **btn_icon_cfg)
            dpg.add_separator()
            dpg.add_image_button(icons['brightness_up'], user_data=ADBKeyCode.BRIGHTNESS_UP, **btn_icon_cfg)
            dpg.add_image_button(icons['brightness_down'], user_data=ADBKeyCode.BRIGHTNESS_DOWN, **btn_icon_cfg)
            dpg.add_separator()
            dpg.add_image_button(icons['screenshot'], user_data=ADBKeyCode.KB_PRINTSCREEN, **btn_icon_cfg)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Screenshot')
            dpg.add_image_button(icons['voice'], user_data=ADBKeyCode.VOICE_ASSIST, **btn_icon_cfg)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Voice Assist')
            dpg.add_image_button(icons['explore'], user_data=ADBKeyCode.EXPLORER, **btn_icon_cfg)
            dpg.add_image_button(icons['calculate'], user_data=ADBKeyCode.CALCULATOR, **btn_icon_cfg)
            dpg.add_image_button(icons['calendar'], user_data=ADBKeyCode.CALENDAR, **btn_icon_cfg)
            dpg.add_image_button(icons['call'], user_data=ADBKeyCode.CALL, **btn_icon_cfg)
            dpg.add_image_button(icons['contacts'], user_data=ADBKeyCode.CONTACTS, **btn_icon_cfg)

    def update(self, callback: Callable, switch_show_callback: Callable, *args, **kwargs):
        self._callback = callback
        self._switch_show_callback = switch_show_callback
        self.status = kwargs.get('status', False)
