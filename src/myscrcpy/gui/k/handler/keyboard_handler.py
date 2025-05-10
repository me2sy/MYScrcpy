# -*- coding: utf-8 -*-
"""
    keyboard_handler
    ~~~~~~~~~~~~~~~~~~

    Log:
        2025-04-24 3.2.0 Me2sY
            1.增加Side Panel 状态按钮
            2.2025-05-09 切换 MYDevice

        2025-04-12 0.1.0 Me2sY 创建
"""

__author__ = 'Me2sY'
__version__ = '3.2.0'

__all__ = [
    'KeyboardMode',
    'KeyboardHandlerConfig', 'KeyboardHandler', 'ActionCallback'
]

from dataclasses import dataclass, field
from enum import IntEnum
from functools import wraps
import threading
from typing import Callable, List

from kivy.core.window import Window
from kivy.logger import Logger
from kivy.uix.widget import Widget

from myscrcpy.core import ControlAdapter, KeyboardWatcher
from myscrcpy.gui.k import StoredConfig, create_snack, MYCombineColors
from myscrcpy.gui.k.handler.device_handler import MYDevice
from myscrcpy.utils import UnifiedKeys, UnifiedKey, Action, KeyMapper, ADBKeyCode


class KeyboardMode(IntEnum):
    """
        键盘工作模式
    """
    UHID = 0
    ADB = 1
    CTRL = 2


@dataclass
class KeyboardHandlerConfig(StoredConfig):
    """
        Keyboard handler configuration
    """
    _STORAGE_KEY = 'keyboard_handler'

    mode: KeyboardMode = field(default=KeyboardMode.CTRL)
    space: int = 0

    uk_keyboard_id: int = 1
    uk_mode_switch_key: UnifiedKeys = field(default=UnifiedKeys.UK_KB_F8)
    uk_mode_switch_space: UnifiedKeys = field(default=UnifiedKeys.UK_KB_F7)


@dataclass
class ActionCallback:
    """
        Keyboard Action Callback
    """
    action: Action
    key_code: int
    uk: UnifiedKey
    modifiers: List[UnifiedKey] = field(default_factory=list)


class KeyboardHandler(Widget):

    MAX_SPACE_N = 1

    def __init__(
            self,
            cfg: KeyboardHandlerConfig,
            control_adapter: ControlAdapter,
            my_device: MYDevice,
            switch_callback: Callable,
            **kwargs
    ):
        """
            键盘处理器
        :param cfg:
        :param control_adapter:
        :param my_device:
        :param switch_callback:
        :param kwargs:
        """

        super(KeyboardHandler, self).__init__(**kwargs)

        self.cfg = cfg
        self.ca = control_adapter
        self.device: MYDevice = my_device
        self.switch_callback = switch_callback

        self.is_supported = self.device.device_info.is_uhid_supported

        if self.is_supported:
            self.ca.f_uhid_keyboard_create(keyboard_id=self.cfg.uk_keyboard_id)
            self.keyboard_watcher = KeyboardWatcher(self.uhid_send)
            self.keyboard_watcher.clear()
            Logger.info('UHID keyboard created!')

        # 系统注册按键 不受space控制
        self.system_control_keys = {
            self.cfg.uk_mode_switch_key: lambda ac : ac.action == Action.DOWN and self.switch_mode(),
            self.cfg.uk_mode_switch_space: lambda ac: ac.action == Action.DOWN and self.switch_space(),
        }

        # 注册按键空间 在 Ctrl Mode 生效
        self.registered_control_keys = {
            _: {} for _ in range(self.MAX_SPACE_N)
        }

    def activate(self):
        """
            激活键盘功能
        :return:
        """
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down, on_key_up=self._on_keyboard_up)

    def deactivate(self):
        """
            失活键盘功能
        :return:
        """
        Window.release_keyboard(self._keyboard_closed)

    def uhid_send(self, modifiers, key_scan_codes):
        """
            UHID 键盘 发送方法
        :param modifiers:
        :param key_scan_codes:
        :return:
        """
        if self.is_supported:
            self.ca.f_uhid_keyboard_input(
                keyboard_id=self.cfg.uk_keyboard_id,
                modifiers=modifiers, key_scan_codes=key_scan_codes
            )

    def _keyboard_closed(self):
        """
            键盘关闭事件
        :return:
        """
        self._keyboard.unbind(on_key_down=self._on_keyboard_down, on_key_up=self._on_keyboard_up)
        self._keyboard.release()

    @staticmethod
    def trans2uk(func):
        """
            将按键转为 UnifiedKey
        :param func:
        :return:
        """
        @wraps(func)
        def wrapper(self, keyboard, keycode, *args, **kwargs):
            if len(args) > 0:
                modifiers = args[1]
            else:
                modifiers = Window.modifiers
            uk = KeyMapper.ky2uk(keycode[0])
            return func(self, uk, keycode[0], modifiers)
        return wrapper

    @trans2uk
    def _on_keyboard_down(self, uk:UnifiedKey, keycode: int, modifiers):
        """
            按键按下事件
        :param uk:
        :param keycode:
        :param modifiers:
        :return:
        """

        if uk in self.system_control_keys:
            self.system_control_keys[uk](
                ActionCallback(action=Action.DOWN, uk=uk, modifiers=modifiers, key_code=keycode)
            )
            if uk == self.cfg.uk_mode_switch_key:
                self.switch_callback()
            return

        if self.cfg.mode == KeyboardMode.CTRL:
            self.registered_control_keys[self.cfg.space].get(uk, lambda _: ...)(
                ActionCallback(action=Action.DOWN, uk=uk, modifiers=modifiers, key_code=keycode)
            )
        elif self.cfg.mode == KeyboardMode.UHID:
            self.keyboard_watcher.key_pressed(uk)

        elif self.cfg.mode == KeyboardMode.ADB:
            if uk not in [
                UnifiedKeys.UK_KB_CONTROL, UnifiedKeys.UK_KB_CONTROL_L, UnifiedKeys.UK_KB_CONTROL_R,
                UnifiedKeys.UK_KB_SHIFT, UnifiedKeys.UK_KB_SHIFT_L, UnifiedKeys.UK_KB_SHIFT_R,
                UnifiedKeys.UK_KB_ALT, UnifiedKeys.UK_KB_ALT_L, UnifiedKeys.UK_KB_ALT_R
            ]:
                self.to_adb(uk)

    @trans2uk
    def _on_keyboard_up(self, uk: UnifiedKey, keycode: int, modifiers):
        """
            按键释放
        :param uk:
        :param keycode:
        :param modifiers:
        :return:
        """
        if uk in self.system_control_keys:
            self.system_control_keys[uk](
                ActionCallback(action=Action.RELEASE, uk=uk, modifiers=modifiers, key_code=keycode)
            )
        else:
            if self.cfg.mode == KeyboardMode.CTRL:
                self.registered_control_keys[self.cfg.space].get(uk, lambda _: ...)(
                    ActionCallback(action=Action.RELEASE, uk=uk, modifiers=modifiers, key_code=keycode)
                )
            elif self.cfg.mode == KeyboardMode.UHID:
                self.keyboard_watcher.key_release(uk)

    def register_system_key_callback(self, key: UnifiedKey, callback: Callable):
        """
            注册系统按键
        :param key:
        :param callback:
        :return:
        """
        self.system_control_keys[key] = callback

    def register_ctrl_key_callback(self, space: int, key: UnifiedKey, callback: Callable):
        """
            注册按键回调事件
        :param space:
        :param key:
        :param callback:
        :return:
        """
        if key in [self.cfg.uk_mode_switch_key, self.cfg.uk_mode_switch_space]:
            raise KeyError(f"{self.cfg.uk_mode_switch_key}/{self.cfg.uk_mode_switch_space} Not Allowed Register!")

        self.registered_control_keys[space][key] = callback

    def switch_mode(self, mode: KeyboardMode = None):
        """
            切换模式
        :param mode:
        :return:
        """
        if mode is None:
            # 如果支持UHID 则屏蔽 ADB模式
            if self.cfg.mode == KeyboardMode.CTRL:
                if self.is_supported:
                    self.cfg.mode = KeyboardMode.UHID
                else:
                    self.cfg.mode = KeyboardMode.ADB
            else:
                self.cfg.mode = KeyboardMode.CTRL

            # # 循环
            # self.cfg.mode = KeyboardMode(
            #     self.cfg.mode.value + (
            #         -KeyboardMode.CTRL.value + (0 if self.is_supported else 1) if self.cfg.mode == KeyboardMode.CTRL
            #         else 1
            #     )
            # )
        else:
            self.cfg.mode = mode

        self.cfg.save()

        create_snack(f"键盘 {'控制' if self.cfg.mode == KeyboardMode.CTRL else '输入'} 模式，(F8切换)",
                     color=MYCombineColors.orange if self.cfg.mode == KeyboardMode.CTRL else MYCombineColors.blue,
                     duration=1).open()

    def switch_space(self, space: int = None):
        """
            切换控制空间
        :return:
        """
        if space is None:
            self.cfg.space = self.cfg.space + (
                (-self.MAX_SPACE_N + 1) if self.cfg.space == (self.MAX_SPACE_N - 1) else 1
            )

        elif type(space) is int and 0 <= space < self.MAX_SPACE_N:
            self.cfg.space = space

        self.cfg.save()

        Logger.info(f'Switched Keyboard Space To: {self.cfg.space}')

    def to_adb(self, key: UnifiedKey):
        """
            ADB 模拟组合键
        :param key:
        :return:
        """
        func_down = ''

        for _ in Window.modifiers:
            fn = {
                'ctrl': ADBKeyCode.KB_CONTROL_L,
                'shift': ADBKeyCode.KB_SHIFT_L,
                'alt': ADBKeyCode.KB_ALT_L,
            }.get(_, None)
            if fn:
                func_down += f'{fn}'

        if func_down:
            t = self.device.adb_dev.shell
            args = (f"input keycombination {func_down} {KeyMapper.uk2adb(key)}", )

        else:
            t = self.device.adb_dev.keyevent
            args = (KeyMapper.uk2adb(key), )

        threading.Thread(target=t, args=args).start()
