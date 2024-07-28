# -*- coding: utf-8 -*-
"""
    Devices
    ~~~~~~~~~~~~~~~~~~
    主窗口，显示所有设备，进行下一步操作

    Log:
        2024-07-28 1.0.0 Me2sY
            发布初版

        2024-06-18 0.1.1 Me2sY
            重构

        2024-06-04 0.1.0 Me2sY
            创建

"""

__author__ = 'Me2sY'
__version__ = '1.0.0'

__all__ = []

import time

import dearpygui.dearpygui as dpg

from myscrcpy.device_controller import DeviceController, DeviceFactory
from myscrcpy.gui.dpg.window_video import WindowVideo


class WindowDevice:
    """
        单个Device设置、启动窗口
    """

    def __init__(self, device: DeviceController):
        self.device = device

        self.tag_win = dpg.generate_uuid()
        self.tag_ipt_fps = dpg.generate_uuid()
        self.tag_ipt_max_size = dpg.generate_uuid()
        self.tag_cb_zmq_c = dpg.generate_uuid()
        self.tag_ipt_zmq_c_url = dpg.generate_uuid()
        self.tag_ipt_record_frames = dpg.generate_uuid()

        self.tag_cb_zmq_v = dpg.generate_uuid()
        self.tag_ipt_zmq_v_url = dpg.generate_uuid()
        self.tag_btn_connect = dpg.generate_uuid()
        self.tag_btn_close = dpg.generate_uuid()
        self.tag_txt_device = dpg.generate_uuid()

    def connect(self):
        dpg.configure_item(self.tag_btn_connect, enabled=False)

        self.device.connect_to_scrcpy(
            max_size=dpg.get_value(self.tag_ipt_max_size),
            fps=dpg.get_value(self.tag_ipt_fps),
            record_frames=dpg.get_value(self.tag_ipt_record_frames),
            v_zmq_publish=dpg.get_value(self.tag_cb_zmq_v),
            v_zmq_url=dpg.get_value(self.tag_ipt_zmq_v_url),
            c_zmq_pull=dpg.get_value(self.tag_cb_zmq_c),
            c_zmq_url=dpg.get_value(self.tag_ipt_zmq_c_url)
        )
        time.sleep(1)
        dpg.configure_item(self.tag_btn_connect, label='Connected!')
        dpg.set_value(self.tag_txt_device, self.device_info())

        self.window_video = WindowVideo(self.device)
        self.window_video.init()

        def _close():
            dpg.configure_item(self.tag_btn_connect, label='Ready to Connect', enabled=True)
            self.window_video.close()

        dpg.configure_item(self.window_video.tag_win_main, on_close=_close)

    def device_info(self) -> str:
        return f"Device => {self.device}"

    def init(self):
        with dpg.window(label=self.device.serial, tag=self.tag_win, autosize=True, pos=(100, 100)):
            dpg.add_text(self.device_info(), tag=self.tag_txt_device)

            device_height = self.device.coordinate.height

            dpg.add_separator()
            dpg.add_text('VideoSocket:')
            dpg.add_checkbox(
                label='close Screen', default_value=True,
                callback=lambda s, a: self.device.cs.set_screen_on(not a)
            )
            dpg.add_drag_int(
                label='max_size',
                default_value=device_height // 1.5,
                min_value=device_height // 10, max_value=self.device.coordinate.max_size,
                speed=self.device.coordinate.height // 10,
                tag=self.tag_ipt_max_size
            )
            dpg.add_drag_int(label='fps', default_value=120, min_value=30, max_value=120, speed=30,
                             tag=self.tag_ipt_fps)
            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_button(
                    label='Ready to Connect', width=280, height=50, callback=self.connect, tag=self.tag_btn_connect
                )
                dpg.add_spacer(width=40)
                dpg.add_button(
                    label='Close', width=280, height=50, callback=self.close
                )

    def close(self):
        if self.device.is_scrcpy_running:
            self.device.close()
        dpg.delete_item(self.tag_win)


class WindowDevices:
    """
        Device 列表
    """

    def __init__(self):
        self.tag_win = dpg.generate_uuid()
        self.tag_btn_load = dpg.generate_uuid()
        self.tag_group_device = dpg.generate_uuid()

    def init(self):
        with dpg.window(label="Devices", autosize=True, tag=self.tag_win):
            def _init_device_win(sender, appdata):
                WindowDevice(DeviceFactory.device(dpg.get_item_label(sender))).init()

            def _load_devices():
                dpg.delete_item(self.tag_group_device, children_only=True)
                DeviceFactory.init_all_devices()
                for serial in DeviceFactory.devices().keys():
                    dpg.add_button(
                        label=serial, width=200, callback=_init_device_win,
                        parent=self.tag_group_device, height=30
                    )

            dpg.add_button(label="Load Devices", tag=self.tag_btn_load, callback=_load_devices, width=200, height=40)
            dpg.add_text('Devices:')

            dpg.add_separator()
            with dpg.group(tag=self.tag_group_device):
                ...

        _load_devices()


def main():
    from myscrcpy.gui.dpg.loop_register import LoopRegister
    from myscrcpy.utils import Param

    dpg.create_context()
    dpg.create_viewport(
        title='MYScrcpy - Devices', width=1920, height=1080,
        small_icon=Param.PATH_STATICS_ICON.__str__(),
        large_icon=Param.PATH_STATICS_ICON.__str__(),
    )

    dw = WindowDevices()
    dw.init()

    dpg.setup_dearpygui()
    dpg.show_viewport()

    while dpg.is_dearpygui_running():
        try:
            LoopRegister.func_call_loop()
        except Exception as e:
            pass
        dpg.render_dearpygui_frame()

    DeviceFactory.close_all_devices()
    dpg.stop_dearpygui()
    dpg.destroy_context()


if __name__ == '__main__':
    main()
