# -*- coding: utf-8 -*-
"""
    Device Components
    ~~~~~~~~~~~~~~~~~~
    设备相关组件

    Log:
        2024-08-15 1.3.0 Me2sY  发布初版

        2024-08-14 0.1.3 Me2sY  去除WindowSize信息展示（加载慢），加速设备加载

        2024-08-11 0.1.2 Me2sY  完成全部功能开发及初步测试

        2024-08-10 0.1.1 Me2sY  分离
"""

__author__ = 'Me2sY'
__version__ = '1.3.0'

__all__ = [
    'WinDevices', 'CPMDevice'
]

import time
from functools import partial
from typing import Callable

from adbutils import adb
import dearpygui.dearpygui as dpg
from loguru import logger

from myscrcpy.utils import ValueManager as VM
from myscrcpy.controller.device_controller import DeviceController, DeviceFactory
from myscrcpy.controller.video_socket_controller import VideoSocketController as VSC, VideoCamera
from myscrcpy.controller.audio_socket_controller import AudioSocketController as ASC
from myscrcpy.controller.control_socket_controller import ControlSocketController as CSC
from myscrcpy.gui.dpg_adv.components.component_cls import *
from myscrcpy.gui.dpg_adv.components.scrcpy_cfg import *


class CPMDeviceInfo(ValueComponent):
    """
        设备信息组件
    """

    HEIGHT_CONTAINER = 128

    @classmethod
    def default_container(cls, parent=None):
        return cls.create_container(dpg.add_child_window, parent, height=cls.HEIGHT_CONTAINER, autosize_x=True)

    def connect_adb(self):
        """
            将设备连接至ADB
        """
        wlan = self.device.wlan_ip
        port = self.value_controller.get_value('port')
        if wlan and 65535 > port > 0:
            try:
                logger.info(adb.connect(f"{wlan}:{port}", timeout=2))
                logger.info(f"Connected to Adb {wlan}:{port}")
            except Exception as e:
                logger.error(f"Adb Connect Error: {e}")

    def set_tcpip_port(self):
        """
            设置设备无线端口
        """
        if hasattr(self, 'device') and self.device and 65535 > self.value_controller.get_value('port') > 1:

            tag_win_loading = TempModal.draw_loading('Reconnecting...')
            self.device.set_tcpip(self.value_controller.get_value('port'))
            time.sleep(2)
            self.update(self.device)
            dpg.delete_item(tag_win_loading)

    def setup_inner(self):
        for attr, default_value in [
            ('serial_no', 'Not Connected'),
            ('brand', ''), ('release', -1), ('model', ''), ('sdk', -1),
            ('wlan', ''), ('port', -1),
        ]:
            self.value_controller.set_default_value(attr, default_value)

        with dpg.group(horizontal=True):
            dpg.add_input_text(label='serial', enabled=False, width=160, source=self.value_controller.tag('serial_no'))
            dpg.add_button(label='<->', width=30, callback=self.connect_adb)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Connect to ADB')

        with dpg.group(horizontal=True):
            dpg.add_input_text(label=':', source=self.value_controller.tag('wlan'), enabled=False, width=105)
            dpg.add_drag_int(
                label='port', source=self.value_controller.tag('port'), width=45, min_value=-1, max_value=65535
            )
            dpg.add_button(label='SET', width=30, callback=self.set_tcpip_port)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Set TCPIP Mode')

        with dpg.group(horizontal=True):
            dpg.add_input_text(label='brand', source=self.value_controller.tag('brand'), enabled=False, width=80)
            dpg.add_drag_int(
                label='android', source=self.value_controller.tag('release'), width=30, no_input=True, enabled=False)

        with dpg.group(horizontal=True):
            dpg.add_input_text(label='model', source=self.value_controller.tag('model'), enabled=False, width=80)
            dpg.add_drag_int(
                label='sdk', source=self.value_controller.tag('sdk'), width=30, no_input=True, enabled=False)

    def update(self, device: DeviceController):
        """
            加载设备，显示设备信息
        """
        self.device = device
        wlan_ip = device.wlan_ip
        if wlan_ip is None:
            wlan_ip = 'Not Connected'
        self.value_controller.load({
            **device.info._asdict(),
            'wlan': wlan_ip,
            'port': device.tcpip_port,
        })


class CPMDevice(ValueComponent):
    """
        设备组件
        显示设备信息、配置Scrcpy连接信息
    """

    DEFAULT_CONTAINER_ADD_METHOD = dpg.add_child_window
    N_RECENT_RECORDS = 10

    def setup_inner(self, icons):
        self.icons = {
            'wifi': {
                True: icons['wifi'],
                False: icons['wifi_off']
            },
            'usb': {
                True: icons['usb'],
                False: icons['usb_off']
            }
        }

        self.cpm_device_info = CPMDeviceInfo(
            parent_container=CPMDeviceInfo.default_container(self.tag_container)
        ).draw()

        self.cpm_scrcpy_cfg = CPMScrcpyCfg(
            parent_container=CPMScrcpyCfg.default_container(self.tag_container)
        ).draw()

        with dpg.group(horizontal=True):
            self.tag_btn_usb = dpg.add_image_button(
                texture_tag=icons['usb_off'], width=32, height=32, enabled=False,
            )
            self.tag_btn_wifi = dpg.add_image_button(
                texture_tag=icons['wifi_off'], width=32, height=32, enabled=False
            )
            self.tag_btn_connect = dpg.add_button(
                label='Connect', height=40, width=-50, callback=self.connect, enabled=False
            )
            self.tag_btn_choose = dpg.add_button(
                label='ADB', height=40, width=-1, callback=self.choose, enabled=False
            )
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Only Use ADB Control')

    def connect(self):
        """
            连接至Scrcpy
        """
        if not hasattr(self, 'device') or self.device is None:
            return None

        cfg = self.cpm_scrcpy_cfg.use()

        controllers = self.cfg2controllers(cfg)

        # 创建 Scrcpy 连接
        if controllers:

            tag_win_loading = TempModal.draw_loading(f"Connecting to {self.device.serial_no}")

            dpg.configure_item(self.tag_btn_connect, enabled=False, label='Connecting...')

            if self.device.is_scrcpy_running:
                try:
                    self.device.close()
                except Exception as e:
                    pass

            self.device = DeviceFactory.device(self.device.serial_no)
            self.device.connect(*controllers)
            self.device.scrcpy_cfg = self.cpm_scrcpy_cfg.config_name

            # 新增 最近连接设备记录
            records = VM.get_global('recent_connected', [])
            record = [self.device.adb_dev.serial, self.cpm_scrcpy_cfg.config_name]

            try:
                records.remove(record)
            except ValueError:
                pass

            records.insert(0, record)

            VM.set_global('recent_connected', records[:self.N_RECENT_RECORDS])

            dpg.delete_item(tag_win_loading)

            self.connect_callback(self.device)
        else:
            with dpg.window(no_move=True, no_resize=True, no_title_bar=True) as tag_win:
                dpg.add_text("No V/A/C Selected!")
                dpg.add_separator()
                dpg.add_button(label='Close', width=-1, height=35, callback=lambda: dpg.delete_item(tag_win))

    @staticmethod
    def cfg2controllers(scrcpy_cfg: dict) -> list:
        """
            解析字典型配置文件，创建 V/A/C 实例
        """
        controllers = []
        if scrcpy_cfg.get('video', False):

            camera = None

            if scrcpy_cfg.get('video_source', VSC.SOURCE_DISPLAY) == VSC.SOURCE_CAMERA:
                camera = VideoCamera(**scrcpy_cfg)

            controllers.append(
                VSC(**scrcpy_cfg, camera=camera)
            )

        if scrcpy_cfg.get('audio', False):
            controllers.append(ASC(**scrcpy_cfg))

        if scrcpy_cfg.get('control', False):
            controllers.append(CSC(**scrcpy_cfg))

        return controllers

    def choose(self):
        """
            仅选择，回传ADBClient
        """
        self.choose_callback(self.device)

    def update(self, device: DeviceController, connect_callback: Callable, choose_callback: Callable):
        """
            加载设备，显示设备信息及Scrcpy配置
        """
        tag_win_loading = TempModal.draw_loading(
            f"Loading {device.info.brand} / {device.info.model}\n{device.serial_no}"
        )

        self.device = device
        self.connect_callback = connect_callback
        self.choose_callback = choose_callback
        self.cpm_device_info.update(device)
        self.cpm_scrcpy_cfg.update(device)

        _usb = device.usb_dev is not None
        dpg.configure_item(
            self.tag_btn_usb, texture_tag=self.icons['usb'][_usb], enabled=_usb
        )

        _wifi = device.net_dev is not None
        dpg.configure_item(
            self.tag_btn_wifi, texture_tag=self.icons['wifi'][_wifi], enabled=_wifi
        )

        dpg.configure_item(self.tag_btn_connect, enabled=True and (_usb or _wifi))
        dpg.configure_item(self.tag_btn_choose, enabled=True and (_usb or _wifi))

        dpg.delete_item(tag_win_loading)


class CPMDeviceList(Component):
    """
        设备列表组件
    """

    WIDTH = 110

    @classmethod
    def default_container(cls, parent=None):
        return cls.create_container(dpg.add_child_window, parent, width=cls.WIDTH)

    def refresh(self):
        self._draw_devices()

    def connect_to_tcpip(self):
        """
            连接 Adb Wifi Device
        """
        def adb_connect():
            try:
                dpg.set_value(tag_txt_msg, 'Connecting... Timeout=5s')
                dpg.set_value(tag_txt_info, '')
                msg = adb.connect(dpg.get_value(tag_ipt_addr), timeout=5)
                dpg.set_value(tag_txt_msg, msg[:30] + '...')
                dpg.set_value(tag_txt_info, msg)
                self.refresh()
            except Exception as e:
                dpg.set_value(tag_txt_msg, 'Connect Failed')
                dpg.set_value(tag_txt_info, str(e))

        with dpg.window(
                modal=True, no_move=True, no_resize=True, no_title_bar=True, no_scrollbar=True, width=240
        ) as tag_win:
            dpg.add_text('Connect a WIFI Device to ADB')
            tag_ipt_addr = dpg.add_input_text(label='[IP:]PORT', width=-60, on_enter=True, callback=adb_connect)
            with dpg.group(horizontal=True):
                dpg.add_button(label='ADB Connect', height=35, width=-70, callback=adb_connect)
                dpg.add_button(label='Close', height=35, width=-1, callback=lambda: dpg.delete_item(tag_win))
            tag_txt_msg = dpg.add_text('Ready to Connect')
            with dpg.tooltip(dpg.last_item()):
                tag_txt_info = dpg.add_text('Ready to Connect')

    def _draw_devices(self):
        """
            加载设备列表
        """

        tag_win_loading = TempModal.draw_loading('Loading Devices')

        try:
            dpg.delete_item(self.tag_group, children_only=True)
        except Exception as e:
            pass

        DeviceFactory.load_devices()

        btn_cfg = dict(width=-1, height=25, callback=self.choose_dev, parent=self.tag_group)
        for ser, device in DeviceFactory.devices().items():

            msg = f"{device.info.brand[:6]}/{device.info.serial_no}"[:11]
            dpg.add_button(
                label=msg, user_data=device, **btn_cfg, enabled=device.info.is_scrcpy_supported
            )
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text(default_value=str(device.info.serial_no))
                if not device.info.is_scrcpy_supported:
                    dpg.add_text(f"Warning!!! This Device Not Support Scrcpy. {device.info.sdk} < API 21")

        if DeviceFactory.device_num() > 0:
            self.choose_dev(None, None, list(DeviceFactory.devices().values())[0])

        dpg.delete_item(tag_win_loading)

    def choose_dev(self, sender, app_data, device: DeviceController):
        self.choose_callback(device)

    def setup_inner(self, icons, *args, **kwargs):
        with dpg.group(horizontal=True):
            dpg.add_image_button(
                icons['refresh'],  width=30, height=30,
                callback=self.refresh, background_color=(234, 51, 35)
            )
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Refresh Adb')

            dpg.add_image_button(
                icons['link'], width=30, height=30, callback=self.connect_to_tcpip,
                background_color=(21, 200, 78)
            )
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Link To Tcpip Device')

        dpg.add_separator()
        self.tag_group = dpg.add_group()

    def update(self, choose_callback, *args, **kwargs):
        self.choose_callback = choose_callback
        self._draw_devices()


class WinDevices(ValueComponent):
    """
        设备选择窗口
    """

    WIDTH = 400
    HEIGHT = 495

    @classmethod
    def default_container(cls, parent=None):
        return partial(
            dpg.add_window, width=cls.WIDTH, height=cls.HEIGHT, no_resize=True, no_scrollbar=True, no_collapse=True,
            label='Choose A Device', pos=(5, 5),
        )

    def setup_inner(self, icons, *args, **kwargs):

        def connect_scrcpy_callback(device: DeviceController):
            dpg.delete_item(self.tag_container)
            self.scrcpy_callback(device)

        def choose_adb_callback(device: DeviceController):
            dpg.delete_item(self.tag_container)
            self.choose_callback(device)

        def _choose_callback(device: DeviceController):
            self.cpm_device.update(device, connect_scrcpy_callback, choose_adb_callback)

        with dpg.group(horizontal=True, parent=self.tag_container) as tag_g:
            self.cpm_device_list = CPMDeviceList().draw(icons)
            self.cpm_device = CPMDevice(parent_container=CPMDevice.default_container(tag_g)).draw(icons)

        self.cpm_device_list.update(_choose_callback)

    def update(self, choose_callback, scrcpy_callback, *args, **kwargs):
        self.choose_callback = choose_callback
        self.scrcpy_callback = scrcpy_callback
        return self


if __name__ == '__main__':

    import dearpygui.dearpygui as dpg
    from loguru import logger
    from myscrcpy.utils import Param
    dpg.create_context()

    Static.load()

    with dpg.font_registry():
        with dpg.font(
                Param.PATH_LIBS.joinpath('AlibabaPuHuiTi-3-45-Light.ttf').__str__(),
                size=18,
        ) as def_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
    dpg.bind_font(def_font)

    wd = WinDevices().draw(Static.ICONS).update(
        lambda x: ..., lambda x: ...
    )

    dpg.create_viewport(title='Test Case For Devices', x_pos=900, y_pos=600)

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.stop_dearpygui()
    dpg.destroy_context()
