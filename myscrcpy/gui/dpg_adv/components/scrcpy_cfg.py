# -*- coding: utf-8 -*-
"""
    Scrcpy Cfg Component
    ~~~~~~~~~~~~~~~~~~~~
    Scrcpy 连接属性配置组件

    Log:
        2024-08-15 1.3.0 Me2sY  发布初版

        2024-08-15 0.1.3 Me2sY  适配 ValueManager 进行配置存储及管理

        2024-08-11 0.1.2 Me2sY 完成结构改造及全部功能开发

        2024-08-10 0.1.1 Me2sY
            1.分离
            2.根据新 Component 结构进行改造
"""

__author__ = 'Me2sY'
__version__ = '1.3.0'

__all__ = [
    'CPMScrcpyCfg', 'CPMScrcpyCfgController'
]

import time
from typing import Callable

import dearpygui.dearpygui as dpg

from myscrcpy.controller.device_controller import DeviceController
from myscrcpy.controller.video_socket_controller import VideoSocketController as VSC
from myscrcpy.controller.audio_socket_controller import AudioSocketController as ASC
from myscrcpy.utils import ValueManager

from myscrcpy.gui.dpg_adv.components.component_cls import *


class CPMScrcpyCfgVideoCamera(ValueComponent):
    """
        VideoCamera Component
        # TODO 2024-08-15 Me2sY 获取 Device AR/Size 信息
    """

    DEFAULT_CONTAINER_ADD_METHOD = dpg.add_group

    def setup_inner(self, *args, **kwargs):

        with dpg.group(horizontal=True):
            dpg.add_input_int(
                label='c_id', source=self.value_controller.tag('camera_id'), width=85, min_value=0, max_value=99
            )
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('camera_id 0/1/etc')
            dpg.add_drag_int(label='fps', source=self.value_controller.tag('camera_fps'), width=70)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('camera fps 30/120/240/480/etc')

        dpg.add_input_text(label='camera_ar', width=-90, source=self.value_controller.tag('camera_ar'))

        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(f"Like 1:1 or 4:3 or etc")
            dpg.add_text(f"(AR OR Size, Use scrcpy --list-camera-sizes)")

        dpg.add_input_text(
            label='camera_size', width=-90, source=self.value_controller.tag('camera_size'),
        )
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(f"Like 800x600 or 1920x1080 or etc")
            dpg.add_text(f"(AR OR Size, Use scrcpy --list-camera-sizes)")


class CPMScrcpyCfgBase(ValueComponent):

    HEIGHT_CONTAINER = 185

    @classmethod
    def default_container(cls, parent=None):
        return cls.create_container(dpg.add_child_window, parent, height=cls.HEIGHT_CONTAINER, width=-1)


class CPMScrcpyCfgVideo(CPMScrcpyCfgBase):
    """
        视频连接参数组件
    """

    def source_changed(self, sender, app_data):
        """
            当 Source 为 camera 时，显示Camera配置面板
        """
        if self.value_controller.get_value('video_source') == VSC.SOURCE_CAMERA:
            dpg.show_item(self.tag_g_camera)
        else:
            dpg.hide_item(self.tag_g_camera)

    def setup_inner(self, *args, **kwargs):
        dpg.add_checkbox(label='Enable', source=self.value_controller.tag('video'))
        with dpg.group(horizontal=True):

            dpg.add_drag_int(
                label='max_size', source=self.value_controller.tag('max_size'),
                width=60, min_value=1, max_value=9999, speed=100
            )

            dpg.add_drag_int(
                label='fps', source=self.value_controller.tag('fps'),
                width=60, min_value=1, max_value=480, speed=10
            )

        with dpg.group(horizontal=True):
            dpg.add_combo(
                label='codec', items=[VSC.CODEC_H264, VSC.CODEC_H265],
                source=self.value_controller.tag('video_codec'), width=60
            )
            self.tag_cb_source = dpg.add_combo(
                label='d/c', items=[VSC.SOURCE_DISPLAY, VSC.SOURCE_CAMERA],
                source=self.value_controller.tag('video_source'), callback=self.source_changed, width=80
            )
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Video Source')

        with dpg.group(show=self.value_controller.get_value('video_source') == VSC.SOURCE_CAMERA) as self.tag_g_camera:
            CPMScrcpyCfgVideoCamera(self.value_controller).draw()

    def update(self, *args, **kwargs):
        self.source_changed(None, None)


class CPMScrcpyCfgAudio(CPMScrcpyCfgBase):
    """
        音频连接参数组件
    """
    def setup_inner(self, *args, **kwargs):
        dpg.add_checkbox(label='Enable', source=self.value_controller.tag('audio'))
        dpg.add_combo(
            items=[ASC.SOURCE_OUTPUT, ASC.SOURCE_MIC], source=self.value_controller.tag('audio_source'),
            width=-45, label='Source'
        )


class CPMScrcpyCfgControl(CPMScrcpyCfgBase):
    """
        控制连接参数组件
    """
    def setup_inner(self, *args, **kwargs):
        dpg.add_checkbox(label='Enable', source=self.value_controller.tag('control'))
        dpg.add_checkbox(label='Close Screen', source=self.value_controller.tag('close_screen'))


class CPMScrcpyCfgController(ValueComponent):
    """
        Scrcpy Cfg 控制器，用于管理设备相关配置
        使用 ValueManager 保存配置
    """

    DEFAULT_CONTAINER_ADD_METHOD = dpg.add_group
    VM_NAME = 'scrcpy_cfg'

    @staticmethod
    def default_cfg() -> dict:
        return {
            'video': True,
            'max_size': 1920,
            'fps': 60,
            'video_codec': VSC.CODEC_H264,
            'video_source': VSC.SOURCE_DISPLAY,
            'camera_id': 0,
            'camera_fps': 60,
            'camera_ar': '',
            'camera_size': '',
            'audio': True,
            'audio_source': ASC.SOURCE_OUTPUT,
            'control': True,
            'close_screen': True
        }

    @classmethod
    def get_config(cls, device_serial: str, cfg_name: str) -> dict:
        """
            获取设备指定名称的Scrcpy配置文件
        """
        return ValueManager(cls.VM_NAME).get_value(f"dev_{device_serial}", default_value={}).get(cfg_name, None)

    @property
    def config_name(self) -> str:
        return dpg.get_value(self.tag_cb_cfgs)

    def load_device_configs(self, device_serial: str):
        """
            加载设备对应Scrcpy配置文件
        """
        self.configs = self.vm.get_value(
            f"dev_{device_serial}",
            default_value={'default': self.default_cfg()}
        )

        for key, value in self.configs['default'].items():
            self.value_controller.set_default_value(key, value)

    def setup_inner(self, *args, **kwargs):
        with dpg.group(horizontal=True):
            dpg.add_text('Config:')
            self.tag_cb_cfgs = dpg.add_combo(
                items=['default'], default_value='default', width=70, callback=self.load_config
            )
            dpg.add_button(label='Save', callback=self.save_config)
            dpg.add_spacer(width=1)
            dpg.add_button(label='+', width=22, callback=self.new_config)
            dpg.add_button(label='-', width=22, callback=self.delete_config)

    def new_config(self):
        """
            新建 Scrcpy 连接配置
        """
        def save():
            _name = dpg.get_value(tag_ipt_name)
            if _name is None or _name == '':
                return
            else:
                self.configs[_name] = self.default_cfg()
                dpg.configure_item(self.tag_cb_cfgs, items=list(self.configs.keys()), default_value=_name)
                self.load_config(self.tag_cb_cfgs, _name)
                dpg.delete_item(tag_win)

        with dpg.window(modal=True, label='New Config', no_resize=True, width=252) as tag_win:
            tag_ipt_name = dpg.add_input_text(label='Config Name', width=-100)
            with dpg.group(horizontal=True):
                dpg.add_button(label='Create', width=150, height=45, callback=save)
                dpg.add_button(label='Close', width=-1, height=45, callback=lambda: dpg.delete_item(tag_win))

    def save_config(self):
        """
            保存配置文件
        """
        if not hasattr(self, 'device') or self.device is None:
            return

        cfg_name = dpg.get_value(self.tag_cb_cfgs)
        key = f"dev_{self.device.serial_no}"

        self.configs[cfg_name] = self.value_controller.dump()

        tag_win_loading = TempModal.draw_loading(f'Saved to {cfg_name}')

        self.vm.set_value(key, self.configs)

        time.sleep(0.2)
        dpg.delete_item(tag_win_loading)

    def load_config(self, sender, app_data, user_data=None):
        """
            装载指定配置文件
        """
        self.value_controller.load(self.configs[app_data])
        self.update_callback(app_data, self.configs[app_data])

    def update(self, device: DeviceController, update_callback: Callable, *args, **kwargs):
        """
            加载DeviceController 获取配置并更新界面
        """
        self.device = device
        self.load_device_configs(self.device.serial_no)
        self.update_callback = update_callback

        dpg.configure_item(self.tag_cb_cfgs, items=list(self.configs.keys()), default_value='default')

        self.load_config(self.tag_cb_cfgs, 'default')

    def delete_config(self):
        """
            删除配置
        """
        def _delete():
            """
                删除配置
            """
            self.configs.pop(cfg_name)
            dpg.configure_item(self.tag_cb_cfgs, items=list(self.configs.keys()), default_value='default')
            self.load_config(self.tag_cb_cfgs, 'default')
            self.vm.set_value(f"dev_{self.device.serial_no}", self.configs)

            dpg.delete_item(tag_win)

        cfg_name = dpg.get_value(self.tag_cb_cfgs)
        if cfg_name == 'default':
            return
        else:
            with dpg.window(
                    modal=True, label='Warning!', no_resize=True, width=252, no_scrollbar=True,
                    no_title_bar=True
            ) as tag_win:
                dpg.add_text(default_value=f"Delete Config {cfg_name}?")
                with dpg.group(horizontal=True):
                    dpg.add_button(label='Confirm', callback=_delete, width=100, height=35)
                    dpg.add_button(label='Cancel', callback=lambda: dpg.delete_item(tag_win), width=-1, height=35)


class CPMScrcpyCfg(ValueComponent):
    """
        Scrcpy 连接参数组件
    """

    @classmethod
    def default_container(cls, parent=None):
        return cls.create_container(
            dpg.add_child_window, parent, height=CPMScrcpyCfgBase.HEIGHT_CONTAINER + 76, width=-1
        )

    def setup_inner(self, *args, **kwargs):

        self.cpm_cfg_controller = CPMScrcpyCfgController(self.value_controller).draw()
        self.value_controller.load(self.cpm_cfg_controller.default_cfg())

        dpg.add_separator()

        with dpg.tab_bar():
            with dpg.tab(label='Video'):
                self.cpm_video = CPMScrcpyCfgVideo(self.value_controller).draw()
            with dpg.tab(label='Audio'):
                CPMScrcpyCfgAudio(self.value_controller).draw()
            with dpg.tab(label='Control'):
                CPMScrcpyCfgControl(self.value_controller).draw()

    def update(self, device: DeviceController, *args, **kwargs):
        def load_callback(cfg_name, scrcpy_config):
            self.cpm_video.update()

        self.cpm_cfg_controller.update(device, load_callback)

    def use(self) -> dict:
        self.cpm_cfg_controller.save_config()
        return self.value_controller.dump()

    @property
    def config_name(self) -> str:
        return self.cpm_cfg_controller.config_name
