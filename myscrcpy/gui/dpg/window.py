# -*- coding: utf-8 -*-
"""
    新一代 MYScrcpy 客户端
    ~~~~~~~~~~~~~~~~~~~~~

    Log:
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
__version__ = '1.4.0'

__all__ = ['start_dpg_adv']

import pathlib
import threading
import time
from functools import partial
import webbrowser
from typing import Dict

from adbutils import adb
import dearpygui.dearpygui as dpg
from loguru import logger

from myscrcpy.core import *
from myscrcpy.gui.pg.window_control import PGControlWindow
from myscrcpy.gui.dpg.window_mask import WindowTwin

from myscrcpy.utils import Param, Action, KeyMapper, ValueManager as VM, ADBKeyCode
from myscrcpy.utils import Coordinate, ROTATION_VERTICAL, ROTATION_HORIZONTAL, ScalePointR

from myscrcpy.gui.dpg.components.component_cls import TempModal, Static
from myscrcpy.gui.dpg.components.device import WinDevices, CPMDevice
from myscrcpy.gui.dpg.components.vc import VideoController, CPMVC
from myscrcpy.gui.dpg.components.pad import *
from myscrcpy.gui.dpg.components.scrcpy_cfg import CPMScrcpyCfgController

from myscrcpy.gui.gui_utils import *

inject_pg_key_mapper()
inject_dpg_key_mapper()


class WindowMain:
    """
        MYSDPG
        主界面
    """

    WIDTH_CTRL = 120
    WIDTH_SWITCH = 38
    WIDTH_BOARD = 8

    HEIGHT_MENU = 19
    HEIGHT_BOARD = 8

    N_RECENT_RECORDS = 10

    def __init__(self):

        self.tag_window = dpg.generate_uuid()
        self.tag_cw_ctrl = dpg.generate_uuid()
        self.tag_cw_switch = dpg.generate_uuid()
        self.tag_hr_resize = dpg.generate_uuid()
        self.tag_msg_log = dpg.generate_uuid()
        self.tag_mouse_ctrl = dpg.generate_uuid()

        self.tag_hr_hid = dpg.generate_uuid()
        self.tag_hr_wheel = dpg.generate_uuid()

        self.tag_hr_ml_c = dpg.generate_uuid()
        self.tag_hr_ml_r = dpg.generate_uuid()

        self.tag_hr_ml_m = dpg.generate_uuid()

        self.tag_hr_mr_c = dpg.generate_uuid()
        self.tag_hr_mr_r = dpg.generate_uuid()

        self.device = None
        self.session = None

        self.video_controller = VideoController()
        self.video_controller.register_resize_callback(self._video_resize)
        self.video_controller.register_resize_callback(self._camera_resize)

        self.is_paused = False
        self.dev_cfg = None

        self.v_last_vp_width = dpg.get_viewport_width()
        self.v_last_vp_height = dpg.get_viewport_height()
        self.h_last_vp_width = dpg.get_viewport_width()
        self.h_last_vp_height = dpg.get_viewport_height()

        self.touch_id = 0x0413
        self.touch_id_right = self.touch_id + 10
        self.touch_id_wheel = self.touch_id + 20
        self.touch_id_sec = self.touch_id + 30
        self.pos_r = None
        self.vcam_running = False

    def close(self):
        dpg.delete_item(self.tag_window)
        if self.session:
            self.session.disconnect()

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
            dpg.set_viewport_width(w + 32)

        if h > vph:
            dpg.set_viewport_height(h + 64)

    def disconnect(self):
        """
            关闭Session连接
        """

        self.is_paused = True

        self.device = None

        win_loading = TempModal.LoadingWindow()
        win_loading.update_message(f"Closing Session")

        try:
            self.session.disconnect()
        except:
            ...

        self.session = None
        self.video_controller.load_frame(
            VideoController.create_default_frame(
                Coordinate(400, 500), rgb_color=0
            )
        )

        win_loading.update_message(f"Closing Handler")
        # 2024-08-16 Me2sY  修复回调不释放导致多次操作问题
        for _ in [
            self.tag_hr_ml_c, self.tag_hr_ml_r, self.tag_hr_ml_m,
            self.tag_hr_mr_c, self.tag_hr_mr_r,
            self.tag_hr_wheel,
            self.tag_mouse_ctrl
        ]:
            try:
                dpg.delete_item(_)
            except:
                ...

        dpg.configure_item(self.tag_menu_disconnect, enabled=False, show=False)

        win_loading.close()

        self.is_paused = False

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

        _pause = self.is_paused
        self.is_paused = True

        cw_c = 1 if dpg.is_item_shown(self.tag_cw_ctrl) else 0

        fix_w = dpg.get_viewport_width() - dpg.get_viewport_client_width()
        vp_w = coord.width + self.WIDTH_SWITCH + self.WIDTH_CTRL * cw_c + self.WIDTH_BOARD * (3 + cw_c) + fix_w
        dpg.set_viewport_width(vp_w)

        fix_h = dpg.get_viewport_height() - dpg.get_viewport_client_height()
        vp_h = coord.height + self.HEIGHT_BOARD * 3 + self.HEIGHT_MENU + fix_h
        dpg.set_viewport_height(vp_h)

        self.is_paused = _pause

    def load_recent_device(self, parent_tag):
        """
            最近连接配置功能
        """

        dpg.delete_item(parent_tag, children_only=True)

        def _connect(sender, app_data, user_data):
            """
                快速连接
            """
            serial, _cfg_name = user_data
            device = AdvDevice.from_adb_direct(serial)

            device.scrcpy_cfg = _cfg_name
            cfg = CPMScrcpyCfgController.get_config(device.serial_no, _cfg_name)
            if cfg is None:
                TempModal.draw_msg_box(
                    partial(dpg.add_text, f"{_cfg_name} Not Found!")
                )
                dpg.delete_item(sender)
                recent_connected.remove([serial, _cfg_name])
                VM.set_global('recent_connected', recent_connected)
            else:
                self.setup_session(device, cfg)

        devices = {dev.serial: dev for dev in adb.device_list()}

        recent_connected = VM.get_global('recent_connected', [])
        for adb_serial, cfg_name in recent_connected:
            try:
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
                    self.load_recent_device(self.tag_menu_recent)

                self.tag_menu_disconnect = dpg.add_menu_item(
                    label='Disconnect', callback=self.disconnect, enabled=False, show=False
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
                        self.disconnect()

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

                # dpg.add_menu_item(label='APK Manager', callback=lambda: ...)

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
                    self.tag_cb_uhid = dpg.add_checkbox(label='UHID', default_value=True)

                    # 2024-08-19 Me2sY  优化为可选项
                    def set_screen(sender, app_data, user_data):
                        if self.session.is_control_ready:
                            self.session.ca.f_set_screen(user_data)

                    with dpg.menu(label='Screen'):
                        with dpg.group(horizontal=True):
                            dpg.add_button(label='On', callback=set_screen, user_data=True, width=50, height=30)
                            dpg.add_button(label='Off', callback=set_screen, user_data=False, width=50, height=30)

                    def set_clipboard(sender, app_data, user_data):
                        if self.session.is_control_ready:
                            self.session.ca.set_clipboard_status(user_data)

                    with dpg.menu(label='ClipBoard'):
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

                about_msg = (f"A Scrcpy client implemented by Python\n"
                              f"GUI: Dearpygui/pygame, etc.\n"
                              f"With video, audio, and controls. \n"
                              f"Supports UHID Keyboard and Chinese input.\n"
                              f"Key proxy, and more. ")

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
            TODO Me2sY  待优化
        """
        wt = WindowTwin(self.session)
        wt.init()

    def open_pyg(self):
        """
            开启 Pygame GameMode
            TODO Me2sY  待优化
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
            with dpg.collapsing_header(label='CtrlPad', default_open=True):
                CPMControlPad().draw().update(self.send_key_event)
            dpg.add_separator()

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

            self._window_resize()

        CPMSwitchPad(
            parent_container=CPMSwitchPad.default_container(parent_tag)
        ).draw(Static.ICONS).update(
            self.send_key_event, lambda show: switch(show)
        )

    def draw(self):
        """
            绘制主窗口
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
                self.cpm_vc = CPMVC(parent_container=CPMVC.default_container(tag_g)).draw()

    def _video_resize(self, tag_texture, old_coord: Coordinate, new_coord: Coordinate):
        """
            视频源尺寸变化回调函数
        """
        self._init_video(tag_texture, new_coord)

        # 发生旋转时，记录旋转前位置，加载旋转后位置
        if self.device is not None and old_coord.rotation != new_coord.rotation:

            now_pos = dpg.get_viewport_pos()

            # 加载旋转后窗口位置
            new_pos = self.device.vm.get_value(
                f"win_pos_{new_coord.rotation}", {'cfg': self.device.scrcpy_cfg},
                now_pos
            )

            if old_coord.width == 0:
                return
            # 保存旋转前窗口位置
            self.device.vm.set_value(f"win_pos_{old_coord.rotation}", value=now_pos, conditions={
                'cfg': self.device.scrcpy_cfg
            })

            dpg.set_viewport_pos(new_pos)

    def _window_resize(self):
        """
            窗口调整回调函数
            2024-08-20 Me2sY 更新计算逻辑 解决Linux系统下 边框宽度计算问题
        """

        vpw = dpg.get_viewport_client_width()
        vph = dpg.get_viewport_client_height()

        # 更新 CPM_VC 画面大小
        cw_c = 1 if dpg.is_item_shown(self.tag_cw_ctrl) else 0
        new_vc_coord = Coordinate(
            vpw - self.WIDTH_CTRL * cw_c - self.WIDTH_SWITCH - self.WIDTH_BOARD * (3 + cw_c),
            vph - self.HEIGHT_MENU - self.HEIGHT_BOARD * 3
        )

        self.cpm_vc.update_frame(new_vc_coord)

        title = f"{Param.PROJECT_NAME} - {Param.AUTHOR}"
        if self.device:
            title += f" - {self.device.info.serial_no} - {new_vc_coord.width} X {new_vc_coord.height}"

            # 更新 Menu/Video/Resize相关控件
            scale = min(
                round(new_vc_coord.width / self.video_controller.coord_frame.width, 3),
                round(new_vc_coord.height / self.video_controller.coord_frame.height, 3)
            )
            dpg.set_value(self.tag_drag_video_s, scale)
            dpg.set_value(self.tag_drag_video_w, new_vc_coord.width)
            dpg.set_value(self.tag_drag_video_h, new_vc_coord.height)

            # 记录当前设备当前配置下窗口大小
            self.device.vm.set_value('draw_coord', value=new_vc_coord.d, conditions={
                'r': new_vc_coord.rotation, 'cfg': self.device.scrcpy_cfg
            })

        dpg.set_viewport_title(title)

    def _init_resize_handler(self):
        try:
            dpg.delete_item(self.tag_hr_resize)
        except Exception:
            pass

        with dpg.item_handler_registry(tag=self.tag_hr_resize):
            dpg.add_item_resize_handler(callback=self._window_resize)
        dpg.bind_item_handler_registry(self.tag_window, self.tag_hr_resize)

    def send_key_event(self, keycode: int | ADBKeyCode):
        """
            通过 ADB 发送 Key Event
        """
        if self.device:
            if isinstance(keycode, int):
                self.device.adb_dev.keyevent(keycode)
            else:
                self.device.adb_dev.keyevent(keycode.value)

    def setup_session(self, device: AdvDevice, connect_configs: Dict):
        """
            创建连接 session
        """

        win_loading = TempModal.LoadingWindow()
        win_loading.update_message(f"Connecting to {device.info.serial_no}")

        # 2024-08-21 Me2sY 避免重复加载
        self.is_paused = True
        self.device = device

        try:
            self.session.disconnect()
        except Exception:
            ...

        self.session = Session.connect_by_configs(self.device.adb_dev, **connect_configs)

        self.device.sessions.add(self.session)

        records = VM.get_global('recent_connected', [])
        record = [self.device.adb_dev.serial, self.device.scrcpy_cfg]

        # 复原位置
        pos = self.device.vm.get_value(
            f"win_pos_{self.device.get_rotation()}", {'cfg': self.device.scrcpy_cfg},
            dpg.get_viewport_pos()
        )
        dpg.set_viewport_pos(pos)

        try:
            records.remove(record)
        except ValueError:
            pass

        records.insert(0, record)

        VM.set_global('recent_connected', records[:self.N_RECENT_RECORDS])

        win_loading.update_message('Preparing Video Interface...')

        if self.session.is_video_ready:
            frame = self.session.va.get_frame()
            self.cpm_vc.draw_layer(self.cpm_vc.tag_layer_1, clear=True)

        else:
            frame = VideoController.create_default_frame(coordinate=self.device.get_window_size(), rgb_color=80)
            msg = 'No Video.'
            if self.session.is_control_ready:
                if self.device.info.is_uhid_supported:
                    msg += 'UHID Mode.'
                else:
                    msg += 'UHID Not Support!'

            self.cpm_vc.draw_layer(
                self.cpm_vc.tag_layer_1,
                partial(dpg.draw_text, pos=(10, 10), text=f"{msg}", size=18)
            )

        # 更新界面，如果未连接则显示默认界面
        self.video_controller.load_frame(frame)
        self._init_resize_handler()

        # TODO 2024-08-08 Me2sY  ADB Shell功能
        # TODO 2024-08-08 Me2sY  uiautomator2

        win_loading.update_message('Preparing Control Functions...')
        if self.session.is_control_ready:
            self._init_mouse_control()
            self._init_uhid_keyboard_control()

        dpg.configure_item(self.tag_menu_disconnect, enabled=True, show=True)
        self.load_recent_device(self.tag_menu_recent)

        self.is_paused = False

        win_loading.close()

    def _init_uhid_keyboard_control(self):
        """
            初始化 UHID 键盘控制
        """
        if self.session.is_control_ready:
            dpg.configure_item(
                self.tag_cb_uhid,
                label='UHID Keyboard' if self.device.info.is_uhid_supported else 'UHID NOT SUPPORTED',
                enabled=self.device.info.is_uhid_supported,
                default_value=self.device.info.is_uhid_supported
            )
            if not self.device.info.is_uhid_supported:
                return

        def _send(modifiers, key_scan_codes):
            self.session.ca.f_uhid_keyboard_input(
                modifiers=modifiers, key_scan_codes=key_scan_codes
            )

        self.key_watcher = KeyboardWatcher(
            uhid_keyboard_send_method=_send, active=self.device.info.is_uhid_supported
        )

        def press(sender, app_data):
            if dpg.is_item_focused(self.cpm_vc.tag_dl) and dpg.get_value(self.tag_cb_uhid):
                try:
                    self.key_watcher.key_pressed(KeyMapper.dpg2uk(app_data))
                except:
                    pass

        def release(sender, app_data):
            if dpg.is_item_focused(self.cpm_vc.tag_dl) and dpg.get_value(self.tag_cb_uhid):
                try:
                    self.key_watcher.key_release(KeyMapper.dpg2uk(app_data))
                except:
                    pass

        with dpg.handler_registry(tag=self.tag_hr_hid):
            dpg.add_key_press_handler(callback=press)
            dpg.add_key_release_handler(callback=release)

        self.session.ca.f_uhid_keyboard_create()

    def _init_mouse_control(self):
        """
            初始化鼠标控制器
        """

        with dpg.handler_registry(tag=self.tag_mouse_ctrl):
            def _down(sender, app_data):
                if not self.session.is_control_ready or not self.cpm_vc.is_hovered:
                    return

                self.session.ca.f_touch_spr(
                    Action.DOWN.value,
                    ScalePointR(*self.cpm_vc.scale_point, self.video_controller.coord_frame.rotation),
                    touch_id=self.touch_id
                )

            def _release(sender, app_data):
                if not self.session.is_control_ready:
                    return

                self.session.ca.f_touch_spr(
                    Action.RELEASE.value,
                    ScalePointR(*self.cpm_vc.scale_point, self.video_controller.coord_frame.rotation),
                    touch_id=self.touch_id
                )

            def _move(sender, app_data):
                if not self.session.is_control_ready:
                    return

                if self.cpm_vc.is_hovered and dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
                    self.session.ca.f_touch_spr(
                        Action.MOVE.value,
                        ScalePointR(*self.cpm_vc.scale_point, self.video_controller.coord_frame.rotation),
                        touch_id=self.touch_id
                    )

            dpg.add_mouse_click_handler(
                tag=self.tag_hr_ml_c, button=dpg.mvMouseButton_Left, callback=_down
            )
            dpg.add_mouse_release_handler(
                tag=self.tag_hr_ml_r, button=dpg.mvMouseButton_Left, callback=_release
            )
            dpg.add_mouse_move_handler(
                tag=self.tag_hr_ml_m, callback=_move
            )

            # 右键旋转/旋转
            # 单击右键后，在右键处生成一个固定触控点
            # 通过左键实现两点放大、缩小、旋转等功能
            def _down_r(sender, app_data):

                if not self.session.is_control_ready or not self.cpm_vc.is_hovered:
                    return

                self.pos_r = ScalePointR(*self.cpm_vc.scale_point, self.video_controller.coord_frame.rotation)
                self.session.ca.f_touch_spr(Action.DOWN.value, self.pos_r, touch_id=self.touch_id_right)

            def _release_r(sender, app_data):

                if not self.session.is_control_ready or not self.cpm_vc.is_hovered:
                    return

                self.session.ca.f_touch_spr(Action.RELEASE.value, self.pos_r, touch_id=self.touch_id_right)

            dpg.add_mouse_click_handler(
                button=dpg.mvMouseButton_Right, callback=_down_r, tag=self.tag_hr_mr_c
            )
            dpg.add_mouse_release_handler(
                button=dpg.mvMouseButton_Right, callback=_release_r, tag=self.tag_hr_mr_r
            )

            # Use Mouse Wheel To zoom or swipe
            # 滚轮实现上下滚动
            # 按下Ctrl 实现放大缩小
            def _wheel(sender, app_data):
                if not self.session.is_control_ready or not self.cpm_vc.is_hovered or not isinstance(app_data, int):
                    return

                cf = self.cpm_vc.coord_draw

                move_dis = cf.width // 8

                m_pos = dpg.get_drawing_mouse_pos()

                sec_pos = [m_pos[0] - move_dis, m_pos[1] - move_dis]

                step = 1 * (1 if app_data > 0 else -1)

                if dpg.is_key_down(dpg.mvKey_Control):
                    # Ctrl Press Then Wheel to Zoom
                    self.session.ca.f_touch_spr(
                        Action.DOWN.value,
                        ScalePointR(
                            *self.cpm_vc.to_scale_point(m_pos[0] + move_dis, m_pos[1] + move_dis),
                            self.video_controller.coord_frame.rotation
                        ),
                        touch_id=self.touch_id_wheel
                    )

                    self.session.ca.f_touch_spr(
                        Action.DOWN.value,
                        ScalePointR(
                            *self.cpm_vc.to_scale_point(*sec_pos), self.video_controller.coord_frame.rotation
                        ),
                        touch_id=self.touch_id_sec
                    )
                    dis = cf.width // 20
                    t = 0.08 / dis
                    for i in range(dis):
                        next_pos = [m_pos[0] + move_dis - i * step, m_pos[1] + move_dis - i * step]

                        self.session.ca.f_touch_spr(
                            Action.MOVE.value,
                            ScalePointR(
                                *self.cpm_vc.to_scale_point(*next_pos), self.video_controller.coord_frame.rotation
                            ),
                            touch_id=self.touch_id_wheel
                        )

                        time.sleep(t)
                else:
                    # Wheel to swipe
                    self.session.ca.f_touch_spr(
                        Action.DOWN.value,
                        ScalePointR(
                            *self.cpm_vc.to_scale_point(*m_pos), self.video_controller.coord_frame.rotation
                        ),
                        touch_id=self.touch_id_wheel
                    )
                    dis = cf.height // 15
                    t = 0.05 / dis
                    for i in range(dis):
                        next_pos = [m_pos[0], m_pos[1] + i * step]
                        self.session.ca.f_touch_spr(
                            Action.MOVE.value,
                            ScalePointR(
                                *self.cpm_vc.to_scale_point(*next_pos), self.video_controller.coord_frame.rotation
                            ),
                            touch_id=self.touch_id_wheel
                        )
                        time.sleep(t)

                self.session.ca.f_touch_spr(
                    Action.RELEASE.value,
                    ScalePointR(*self.cpm_vc.to_scale_point(*next_pos), self.video_controller.coord_frame.rotation),
                    touch_id=self.touch_id_wheel
                )

                self.session.ca.f_touch_spr(
                    Action.RELEASE.value,
                    ScalePointR(*self.cpm_vc.to_scale_point(*sec_pos), self.video_controller.coord_frame.rotation),
                    touch_id=self.touch_id_sec
                )

            dpg.add_mouse_wheel_handler(tag=self.tag_hr_wheel, callback=_wheel)

    def _init_video(self, tag_texture: int | str, coord: Coordinate):
        """
            创建 Video 显示
        """
        auto_fix = True
        if self.device:
            # 加载历史窗口大小配置
            his_coord = self.device.vm.get_value('draw_coord', {'r': coord.rotation, 'cfg': self.device.scrcpy_cfg})
            if his_coord:
                coord = Coordinate(**his_coord)
                auto_fix = False

        draw_coord = self.cpm_vc.init_image(tag_texture, coord, auto_fix=auto_fix)

        self.set_d2v(draw_coord)

    def update(self):
        """
            更新视频显示
        """
        if not self.is_paused and self.session is not None and self.session.is_video_ready:
            self.video_controller.load_frame(self.session.va.get_frame())

    def open_virtual_camera(self, sender=None, app_data=None, user_data=None):
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
                    logger.success(f"Virtual Camera Running")
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

                    logger.warning(f"Virtual Camera Stopped")
            except Exception as e:
                logger.warning(f"Virtual Camera Error: {e}")
                return


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

    dpg.create_viewport(
        title=f"{Param.PROJECT_NAME} - {Param.AUTHOR}",
        width=500, height=600,
        **VM.get_global('viewport_pos', {'x_pos': 400, 'y_pos': 400}),
        min_width=248, min_height=350,
        large_icon=Param.PATH_STATICS_ICON.__str__(),
        small_icon=Param.PATH_STATICS_ICON.__str__()
    )

    logger.info('Start ADB Server. Please Wait...')

    wd = WindowMain()
    wd.draw()
    dpg.set_primary_window(wd.tag_window, True)
    dpg.setup_dearpygui()

    def fix_vp_size():
        """
            Viewport 缩小至指定值后，会卡住界面
            修复此缺陷
        """
        vpw = dpg.get_viewport_width()
        vph = dpg.get_viewport_height()

        if vpw < dpg.get_viewport_min_width() + 3:
            dpg.set_viewport_width(dpg.get_viewport_min_width() + 5)
            return

        if vph < dpg.get_viewport_min_height() + 3:
            dpg.set_viewport_height(dpg.get_viewport_min_height() + 5)
            return

    dpg.set_viewport_resize_callback(fix_vp_size)

    dpg.show_viewport()

    logger.success('ADB Server Ready. Viewport And Windows Ready.')
    logger.success(f"MYScrcpy {Param.VERSION} Ready To Move!\n {'-' * 100}")

    while dpg.is_dearpygui_running():
        wd.update()
        dpg.render_dearpygui_frame()

    x, y = dpg.get_viewport_pos()

    VM.set_global('viewport_pos', {'x_pos': x, 'y_pos': y})

    dpg.destroy_context()

    DeviceFactory.close_all_devices()


if __name__ == '__main__':
    # 注意！ DearPyGui https://github.com/hoffstadt/DearPyGui/issues/2049
    # Windows11 窗口最小化后会导致内存大量占用，目前问题尚未修复

    start_dpg_adv()
