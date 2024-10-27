# -*- coding: utf-8 -*-
"""
    按键处理器
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-10-27 1.7.0 Me2sY  升级 Scrcpy 2.7.0 / dearpygui 2.x

        2024-09-28 1.6.4 Me2sY  统一回调函数及传参

        2024-09-19 1.6.0 Me2sY
            1. 创建，统一处理按键事件
            2. 预留 Space 0 作为 Proxy 层
"""

__author__ = 'Me2sY'
__version__ = '1.7.0'

__all__ = [
    'KeyboardHandler'
]

from enum import IntEnum
import threading
from typing import Callable

import dearpygui.dearpygui as dpg
from loguru import logger

from myscrcpy.core import AdvDevice, Session, KeyboardWatcher
from myscrcpy.gui.dpg.dpg_extension import ValueManager, ActionCallbackParam
from myscrcpy.utils import UnifiedKeys, KeyMapper, UnifiedKey, ADBKeyCode, Action


class KeyboardHandler:
    """
        键盘事件处理器
    """

    key_mapper = {
        dpg.mvKey_LShift: ADBKeyCode.KB_SHIFT_L,
        dpg.mvKey_RShift: ADBKeyCode.KB_SHIFT_R,

        dpg.mvKey_LControl: ADBKeyCode.KB_CONTROL_L,
        dpg.mvKey_RControl: ADBKeyCode.KB_CONTROL_R,

    }

    class Mode(IntEnum):
        UHID = 0
        ADB = 1
        CTRL = 2

    # 最大操作空间
    MAX_SPACE_N = 4

    MODE_SWITCH_KEY = UnifiedKeys.UK_KB_F12
    MODE_SWITCH_SPACE = UnifiedKeys.UK_KB_F11

    def __init__(
            self,
            vm: ValueManager,
            switch_callback: Callable = None,
            space_callback: Callable = None
    ):

        self.vm = vm

        self.enabled = True

        self.adv_device: AdvDevice = None
        self.session: Session = None

        self.key_watcher = KeyboardWatcher(self.uhid_send)

        self.tag_handler_key = dpg.generate_uuid()

        self.mode = self.vm.register('kbh.mode', self.Mode.CTRL, rewrite=False, set_kv=True)
        self.ctrl_space = self.vm.register('kbh.cs_key', 1, rewrite=False, set_kv=True)

        self.is_uhid_supported = False

        self.switch_callback = switch_callback
        self.space_callback = space_callback

        self.registered_control_keys = {
            _: {} for _ in range(self.MAX_SPACE_N)
        }

        self.pressed_keys = set()

    def switch_mode(self, mode: Mode = None):
        """
            切换模式
        :param mode:
        :return:
        """
        if mode is None:
            # 循环
            self.mode(
                self.Mode(
                    self.mode() +
                    (
                        -self.Mode.CTRL + (0 if self.is_uhid_supported else 1) if self.mode() == self.Mode.CTRL else 1
                    )
                )
            )
        else:
            self.mode(mode)

        self.switch_callback and self.switch_callback(self.mode())

    def switch_space(self, space: int = None):
        """
            切换控制空间
        :return:
        """
        if space is None:
            self.ctrl_space(
                self.ctrl_space() + (
                    (-self.MAX_SPACE_N + 1) if self.ctrl_space() == (self.MAX_SPACE_N - 1) else 1
                )
            )

        elif type(space) is int and 0 <= space < self.MAX_SPACE_N:
            self.ctrl_space(space)
        else:
            return

        self.space_callback and self.space_callback(self.ctrl_space())

    def device_connect(self, adv_device: AdvDevice, session: Session):
        """
            设备连接
        :param adv_device:
        :param session:
        :return:
        """

        self.adv_device = adv_device
        self.session = session

        self.is_uhid_supported = session.is_control_ready and adv_device.info.is_uhid_supported

        self.key_watcher.clear()
        self.key_watcher.active = self.is_uhid_supported

        with dpg.handler_registry() as self.tag_handler_key:
            dpg.add_key_press_handler(callback=self.press)
            dpg.add_key_release_handler(callback=self.release)
            dpg.add_key_down_handler(callback=self.down)

        if self.is_uhid_supported:
            self.session.ca.f_uhid_keyboard_create()

    def device_disconnect(self):
        """
            设备断联
        :return:
        """

        self.adv_device = None
        self.session = None
        self.is_uhid_supported = False
        self.key_watcher.clear()
        if dpg.does_item_exist(self.tag_handler_key):
            dpg.delete_item(self.tag_handler_key, children_only=True, slot=1)

    def uhid_send(self, modifiers, key_scan_codes):
        """
            UHID 发送方法
        :param modifiers:
        :param key_scan_codes:
        :return:
        """
        if self.is_uhid_supported:
            self.session.ca.f_uhid_keyboard_input(modifiers=modifiers, key_scan_codes=key_scan_codes)

    def press(self, sender, app_data):
        """
            屏蔽 Mode 切换 及 Space 切换
        :param sender:
        :param app_data:
        :return:
        """
        key = KeyMapper.dpg2uk(app_data)

        if key == self.MODE_SWITCH_KEY:
            self.switch_mode()
            return

        if self.mode() == self.Mode.CTRL and key == self.MODE_SWITCH_SPACE:
            self.switch_space()
            return

        self._press(key, app_data)

    def _press(self, key: UnifiedKey, dpg_key: int):
        """
            press 处理器
        :param key:
        :return:
        """
        if not self.enabled:
            return

        if self.mode() == self.Mode.UHID:
            try:
                self.key_watcher.key_pressed(key)
            except Exception as e:
                logger.error(f"key_press error -> {e}")

            return

        if self.mode() == self.Mode.ADB:
            if key not in [
                UnifiedKeys.UK_KB_CONTROL, UnifiedKeys.UK_KB_CONTROL_L, UnifiedKeys.UK_KB_CONTROL_R,
                UnifiedKeys.UK_KB_SHIFT, UnifiedKeys.UK_KB_SHIFT_L, UnifiedKeys.UK_KB_SHIFT_R,
                UnifiedKeys.UK_KB_ALT, UnifiedKeys.UK_KB_ALT_L, UnifiedKeys.UK_KB_ALT_R
            ]:
                self.to_adb(key)
            return

        # 2024-09-28 1.6.4 Me2sY
        # Key Click ONLY SEND ONE Single, Use Down To Get Pressed Infos
        if self.mode() == self.Mode.CTRL:
            _, callback = self.registered_control_keys[self.ctrl_space()].get(key, (None, lambda _: None))
            if _:
                threading.Thread(target=callback, args=[
                    ActionCallbackParam(
                        action=Action.DOWN, is_first=not dpg_key in self.pressed_keys, uk=key, app_data=dpg_key
                    )
                ]).start()
            self.pressed_keys.add(dpg_key)

    def down(self, sender, app_data):
        """
            转化为 Action.PRESSED 事件
            以帧频率回调
        :param sender:
        :param app_data:
        :return:
        """
        if self.mode() == self.Mode.CTRL:
            key = KeyMapper.dpg2uk(app_data[0])
            _, callback = self.registered_control_keys[self.ctrl_space()].get(key, (None, lambda _: None))
            if _:
                threading.Thread(target=callback, args=[
                    ActionCallbackParam(
                        action=Action.PRESSED, uk=key, action_data=app_data[1], app_data=app_data,
                        is_first=app_data[1] == 0.0
                    )
                ]).start()

    def release(self, sender, app_data):
        """
            按键释放
        :param sender:
        :param app_data:
        :return:
        """
        key = KeyMapper.dpg2uk(app_data)
        if key == self.MODE_SWITCH_KEY:
            return

        if self.mode() == self.Mode.CTRL and key == self.MODE_SWITCH_SPACE:
            return

        self.pressed_keys.discard(app_data)

        self._release(key, app_data)

    def to_adb(self, key: UnifiedKey):
        """
            ADB 模拟组合键
        :param key:
        :return:
        """
        func_down = ''

        for _, adb_key in self.key_mapper.items():
            if dpg.is_key_down(_):
                func_down += f"{adb_key} "

        if func_down:
            t = self.adv_device.adb_dev.shell
            args = (f"input keycombination {func_down}{KeyMapper.uk2adb(key)}", )

        else:
            t = self.adv_device.adb_dev.keyevent
            args = (KeyMapper.uk2adb(key), )

        threading.Thread(target=t, args=args).start()

    def _release(self, key: UnifiedKey, dpg_key: int):
        """
            释放
        :param key:
        :param dpg_key:
        :return:
        """
        if not self.enabled:
            return

        if self.mode() == self.Mode.UHID:
            try:
                self.key_watcher.key_release(key)
            except Exception as e:
                logger.error(f"key_release error -> {e}")
            return

        if self.mode() == self.Mode.CTRL:
            _, callback = self.registered_control_keys[self.ctrl_space()].get(key, (None, lambda _: None))
            if _:
                threading.Thread(target=callback, args=[
                    ActionCallbackParam(action=Action.RELEASE, uk=key, app_data=dpg_key)
                ]).start()

    def register_ctrl_key_callback(
            self, receiver: str, space: int, key: UnifiedKey,
            callback: Callable[[ActionCallbackParam], None]
    ):
        """
            注册 Ctrl 模式 按键回调函数
        :param receiver:
        :param space:
        :param key:
        :param callback:
        :return:
        """
        if key in [self.MODE_SWITCH_KEY, self.MODE_SWITCH_SPACE]:
            raise KeyError(f"{self.MODE_SWITCH_KEY}/{self.MODE_SWITCH_SPACE} Not Allowed Register!")

        if space < 1 or space >= self.MAX_SPACE_N or type(space) is not int:
            raise KeyError(f"Register to  {' / '.join([str(_) for _ in range(1, self.MAX_SPACE_N)])} Space Only!")

        _receiver, func = self.registered_control_keys[space].get(key, (None, None))
        if _receiver is not None and _receiver != receiver:
            logger.warning(f"Key {key} is registered by {receiver}")
            return

        self.registered_control_keys[space][key] = (receiver, callback)

    def release_ctrl_key_callback(self, space: int, key: UnifiedKey):
        """
            释放注册监听
        :param space:
        :param key:
        :return:
        """
        del self.registered_control_keys[space][key]
