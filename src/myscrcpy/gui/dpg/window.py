# -*- coding: utf-8 -*-
"""
    新一代 MYScrcpy 客户端
    ~~~~~~~~~~~~~~~~~~~~~

    Log:
        2024-09-24 1.6.1 Me2sY
            1. 修复 Linux 下 Viewport 调整缺陷
            2. 修复 窗口坐标 缺陷
            3. 修复 最近加载菜单 重复加载 缺陷
            4. 修复 暂停功能

        2024-09-18 1.6.0 Me2sY
            1. 适配 插件 体系
            2. 使用 keyboardHandler 对 按键进行管理 支持模式切换
            3. 优化显示效果，修复窗口调节过程中抖动缺陷
            4. 重构 MouseHandler 支持插件，修复DPG异常退出缺陷

        2024-09-12 1.5.10 Me2sY 新增 Extensions

        2024-09-10 1.5.9 Me2sY  新增文件管理器

        2024-09-09 1.5.8 Me2sY  支持文件拷贝

        2024-09-06 1.5.5 Me2sY
            1. 新增剪切板同步功能
            2. 修复视频加载BUG issue #7

        2024-09-05 1.5.4 Me2sY  降低CPU占用

        2024-09-02 1.5.0 Me2sY  修复部分缺陷，发布pypi初版

        2024-09-01 1.4.2 Me2sY  新增 鼠标控制器，优化结构，支持鼠标收拾功能

        2024-08-31 1.4.1 Me2sY
            1.改用新 KVManager
            2.优化部分功能

        2024-08-30 1.4.0 Me2sY  适配新 Session 结构

        2024-08-21 1.3.5 Me2sY
            1.重构 按键映射方法
            2.修复部分缺陷

        2024-08-20 1.3.4 Me2sY
            1.优化显示效果
            2.修复部分缺陷

        2024-08-19 1.3.3 Me2sY
            1.新增 选择音频播放设备功能 支持 VB-Cables 模拟麦克风输入
            2.优化 虚拟摄像头输入选择功能 支持 选择 UnityCapture https://github.com/schellingb/UnityCapture
            3.新增 Reboot功能，优化屏幕控制功能

        2024-08-18 1.3.2 Me2sY  新增 虚拟摄像头功能，支持OBS串流

        2024-08-16 1.3.1 Me2sY
            1.修复 切换设备后 鼠标事件未释放错误
            2.优化 滚轮操作

        2024-08-15 1.3.0 Me2sY  发布初版

        2024-08-14 0.1.5 Me2sY
            1.优化 部分功能
            2.新增 断线功能

        2024-08-13 0.1.4 Me2sY
            1.修复 Wheel 放大缩小功能
            2.优化 Video大小调整逻辑及算法

        2024-08-09 0.1.3 Me2sY
            1.完成 Control 功能迁移
            2.替换 采用 Google Material Symbols & Icons 替换部分按钮 https://fonts.google.com/icons
            3.调整 Devices 窗口大小，排版缩小至合适尺寸

        2024-08-08 0.1.2 Me2sY
            1.完成 视频、音频、控制 参数配置界面
            2.完成 Device Connect

        2024-08-07 0.1.1 Me2sY
            1.完成 视频解析及绘制
            2.完成 ControlPad SwitchPad

        2024-08-06 0.1.0 Me2sY  创建，完成视频控制器编写
"""

__author__ = 'Me2sY'
__version__ = '1.6.1'

__all__ = ['start_dpg_adv']


import pathlib
import threading
import time
from functools import partial
import webbrowser
from typing import Dict

import av
from adbutils import adb
import dearpygui.dearpygui as dpg
from loguru import logger

from myscrcpy.core import *
from myscrcpy.gui.pg.window_control import PGControlWindow
from myscrcpy.gui.dpg.window_mask import WindowTwin

from myscrcpy.utils import Param, kv_global, ADBKeyCode, KVManager, KeyValue
from myscrcpy.utils import Coordinate, ROTATION_VERTICAL, ROTATION_HORIZONTAL

from myscrcpy.gui.dpg.components.component_cls import TempModal, Static
from myscrcpy.gui.dpg.components.device import WinDevices
from myscrcpy.gui.dpg.components.vc import VideoController, CPMVC
from myscrcpy.gui.dpg.components.pad import *
from myscrcpy.gui.dpg.components.scrcpy_cfg import CPMScrcpyCfgController
from myscrcpy.gui.dpg.mouse_handler import *
from myscrcpy.gui.dpg.keyboard_handler import KeyboardHandler
from myscrcpy.gui.gui_utils import *

from myscrcpy.gui.dpg.dpg_extension import DPGExtensionManager, DPGExtManagerWindow, ValueManager, ViewportCoordManager

inject_pg_key_mapper()
inject_dpg_key_mapper()


class Window:
    """
        MYSDPG
        主界面
    """

    WIDTH_CTRL = 256
    WIDTH_SWITCH = 38
    WIDTH_BOARD = 8

    HEIGHT_MENU = 19
    HEIGHT_BOARD = 8
    HEIGHT_BOTTOM = 42

    N_RECENT_RECORDS = 10

    def __init__(self):

        self.tag_window = dpg.generate_uuid()
        self.tag_cw_ctrl = dpg.generate_uuid()
        self.tag_hr_resize = dpg.generate_uuid()
        self.tag_ext_pad = dpg.generate_uuid()
        self.tag_ext_menu = dpg.generate_uuid()

        self.device: AdvDevice = None
        self.session: Session = None

        self.kv = KVManager('dpg_main_window')
        self.vm = ValueManager(self.kv, load_kvs=True)
        self.ext_manager = DPGExtensionManager(self)

        self.vcm = ViewportCoordManager()
        self.vcm.register_resize_callback(self.vp_resize)

        self.video_controller = VideoController()
        self.video_controller.register_resize_callback(self._video_resize)
        self.video_controller.register_resize_callback(self._camera_resize)

        self.video_controller.register_resize_callback(
            lambda t, old_c, new_c: self.ext_manager.device_rotation(new_c)
        )

        self.is_paused = True

        self.mouse_handler: MouseHandler = None
        self.keyboard_handler: KeyboardHandler = None

        self.vcam_running = False

    def vp_resize(self, old_client_coord: Coordinate, new_client_coord: Coordinate):
        """
            Viewport Resize 回调
        :param old_client_coord:
        :param new_client_coord:
        :return:
        """

        # 更新 CPM_VC 画面大小
        cw_c = 1 if dpg.is_item_shown(self.tag_cw_ctrl) else 0

        new_vc_coord = Coordinate(
            new_client_coord.width - self.WIDTH_CTRL * cw_c - self.WIDTH_SWITCH - self.WIDTH_BOARD * (3 + cw_c),
            new_client_coord.height - self.HEIGHT_MENU - self.HEIGHT_BOARD * 3 - self.HEIGHT_BOTTOM
        )

        # 1.6.1 Me2sY 增加判断
        if new_vc_coord != self.cpm_vc.coord_draw:
            self.cpm_vc.resize(new_vc_coord)

        title = f"{Param.PROJECT_NAME} - {Param.AUTHOR}"
        if self.device:
            title += f" - {self.device.info.serial_no} - {new_vc_coord.width} X {new_vc_coord.height}"

            if not dpg.is_item_hovered(self.tag_drag_video_s) and not dpg.is_item_clicked(self.tag_drag_video_s):
                # 更新 Menu/Video/Resize相关控件
                scale = min(
                    round(new_vc_coord.width / self.video_controller.coord_frame.width, 3),
                    round(new_vc_coord.height / self.video_controller.coord_frame.height, 3)
                )
                dpg.set_value(self.tag_drag_video_s, scale)

            dpg.set_value(self.tag_drag_video_w, new_vc_coord.width)
            dpg.set_value(self.tag_drag_video_h, new_vc_coord.height)

            # 记录当前设备当前配置下窗口大小
            win_pos_kv = KeyValue(
                key=f"win_pos_{new_vc_coord.rotation}_{self.device.scrcpy_cfg}",
                value=dpg.get_viewport_pos()
            )
            win_coord = KeyValue(
                key=f"draw_coord_{new_vc_coord.rotation}_{self.device.scrcpy_cfg}",
                value=new_vc_coord.d
            )
            self.device.kvm.set_many([win_pos_kv, win_coord])

        else:
            dpg.set_value(self.tag_drag_video_s, 1)
            dpg.set_value(self.tag_drag_video_w, new_vc_coord.width)
            dpg.set_value(self.tag_drag_video_h, new_vc_coord.height)

        dpg.set_viewport_title(title)

    def _adb_devices(self):
        """
            设备选择窗口
        """
        def choose_callback(device: AdvDevice):
            self.device = device
            if self.session:
                self.session.disconnect()
            self.session = None

        self.cpm_device = WinDevices()
        self.cpm_device.draw(Static.ICONS)
        self.cpm_device.update(
            choose_callback, self.setup_session
        )

        vpw = dpg.get_viewport_width()
        vph = dpg.get_viewport_height()

        w, h = dpg.get_item_rect_size(self.cpm_device.tag_container)

        if w > vpw:
            dpg.set_viewport_width(w + 64)

        if h > vph:
            dpg.set_viewport_height(h + 64)

    def disconnect(self, draw_default_frame: bool = True, loading_window=None):
        """
            断联
        :param draw_default_frame:
        :param loading_window:
        :return:
        """

        _is_paused = self.is_paused

        self.is_paused = True

        win_loading = TempModal.LoadingWindow() if loading_window is None else loading_window

        # 2024-08-31 1.4.1 Me2sY  保存窗口位置
        win_loading.update_message(f"Saving Configs")

        if self.session and self.session.is_video_ready:

            rotation = self.session.va.coordinate.rotation

            # 保存 窗口位置及大小
            win_pos_kv = KeyValue(
                key=f"win_pos_{rotation}_{self.device.scrcpy_cfg}",
                value=dpg.get_viewport_pos()
            )
            win_coord = KeyValue(
                key=f"draw_coord_{rotation}_{self.device.scrcpy_cfg}",
                value=self.cpm_vc.coord_draw.d
            )
            self.device.kvm.set_many([win_pos_kv, win_coord])

        win_loading.update_message(f"Closing Handler")

        # 2024-09-01 1.4.2 Me2sY  关闭鼠标控制器
        # 2024-09-23 1.6.0 Me2sY   关闭鼠标进程
        self.mouse_handler and self.mouse_handler.device_disconnect()

        # 2024-09-18 1.6.0 Me2sY  关闭键盘控制器
        self.keyboard_handler and self.keyboard_handler.device_disconnect()

        # Extensions 断开设备连接
        self.ext_manager.device_disconnect()

        win_loading.update_message(f"Closing Session")

        self.session and self.session.disconnect()

        _device_serial = self.device.serial_no

        self.session = None
        self.device = None

        if draw_default_frame:
            self.video_controller.load_frame(
                VideoController.create_default_av_video_frame(Coordinate(400, 500), rgb_color=0)
            )
            # 避免下次连接不加载窗口位置
            self.video_controller.coord_frame = Coordinate(0, 0)

        dpg.configure_item(self.tag_menu_disconnect, enabled=False, show=False)

        if loading_window is None:
            win_loading.close()

        self.cpm_bottom.show_message(f"Device {_device_serial} Disconnected!")

        self.is_paused = _is_paused

    def video_fix(self, sender, app_data, user_data):
        """
            按边调整Video比例以适配原生比例
        """
        if user_data == ROTATION_VERTICAL:
            coord_new = self.cpm_vc.coord_draw.fix_width(self.video_controller.coord_frame)
        else:
            coord_new = self.cpm_vc.coord_draw.fix_height(self.video_controller.coord_frame)
        self.set_d2v(coord_new)

    def video_scale(self, sender, app_data, user_data):
        """
            按比例调整Video比例
        """
        nc = self.video_controller.coord_frame * dpg.get_value(self.tag_drag_video_s)
        dpg.set_value(self.tag_drag_video_w, nc.width)
        dpg.set_value(self.tag_drag_video_h, nc.height)
        self.set_d2v(nc)

    def video_set_scale(self, sender, app_data, user_data):
        """
            通过Width Height 调整Video比例
        """
        self.set_d2v(Coordinate(
            dpg.get_value(self.tag_drag_video_w),
            dpg.get_value(self.tag_drag_video_h)
        ))

    def set_d2v(self, coord: Coordinate):
        """
            根据 Video大小 调整view_port窗口大小
            2024-08-20 Me2sY 更新计算逻辑 解决Linux系统下 边框宽度计算问题
            2024-08-21 Me2sY 新增暂停机制
        """

        # 2024-09-02 1.4.3 优化窗口大小调整，避免过小导致错误
        if coord.width < dpg.get_viewport_min_width() + 16:
            return

        if coord.height < dpg.get_viewport_min_height() + 16:
            return

        _pause = self.is_paused
        self.is_paused = True

        cw_c = 1 if dpg.is_item_shown(self.tag_cw_ctrl) else 0

        # 2024-09-18 1.6.0 使用 ViewportCoordManager 管理 避免调整抖动

        vp_w = coord.width + self.WIDTH_SWITCH + self.WIDTH_CTRL * cw_c + self.WIDTH_BOARD * (3 + cw_c)
        vp_h = coord.height + self.HEIGHT_BOARD * 3 + self.HEIGHT_MENU + self.HEIGHT_BOTTOM

        self.vcm.set_viewport_client_size(Coordinate(vp_w, vp_h))

        self.is_paused = _pause

    def draw_menu_recent_device(self, parent_tag):
        """
            最近连接配置功能
            2024-09-24 1.6.1 Me2sY
            新增菜单栏中过滤当前连接功能
        """

        dpg.delete_item(parent_tag, children_only=True)

        def _connect(sender, app_data, user_data):
            """
                快速连接
            """
            serial, _cfg_name = user_data

            # 同配置则不连接
            if self.device and self.device.adb_dev.serial == serial and self.device.scrcpy_cfg == _cfg_name:
                return

            device = AdvDevice.from_adb_direct(serial)

            device.scrcpy_cfg = _cfg_name
            cfg = CPMScrcpyCfgController.get_config(device.serial_no, _cfg_name)
            if cfg is None or len(cfg) == 0:
                TempModal.draw_msg_box(
                    partial(dpg.add_text, f"{_cfg_name} Not Found!")
                )
                dpg.delete_item(sender)
                recent_connected.remove([serial, _cfg_name])
                kv_global.set('recent_connected', recent_connected)
            else:
                self.setup_session(device, cfg)

        devices = {dev.serial: dev for dev in adb.device_list()}

        recent_connected = kv_global.get('recent_connected', [])
        for adb_serial, cfg_name in recent_connected:
            try:
                if self.device and self.device.adb_dev.serial == adb_serial and self.device.scrcpy_cfg == cfg_name:
                    continue

                msg = adb_serial[:15] + '/' + cfg_name[:5]

                if adb_serial in devices:
                    dpg.add_menu_item(
                        label=msg, user_data=(adb_serial, cfg_name), callback=_connect,
                        parent=parent_tag
                    )
                else:
                    dpg.add_menu_item(
                        label=f"X {msg}", parent=parent_tag, enabled=False
                    )
            except Exception as e:
                pass

        if len(recent_connected) == 0:
            dpg.add_text('No Records', parent=parent_tag)

    # 2024-08-30 1.4.0 Me2sY
    # 受益于新 Session/Connection架构，可以实现单V/A/C重连、断连机制
    def reconnect_adapter(self, sender, app_data, user_data):
        """
            重连
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        if user_data == 'video':
            if self.session.is_video_ready:
                self.session.va.stop()

            if self.session.va is not None:
                self.session.va.start(self.session.adb_device)

        if user_data == 'audio':
            if self.session.is_audio_ready:
                self.session.aa.stop()

            if self.session.aa is not None:
                self.session.aa.start(self.session.adb_device)

    def disconnect_adapter(self, sender, app_data, user_data):
        """
            断开连接
            目前很多逻辑不完善，不推荐使用
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        if user_data == 'video' and self.session.is_video_ready:
            self.session.va.stop()
            self.is_paused = True

        if user_data == 'audio' and self.session.is_audio_ready:
            self.session.aa.stop()

    def _draw_menu(self):
        """
            初始化Menu
        """

        with dpg.menu_bar(parent=self.tag_window):

            dpg.add_image_button(Static.ICONS['devices'], callback=self._adb_devices, width=23, height=23)

            with dpg.menu(label='Device'):
                with dpg.menu(label='Recent') as self.tag_menu_recent:
                    self.draw_menu_recent_device(self.tag_menu_recent)

                self.tag_menu_disconnect = dpg.add_menu_item(
                    label='Disconnect',
                    callback=lambda s, a, u: self.disconnect(True),
                    enabled=False, show=False
                )

            # ADB 相关功能
            with dpg.menu(label=' Adb '):
                with dpg.menu(label='NumPad'):
                    # Num Pad 适用某些机型锁屏下 需要输入数字密码场景
                    CPMNumPad().draw().update(self.send_key_event)

                # 2024-08-19 Me2sY  新增 重启设备功能
                def reboot():
                    def _f():
                        self.device.reboot()
                        self.disconnect(True)

                    if self.device:
                        TempModal.draw_confirm(
                            'Reboot Device?',
                            _f,
                            partial(
                                dpg.add_text,
                                'Device Will DISCONNECT! \nWait and then try reconnect.'
                            ),
                            width=220
                        )

                dpg.add_spacer(height=10)

                dpg.add_menu_item(label='! Reboot !', callback=reboot)

            # Scrcpy Video/Audio/Control 相关功能
            with dpg.menu(label=' VAC '):
                with dpg.menu(label='Video'):
                    self.tag_drag_video_s = dpg.add_drag_float(
                        label='Scale', default_value=1.0, min_value=0.1, max_value=2.0, width=90,
                        speed=0.001, callback=self.video_scale, clamped=True
                    )
                    with dpg.group(horizontal=True):
                        drag_cfg = dict(
                            min_value=100, max_value=9999, width=50, clamped=True, speed=1,
                            callback=self.video_set_scale
                        )
                        self.tag_drag_video_w = dpg.add_drag_int(label='x', **drag_cfg)
                        self.tag_drag_video_h = dpg.add_drag_int(**drag_cfg)
                    dpg.add_separator()
                    dpg.add_menu_item(label='fix_W(>)', callback=self.video_fix, user_data=ROTATION_VERTICAL)
                    dpg.add_menu_item(label='fix_H(V)', callback=self.video_fix, user_data=ROTATION_HORIZONTAL)
                    dpg.add_separator()

                    # 暂停画面更新
                    self.tag_menu_pause = dpg.add_menu_item(
                        label='Pause', default_value=False, callback=lambda s, a: setattr(self, 'is_paused', a),
                        check=True
                    )

                    dpg.add_separator()
                    dpg.add_menu_item(label='Reconnect', callback=self.reconnect_adapter, user_data='video')
                    dpg.add_menu_item(label='Disconnect', callback=self.disconnect_adapter, user_data='video')

                with dpg.menu(label='Audio'):
                    dpg.add_menu_item(label='Mute(Scrcpy)', callback=self.audio_switch_mute)

                    # 2024-08-19 Me2sY  选择播放设备
                    dpg.add_menu_item(label='Output Device', callback=self.audio_choose_output_device)

                    dpg.add_separator()
                    dpg.add_menu_item(label='Reconnect', callback=self.reconnect_adapter, user_data='audio')
                    dpg.add_menu_item(label='Disconnect', callback=self.disconnect_adapter, user_data='audio')

                with dpg.menu(label='Ctrl'):
                    # 2024-08-19 Me2sY  优化为可选项
                    def set_screen(sender, app_data, user_data):
                        if self.session.is_control_ready:
                            self.session.ca.f_set_screen(user_data)

                    with dpg.menu(label='Screen'):
                        with dpg.group(horizontal=True):
                            dpg.add_button(label='On', callback=set_screen, user_data=True, width=50, height=30)
                            dpg.add_button(label='Off', callback=set_screen, user_data=False, width=50, height=30)

                    # ClipBoard 相关功能

                    dpg.add_menu_item(label='CopyToDevice', callback=self.copy_to_device)

                    def set_clipboard(sender, app_data, user_data):
                        if self.session.is_control_ready:
                            self.session.ca.set_clipboard_status(user_data)

                    with dpg.menu(label='ClipBoardSync'):
                        with dpg.group(horizontal=True):
                            dpg.add_button(label='On', callback=set_clipboard, user_data=True, width=50, height=30)
                            dpg.add_button(label='Off', callback=set_clipboard, user_data=False, width=50, height=30)

                    dpg.add_separator()

            with dpg.menu(label='Tools'):
                dpg.add_menu_item(label='TPEditor', callback=self.open_win_tpeditor)
                dpg.add_menu_item(label='GameMode', callback=self.open_pyg)
                dpg.add_separator()

                # 2024-08-19 Me2sY 可选来源
                with dpg.menu(label='VirtualCam'):
                    # Auto
                    dpg.add_menu_item(label='Auto', user_data=None, callback=self.open_virtual_camera)

                    dpg.add_separator()

                    # WIN / macOS
                    dpg.add_menu_item(label='OBS(WIN/macOS)', user_data='obs', callback=self.open_virtual_camera)

                    # Win
                    dpg.add_menu_item(
                        label='unitycapture(WIN)', user_data='unitycapture', callback=self.open_virtual_camera
                    )

                    # Linux
                    dpg.add_menu_item(
                        label='v4l2loopback(Linux)', user_data='v4l2loopback', callback=self.open_virtual_camera
                    )

                    dpg.add_separator()

                    dpg.add_menu_item(label='StopVCam', callback=lambda: setattr(self, 'vcam_running', False))

                dpg.add_separator()

                about_msg = (f"A Scrcpy client implemented in Python. \n"
                             f"Gui with dearpygui/pygame. \n "
                             f"With Video, Audio, also Control. \n"
                             f"GUI Supports Key Proxy, \n"
                             f"window position record,\n"
                             f" right-click gesture control, \n"
                             f"UHID Keyboard and Chinese input and more.")

                dpg.add_menu_item(label='About', callback=lambda: TempModal.draw_msg_box(
                    partial(dpg.add_text, f"MYScrcpy V{Param.VERSION}\nBY {Param.AUTHOR}"),
                    partial(
                        dpg.add_button, label=Param.GITHUB, width=-1, callback=lambda: webbrowser.open(Param.GITHUB)
                    ),
                    partial(
                        dpg.add_button, label=Param.EMAIL, width=-1, callback=lambda: webbrowser.open(
                            'mailto:' + Param.EMAIL
                        )
                    ),
                    partial(dpg.add_text, about_msg),
                    width=280
                ))

                # TODO 2024-08-14 Me2sY
                #     dpg.add_menu_item(label='ZMQ')
                #     dpg.add_menu_item(label='Twisted')
                #     dpg.add_menu_item(label='UIAutomator2')
                #     dpg.add_separator()
                #     dpg.add_menu_item(label='Help')

            # 2024-09-18 1.6.0 Me2sY 新增插件管理菜单
            with dpg.menu(label='Exts', tag=self.tag_ext_menu):
                dpg.add_menu_item(label='Manager', callback=lambda: DPGExtManagerWindow(self.ext_manager).draw())

    def copy_to_device(self, *args, **kwargs):
        """
            copy clipboard text to device
        :param args:
        :param kwargs:
        :return:
        """
        if self.session.is_control_ready:
            if self.session.ca.f_clipboard_pc2device():
                return

        # 2024-09-09 1.5.8 Me2sY 新增文件拷贝方法
        self.device.file_manager.push_clipboard_to_device()

    def audio_choose_output_device(self):
        """
            选择Audio外放设备
        :return:
        """

        if self.session is None or not self.session.is_audio_ready:
            return False

        def select():
            """
                选择播放设备
            :return:
            """
            name = dpg.get_value(tag_cb_dev)
            if name != device_info['name']:

                index = None
                for _ in devices:
                    if name == _['name']:
                        index = _['index']
                        break

                self.session.aa.select_device(index)

            dpg.delete_item(tag_win)

        with dpg.window(modal=True, width=268, no_move=True, no_resize=True, no_title_bar=True) as tag_win:
            devices = self.session.aa.get_output_devices()
            device_info = self.session.aa.current_output_device_info

            dpg.add_text(f"Choose Audio Output Device")
            tag_cb_dev = dpg.add_combo(items=[_['name'] for _ in devices], default_value=device_info['name'], width=-1)
            with dpg.group(horizontal=True):
                dpg.add_button(label='Select', callback=select, width=-60, height=35)
                dpg.add_button(label='Close', callback=lambda: dpg.delete_item(tag_win), height=35, width=-1)

    def audio_switch_mute(self):
        """
            Scrcpy 静音
        """
        if self.session is not None and self.session.is_audio_ready:
            self.session.aa.switch_mute()

    def open_win_tpeditor(self):
        """
            开启 TPEditor
        """
        wt = WindowTwin(self.session)
        wt.init()

    def open_pyg(self):
        """
            开启 Pygame GameMode
        """
        def run():
            pgcw = PGControlWindow()
            self._open_pg(pgcw, Param.PATH_TPS.joinpath(dpg.get_value(tag_cfg) + '.json'))
            self.is_paused = True
            dpg.set_value(self.tag_menu_pause, True)
            dpg.delete_item(tag_win)

        if self.session and self.session.is_video_ready and self.session.is_control_ready:
            with dpg.window(width=200, label='Choose TP Config', no_resize=True, no_collapse=True) as tag_win:
                cfgs = []
                for _ in Param.PATH_TPS.glob('*.json'):
                    cfgs.append(_.stem)

                # 2024-08-19 Me2sY  修复新PC无配置文件问题
                if len(cfgs) == 0:
                    dpg.add_text(f"Create TP Config First!\nTry TPEditor")
                    dpg.add_button(label='Close', callback=lambda: dpg.delete_item(tag_win), width=-1, height=35)
                else:
                    tag_cfg = dpg.add_combo(cfgs, label='Configs', default_value=cfgs[0], width=-50)
                    dpg.add_button(label='Start GameMode', callback=run, width=-1, height=35)
        else:
            logger.warning(f"Connect A Device With VideoSocket And ControlSocket First!")

    def _open_pg(self, pgcw: PGControlWindow, cfg_path: pathlib.Path):
        threading.Thread(target=pgcw.run, args=(
            self.session, self.device, self.video_controller.coord_frame, cfg_path
        )).start()

    def _draw_control_pad(self):
        """
            绘制Control Pad
        """
        with dpg.child_window(tag=self.tag_cw_ctrl, width=self.WIDTH_CTRL, no_scrollbar=True, show=False):
            with dpg.collapsing_header(label='CtrlPad', default_open=False):
                CPMControlPad().draw().update(self.send_key_event)

            with dpg.collapsing_header(label='FileManagerPad', default_open=False):
                self.cpm_file_pad = CPMFilePad()
                self.cpm_file_pad.draw()

            dpg.add_separator()

            dpg.add_group(tag=self.tag_ext_pad)

    def _draw_switch_pad(self, parent_tag):
        """
            switch pad
            用于 显示/隐藏 控制面板
        """

        def switch(show):
            """
                显示、隐藏侧边工具栏
            """
            if show:
                dpg.show_item(self.tag_cw_ctrl)
                dpg.set_viewport_width(dpg.get_viewport_width() + self.WIDTH_CTRL + self.WIDTH_BOARD)
            else:
                dpg.hide_item(self.tag_cw_ctrl)
                dpg.set_viewport_width(dpg.get_viewport_width() - self.WIDTH_CTRL - self.WIDTH_BOARD)

        CPMSwitchPad(
            parent_container=CPMSwitchPad.default_container(parent_tag)
        ).draw(Static.ICONS).update(
            self.send_key_event, lambda show: switch(show)
        )

    def draw(self):
        """
            初始化Window窗口
        :return:
        """
        with dpg.window(tag=self.tag_window, no_scrollbar=True):
            # 1:1 Menu
            self._draw_menu()

            with dpg.group(horizontal=True) as tag_g:
                # 2:1 ControlPad
                self._draw_control_pad()

                # 2:2 Switch Pad
                self._draw_switch_pad(tag_g)

                # 2:3 Video Component

                with dpg.group() as tag_gv:
                    # 2:3:1 VC
                    self.cpm_vc = CPMVC(parent_container=CPMVC.default_container(tag_gv)).draw()

                    # 2024-09-18 1.6.0 Me2sY 增加底部栏
                    # 2:3:2 Bottom
                    self.cpm_bottom = CPMBottomPad(parent_container=CPMBottomPad.default_container(tag_gv))
                    self.cpm_bottom.draw()
                    self.cpm_bottom.show_message(f"MYScrcpy Ready.")

        # 注册 按键管理器
        self.keyboard_handler = KeyboardHandler(
            self.vm,
            lambda mode: self.cpm_bottom.show_message(f"Ctrl Mode > {KeyboardHandler.Mode(mode).name}"),
            lambda space: self.cpm_bottom.show_message(f"Ctrl Space > {space}")
        )

        # 注册 鼠标管理器
        self.mouse_handler = MouseHandler(
            self.vm, self.cpm_vc
        )

        # 增加插件管理器
        self.ext_manager.load_extensions()
        self.ext_manager.register_extensions()

    def _video_resize(self, tag_texture, old_coord: Coordinate, new_coord: Coordinate):
        """
            视频源尺寸变化回调函数
        :param tag_texture:
        :param old_coord:
        :param new_coord:
        :return:
        """

        # 设备连接
        if self.device:
            if old_coord.width == 0:        # 初次连接，只连接，不保存
                new_pos = self.device.kvm.get(f"win_pos_{new_coord.rotation}_{self.device.scrcpy_cfg}", [])
                if new_pos:
                    dpg.set_viewport_pos(new_pos)

            else:
                if old_coord.rotation != new_coord.rotation:    # 旋转
                    self.device.kvm.set(
                        f"win_pos_{old_coord.rotation}_{self.device.scrcpy_cfg}", value=dpg.get_viewport_pos())

                    new_pos = self.device.kvm.get(f"win_pos_{new_coord.rotation}_{self.device.scrcpy_cfg}", [])
                    if new_pos:
                        dpg.set_viewport_pos(new_pos)

        self._init_video(tag_texture, new_coord)

    def _init_video(self, tag_texture: int | str, coord: Coordinate):
        """
            创建 Video 显示
        """
        auto_fix = True
        if self.device:
            # 加载历史窗口大小配置
            his_coord = self.device.kvm.get(f"draw_coord_{coord.rotation}_{self.device.scrcpy_cfg}")
            if his_coord:
                coord = Coordinate(**his_coord)
                auto_fix = False

        draw_coord = self.cpm_vc.init_image(tag_texture, coord, auto_fix=auto_fix)

        self.set_d2v(draw_coord)

    def send_key_event(self, keycode: int | ADBKeyCode, *args, **kwargs):
        """
            通过 ADB 发送 Key Event
        """
        if self.device:
            if isinstance(keycode, int):
                self.device.adb_dev.keyevent(keycode)
            else:
                self.device.adb_dev.keyevent(keycode.value)

    def video_frame_callback(self, last_video_frame: av.VideoFrame, frame_n: int):
        """
            由 VideoAdapter 进行回调

        :param last_video_frame:
        :param frame_n:
        :return:
        """
        if not self.is_paused:
            self.video_controller.load_frame(last_video_frame)

    def update_recent_connect_records(self):
        """
            更新最近连接记录
        :return:
        """

        records = kv_global.get('recent_connected', [])
        record = [self.device.adb_dev.serial, self.device.scrcpy_cfg]

        try:
            records.remove(record)
        except ValueError:
            pass

        records.insert(0, record)
        kv_global.set('recent_connected', records[:self.N_RECENT_RECORDS])

    def setup_session(self, device: AdvDevice, connect_configs: Dict):
        """
            创建连接 session
        """
        win_loading = TempModal.LoadingWindow()
        win_loading.update_message(f"Connecting to {device.info.serial_no}")

        # 2024-08-21 Me2sY 避免重复加载
        self.is_paused = True

        # 2024-09-22 1.6.0 Me2sY  重连不刷新界面
        if self.session or self.device:
            self.disconnect(draw_default_frame=False, loading_window=win_loading)

        win_loading.update_message(f"Session Connecting...")

        self.device = device

        self.session = Session.connect_by_configs(
            self.device.adb_dev, **connect_configs, frame_update_callback=self.video_frame_callback
        )

        win_loading.update_message('Preparing Video Interface...')

        # 准备视频
        if self.session.is_video_ready:
            frame = self.session.va.get_video_frame()
            self.cpm_vc.draw_layer(self.cpm_vc.tag_layer_1, clear=True)
        else:

            # 2024-09-22 1.6.0 若无Video 控制窗口大小
            control_coord = self.device.get_window_size().get_max_coordinate(
                800, 800
            )

            frame = VideoController.create_default_av_video_frame(coordinate=control_coord, rgb_color=80)
            msg = 'No Video.'
            if self.session.is_control_ready:
                if self.device.info.is_uhid_supported:
                    msg += 'UHID Mode.'
                else:
                    msg += 'UHID Not Support!'

            self.cpm_vc.draw_layer(
                self.cpm_vc.tag_layer_1, partial(dpg.draw_text, pos=(10, 10), text=f"{msg}", size=18)
            )

        # 更新界面，如果未连接则显示默认界面
        self.video_controller.load_frame(frame)

        if not self.session.is_video_ready:
            self.video_controller.coord_frame = Coordinate(0, 0)
            dpg.set_viewport_resizable(False)
        else:
            dpg.set_viewport_resizable(True)

        win_loading.update_message('Preparing Control Functions...')
        if self.session.is_control_ready:
            self.mouse_handler.device_connect(self.device, self.session)

        # 初始化 Keyboard Handler
        self.keyboard_handler.device_connect(self.device, self.session)

        win_loading.update_message('Preparing Extensions...')

        # 初始化插件
        self.ext_manager.device_connected(self.device, self.session)

        # 更新最近连接目录
        self.update_recent_connect_records()
        dpg.configure_item(self.tag_menu_disconnect, enabled=True, show=True)
        self.draw_menu_recent_device(self.tag_menu_recent)

        # 加载文件管理面板
        self.cpm_file_pad.update(lambda: ..., self.device)

        # 初始化 Scale
        if self.session.is_video_ready:
            dpg.set_value(
                self.tag_drag_video_s, dpg.get_item_width(self.cpm_vc.tag_dl) / self.session.va.coordinate.width
            )
        else:
            dpg.set_value(self.tag_drag_video_s, 1)

        self.is_paused = False

        self.cpm_bottom.show_message(f"Device {self.device.serial_no} Connected!")

        win_loading.close()

    def open_virtual_camera(self, sender=None, app_data=None, user_data=None):
        """
            开启虚拟摄像头
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        threading.Thread(target=self._virtual_camera, args=(user_data,)).start()

    def _camera_resize(self, tag_texture, old_coord, new_coord):
        """
            旋转时重启摄像头
        :param tag_texture:
        :param old_coord:
        :param new_coord:
        :return:
        """
        if self.vcam_running and self.session is not None and self.session.is_video_ready:
            self.vcam_running = False
            time.sleep(0.5)
            self.open_virtual_camera()

    def _virtual_camera(self, backend: str = None):
        """
            启动虚拟摄像头
        :param backend: 虚拟摄像头服务
        :return:
        """
        try:
            import pyvirtualcam
        except ImportError:
            logger.warning('pyvirtualcam is not installed')
            return False

        if self.session and self.session.is_video_ready:
            try:
                with pyvirtualcam.Camera(
                        **self.video_controller.coord_frame.d, fps=self.session.va.conn.args.fps, backend=backend
                ) as cam:
                    self.cpm_bottom.show_message('Virtual Camera Running')
                    self.vcam_running = True
                    try:
                        while self.session.va.is_running and self.vcam_running:
                            if not self.is_paused:
                                cam.send(self.session.va.get_frame())
                            cam.sleep_until_next_frame()

                        # 2024-08-19 Me2sY  画面置黑
                        cam.send(VideoController.create_default_frame(self.video_controller.coord_frame, 0))

                    except Exception as e:
                        logger.warning(f"Virtual Camera Error: {e}")
                        return

                    self.cpm_bottom.show_message('Virtual Camera Stop')
            except Exception as e:
                logger.warning(f"Virtual Camera Error: {e}")
                return

    def loop_call(self):
        """
            循环调用
        :return:
        """
        threading.Thread(target=self.ext_manager.loop_call).start()


def start_dpg_adv():
    """
        运行
    """

    dpg.create_context()

    Static.load()
    logger.success('Static Files Loaded!')

    with dpg.font_registry():
        with dpg.font(
                Param.PATH_LIBS.joinpath('AlibabaPuHuiTi-3-45-Light.ttf').__str__(),
                size=18,
        ) as def_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
    dpg.bind_font(def_font)
    logger.success('Font Loaded!')

    # 2024-09-24 1.6.1 Me2sY 修复 Linux 下 Viewport过大导致的显示错误
    max_width = 10000
    max_height = 10000

    if dpg.get_platform() == dpg.mvPlatform_Linux:
        import subprocess
        r = subprocess.run(r"xrandr | grep \* | cut -d ' ' -f4", shell=True, capture_output=True)
        try:
            w, h = [int(_) for _ in r.stdout.decode().replace('\n', '').split('x')]
            max_width = round(w * 0.95)
            max_height = round(h * 0.9)
        except Exception as e:
            logger.warning(f"Get Windows Size Error. Scale MAY Wrong!")

    dpg.create_viewport(
        title=f"{Param.PROJECT_NAME} - {Param.AUTHOR}",
        width=500, height=600,
        **kv_global.get('viewport_pos', {'x_pos': 400, 'y_pos': 400}),
        min_width=300, min_height=420, max_width=max_width, max_height=max_height,
        large_icon=Param.PATH_STATICS_ICON.__str__(),
        small_icon=Param.PATH_STATICS_ICON.__str__()
    )

    logger.info('Start ADB Server. Please Wait...')

    wd = Window()
    wd.draw()
    dpg.set_primary_window(wd.tag_window, True)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    logger.success('ADB Server Ready. Viewport And Windows Ready.')
    logger.success(f"MYScrcpy {Param.VERSION} Ready To Move!\n {'-' * 100}")

    # while dpg.is_dearpygui_running():
    #     dpg.render_dearpygui_frame()
    #     wd.loop_call()

    dpg.start_dearpygui()

    logger.warning('Viewport Closed.')

    x, y = dpg.get_viewport_pos()

    if wd.device:
        wd.device.kvm.set(f"win_pos_{wd.device.get_rotation()}_{wd.device.scrcpy_cfg}", value=[x, y])

    kv_global.set('viewport_pos', {'x_pos': x, 'y_pos': y})

    DeviceFactory.close_all_devices()


if __name__ == '__main__':
    # 注意！ DearPyGui https://github.com/hoffstadt/DearPyGui/issues/2049
    # Windows11 窗口最小化后可能会导致内存大量占用，目前问题DPG尚未修复

    start_dpg_adv()
