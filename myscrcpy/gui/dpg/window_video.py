# -*- coding: utf-8 -*-
"""
    Video Window
    ~~~~~~~~~~~~~~~~~~
    设备操作窗口

    Log:
        2024-07-31 1.1.1 Me2sY  适配新Controller

        2024-07-28 1.0.1 Me2sY  新增 ZMQ Server

        2024-07-28 1.0.0 Me2sY  发布初版

        2024-07-28 0.4.2 Me2sY
            1.新增右键虚拟点 用于缩放等操作
            2.新增鼠标滑轮滑动功能

        2024-07-23 0.4.1 Me2sY
            1.新增 input pad 用于输入解锁密码、中文等
            2.适配 scrcpy-server-2.5

        2024-06-29 0.4.0 Me2sY  重构，使用 DpgVideoController 统一控制 Resize Reset 等, 增加 MouseCtrl，用于开关鼠标控制

        2024-06-18 0.3.0 Me2sY  重构，去掉控制功能，由pygame接管，保留基础点击及编辑按钮功能

        2024-06-15 0.2.1 Me2sY  新增TouchCross

        2024-06-13 0.2.0 Me2sY  重构结构

        2024-06-06 0.1.2 Me2sY
            1.新增TouchProxy加载配置文件设置
            2.新增EventHandler

        2024-06-05 0.1.1 Me2sY
            1.改用 drawlist/draw_layer/draw_image 替换原有 add_image 后期绘制图层做准备
            2.使用 child_window 在画面左侧添加控制栏
            3.实现 Rotation 窗口任意大小等功能
            4.功能栏新增 Resize Pause功能

        2024-06-04 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '1.1.1'

__all__ = [
    'WindowVideo', 'WindowInputPad'
]

import pathlib
import threading
import time

from loguru import logger
import dearpygui.dearpygui as dpg

from myscrcpy.controller import DeviceController, KeyboardWatcher

from myscrcpy.gui.dpg.loop_register import LoopRegister
from myscrcpy.gui.dpg.video_controller import DpgVideoController
from myscrcpy.gui.dpg.window_mask import WindowTwin

from myscrcpy.gui.pg.window_control import PGControlWindow

from myscrcpy.utils import Coordinate, Action, Param, ScalePoint, ADBKeyCode, UnifiedKeyMapper


class WindowInputPad:
    """
        输入面板
    """

    def __init__(self, device: DeviceController):
        self.device = device

        self.tag_win = dpg.generate_uuid()
        self.tag_ipt_psw = dpg.generate_uuid()
        self.tag_ipt_txt = dpg.generate_uuid()

        self.device.csc.f_uhid_keyboard_create()

        def _send(modifiers, key_scan_codes):
            self.device.csc.f_uhid_keyboard_input(
                modifiers=modifiers, key_scan_codes=key_scan_codes
            )

        self.key_watcher = KeyboardWatcher(uhid_keyboard_send_method=_send)

    def draw(self):

        def callback(sender, app_data, user_data):

            key = dpg.get_item_label(sender).upper()

            if key == 'CLOSE':
                self.close()
                return

            if key in [
                'BACK', 'ENTER', 'HOME', 'MENU', 'POWER', 'ESCAPE'
            ]:
                self.device.adb_dev.keyevent(ADBKeyCode[key].value)
                dpg.set_value(self.tag_ipt_psw, '')
                return
            elif key == '|<-':
                self.device.adb_dev.keyevent(ADBKeyCode['BACKSPACE'].value)
                dpg.set_value(self.tag_ipt_psw, dpg.get_value(self.tag_ipt_psw)[:-1])
                return
            else:
                psw = ADBKeyCode[f"N{key}"]
                self.device.adb_dev.keyevent(psw.value)
                dpg.set_value(self.tag_ipt_psw, dpg.get_value(self.tag_ipt_psw) + '*')

        btn_cfg = dict(width=50, height=30, callback=callback)

        with dpg.window(
                tag=self.tag_win,
                label=f"InputPad - {self.device.serial}", no_resize=True, no_collapse=True, pos=[10, 10],
                no_scrollbar=True, no_scroll_with_mouse=True
        ):
            dpg.add_input_text(label='PSW', width=130, height=50, tag=self.tag_ipt_psw, enabled=False)
            with dpg.group(horizontal=True):
                dpg.add_button(label='1', **btn_cfg)
                dpg.add_button(label='2', **btn_cfg)
                dpg.add_button(label='3', **btn_cfg)

            with dpg.group(horizontal=True):
                dpg.add_button(label='4', **btn_cfg)
                dpg.add_button(label='5', **btn_cfg)
                dpg.add_button(label='6', **btn_cfg)

            with dpg.group(horizontal=True):
                dpg.add_button(label='7', **btn_cfg)
                dpg.add_button(label='8', **btn_cfg)
                dpg.add_button(label='9', **btn_cfg)

            with dpg.group(horizontal=True):
                dpg.add_button(label='|<-', **btn_cfg)
                dpg.add_button(label='0', **btn_cfg)
                dpg.add_button(label='Enter', **btn_cfg)

            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_button(label='BACK', **btn_cfg)
                dpg.add_button(label='HOME', **btn_cfg)
                dpg.add_button(label='MENU', **btn_cfg)

            with dpg.group(horizontal=True):
                dpg.add_button(label='ESCAPE', **btn_cfg)
                dpg.add_button(label='POWER', **btn_cfg)
                dpg.add_button(label='Close', **btn_cfg)

            dpg.add_separator()

            uhid = dpg.add_checkbox(label='UHID_KEYBOARD', default_value=True)

            def callback_input():
                txt = dpg.get_value(self.tag_ipt_txt)
                if txt != '':
                    self.device.csc.f_text_paste(txt)
                    dpg.set_value(self.tag_ipt_txt, '')

            dpg.add_input_text(tag=self.tag_ipt_txt, width=165, on_enter=True, callback=callback_input)
            dpg.add_button(label='Paste', width=165, height=30, callback=callback_input)

            def press(sender, app_data):
                if dpg.is_item_focused(self.tag_win) or dpg.get_value(uhid):
                    try:
                        self.key_watcher.key_pressed(UnifiedKeyMapper.dpg2uk(app_data))
                    except:
                        pass

            def release(sender, app_data):
                if dpg.is_item_focused(self.tag_win) or dpg.get_value(uhid):
                    try:
                        self.key_watcher.key_release(UnifiedKeyMapper.dpg2uk(app_data))
                    except:
                        pass

            with dpg.handler_registry():
                dpg.add_key_press_handler(callback=press)
                dpg.add_key_release_handler(callback=release)

    def close(self):
        dpg.delete_item(self.tag_win)


class WindowVideo:
    ROTATION_UP_HEIGHT = 1080
    WIN_BORDER = 8
    WIN_TITLE_HEIGHT = 20
    WIN_CONTROL_WIDTH = 120
    WIN_CTRL_BTN_HEIGHT = 30

    def __init__(self, device: DeviceController):

        self.device = device
        self.dvc = DpgVideoController(self.device, max_height=self.ROTATION_UP_HEIGHT)

        self.tag_win_main = dpg.generate_uuid()
        self.tag_drawlist_main = dpg.generate_uuid()
        self.tag_mouse_ctrl = dpg.generate_uuid()

        self.touch_id = 0x0413  # My Wife sY's Birthday :)

        self.touch_id_sec = self.touch_id + 10
        self.touch_id_wheel = self.touch_id + 20

        self._init_font()

    def _init_font(self):
        try:
            with dpg.font_registry():
                with dpg.font(
                        Param.PATH_LIBS.joinpath('AlibabaPuHuiTi-3-45-Light.ttf').__str__(),
                        size=18,
                ) as def_font:
                    dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
            dpg.bind_font(def_font)
        except Exception as e:
            logger.warning(f"Download AlibabaPuHuiTi-3-45-Light.ttf and Put in {Param.PATH_LIBS.__str__()}")

    @property
    def window_label(self) -> str:
        return f"{self.device.serial} " + f"{self.dvc.coord_draw.width} x {self.dvc.coord_draw.height}"

    def init(self):
        logger.debug(f"Init Video Window {self.dvc.coord_draw}")

        # Init Window
        with dpg.window(
                label=self.window_label, tag=self.tag_win_main, no_scrollbar=True, no_scroll_with_mouse=True,
                pos=[50, 50]
        ):
            with dpg.group(horizontal=True):
                with dpg.child_window(
                        width=self.WIN_CONTROL_WIDTH,
                        autosize_y=True, no_scrollbar=True, border=True,
                ):
                    with dpg.tab_bar():
                        with dpg.tab(label='Ctrl'):
                            self._init_tab_control()

                with dpg.drawlist(**self.dvc.coord_draw.d, tag=self.tag_drawlist_main):
                    with dpg.draw_layer():
                        self.dvc.draw_image()

        # Resize Handler
        with dpg.item_handler_registry() as ihr:
            dpg.add_item_resize_handler(
                callback=lambda s, a, u: self.dvc.resize_handler(s, a, u) or dpg.configure_item(
                    self.tag_win_main, label=self.window_label),
                user_data={'fix_coord': Coordinate(
                    -self.WIN_CONTROL_WIDTH - self.WIN_BORDER * 3,
                    -(self.WIN_BORDER * 2 + self.WIN_TITLE_HEIGHT)
                )}
            )
        dpg.bind_item_handler_registry(self.tag_win_main, ihr)

        def _win_rotation(_dvc):
            dpg.configure_item(
                self.tag_win_main,
                **(_dvc.coord_draw + Coordinate(
                    self.WIN_CONTROL_WIDTH + self.WIN_BORDER * 3,
                    self.WIN_BORDER * 2 + self.WIN_TITLE_HEIGHT
                )).d, label=self.window_label
            )

        self.dvc.register_changed_callback(_win_rotation)
        self.dvc.reset()

        # Mouse Controller
        with dpg.handler_registry(tag=self.tag_mouse_ctrl, show=True):
            def _down(sender, app_data):
                if not dpg.is_item_hovered(self.tag_drawlist_main):
                    return

                self.device.csc.f_touch(
                    Action.DOWN.value, **self.dvc.to_touch_d(dpg.get_drawing_mouse_pos()), touch_id=self.touch_id
                )

            def _release(sender, app_data):
                self.device.csc.f_touch(
                    Action.RELEASE.value, **self.dvc.to_touch_d(dpg.get_drawing_mouse_pos()), touch_id=self.touch_id
                )

            def _move(sender, app_data):
                if dpg.is_item_hovered(self.tag_drawlist_main) and dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
                    self.device.csc.f_touch(
                        Action.MOVE.value, **self.dvc.to_touch_d(dpg.get_drawing_mouse_pos()), touch_id=self.touch_id
                    )

            dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Left, callback=_down)
            dpg.add_mouse_release_handler(button=dpg.mvMouseButton_Left, callback=_release)
            dpg.add_mouse_move_handler(callback=_move)

            # Use Mouse Right Button To Create Another Point
            r_pos = None

            def _down_r(sender, app_data):
                if not dpg.is_item_hovered(self.tag_drawlist_main):
                    return

                global r_pos
                r_pos = dpg.get_drawing_mouse_pos()

                self.device.csc.f_touch(Action.DOWN.value, **self.dvc.to_touch_d(r_pos), touch_id=self.touch_id_sec)

            def _release_r(sender, app_data):
                global r_pos
                self.device.csc.f_touch(Action.RELEASE.value, **self.dvc.to_touch_d(r_pos), touch_id=self.touch_id_sec)

            dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Right, callback=_down_r)
            dpg.add_mouse_release_handler(button=dpg.mvMouseButton_Right, callback=_release_r)

            # Use Mouse Wheel To zoom or swipe
            def _wheel(sender, app_data):
                if not dpg.is_item_hovered(self.tag_drawlist_main):
                    return

                m_pos = dpg.get_drawing_mouse_pos()

                sec_pos = [m_pos[0] - 50, m_pos[1] - 50]

                step = 10 * (1 if app_data > 0 else -1)

                if dpg.is_key_down(dpg.mvKey_Control):
                    # Ctrl Press Then Wheel to Zoom
                    self.device.csc.f_touch(
                        Action.DOWN.value,
                        **self.dvc.to_touch_d([m_pos[0] + 50, m_pos[1] + 50]),
                        touch_id=self.touch_id_wheel
                    )

                    self.device.csc.f_touch(
                        Action.DOWN.value,
                        **self.dvc.to_touch_d(sec_pos),
                        touch_id=self.touch_id_sec
                    )

                    for i in range(3):
                        n_pos = [m_pos[0] + 50 - i * step, m_pos[1] + 50 - i * step]

                        self.device.csc.f_touch(
                            Action.MOVE.value,
                            **self.dvc.to_touch_d(n_pos),
                            touch_id=self.touch_id_wheel
                        )

                        time.sleep(0.05)

                else:
                    # Wheel to swipe
                    self.device.csc.f_touch(
                        Action.DOWN.value,
                        **self.dvc.to_touch_d(m_pos),
                        touch_id=self.touch_id_wheel
                    )

                    for i in range(10):
                        n_pos = [m_pos[0], m_pos[1] + i * step]
                        self.device.csc.f_touch(
                            Action.MOVE.value,
                            **self.dvc.to_touch_d(n_pos),
                            touch_id=self.touch_id_wheel
                        )
                        time.sleep(0.01)

                self.device.csc.f_touch(
                    Action.RELEASE.value,
                    **self.dvc.to_touch_d(n_pos),
                    touch_id=self.touch_id_wheel
                )

                self.device.csc.f_touch(
                    Action.RELEASE.value,
                    **self.dvc.to_touch_d(sec_pos),
                    touch_id=self.touch_id_sec
                )

            dpg.add_mouse_wheel_handler(callback=_wheel)

        # Loop
        LoopRegister.register(self.dvc.loop)

    def _init_tab_control(self):
        """
            Control Tab
        :return:
        """

        btn_cfg = dict(
            width=self.WIN_CONTROL_WIDTH - 5, height=self.WIN_CTRL_BTN_HEIGHT
        )

        def win_input_pad():
            wpp = WindowInputPad(self.device)
            wpp.draw()

        dpg.add_button(label='InputPad', **btn_cfg, callback=win_input_pad)
        dpg.add_separator()

        # Reset DrawList Size to Frame Size
        dpg.add_button(label='Reset', **btn_cfg, callback=self.dvc.reset)

        # Pause
        # When Pause is True, Also Stop Mouse Control.
        tag_btn_pause = dpg.add_checkbox(
            label='Pause', callback=lambda s, a: self.dvc.set_pause(a) or dpg.set_value(
                tag_mc, not a
            ) or dpg.configure_item(self.tag_mouse_ctrl, show=not a)
        )

        # Screen Switch
        def _screen(sender, app_data):
            self.device.csc.f_set_screen(app_data)

        dpg.add_checkbox(label='ScreenOn', callback=_screen, default_value=False)

        # Mouse Control Switch
        tag_mc = dpg.add_checkbox(label='MouseCtrl', callback=lambda s, a: dpg.configure_item(
            self.tag_mouse_ctrl, show=a
        ), default_value=True)

        dpg.add_separator()

        tag_btn_editor = dpg.add_button(label='TPEditor', **btn_cfg, callback=self.open_win_twin)
        with dpg.tooltip(tag_btn_editor):
            dpg.add_text("Press >Insert< To Open a Editor")

        dpg.add_button(label='PYG_Ctrl', **btn_cfg, callback=self.open_pyg)
        # dpg.add_button(label='Scope', **btn_cfg, callback=self.open_scope)

        dpg.add_separator()

        def open_zmq():
            self.device.create_zmq_server(dpg.get_value(zmq_url))
            dpg.disable_item(zmq_btn)

        zmq_url = dpg.add_input_text(label='url', default_value='tcp://127.0.0.1:55556')
        zmq_btn = dpg.add_button(label='zmq', **btn_cfg, callback=open_zmq)

        with dpg.handler_registry():
            dpg.add_key_release_handler(dpg.mvKey_Insert, callback=self.open_win_twin)

    def close(self):
        LoopRegister.unregister(self.dvc.loop)

    def open_win_twin(self):
        wt = WindowTwin(self.device, on_close=lambda: dpg.show_item(self.tag_win_main))
        wt.init()
        dpg.hide_item(self.tag_win_main)

    def open_pyg(self):

        def run():
            pgcw = PGControlWindow()
            self._open_pg(pgcw, Param.PATH_TPS.joinpath(dpg.get_value(tag_cfg) + '.json'))
            self.dvc.set_pause(True)

        with dpg.window():
            cfgs = []
            for _ in Param.PATH_TPS.glob('*.json'):
                cfgs.append(_.stem)

            tag_cfg = dpg.add_combo(cfgs, label='CFG', default_value=cfgs[0])
            dpg.add_button(label='Run', callback=run)

    def _open_pg(self, pgcw: PGControlWindow, cfg_path: pathlib.Path):
        threading.Thread(target=pgcw.run, args=(
            self.device, self, cfg_path
        )).start()

    def open_scope(self):
        with dpg.window():
            with dpg.drawlist(width=800, height=600):
                with dpg.draw_layer():
                    dpg.draw_image(
                        self.dvc.tag_texture,
                        # pmin=self.dvc.coord_draw.to_point(ScalePoint(0.2, 0.2)),
                        (0, 0),
                        # pmax=(500, 500),
                        pmax=self.dvc.coord_draw.to_point(ScalePoint(0.5, 0.5)),
                        # pmax=self.dvc.coord_draw,
                        uv_min=(0.45, 0.45),
                        uv_max=(0.55, 0.55)
                    )


def run():
    from myscrcpy.controller import DeviceFactory
    from myscrcpy.controller import VideoSocketController, AudioSocketController, ControlSocketController

    dpg.create_context()

    dev = DeviceFactory.device()
    dev.connect(
        vsc=VideoSocketController(max_size=1366),
        asc=AudioSocketController(),
        csc=ControlSocketController()
    )

    vw = WindowVideo(dev)
    vw.init()

    dpg.create_viewport(
        title=f"{Param.PROJECT_NAME} - {Param.AUTHOR}", width=1900, height=1060, clear_color=(0, 0, 0, 0), vsync=False,
        x_pos=10, y_pos=10,
        small_icon=Param.PATH_STATICS_ICON.__str__(),
        large_icon=Param.PATH_STATICS_ICON.__str__(),
    )
    dpg.setup_dearpygui()
    dpg.show_viewport()

    dev.set_screen(False)

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
    run()
