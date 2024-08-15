# -*- coding: utf-8 -*-
"""
    新一代 MYScrcpy 客户端
    ~~~~~~~~~~~~~~~~~~~~~

    Log:
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
__version__ = '1.3.0'

__all__ = ['start_dpg_adv']

import pathlib
import threading
import time
from functools import partial
import webbrowser

from adbutils import adb
import dearpygui.dearpygui as dpg
from loguru import logger

from myscrcpy.controller.device_controller import DeviceFactory, DeviceController
from myscrcpy.controller.control_socket_controller import KeyboardWatcher
from myscrcpy.gui.dpg.window_mask import WindowTwin
from myscrcpy.gui.pg.window_control import PGControlWindow

from myscrcpy.utils import Param, Coordinate, Action, UnifiedKeyMapper, ValueManager as VM
from myscrcpy.gui.dpg_adv.components.component_cls import TempModal, Static
from myscrcpy.gui.dpg_adv.components.device import WinDevices, CPMDevice
from myscrcpy.gui.dpg_adv.components.vc import VideoController, CPMVC
from myscrcpy.gui.dpg_adv.components.pad import *
from myscrcpy.gui.dpg_adv.components.scrcpy_cfg import CPMScrcpyCfgController


class WindowMain:
    """
        MYSDPG
        主界面
    """

    WIDTH_CTRL = 120
    WIDTH_SWITCH = 38
    WIDTH_BOARD = 8

    HEIGHT_TITLE = 39
    HEIGHT_MENU = 17
    HEIGHT_BOARD = 8

    def __init__(self):

        self.tag_window = dpg.generate_uuid()
        self.tag_cw_ctrl = dpg.generate_uuid()
        self.tag_cw_switch = dpg.generate_uuid()
        self.tag_hr_resize = dpg.generate_uuid()
        self.tag_msg_log = dpg.generate_uuid()
        self.tag_mouse_ctrl = dpg.generate_uuid()
        self.tag_hr_hid = dpg.generate_uuid()

        self.device = None
        self.vsc = None
        self.csc = None
        self.video_controller = VideoController()
        self.video_controller.register_resize_callback(self._video_resize)

        self.video_ready = False
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

    def close(self):
        dpg.delete_item(self.tag_window)

    def _adb_devices(self):
        """
            设备选择窗口
        """
        def choose_callback(device: DeviceController):
            self.device = device

        def connect_callback(device: DeviceController):
            self.cpm_vc.update()
            self.setup_device(device)

        self.cpm_device = WinDevices()
        self.cpm_device.draw(Static.ICONS)
        self.cpm_device.update(
            choose_callback, connect_callback
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
            关闭设备连接
        """
        if self.device and self.device.is_scrcpy_running:
            tag_win_loading = TempModal.draw_loading(f'Closing Device {self.device.serial_no}')
            try:
                self.device.close()
            except Exception as e:
                logger.error(e)

            self.device = None
            self.vsc = None
            self.csc = None

            for _ in range(3):
                self.video_controller.load_frame(
                    VideoController.create_default_frame(
                        Coordinate(400, 500), rgb_color=0
                    )
                )
                time.sleep(0.1)

            dpg.configure_item(self.tag_mi_disconnect, enabled=False, show=False)
            dpg.delete_item(tag_win_loading)

    def video_fix(self, sender, app_data, user_data):
        """
            按边调整Video比例以适配原生比例
        """
        if user_data == Param.ROTATION_VERTICAL:
            coord_new = self.cpm_vc.coord_draw.fix_width(self.video_controller.coord_frame)
        else:
            coord_new = self.cpm_vc.coord_draw.fix_height(self.video_controller.coord_frame)
        self.set_viewport_coord_by_draw_coord(coord_new)

    def video_scale(self, sender, app_data, user_data):
        """
            按比例调整Video比例
        """
        nc = self.video_controller.coord_frame * dpg.get_value(self.tag_drag_video_s)
        dpg.set_value(self.tag_drag_video_w, nc.width)
        dpg.set_value(self.tag_drag_video_h, nc.height)
        self.set_viewport_coord_by_draw_coord(nc)

    def video_set_scale(self, sender, app_data, user_data):
        """
            通过Width Height 调整Video比例
        """
        self.set_viewport_coord_by_draw_coord(Coordinate(
            dpg.get_value(self.tag_drag_video_w),
            dpg.get_value(self.tag_drag_video_h)
        ))

    def set_viewport_coord_by_draw_coord(self, coord: Coordinate):
        """
            根据 Video大小 调整view_port窗口大小
        """
        cw_c = 1 if dpg.is_item_shown(self.tag_cw_ctrl) else 0
        dpg.set_viewport_width(
            coord.width + self.WIDTH_SWITCH + self.WIDTH_CTRL * cw_c + self.WIDTH_BOARD * (3 + cw_c + 2)
        )
        dpg.set_viewport_height(coord.height + self.HEIGHT_BOARD * 3 + self.HEIGHT_MENU + self.HEIGHT_TITLE)

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
            device = DeviceController.from_adb_direct(serial)
            if self.device:
                self.device.close()

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
                device.connect(*CPMDevice.cfg2controllers(cfg))
                self.setup_device(device)

        devices = {dev.serial: dev for dev in adb.device_list()}

        recent_connected = VM.get_global('recent_connected', [])
        for adb_serial, cfg_name in recent_connected:

            msg = adb_serial[:10] + '/' + cfg_name[:10]

            if adb_serial in devices:
                dpg.add_menu_item(
                    label=msg, user_data=(adb_serial, cfg_name), callback=_connect,
                    parent=parent_tag
                )
            else:
                dpg.add_menu_item(
                    label=f"X {msg}", parent=parent_tag, enabled=False
                )

        if len(recent_connected) == 0:
            dpg.add_text('No Records', parent=parent_tag)

    def _draw_menu(self):
        """
            初始化Menu
        """

        with dpg.menu_bar(parent=self.tag_window):

            dpg.add_image_button(Static.ICONS['devices'], callback=self._adb_devices, width=23, height=23)

            with dpg.menu(label='Device'):
                with dpg.menu(label='Recent') as self.tag_menu_recent:
                    self.load_recent_device(self.tag_menu_recent)

                self.tag_mi_disconnect = dpg.add_menu_item(
                    label='Disconnect', callback=self.disconnect, enabled=False, show=False
                )

            # ADB 相关功能
            with dpg.menu(label=' Adb '):
                with dpg.menu(label='NumPad'):
                    # Num Pad 适用某些机型锁屏下 需要输入数字密码场景
                    CPMNumPad().draw().update(self.send_key_event)

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
                    dpg.add_menu_item(label='fix_W(>)', callback=self.video_fix, user_data=Param.ROTATION_VERTICAL)
                    dpg.add_menu_item(label='fix_H(V)', callback=self.video_fix, user_data=Param.ROTATION_HORIZONTAL)
                    dpg.add_separator()

                    # 暂停画面更新
                    self.tag_menu_pause = dpg.add_menu_item(
                        label='Pause', default_value=False, callback=lambda s, a: setattr(self, 'is_paused', a),
                        check=True
                    )

                with dpg.menu(label='Audio'):
                    dpg.add_menu_item(label='Mute(Scrcpy)', callback=self.audio_switch_mute)

                with dpg.menu(label='Ctrl'):
                    self.tag_cb_uhid = dpg.add_checkbox(label='UHID', default_value=True)
                    self.tag_menu_screen = dpg.add_menu_item(label='DeviceScreenOn/Off', callback=self.close_screen)

            with dpg.menu(label='Tools'):
                dpg.add_menu_item(label='TPEditor', callback=self.open_win_tpeditor)
                dpg.add_menu_item(label='GameMode', callback=self.open_pyg)

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

    def audio_switch_mute(self):
        """
            Scrcpy 静音
        """
        if self.device.asc:
            self.device.asc.switch_mute()

    def close_screen(self):
        """
            关闭屏幕
        """
        if self.csc:
            self.csc.f_set_screen(self.csc.close_screen)

    def open_win_tpeditor(self):
        """
            开启 TPEditor
            TODO Me2sY  待优化
        """
        wt = WindowTwin(self.device)
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

        with dpg.window(width=200, label='Choose TP Config', no_resize=True, no_collapse=True):
            cfgs = []
            for _ in Param.PATH_TPS.glob('*.json'):
                cfgs.append(_.stem)

            tag_cfg = dpg.add_combo(cfgs, label='Configs', default_value=cfgs[0], width=-50)
            dpg.add_button(label='Start GameMode', callback=run, width=-1, height=35)

    def _open_pg(self, pgcw: PGControlWindow, cfg_path: pathlib.Path):
        threading.Thread(target=pgcw.run, args=(
            self.device, self, cfg_path
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

    def _video_resize(self, tag_texture, old_coord, new_coord: Coordinate):
        """
            视频源尺寸变化回调函数
        """
        self._init_video(tag_texture, new_coord)

    def _window_resize(self):
        """
            窗口调整回调函数
        """

        vpw = dpg.get_viewport_width()
        vph = dpg.get_viewport_height()

        # 更新 CPM_VC 画面大小
        cw_c = 1 if dpg.is_item_shown(self.tag_cw_ctrl) else 0
        new_vc_coord = Coordinate(
            vpw - self.WIDTH_CTRL * cw_c - self.WIDTH_SWITCH - self.WIDTH_BOARD * (3 + cw_c + 2),
            vph - self.HEIGHT_MENU - self.HEIGHT_BOARD * 3 - self.HEIGHT_TITLE
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
        with dpg.item_handler_registry(tag=self.tag_hr_resize):
            dpg.add_item_resize_handler(callback=self._window_resize)
        dpg.bind_item_handler_registry(self.tag_window, self.tag_hr_resize)

    def send_key_event(self, keycode):
        """
            通过 ADB 发送 Key Event
        """
        if self.device:
            if isinstance(keycode, int):
                self.device.adb_dev.keyevent(keycode)
            else:
                self.device.adb_dev.keyevent(keycode.value)

    def setup_device(self, device: DeviceController):
        """
            连接设备
        """
        logger.debug(f"Device connected: {device}")

        if self.device and self.device.is_scrcpy_running and self.device.serial_no != device.serial_no:
            self.disconnect()

        self.device = device
        self.vsc = device.vsc

        if self.vsc:
            frame = self.vsc.get_frame()
            self.cpm_vc.draw_layer(self.cpm_vc.tag_layer_1)
        else:
            frame = VideoController.create_default_frame(
                coordinate=Coordinate(*self.device.adb_dev.window_size()),
                rgb_color=80
            )

            msg = 'No Video.'
            if self.device.info.is_uhid_supported:
                msg += 'UHID Mode.'
            else:
                msg += 'UHID Not Support!'

            self.cpm_vc.draw_layer(
                self.cpm_vc.tag_layer_1,
                partial(dpg.draw_text, pos=(10, 10), text=f"No Video. {msg}", size=18)
            )

        self.video_controller.load_frame(frame)
        self._init_video(self.video_controller.tag_texture, self.video_controller.coord_frame)
        self._init_resize_handler()

        # TODO 2024-08-08 Me2sY  断线重连功能
        # TODO 2024-08-08 Me2sY  ADB Shell功能
        # TODO 2024-08-08 Me2sY  uiautomator2

        self.csc = device.csc
        if self.csc:
            self._init_mouse_control()
            self._init_uhid_keyboard_control()
        else:
            try:
                dpg.delete_item(self.tag_mouse_ctrl, children_only=True)
            except Exception:
                pass

            try:
                dpg.delete_item(self.tag_hr_hid, children_only=True)
            except Exception:
                pass

        dpg.configure_item(self.tag_mi_disconnect, enabled=True, show=True)
        self.load_recent_device(self.tag_menu_recent)

    def _init_uhid_keyboard_control(self):
        """
            初始化 UHID 键盘控制
        """
        if self.device:
            dpg.configure_item(
                self.tag_cb_uhid,
                label='UHID Keyboard' if self.device.info.is_uhid_supported else 'UHID NOT SUPPORTED',
                enabled=self.device.info.is_uhid_supported,
                default_value=self.device.info.is_uhid_supported
            )
            if not self.device.info.is_uhid_supported:
                return

        def _send(modifiers, key_scan_codes):
            self.csc.f_uhid_keyboard_input(
                modifiers=modifiers, key_scan_codes=key_scan_codes
            )

        self.key_watcher = KeyboardWatcher(
            uhid_keyboard_send_method=_send, active=self.device.info.is_uhid_supported
        )

        def press(sender, app_data):
            if dpg.is_item_focused(self.cpm_vc.tag_dl) and dpg.get_value(self.tag_cb_uhid):
                try:
                    self.key_watcher.key_pressed(UnifiedKeyMapper.dpg2uk(app_data))
                except:
                    pass

        def release(sender, app_data):
            if dpg.is_item_focused(self.cpm_vc.tag_dl) and dpg.get_value(self.tag_cb_uhid):
                try:
                    self.key_watcher.key_release(UnifiedKeyMapper.dpg2uk(app_data))
                except:
                    pass

        with dpg.handler_registry(tag=self.tag_hr_hid):
            dpg.add_key_press_handler(callback=press)
            dpg.add_key_release_handler(callback=release)

        self.csc.f_uhid_keyboard_create()

    def _init_mouse_control(self):
        """
            初始化鼠标控制器
        """
        with dpg.handler_registry(tag=self.tag_mouse_ctrl):
            def _down(sender, app_data):
                if self.csc is None or not self.cpm_vc.is_hovered:
                    return

                cf = self.video_controller.coord_frame

                self.csc.f_touch(
                    Action.DOWN.value, touch_id=self.touch_id,
                    **cf.d, **cf.to_point(self.cpm_vc.scale_point).d
                )

            def _release(sender, app_data):
                if self.csc is None:
                    return
                cf = self.video_controller.coord_frame
                self.csc.f_touch(
                    Action.RELEASE.value, **cf.d, **cf.to_point(self.cpm_vc.scale_point).d, touch_id=self.touch_id
                )

            def _move(sender, app_data):
                if self.csc is None:
                    return
                if self.cpm_vc.is_hovered and dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
                    cf = self.video_controller.coord_frame
                    self.csc.f_touch(
                        Action.MOVE.value, **cf.d, **cf.to_point(self.cpm_vc.scale_point).d, touch_id=self.touch_id
                    )

            dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Left, callback=_down)
            dpg.add_mouse_release_handler(button=dpg.mvMouseButton_Left, callback=_release)
            dpg.add_mouse_move_handler(callback=_move)

            # 右键旋转/旋转
            # 单击右键后，在右键处生成一个固定触控点
            # 通过左键实现两点放大、缩小、旋转等功能
            def _down_r(sender, app_data):
                if self.csc is None or not self.cpm_vc.is_hovered:
                    return

                self.pos_r = dpg.get_drawing_mouse_pos()
                cf = self.video_controller.coord_frame
                self.csc.f_touch(
                    Action.DOWN.value, touch_id=self.touch_id_right,
                    **cf.d, **cf.to_point(self.cpm_vc.coord_draw.to_scale_point(*self.pos_r)).d
                )

            def _release_r(sender, app_data):
                if self.csc is None:
                    return

                cf = self.video_controller.coord_frame
                self.csc.f_touch(
                    Action.RELEASE.value, touch_id=self.touch_id_right,
                    **cf.d, **cf.to_point(self.cpm_vc.coord_draw.to_scale_point(*self.pos_r)).d
                )

            dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Right, callback=_down_r)
            dpg.add_mouse_release_handler(button=dpg.mvMouseButton_Right, callback=_release_r)

            # Use Mouse Wheel To zoom or swipe
            # 滚轮实现上下滚动
            # 按下Ctrl 实现放大缩小
            def _wheel(sender, app_data):
                if self.csc is None or not self.cpm_vc.is_hovered:
                    return

                move_dis = 100

                m_pos = dpg.get_drawing_mouse_pos()

                sec_pos = [m_pos[0] - move_dis, m_pos[1] - move_dis]

                step = 2 * (1 if app_data > 0 else -1)

                cf = self.video_controller.coord_frame

                if dpg.is_key_down(dpg.mvKey_Control):
                    # Ctrl Press Then Wheel to Zoom
                    self.csc.f_touch(
                        Action.DOWN.value,
                        **cf.d,
                        **cf.to_point(self.cpm_vc.to_scale_point(m_pos[0] + move_dis, m_pos[1] + move_dis)).d,
                        touch_id=self.touch_id_wheel
                    )

                    self.csc.f_touch(
                        Action.DOWN.value,
                        **cf.d,
                        **cf.to_point(self.cpm_vc.to_scale_point(*sec_pos)).d,
                        touch_id=self.touch_id_sec
                    )

                    for i in range(20):
                        n_pos = [m_pos[0] + move_dis - i * step, m_pos[1] + move_dis - i * step]

                        self.csc.f_touch(
                            Action.MOVE.value,
                            **cf.d,
                            **cf.to_point(self.cpm_vc.to_scale_point(*n_pos)).d,
                            touch_id=self.touch_id_wheel
                        )

                        time.sleep(0.005)

                else:
                    # Wheel to swipe
                    self.csc.f_touch(
                        Action.DOWN.value,
                        **cf.d,
                        **cf.to_point(self.cpm_vc.to_scale_point(*m_pos)).d,
                        touch_id=self.touch_id_wheel
                    )

                    for i in range(15):
                        n_pos = [m_pos[0], m_pos[1] + i * step]
                        self.csc.f_touch(
                            Action.MOVE.value,
                            **cf.d,
                            **cf.to_point(self.cpm_vc.to_scale_point(*n_pos)).d,
                            touch_id=self.touch_id_wheel
                        )
                        time.sleep(0.005)

                self.csc.f_touch(
                    Action.RELEASE.value,
                    **cf.d,
                    **cf.to_point(self.cpm_vc.to_scale_point(*n_pos)).d,
                    touch_id=self.touch_id_wheel
                )

                self.csc.f_touch(
                    Action.RELEASE.value,
                    **cf.d,
                    **cf.to_point(self.cpm_vc.to_scale_point(*sec_pos)).d,
                    touch_id=self.touch_id_sec
                )

            dpg.add_mouse_wheel_handler(callback=_wheel)

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
        self.set_viewport_coord_by_draw_coord(draw_coord)

    def update(self):
        """
            更新视频显示
        """
        if self.vsc and not self.is_paused:
            self.video_controller.load_frame(self.vsc.get_frame())


def start_dpg_adv():
    """
        运行
    """

    dpg.create_context()

    Static.load()

    with dpg.font_registry():
        with dpg.font(
                Param.PATH_LIBS.joinpath('AlibabaPuHuiTi-3-45-Light.ttf').__str__(),
                size=18,
        ) as def_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
    dpg.bind_font(def_font)

    dpg.create_viewport(
        title=f"{Param.PROJECT_NAME} - {Param.AUTHOR}",
        width=500, height=600,
        **VM.get_global('viewport_pos', {'x_pos': 400, 'y_pos': 400}),
        min_width=248, min_height=350,
        large_icon=Param.PATH_STATICS_ICON.__str__(),
        small_icon=Param.PATH_STATICS_ICON.__str__()
    )
    dpg.show_viewport()

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
            dpg.set_viewport_width(dpg.get_viewport_min_width() + 3)
            return

        if vph < dpg.get_viewport_min_height() + 3:
            dpg.set_viewport_height(dpg.get_viewport_min_height() + 3)
            return

    dpg.set_viewport_resize_callback(fix_vp_size)

    while dpg.is_dearpygui_running():
        wd.update()
        dpg.render_dearpygui_frame()

    x, y = dpg.get_viewport_pos()

    VM.set_global('viewport_pos', {'x_pos': x, 'y_pos': y})

    dpg.destroy_context()

    DeviceFactory.close_all_devices()


if __name__ == '__main__':
    # 注意！ DearPyGui https://github.com/hoffstadt/DearPyGui/issues/2049
    # 窗口最小化后会导致内存大量占用，目前问题尚未修复

    start_dpg_adv()
