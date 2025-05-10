# -*- coding: utf-8 -*-
"""
    connect_manager
    ~~~~~~~~~~~~~~~~~~
    
    Log:
        2025-05-10 3.2.0 Me2sY  定版

        2025-04-23 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '3.2.0'

__all__ = [
    'ConnectManager'
]

from collections import OrderedDict
from dataclasses import dataclass
from functools import partial, wraps
from typing import Callable

from adbutils import adb

from kivy import Logger
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics.texture import texture_create
from kivy.metrics import sp, Metrics
from kivy.properties import StringProperty
from kivy.storage.dictstore import DictStore

from kivymd.uix.button import MDFabButton
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.tooltip import MDTooltip

from myscrcpy.core import VideoArgs, AudioArgs, ControlArgs, Session
from myscrcpy.gui.k import StoredConfig, MYCombineColors, create_snack
from myscrcpy.gui.k.components.device_panel import load_cfg
from myscrcpy.gui.k.components.video_screen import VideoScreen
from myscrcpy.gui.k.components.indicator import IndicatorManager, ProxyReactor, Indicator
from myscrcpy.gui.k.handler.device_handler import MYDevice
from myscrcpy.gui.k.handler.mouse_handler import *
from myscrcpy.gui.k.handler.keyboard_handler import *
from myscrcpy.utils import Param, Coordinate, ROTATION_VERTICAL, ADBKeyCode, UnifiedKeys, UnifiedKey


@dataclass
class SessionConfig(StoredConfig):
    """
        Session Config
    """

    _STORAGE_KEY = 'session'

    size_v: tuple[int, int] = (600, 800)
    size_h: tuple[int, int] = (1600, 900)

    top_v: int = sp(200)
    left_v: int = sp(200)

    top_h: int = sp(200)
    left_h: int = sp(200)


class ConnectSession:

    def __init__(
            self,
            my_device: MYDevice,
            connect_cfg_name: str,
            manager: 'ConnectManager',
            **kwargs
    ):
        self.my_device: MYDevice = my_device
        self.cfg_name = connect_cfg_name
        self.manager = manager

        # 加载运行配置
        self.run_cfg = SessionConfig.load(
            DictStore(Param.PATH_CONFIGS / 'ky__connect_session.dsf'),
            belongs=f"{self.my_device.connect_serial}_{self.cfg_name}"
        )

        # 加载连接配置
        is_success, args = load_cfg(self.my_device.connect_serial, self.cfg_name)
        if not is_success:
            args = (VideoArgs(), AudioArgs(), ControlArgs())

        self.video_args, self.audio_args, self.control_args = args

        # 连接 Session
        self._sess = Session(
            self.my_device.adb_dev,
            video_args=self.video_args,
            audio_args=self.audio_args,
            control_args=self.control_args
        )

        self.screen_status = self.control_args.screen_status == ControlArgs.STATUS_ON

        # 视频
        self.screen = VideoScreen(name=self.session_name)
        self.screen.rotation = self.my_device.get_rotation()
        self.clock_update_frame = None

        if self._sess.va:
            self.frame_n = self._sess.va.frame_n
            self.is_video_pause: bool = kwargs.get('is_video_pause', False)

            self.coord_frame = self._sess.va.coordinate

            _max, _min = self.coord_frame.max_size, self.coord_frame.min_size
            self.rotation = self.coord_frame.rotation

            # Create Texture
            self.texture_v = texture_create(size=(_min, _max))
            self.texture_h = texture_create(size=(_max, _min))

            self.texture_v.flip_vertical()
            self.texture_h.flip_vertical()
        else:
            self.screen.set_no_connected()
            self.rotation = self.my_device.get_rotation()

        # 音频
        if self._sess.aa:
            self.status_mute = self._sess.aa.mute

        # 控制
        if self._sess.ca:
            self.mouse_handler = MouseHandler(
                MouseHandlerConfig.load(
                    DictStore(Param.PATH_CONFIGS / 'ky__mouse_handler.dsf'),
                    belongs=f"{self.my_device.connect_serial}_{self.cfg_name}"
                ), self.screen, self._sess.ca, self.my_device
            )
            self.keyboard_handler = KeyboardHandler(
                KeyboardHandlerConfig.load(
                    DictStore(Param.PATH_CONFIGS / 'ky__keyboard_handler.dsf'),
                    belongs=f"{self.my_device.connect_serial}_{self.cfg_name}"
                ), self._sess.ca, self.my_device, self.manager.update_keyboard_button_status
            )

            for _ in range(self.mouse_handler.gesture_handler.MAX_SPACE_N):
                self.mouse_handler.gesture_handler.register_gesture_action(
                    _, GesAction('mysc', 'L', 'Back', partial(
                        self.my_device.adb_dev.keyevent, ADBKeyCode.BACK.value))
                )
                self.mouse_handler.gesture_handler.register_gesture_action(
                    _, GesAction('mysc', 'U', 'Home', partial(
                        self.my_device.adb_dev.keyevent, ADBKeyCode.HOME.value))
                )
                self.mouse_handler.gesture_handler.register_gesture_action(
                    _, GesAction('mysc', 'UL', 'Apps', partial(
                        self.my_device.adb_dev.keyevent, ADBKeyCode.APP_SWITCH.value))
                )

            self.keyboard_handler.register_system_key_callback(
                UnifiedKeys.UK_KB_F9,
                lambda *_args, **_kwargs:
                self.mouse_handler.switch_mode_callback(*_args, **_kwargs) or self.manager.update_mouse_button_status()
            )
        else:
            self.mouse_handler = None
            self.keyboard_handler = None

        self.indicator_manager: IndicatorManager | None = None
        self.proxy_reactor: ProxyReactor | None = None

        self.is_activate = False

    def activate(self, rotation_callback: Callable = None):
        """
            激活
        :param rotation_callback:
        :return:
        """
        if self.is_activate:
            return

        # 激活视频刷新定时器
        if self._sess.va:
            self.clock_update_frame = Clock.schedule_interval(
                partial(self.update_frame, rotation_callback), 1 / self.video_args.fps
            )

        # 激活音频状态
        if self._sess.aa:
            self._sess.aa.set_mute(self.status_mute)

        # 激活控制
        if self._sess.ca:
            self.screen.bind(
                on_touch_down=self.mouse_handler.touch_down,
                on_touch_up=self.mouse_handler.touch_up,
                on_touch_move=self.mouse_handler.touch_move,
            )
            self.keyboard_handler.activate()

        if self.proxy_reactor:
            self.proxy_reactor.activate()

        self.is_activate = True

    def deactivate(self):
        """
            失活
        :return:
        """

        if not self.is_activate:
            return

        # 取消激活定时器
        if self._sess.va and self.clock_update_frame:
            self.clock_update_frame.cancel()

        # 音频静音
        if self._sess.aa:
            self.status_mute = self._sess.aa.mute
            self._sess.aa.set_mute(True)

        # 控制
        if self._sess.ca:
            self.keyboard_handler.deactivate()

        if self.proxy_reactor:
            self.proxy_reactor.deactivate()

        self.is_activate = False

    @property
    def session_name(self) -> str:
        """
            Session name
        :return:
        """
        return f'{self.my_device.connect_serial}_{self.cfg_name}'

    def disconnect(self, *args, **kwargs):
        """
            停止 Session
        :param args:
        :param kwargs:
        :return:
        """
        self.deactivate()
        self._sess.disconnect()
        self.run_cfg.save()
        Logger.warning(f"Device: {self.my_device.connect_serial} RunSession Stop")

    def update_frame(self, rotation_callback: Callable[[Coordinate], None] = None, *args, **kwargs):
        """
            更新视频 Frame
        :param rotation_callback:
        :return:
        """
        if not self.is_activate or not self._sess.is_running: return

        if self._sess.va is None or not self._sess.va.is_ready: return

        if self.is_video_pause: return

        if self.frame_n == self._sess.va.frame_n:
            return
        else:
            self.frame_n = self._sess.va.frame_n

        _f = self._sess.va.get_frame()
        _coord = Coordinate.from_np_shape(_f.shape)

        if _coord.rotation == ROTATION_VERTICAL:
            self.texture_v.blit_buffer(_f.tobytes())
            self.screen.update_frame(self.texture_v)
        else:
            self.texture_h.blit_buffer(_f.tobytes())
            self.screen.update_frame(self.texture_h)

        # 旋转
        if _coord.rotation != self.rotation:
            self.rotation = _coord.rotation
            self.screen.rotation = _coord.rotation
            if rotation_callback:
                rotation_callback(_coord)

    def start_indicator_edit(self, cfg_name: str = None):
        """
            启动编辑器
        :param cfg_name:
        :return:
        """
        if self._sess.ca:
            self.indicator_manager = IndicatorManager(self)
            self.manager.add_widget(self.indicator_manager.screen)
            self.manager.current = self.indicator_manager.screen.name

            self.indicator_manager.rect.texture = self.texture_v if self.rotation == ROTATION_VERTICAL \
                else self.texture_h

            self.manager.bind(size=self.indicator_manager.update_pos)

            self.indicator_manager.update_pos()

            if self.proxy_reactor:
                self.indicator_manager.load_cfg(self.proxy_reactor.cfg_name)

            self.manager.gui.side_panel.disabled = True
            self.manager.gui.bottom_bar.disabled = True

            create_snack('映射编辑器启动', color=MYCombineColors.green, duration=2).open()

    def start_proxy(self, cfg_name: str, reg_idt: dict[UnifiedKey, Indicator]):
        """
            启动代理模式
        :param cfg_name:
        :param reg_idt:
        :return:
        """

        # 如果处于编辑模式，则关闭
        if self.indicator_manager:
            self.indicator_manager.close()

        # 如果存在映射处理器，则关闭
        if self.proxy_reactor:
            self.proxy_reactor.close()

        self.manager.btn_mouse.disabled = True
        self.manager.btn_keyboard.disabled = True

        # 创建映射处理器
        self.proxy_reactor = ProxyReactor(cfg_name, reg_idt, self._sess.ca, self.mouse_handler)
        self.proxy_reactor.activate()

        self.manager.update_indicator_status()

        create_snack(f'进入映射模式', color=MYCombineColors.green, duration=2).open()

    def create__menu_indicator(self, caller):
        """
            创建 映射配置文件列表
        :param caller:
        :return:
        """
        def _load_cfg(cfg_name: str):
            im.load_cfg(cfg_name)
            self.start_proxy(cfg_name, im.registered_indicators)

        im = IndicatorManager(self)
        im.list_cfgs(callback=_load_cfg)


class TooltipButton(MDTooltip): ...


class ControlButton(TooltipButton, MDFabButton):
    """
        控制按钮
    """

    text = StringProperty()

    def update_color(self, color: MYCombineColors):
        self.theme_bg_color = 'Custom'
        self.md_bg_color = color.value[0]
        self.theme_icon_color = 'Custom'
        self.icon_color = color.value[1]


class ConnectManager(MDScreenManager):

    def __init__(self, gui, main_cfg, rotation_callback: Callable = None, **kwargs):
        """
            连接管理器，ScreenManager对象，每一个连接生成一个ConnectSession,包含显示Screen
        :param gui:
        :param main_cfg:
        :param rotation_callback:
        :param kwargs:
        """
        super().__init__(**kwargs)

        self.gui = gui
        self.main_cfg = main_cfg
        self.rotation_callback = rotation_callback

        self.sessions: OrderedDict[str, ConnectSession] = OrderedDict()
        self.last_session: ConnectSession | None = None

        self.bind(current=self.set_current)

        Window.bind(
            on_resize=self.on_window_resize,
            top=self.on_window_move_top, left=self.on_window_move_left,
            on_request_close=self.stop
        )

    def _rotation_callback(self, *args, **kwargs):
        """
            屏幕选择回调，重置窗口大小
        :param args:
        :param kwargs:
        :return:
        """
        if self.rotation_callback:
            self.rotation_callback()

        self.reset_window_size_pos()

    def start_session(self, my_device: MYDevice, cfg_name: str, **kwargs) -> ConnectSession | None:
        """
            启动 Connect Session
        :param my_device:
        :param cfg_name:
        :param kwargs:
        :return:
        """
        session_name = f"{my_device.connect_serial}_{cfg_name}"

        # 停止原有Session
        self.stop_session(session_name)

        cs = ConnectSession(my_device, cfg_name, self)
        self.sessions[session_name] = cs
        self.add_widget(cs.screen)

        return cs

    def stop_session(self, session_name: str, **kwargs):
        """
            停止 Connect Session
        :param session_name:
        :param kwargs:
        :return:
        """
        if session_name in self.sessions:
            cs = self.sessions.pop(session_name)
            cs.disconnect()
            self.remove_widget(cs.screen)

    def stop_current_session(self):
        """
            停止当前 Connect Session
        :return:
        """
        cs = self.current_session
        if cs:
            self.stop_session(cs.session_name)

    @property
    def current_session(self) -> ConnectSession | None:
        """
            current session
        :return:
        """
        return self.sessions.get(self.current)

    def set_current(self, instance, cs_name: str, *args, **kwargs):
        """
            设置当前页面
        :param instance:
        :param cs_name:
        :return:
        """
        if cs_name is None:
            Window.set_title('MYScrcpy - Me2sY')
            return

        if cs_name.startswith('__indicator'):
            Window.set_title('按键映射编辑器')
            if self.last_session:
                self.last_session.deactivate()
            return

        self.update_mouse_button_status()
        self.update_keyboard_button_status()
        self.update_screen_switch_status()
        self.update_indicator_status()

        if self.last_session:
            self.last_session.deactivate()

        self.last_session = self.current_session
        self.last_session.activate(self._rotation_callback)

        Window.set_title(f"{self.last_session.session_name}")
        self.reset_window_size_pos()

        history = self.main_cfg.connect_history
        try:
            history.pop(
                history.index(
                    (self.last_session.my_device.connect_serial, self.last_session.cfg_name)
                )
            )
        except ValueError:
            pass

        history.insert(0, (self.last_session.my_device.connect_serial, self.last_session.cfg_name))
        self.main_cfg.connect_history = history[:5]
        self.main_cfg.save()

    def stop(self, *args, **kwargs):
        """
            停止所有 ConnectSession 运行
        :param args:
        :param kwargs:
        :return:
        """
        for cs in self.sessions.values():
            cs.disconnect()

    def create__cs_list_dropdown(self, caller) -> MDDropdownMenu:
        """
            当前已连接设备列表
        :param caller:
        :return:
        """
        mdm = MDDropdownMenu(caller=caller)

        if self.current_session is not None:
            _current_session_name = self.current_session.session_name
        else:
            _current_session_name = None

        items = []
        for session_name in self.sessions.keys():
            if session_name == _current_session_name:
                items.append({'text': session_name, 'leading_icon': 'arrow-right',  'on_release': mdm.dismiss})
            else:
                items.append({
                    'text': session_name, 'leading_icon': 'minus',
                    'on_release': lambda _=session_name: mdm.dismiss() or setattr(self, 'current', _)
                })

        mdm.items = items

        return mdm

    @staticmethod
    def add_rotation(func):
        """
            添加旋转处理
        :param func:
        :return:
        """
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.current_session is None:
                return

            # 使用FrameCoord 如果 VA未建立连接 使用my_device get_rotation方法 通过ADB获取
            if self.current_session._sess.va and self.current_session._sess.va.is_ready:
                func(self, self.current_session._sess.va.coordinate.rotation, *args, **kwargs)
            else:
                # 若未初始化 则初始化 u2d 以便快速获取 rotation
                Clock.schedule_once(self.current_session.my_device.init_u2d)
                func(self, self.current_session.my_device.get_rotation(), *args, **kwargs)

            self.current_session.run_cfg.save()

        return wrapper

    @add_rotation
    def on_window_resize(self, rotation, *args):
        """
            记录窗口重置大小
        :param rotation:
        :param args:
        :return:
        """
        i, w, h = args

        if rotation == ROTATION_VERTICAL:
            self.current_session.run_cfg.size_v = (w, h)
        else:
            self.current_session.run_cfg.size_h = (w, h)

    @add_rotation
    def on_window_move_top(self, rotation, *args):
        """
            保持窗口Top位置
        :param rotation:
        :param args:
        :return:
        """
        i, top = args
        if rotation == ROTATION_VERTICAL:
            self.current_session.run_cfg.top_v = top
        else:
            self.current_session.run_cfg.top_h = top

    @add_rotation
    def on_window_move_left(self, rotation, *args):
        """
            保存窗口Left位置
        :param rotation:
        :param args:
        :return:
        """
        i, left = args
        if rotation == ROTATION_VERTICAL:
            self.current_session.run_cfg.left_v = left
        else:
            self.current_session.run_cfg.left_h = left

    @property
    def is_empty(self) -> bool:
        return len(self.sessions) == 0

    def reset_window_size_pos(self, *args, **kwargs):
        """
            重置Window位置及大小
        :return:
        """

        cs = self.current_session
        if cs is None:
            return

        if cs._sess.va and cs._sess.va.is_ready:
            r = cs._sess.va.coordinate.rotation
        else:
            r = cs.my_device.get_rotation()

        if r == ROTATION_VERTICAL:
            size = cs.run_cfg.size_v
            top = cs.run_cfg.top_v
            left = cs.run_cfg.left_v
        else:
            size = cs.run_cfg.size_h
            top = cs.run_cfg.top_h
            left = cs.run_cfg.left_h

        Window.size = size[0] / Metrics.density, size[1] / Metrics.density
        Window.top = top
        Window.left = left

    def create__history_dropdown(self, caller) -> MDDropdownMenu:
        """
            创建连接历史下拉菜单
        :param caller:
        :return:
        """
        mdm = MDDropdownMenu(caller=caller)

        history = self.main_cfg.connect_history
        device_list = adb.device_list()
        device_online = [d.serial for d in device_list]

        items = []

        def start(_adb_device, _cfg_name: str):
            self.gui.cb__connect_device(_adb_device, _cfg_name)

        for serial, cfg_name in history:
            if serial in device_online:
                is_success, args = load_cfg(serial, cfg_name)
                if is_success:
                    device = adb.device(serial)

                    try:
                        wlan_ip = device.wlan_ip()
                    except Exception as e:
                        wlan_ip = ''

                    items.append(dict(
                        text=f"{serial[:10]} {cfg_name}",
                        leading_icon='wifi' if device.serial.startswith(wlan_ip + ":") else 'usb',
                        on_release=lambda *_args, d=device, c=cfg_name: start(d, c)
                    ))
                else:
                    items.append(dict(
                        text=f"{serial[:10]} {cfg_name}",
                        leading_icon='file-document-remove',
                        on_release=mdm.dismiss
                    ))
            else:
                items.append(dict(
                    text=f"{serial[:10]} {cfg_name}", leading_icon='power-plug-off',
                    on_release=mdm.dismiss
                ))

        mdm.items = items

        return mdm

    def create__resize_dropdown(self, caller) -> MDDropdownMenu:
        """
            创建调节显示DropDown
        :param caller:
        :return:
        """
        mdm = MDDropdownMenu(caller=caller)

        items = [
            dict(
                text='Vertical', leading_icon='arrow-expand-vertical',
                on_release=lambda *args: mdm.dismiss() or self.fit_by_width()
            ),
            dict(
                text='Horizontal', leading_icon='arrow-expand-horizontal',
                on_release=lambda *args: mdm.dismiss() or self.fit_by_height()
            ),
        ]

        mdm.items = items

        return mdm

    def fit_by_width(self):
        """
            以宽度为标准调整高度
        :return:
        """
        w, h = Window.size
        device_coord = self.current_session.my_device.cur_coord()
        nw, nh = self.size
        Window.size = (w / Metrics.density, ((device_coord.w2h(nw) - nh) + h) / Metrics.density)

    def fit_by_height(self):
        """
            以高度为标准调整宽度
        :return:
        """
        w, h = Window.size
        device_coord = self.current_session.my_device.cur_coord()
        nw, nh = self.size
        Window.size = (((device_coord.h2w(nh) - nw) + w) / Metrics.density, h / Metrics.density)

    def create__mouse_button(self) -> ControlButton:
        """
            创建鼠标控制按钮
        :return:
        """
        self.btn_mouse = ControlButton(
            icon='mouse-off', style='small', on_release=self.mouse_action, disabled=True
        )
        self.update_mouse_button_status()
        return self.btn_mouse

    def update_mouse_button_status(self):
        """
            更新鼠标按钮状态
        :return:
        """
        if self.current_session and self.current_session.mouse_handler:
            mode = self.current_session.mouse_handler.cfg.mode

            self.btn_mouse.update_color(
                {
                    MouseHandlerMode.TOUCH: MYCombineColors.orange,
                }.get(mode, MYCombineColors.blue)
            )
            self.btn_mouse.icon='gesture-tap' if mode == MouseHandlerMode.TOUCH else 'mouse'
            self.btn_mouse.disabled = False
        else:
            self.btn_mouse.disabled = True

    def mouse_action(self, *args):
        """
            鼠标按钮事件
        :param args:
        :return:
        """
        if self.current_session and self.current_session.mouse_handler:
            self.current_session.mouse_handler.switch_mode()
            self.update_mouse_button_status()

    def create__keyboard_button(self) -> ControlButton:
        """
            创建键盘控制按钮
        :return:
        """
        self.btn_keyboard = ControlButton(
            icon='keyboard-off', style='small', on_release=self.keyboard_action, disabled=True
        )
        self.update_keyboard_button_status()
        return self.btn_keyboard

    def update_keyboard_button_status(self):
        """
            更新键盘按钮状态
        :return:
        """
        if self.current_session and self.current_session.keyboard_handler:
            mode = self.current_session.keyboard_handler.cfg.mode

            self.btn_keyboard.update_color(
                {
                    KeyboardMode.CTRL: MYCombineColors.orange
                }.get(mode, MYCombineColors.blue)
            )
            self.btn_keyboard.icon='function' if mode == KeyboardMode.CTRL else 'keyboard-variant'
            self.btn_keyboard.disabled = False
        else:
            self.btn_keyboard.disabled = True

    def keyboard_action(self, *args):
        """
            键盘事件
        :param args:
        :return:
        """
        if self.current_session and self.current_session.keyboard_handler:
            self.current_session.keyboard_handler.switch_mode()
            self.update_keyboard_button_status()

    def create__indicator_button(self) -> ControlButton:
        """
            创建指示器按钮
        :return:
        """
        self.btn_indicator = ControlButton(
            icon='controller-off', style='small', disabled=True, on_release=self.indicator_action
        )
        return self.btn_indicator

    def update_indicator_status(self):
        """
            更新指示器按钮状态
        :return:
        """
        if self.current_session and self.current_session._sess.ca:
            self.btn_indicator.disabled = False
            self.btn_indicator.icon = 'controller' if self.current_session.proxy_reactor else 'controller-off'
        else:
            self.btn_indicator.disabled = True
            self.btn_indicator.icon = 'controller-off'

    def close_proxy(self, *args):
        """
            关闭映射
        :param args:
        :return:
        """
        self.current_session.proxy_reactor.close()
        self.current_session.proxy_reactor = None
        self.btn_mouse.disabled = False
        self.btn_keyboard.disabled = False
        self.update_indicator_status()

    def indicator_action(self, *args):
        """
            按键功能
        :param args:
        :return:
        """
        # 根据不同代理状态 显示不同功能菜单
        if self.current_session:
            if self.current_session.proxy_reactor:
                items = [
                    dict(text=f"当前配置文件: {self.current_session.proxy_reactor.cfg_name}", leading_icon='arrow-right',
                         on_release=lambda *_args: mdm.dismiss()),
                    dict(text=f"退出映射模式", leading_icon='close',
                         on_release=lambda *_args: mdm.dismiss() or self.close_proxy())
                ]

            else:
                items = [
                    dict(
                        text='进入按键映射模式', leading_icon='controller', on_release=lambda *_args:
                        mdm.dismiss() or self.current_session.create__menu_indicator(self.btn_indicator)
                    ),
                    dict(text='进入编辑模式', leading_icon='file-edit-outline', on_release=lambda *_args:
                         mdm.dismiss() or self.current_session.start_indicator_edit())
                ]

            mdm = MDDropdownMenu(caller=self.btn_indicator, items=items)
            mdm.open()

    def create__screen_switch_button(self) -> ControlButton:
        """
            创建屏幕控制按钮
        :return:
        """
        self.btn_screen_switch = ControlButton(
            icon='lightbulb-multiple-outline', style='small', on_release=self.screen_switch_action,
            disabled=True
        )
        self.update_screen_switch_status()
        return self.btn_screen_switch

    def update_screen_switch_status(self):
        """
            更新屏幕开关按钮状态
        :return:
        """
        if self.current_session and self.current_session._sess.ca:
            self.btn_screen_switch.disabled = False
            self.btn_screen_switch.update_color(
                MYCombineColors.white if self.current_session.screen_status else MYCombineColors.black
            )
            self.btn_screen_switch.icon = 'lightbulb-on-10' if self.current_session.screen_status else 'lightbulb-off-outline'
        else:
            self.btn_screen_switch.disabled = True

    def screen_switch_action(self, *args):
        """
            开关屏幕
        :param args:
        :return:
        """
        if self.current_session and self.current_session._sess.ca:
            cs = self.current_session
            cs.screen_status = not cs.screen_status
            cs._sess.ca.f_set_screen(cs.screen_status)
            self.update_screen_switch_status()
