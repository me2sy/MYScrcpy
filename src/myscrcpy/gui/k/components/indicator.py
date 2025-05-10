# -*- coding: utf-8 -*-
"""
    indicator
    ~~~~~~~~~~~~~~~~~~
    指示与按键映射

    Log:
        2025-05-06 3.2.0 Me2sY
            1.增加Shift唤醒UHID鼠标功能
            2.2025-05-10 增加不同平台 move 功能
            3.2025-05-10 修复部分缺陷

        2025-04-25 0.1.0 Me2sY 创建
"""

__author__ = 'Me2sY'
__version__ = '3.2.0'

__all__ = [
    'Indicator',
    'IndicatorManager',
    'ProxyReactor'
]

from dataclasses import dataclass, field
from enum import unique, IntEnum
from functools import wraps, partial, cache
import random
import time
from typing import ClassVar, Callable, Any, Dict, Self
import uuid

from kivy import Logger
from kivy.clock import Clock, ClockEvent
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import sp, Metrics
from kivy.storage.jsonstore import JsonStore
from kivy.uix.modalview import ModalView
from kivy.utils import platform

from kivymd.uix.badge import MDBadge
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import (
    MDDialog, MDDialogHeadlineText, MDDialogButtonContainer, MDDialogContentContainer,
    MDDialogSupportingText
)
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.progressindicator import MDCircularProgressIndicator
from kivymd.uix.relativelayout import MDRelativeLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.slider import MDSlider, MDSliderHandle
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
from kivymd.uix.widget import MDWidget

from pynput.mouse import Controller as MouseController
from pynput.mouse import Listener as MouseListener
from pynput.mouse import Button

from myscrcpy.core import ControlAdapter
from myscrcpy.gui.k.handler.mouse_handler import MouseHandler
from myscrcpy.gui.k import create_snack, MYCombineColors, KeyMapper, MYColor
from myscrcpy.utils import ScalePointR, UnifiedKey, UnifiedKeys, Param, Action


@unique
class TouchPointType(IntEnum):
    """
        按键代理类型
    """
    NotDefined = -1

    BtnInstantly = 1
    BtnHold = 2
    BtnRepeat = 3
    BtnSwitch = 4
    BtnAim = 5
    BtnWatch = 6

    Cross = 10


class SetUKButton(MDButton):

    def __init__(
            self, uk: UnifiedKey, key_changed_callback: Callable[[UnifiedKey], bool], **kwargs):
        """
            设置按键控件
        :param uk:
        :param key_changed_callback:
        :param kwargs:
        """
        super().__init__(**kwargs)

        self.style='filled'

        self.uk = uk
        self.key_changed_callback = key_changed_callback

        self.btn_text = MDButtonText(text='点击绑定' if self.uk == UnifiedKeys.UK_UNKNOWN else self.uk.value)
        self.add_widget(self.btn_text)
        self.bind(on_release=self.bind_key)

    def bind_key(self, *args):
        """
            绑定按键
        :return:
        """
        mv = ModalView(auto_dismiss=False)
        mv.add_widget(
            MDLabel(text='按任意键绑定\n按Esc退出', halign='center', theme_text_color='Custom', text_color='white'))
        mv.add_widget(
            MDCircularProgressIndicator(size_hint=(.3, .3))
        )

        def mouse(instance, touch):
            """
                鼠标按键
            :param instance:
            :param touch:
            :return:
            """
            mv.dismiss()
            _keyboard.unbind(on_key_down=_callback)
            _keyboard.release()

            try:
                set_key({
                    'left': UnifiedKeys.UK_MOUSE_L,
                    'right': UnifiedKeys.UK_MOUSE_R,
                    'middle': UnifiedKeys.UK_MOUSE_WHEEL,
                }.get(touch.button))
            except KeyError:
                ...

        mv.bind(on_touch_down=mouse)

        mv.open()

        def _callback(*_args):
            """
                停止键盘响应，判断是否为esc并发起回调
            :param _args:
            :return:
            """
            _keyboard.unbind(on_key_down=_callback)
            _keyboard.release()
            mv.dismiss()

            # ESC为退出键 F1为配置快捷键
            if _args[1][1] in ['escape', 'F1']:
                set_key(self.uk)
            else:
                set_key(KeyMapper.ky2uk(_args[1][0]))

        def set_key(uk):
            """
                设置按键
            :param uk:
            :return:
            """
            if uk == self.uk:
                create_snack(f"按键无变化", color=MYCombineColors.orange, duration=1).open()
                return

            if self.key_changed_callback(uk):

                self.uk = uk
                self.btn_text.text = str(uk.value) if uk.value is not None else uk.code

                create_snack(f"按键设置为{uk.value}", color=MYCombineColors.green, duration=1).open()

        # 注册键盘
        _keyboard = Window.request_keyboard(lambda *_args: ..., mv, 'text', False)
        _keyboard.bind(on_key_down=_callback)


class SettingDialog(MDDialog):

    def __init__(self, indicator_type_name: str, **kwargs):
        """
            设置窗口
        :param kwargs:
        """
        super(SettingDialog, self).__init__(**kwargs)
        self.add_widget(MDDialogHeadlineText(text='按键设置'))
        self.add_widget(MDDialogSupportingText(text=f"类型: {indicator_type_name}"))

        self.container = MDDialogContentContainer(orientation='vertical')
        self.add_widget(self.container)

        self.add_widget(
            MDDialogButtonContainer(
                MDWidget(), MDButton(MDButtonText(text='关闭'), style='text', on_release=self.dismiss),
            )
        )

    def save(self, *args):
        raise NotImplementedError()


@dataclass
class IndicatorStyle:

    name: str = ''
    color: str = MYColor.grey
    icon: str = 'target'


class IndicatorKwargs:
    def __init__(self, **kwargs): ...


class Indicator(MDWidget, IndicatorKwargs):

    TPT = TouchPointType.NotDefined
    IStyle: ClassVar[IndicatorStyle] = field(default=IndicatorStyle())

    KEYS = []

    @staticmethod
    def get_validate(instance: object, attr: str, value_type, ipt_instance, value):
        """
            获取指定类型值
        :param instance:
        :param attr:
        :param value_type: 值类型
        :param ipt_instance:
        :param value:
        :return:
        """
        try:
            setattr(instance, attr, value_type(value))
        except Exception as e:
            ipt_instance.error = True
            ipt_instance.text = ipt_instance.text[:-1]

    def dump(self, keys: list[str] = None) -> Dict[str, Any]:
        """
            转储
        :param keys:
        :return:
        """

        _d = {_key: _value for _key, _value in self.__dict__.items() if _key.startswith('i__') or _key in self.KEYS}

        if keys:
            _d.update({key: getattr(self, key) for key in keys})

        return _d

    def load(self, _obj_dict: Dict[str, Any]):
        """
            加载
        :param _obj_dict:
        :return:
        """
        for k, v in _obj_dict.items():
            setattr(self, k, v)

    def set_uk(self, uk: UnifiedKey | int):
        """
            设置按键
        :param uk:
        :return:
        """
        if isinstance(uk, int):
            self.i_code = uk
        elif isinstance(uk, UnifiedKey):
            self.i_code = uk.code

    def on_key_down(self, *args, **kwargs): ...

    def on_key_up(self, *args, **kwargs): ...

    @property
    def spr(self) -> ScalePointR:
        """
            ScalePointR
        :return:
        """
        return ScalePointR(self.i__x, self.i__y, self.i__r)

    @property
    def uk(self) -> UnifiedKey:
        """
            按键
        :return:
        """
        return UnifiedKeys.get_by_code(self.i__code)

    def __init__(self, indicator_manager: 'IndicatorManager', **kwargs):

        # Run Value
        self.tid = -1
        self.is_pressed = False
        self.proxy_reactor: ProxyReactor | None = None

        # Saved Parameter
        self.i__code = kwargs.pop('i__code', UnifiedKeys.UK_UNKNOWN.code)
        self.i__x = kwargs.pop('i__x', .5)
        self.i__y = kwargs.pop('i__y', .5)
        self.i__r = kwargs.pop('i__r', 0)

        self.i__tpt = self.TPT

        _obj_dict = kwargs.pop('obj_dict', {})
        _obj_dict and self.load(_obj_dict)

        super().__init__(**kwargs)

        self.size_hint = (None, None)
        self.size = (sp(60), sp(60))

        self.idm: IndicatorManager = indicator_manager

        self.is_moving: bool = False

        self.indicator_badge = MDBadge()

        # 注册Icon
        self.indicator_icon = MDIcon(self.indicator_badge, icon=self.IStyle.icon, icon_color=self.IStyle.color)
        self.add_widget(self.indicator_icon, canvas='before')

        self.idm.add_widget(self)
        self.idm.bind(size=self.update_pos)

        # 更新位置
        Clock.schedule_once(self.update_pos, 0)
        self.register()

    def register(self):
        """
            注册响应按键
        :return:
        """
        # 注册按键
        if self.uk != UnifiedKeys.UK_UNKNOWN:
            if self.uk in self.idm.registered_indicators:
                Logger.warning(f"{self.uk} Already Registered!")
                self.set_uk(UnifiedKeys.UK_UNKNOWN)
            else:
                self.idm.registered_indicators[self.uk] = self
                self.indicator_badge.text = str(self.uk.value) if self.uk.value else str(self.uk.code)
                Logger.info(f"{self.uk} Registered!")

    def update_pos(self, *args):
        """
            更新位置
        :param args:
        :return:
        """

        # 统一使用 Window Pos 转会 Widget Pos
        self.center = self.to_widget(
            self.idm.x + self.idm.width * self.i__x,
            self.idm.y + self.idm.height * (1 - self.i__y)
        )
        self.indicator_icon.center = self.center

    def create__dropdown_menu(self) -> MDDropdownMenu:
        """
            创建功能菜单
        :return:
        """
        mdm = MDDropdownMenu(caller=self)

        items = [
            dict(text='设置', leading_icon='cog', on_release=lambda *args: mdm.dismiss() or self.create__setup_dialog()),
            dict(text='删除', leading_icon='delete', on_release=lambda *args: mdm.dismiss() or self.delete()),
            dict(text='锁定/解锁位置', leading_icon='lock', on_release=lambda *args: mdm.dismiss() or self.lock_switch()),
        ]

        mdm.items = items

        return mdm

    def lock_switch(self):
        """
            切换锁定状态
        :return:
        """
        self.disabled = not self.disabled

    def pop_uk(self):
        """
            删除注册按键
        :return:
        """
        if self.uk in self.idm.registered_indicators:
            self.idm.registered_indicators.pop(self.uk)

    def delete(self):
        """
            删除指示器
        :return:
        """
        self.pop_uk()
        self.idm.remove_widget(self)
        create_snack(f"按键已删除", color=MYCombineColors.red, duration=1).open()

    def create__setup_dialog(self):
        """
            创建设置窗口
        :return:
        """
        # 创建布局
        sd = SettingDialog(self.IStyle.name)
        content = MDGridLayout(cols=2, adaptive_height=True, spacing=sp(15))
        sd.container.add_widget(content)

        # 配置按键列
        content.add_widget(MDLabel(text='按键', size_hint=(None, 1), width=sp(40)))

        def register_key(uk: UnifiedKey) -> bool:
            """
                注册按键
            :param uk:
            :return:
            """
            if uk is None:
                create_snack(f"设置出错，请重试！", color=MYCombineColors.red, duration=1).open()
                return False

            if uk in self.idm.registered_indicators:
                create_snack(f"按键 {uk.value} 重复！", color=MYCombineColors.red, duration=1).open()
                return False

            else:
                if self.uk in self.idm.registered_indicators:
                    self.idm.registered_indicators.pop(self.uk)

                self.i__code = uk.code
                self.idm.registered_indicators[self.uk] = self
                self.indicator_badge.text = str(self.uk.value) if self.uk.value is not None else str(self.uk.code)
                return True

        content.add_widget(SetUKButton(self.uk, register_key))

        self.setup_details(sd.container)

        sd.open()

    def setup_details(self, container: MDDialogContentContainer): ...

    @staticmethod
    def before_touch(func):
        """
            锁定控件
        :param func:
        :return:
        """
        @wraps(func)
        def wrapper(self, touch):
            if touch.button == 'right':
                return func(self, touch)

            else:
                if self.disabled:
                    return None
                else:
                    return func(self, touch)

        return wrapper

    @before_touch
    def on_touch_down(self, touch):
        """
            触摸事件
        :param touch:
        :return:
        """
        if self.collide_point(*touch.pos):
            if touch.button == 'right':
                self.create__dropdown_menu().open()
            elif touch.is_double_tap:
                self.create__setup_dialog()
            else:
                self.is_moving = True

            # 拦截 Event
            return True

        else:
            self.is_moving = False
            return None

    @before_touch
    def on_touch_move(self, touch):
        """
            移动指示器
        :param touch:
        :return:
        """
        if self.is_moving:
            self.i__x, self.i__y, self.i__r = self.idm.get_spr(self.to_window(*touch.pos))
            self.update_pos()

    @before_touch
    def on_touch_up(self, touch):
        """
            释放移动
        :param touch:
        :return:
        """
        self.is_moving = False


class IButtonHold(Indicator):
    """
        持续按键，按键按下则屏幕按下，按键释放则屏幕释放
    """

    TPT = TouchPointType.BtnHold
    IStyle = IndicatorStyle('持续', MYColor.green, 'target')

    def on_key_down(self, *args, **kwargs):
        """
            按下持续
        :param args:
        :param kwargs:
        :return:
        """
        self.proxy_reactor.ca.f_touch_spr(Action.DOWN, self.spr, self.tid)
        self.is_pressed = True

    def on_key_up(self, *args, **kwargs):
        """
            按下释放
        :param args:
        :param kwargs:
        :return:
        """
        self.proxy_reactor.ca.f_touch_spr(Action.RELEASE, self.spr, self.tid)
        self.is_pressed = False


class IButtonInstantly(Indicator):
    """
        立即按键，按键按下时立即出发，不等待释放
    """

    TPT = TouchPointType.BtnInstantly
    IStyle = IndicatorStyle('立即', MYColor.orange, 'lightning-bolt')

    def __init__(self, **kwargs):
        self.i__hold_ms = kwargs.pop('i__hold_ms', 50)
        super().__init__(**kwargs)

    def setup_details(self, container: MDDialogContentContainer):
        """
            输入持续时间
        :param container:
        :return:
        """
        content = MDGridLayout(cols=2, adaptive_height=True, spacing=sp(10))
        content.add_widget(MDLabel(text='按键按下持续时间', size_hint=(None, 1), width=sp(120)))

        tf_hold_ms = MDTextField(MDTextFieldHintText(text='毫秒'), text=str(self.i__hold_ms), mode='filled')
        tf_hold_ms.bind(text=partial(self.get_validate, self, 'i__hold_ms', int))
        content.add_widget(tf_hold_ms)

        container.add_widget(content)

    def on_key_down(self, *args, **kwargs):
        """
            立刻按下，若已经按下 则跳过
        :param args:
        :param kwargs:
        :return:
        """
        if self.is_pressed:
            return
        else:
            self.is_pressed = True

        self.proxy_reactor.ca.f_touch_spr(Action.DOWN, self.spr, self.tid)

        def _release(*_args):
            """
                释放按键
            :return:
            """
            self.proxy_reactor.ca.f_touch_spr(Action.RELEASE, self.spr, self.tid)
            self.is_pressed = False

        Clock.schedule_once(_release, self.i__hold_ms / 1000)


class IButtonRepeat(Indicator):
    """
        重复按键，按下后以一定间隔重复按键
    """
    TPT = TouchPointType.BtnRepeat
    IStyle = IndicatorStyle('重复', MYColor.red, 'timer-marker')

    def __init__(self, **kwargs):

        self.i__hold_ms = kwargs.pop('i__hold_ms', 50)
        self.i__repeat_ms = kwargs.pop('i__repeat_ms', 500)

        super().__init__(**kwargs)

        self.run_interval: ClockEvent

    def setup_details(self, container: MDDialogContentContainer):
        """
            绘制参数项
        :param container:
        :return:
        """
        content = MDGridLayout(cols=2, adaptive_height=True, spacing=sp(10))

        tf_hold_ms = MDTextField(MDTextFieldHintText(text='毫秒'), text=str(self.i__hold_ms), mode='filled')
        tf_hold_ms.bind(text=partial(self.get_validate, self, 'i__hold_ms', int))

        content.add_widget(MDLabel(text='按下持续时间', size_hint=(None, 1), width=sp(120)))
        content.add_widget(tf_hold_ms)

        tf_repeat_ms = MDTextField(MDTextFieldHintText(text='毫秒'), text=str(self.i__repeat_ms), mode='filled')
        tf_repeat_ms.bind(text=partial(self.get_validate, self, 'i__repeat_ms', int))

        content.add_widget(MDLabel(text='重复间隔', size_hint=(None, 1), width=sp(120)))
        content.add_widget(tf_repeat_ms)

        container.add_widget(content)

    def on_key_down(self, *args, **kwargs):
        """
            按键按下后，以repeat_ms为间隔重复按下
        :param args:
        :param kwargs:
        :return:
        """
        def _release(*_args):
            self.proxy_reactor.ca.f_touch_spr(Action.RELEASE, self.spr, self.tid)

        def _down(*_args):
            self.proxy_reactor.ca.f_touch_spr(Action.DOWN, self.spr, self.tid)
            Clock.schedule_once(_release, self.i__hold_ms / 1000)

        _down()
        self.run_interval = Clock.schedule_interval(_down, (self.i__repeat_ms + self.i__hold_ms + 5) / 1000)

    def on_key_up(self, *args, **kwargs):
        """
            释放定时器
        :param args:
        :param kwargs:
        :return:
        """
        self.run_interval.cancel()


class IButtonSwitch(Indicator):
    """
        开关按钮 按下后切换按下状态
    """
    TPT = TouchPointType.BtnSwitch
    IStyle = IndicatorStyle('切换', MYColor.blue, 'toggle-switch')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.status: bool = False

    def on_key_down(self, *args, **kwargs):
        """
            开关按钮，按下后切换开关状态
        :param args:
        :param kwargs:
        :return:
        """
        self.proxy_reactor.ca.f_touch_spr(Action.RELEASE if self.status else Action.DOWN, self.spr, self.tid)
        self.status = not self.status


class IButtonAim(Indicator):
    """
        瞄准按钮
    """
    TPT = TouchPointType.BtnAim
    IStyle = IndicatorStyle('瞄准', MYColor.yellow, 'target-account')

    MOUSE_BUTTON_MAP = {
        Button.left: UnifiedKeys.UK_MOUSE_L,
        Button.right: UnifiedKeys.UK_MOUSE_R,
        Button.middle: UnifiedKeys.UK_MOUSE_WHEEL
    }

    def __init__(self, **kwargs):

        self.i__scale_x = kwargs.pop('i__scale_x', 0.2)
        self.i__scale_y = kwargs.pop('i__scale_y', 0.2)
        self.i__uhid = kwargs.pop('i__uhid', False)

        super().__init__(**kwargs)

        self.mouse_controller = MouseController()
        self.mouse_listener: MouseListener
        self.is_mouse_listener_running: bool
        self.base_pos: tuple[int, int]
        self.aim_spr: ScalePointR
        self.last_move: float
        self.is_disabled: bool = False
        self.last_point: tuple[int, int]

    def setup_details(self, container: MDDialogContentContainer):
        """
            具体配置窗口
        :param container:
        :return:
        """
        content = MDGridLayout(cols=4, adaptive_height=True, spacing=sp(10))

        tf_scale_x = MDTextField(text=str(self.i__scale_x), mode='filled')
        tf_scale_x.bind(text=partial(self.get_validate, self, 'i__scale_x', float))

        content.add_widget(MDLabel(text='X轴灵敏度', size_hint=(None, 1), width=sp(100)))
        content.add_widget(tf_scale_x)

        tf_scale_y = MDTextField(text=str(self.i__scale_y), mode='filled')
        tf_scale_y.bind(text=partial(self.get_validate, self, 'i__scale_y', float))

        content.add_widget(MDLabel(text='Y轴灵敏度', size_hint=(None, 1), width=sp(100)))
        content.add_widget(tf_scale_y)

        content.add_widget(MDLabel(text='Shift激活UHID', size_hint=(None, 1), width=sp(150)))
        sw_uhid = MDSwitch()
        sw_uhid.active = self.i__uhid
        sw_uhid.bind(active=lambda instance, is_activate: setattr(self, 'i__uhid', is_activate))
        content.add_widget(sw_uhid)

        container.add_widget(content)

    def deactivate(self):
        """
            退出控制状态
        :return:
        """

        self.mouse_listener.stop()

        Window.show_cursor = True
        Window.ungrab_mouse()

        self.proxy_reactor.ca.f_touch_spr(Action.RELEASE, self.aim_spr, self.tid)

        self.proxy_reactor.mouse_handler.cfg.running = self.is_mouse_listener_running

        self.is_pressed = False
        self.proxy_reactor.indicator_aim = None

    def activate(self):
        """
            激活
        :return:
        """
        self.is_pressed = True
        self.proxy_reactor.indicator_aim = self

        # 关闭鼠标控制器
        self.is_mouse_listener_running = self.proxy_reactor.mouse_handler.cfg.running
        if self.is_mouse_listener_running:
            self.proxy_reactor.mouse_handler.cfg.running = False

        Window.grab_mouse()

        self.p_l = Window.left
        self.p_r = Window.left + Window.width / Metrics.density
        self.p_t = Window.top
        self.p_b = Window.top + Window.height / Metrics.density

        self.p_w = Window.width / Metrics.density
        self.p_h = Window.height / Metrics.density

        self.p_move_x = self.p_w / self.i__scale_x
        self.p_move_y = self.p_h / self.i__scale_y

        self.base_pos = (int((self.p_l + self.p_r) / 2), int((self.p_t + self.p_b) / 2))

        # 鼠标定位
        self.mouse_controller.position = self.base_pos

        self.last_point = self.base_pos
        self.aim_spr = ScalePointR(self.i__x, self.i__y, self.i__r)

        self.last_move = time.time()

        self.proxy_reactor.ca.f_touch_spr(Action.DOWN, self.spr, self.tid)

        # 不同平台 pynput 效果不同
        if platform == 'macosx':
            self.mouse_listener = MouseListener(on_click=self.click, on_move=self.move_maxosx, suppress=True)
        elif platform == 'win':
            self.mouse_listener = MouseListener(on_click=self.click, on_move=self.move_win, suppress=True)
        elif platform == 'linux':
            self.mouse_listener = MouseListener(on_click=self.click, on_move=self.move_linux, suppress=True)

        self.mouse_listener.start()

        Window.show_cursor = False

    def on_key_down(self, *args, **kwargs):
        """
            切换控制状态
        :param args:
        :param kwargs:
        :return:
        """
        if not self.is_pressed:
            self.activate()
        else:
            # 退出瞄准状态
            self.deactivate()

    def move_win(self, x: int, y: int, injected: bool):
        """
            Windows平台下 mouse自动归位
        :param x:
        :param y:
        :param injected:
        :return:
        """

        x = int(x)
        y = int(y)

        _pos = self.mouse_controller.position

        move_dx, move_dy = x - _pos[0], y - _pos[1]

        # 避免无效操作
        if (move_dx == 0 and move_dy == 0) or abs(move_dx) > 127 or abs(move_dy) > 127:
            if time.time() - self.last_move > 1.5:
                self.reset()
            return

        if self.i__uhid and 'shift' in Window.modifiers:
            # UHID
            self.proxy_reactor.mouse_handler.uhid_mouse_handler.move(self, [], dx=move_dx, dy=move_dy)

        else:
            # Aim
            self.aim_spr = self.aim_spr + ScalePointR(move_dx / self.p_move_x, move_dy / self.p_move_y, self.i__r)
            self.proxy_reactor.ca.f_touch_spr(Action.MOVE, self.aim_spr, self.tid)

            # 触摸范围过大时归零
            if abs(self.aim_spr.x - self.i__x) > 0.15 or abs(self.aim_spr.y - self.i__y) > 0.1:
                self.reset()
            elif time.time() - self.last_move > 1.5:
                self.reset()

    def move_linux(self, x: int, y: int, injected: bool):
        """
            Linux X11 移动
        :param x:
        :param y:
        :param injected:
        :return:
        """
        x = int(x)
        y = int(y)

        # 有效范围内
        if (self.p_l + sp(10) < x < self.p_r - sp(10)) and self.p_t + sp(10) < y < self.p_b - sp(10):
            move_dx = x - self.last_point[0]
            move_dy = y - self.last_point[1]
            self.last_point = (x, y)

            # 避免无效操作
            if (move_dx == 0 and move_dy == 0) or abs(move_dx) > 127 or abs(move_dy) > 127:
                if time.time() - self.last_move > 1.5:
                    self.reset()
                return

            if self.i__uhid and 'shift' in Window.modifiers:
                # UHID
                self.proxy_reactor.mouse_handler.uhid_mouse_handler.move(self, [], dx=move_dx, dy=move_dy)
            else:
                # Aim
                self.aim_spr = self.aim_spr + ScalePointR(move_dx / self.p_move_x, move_dy / self.p_move_y, self.i__r)
                self.proxy_reactor.ca.f_touch_spr(Action.MOVE, self.aim_spr, self.tid)

                # 触摸范围过大时归零
                if abs(self.aim_spr.x - self.i__x) > 0.15 or abs(self.aim_spr.y - self.i__y) > 0.1:
                    self.reset()
                elif time.time() - self.last_move > 1.5:
                    self.reset()

        else:
            # 重置鼠标位置
            self.mouse_controller.position = self.base_pos
            self.last_point = self.base_pos

    def move_maxosx(self, x: int, y: int, injected: bool):
        """
            MacOS X 下，injected回传有效
        :param x:
        :param y:
        :param injected:
        :return:
        """
        if injected:
            # 注入 则跳过处理
            if self.mouse_controller.position != self.base_pos:
                self.mouse_controller.position = self.base_pos
                self.last_point = self.base_pos
                self.reset()
            return

        x = int(x)
        y = int(y)

        # 有效范围内
        if (self.p_l + sp(10) < x < self.p_r - sp(10)) and self.p_t + sp(10) < y < self.p_b - sp(10):
            move_dx = x - self.last_point[0]
            move_dy = y - self.last_point[1]
            self.last_point = (x, y)

            # 避免无效操作
            if (move_dx == 0 and move_dy == 0) or abs(move_dx) > 127 or abs(move_dy) > 127:
                if time.time() - self.last_move > 1.5:
                    self.reset()
                return

            if self.i__uhid and 'shift' in Window.modifiers:
                # UHID
                self.proxy_reactor.mouse_handler.uhid_mouse_handler.move(self, [], dx=move_dx, dy=move_dy)
            else:
                # Aim
                self.aim_spr = self.aim_spr + ScalePointR(move_dx / self.p_move_x, move_dy / self.p_move_y, self.i__r)
                self.proxy_reactor.ca.f_touch_spr(Action.MOVE, self.aim_spr, self.tid)

                # 触摸范围过大时归零
                if abs(self.aim_spr.x - self.i__x) > 0.15 or abs(self.aim_spr.y - self.i__y) > 0.1:
                    self.reset()
                elif time.time() - self.last_move > 1.5:
                    self.reset()

        else:
            # 重置鼠标位置
            dx, dy = x - self.base_pos[0], y - self.base_pos[1]
            move_x = 0 if dx == 0 else int(self.p_w / 2 * dx / abs(dx))
            move_y = 0 if dy == 0 else int(self.p_h / 2 * dy / abs(dy))
            self.mouse_controller.move(move_x, move_y)

    def reset(self):
        """
            重置准星触摸位置
        :return:
        """
        self.proxy_reactor.ca.f_touch_spr(Action.RELEASE, self.aim_spr, self.tid)
        time.sleep(2 / 60)
        self.proxy_reactor.ca.f_touch_spr(Action.DOWN, self.spr, self.tid)
        time.sleep(1 / 60)
        self.aim_spr = ScalePointR(self.i__x, self.i__y, self.i__r)
        self.last_move = time.time()


    @dataclass
    class ITouch:
        button: str

        @classmethod
        def create(cls, button) -> Self:
            return cls(
                button={
                    Button.left: 'left', Button.right: 'right', Button.middle: 'middle'
                }.get(button)
            )

    def click(self, x, y, button, pressed):
        """
            点击事件，触发鼠标事件
        :param x:
        :param y:
        :param button:
        :param pressed:
        :return:
        """

        if self.i__uhid and 'shift' in Window.modifiers:
            is_activated = self.proxy_reactor.mouse_handler.uhid_mouse_handler.activated
            self.proxy_reactor.mouse_handler.uhid_mouse_handler.activated = True

            if pressed:
                self.proxy_reactor.mouse_handler.uhid_mouse_handler.touch_down(self.ITouch.create(button))
            else:
                self.proxy_reactor.mouse_handler.uhid_mouse_handler.touch_up(self.ITouch.create(button))

            self.proxy_reactor.mouse_handler.uhid_mouse_handler.activated = is_activated
            Window.show_cursor = False
            return

        uk = self.MOUSE_BUTTON_MAP.get(button, None)
        if uk and uk in self.proxy_reactor.reg_idt:
            if pressed:
                Clock.schedule_once(self.proxy_reactor.reg_idt[uk].on_key_down, 0)
            else:
                Clock.schedule_once(self.proxy_reactor.reg_idt[uk].on_key_up, 0)

        Window.show_cursor = False


class IButtonWatch(Indicator):
    """
        观察按钮
    """
    TPT = TouchPointType.BtnWatch
    IStyle = IndicatorStyle('观察', MYColor.yellow, 'eye-circle')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.mouse_controller = MouseController()
        self.is_mouse_listener_running: bool
        self.base_pos = self.mouse_controller.position
        self.is_aimed = None

    def on_key_down(self, *args, **kwargs):
        """
            进入观察模式
        :param args:
        :param kwargs:
        :return:
        """

        self.is_mouse_listener_running = self.proxy_reactor.mouse_handler.cfg.running

        if self.is_mouse_listener_running:
            self.proxy_reactor.mouse_handler.cfg.running = False

        if self.proxy_reactor.indicator_aim:
            self.is_aimed = self.proxy_reactor.indicator_aim
            self.proxy_reactor.indicator_aim.deactivate()
        else:
            self.is_aimed = None
            Window.grab_mouse()

        self.mouse_controller.position = (
            Window.left + Window.width / Metrics.density // 2,
            Window.top + Window.height / Metrics.density // 2
        )

        self.base_pos = self.mouse_controller.position

        self.proxy_reactor.ca.f_touch_spr(Action.DOWN, self.spr, self.tid)
        Window.show_cursor = False
        time.sleep(2 / 60)
        Window.bind(mouse_pos=self.move)

    def on_key_up(self, *args, **kwargs):
        """
            释放
        :param args:
        :param kwargs:
        :return:
        """

        Window.unbind(mouse_pos=self.move)
        self.proxy_reactor.ca.f_touch_spr(Action.RELEASE, self.spr, self.tid)
        Window.show_cursor = True

        if self.is_mouse_listener_running:
            self.proxy_reactor.mouse_handler.cfg.running = True

        if self.is_aimed:
            self.is_aimed.activate()
        else:
            Window.ungrab_mouse()

    def move(self, window_instance, win_pos):
        """
            移动观察触点
        :param window_instance:
        :param win_pos:
        :return:
        """

        cx, cy = self.mouse_controller.position
        dx, dy = cx - self.base_pos[0], cy - self.base_pos[1]
        _spr = self.spr + ScalePointR(
            dx / (Window.width / Metrics.density),
            dy / (Window.height / Metrics.density),
            self.i__r
        ) * 0.8
        self.proxy_reactor.ca.f_touch_spr(Action.MOVE, _spr, self.tid)
        Window.show_cursor = False


class IButtonCross(Indicator):
    """
        十字键
    """
    TPT = TouchPointType.Cross
    IStyle = IndicatorStyle('方向', MYColor.grey, 'gamepad')

    def __init__(self, **kwargs):

        self.i__code_up = kwargs.pop('i__code_up', -1)
        self.i__code_down = kwargs.pop('i__code_down', -1)
        self.i__code_left = kwargs.pop('i__code_left', -1)
        self.i__code_right = kwargs.pop('i__code_right', -1)

        self.i__cr = kwargs.pop('i__cr', .2)
        self.i__cw = kwargs.pop('i__cw', 0.0)
        self.i__cw_wait = kwargs.pop('i__cw_wait', 1.5)

        super().__init__(**kwargs)

        self.u = UnifiedKeys.get_by_code(self.i__code_up)
        self.d = UnifiedKeys.get_by_code(self.i__code_down)
        self.l = UnifiedKeys.get_by_code(self.i__code_left)
        self.r = UnifiedKeys.get_by_code(self.i__code_right)
        self.c_spr: ScalePointR

        with self.canvas.before:
            Color(.2, 1, 0, 0.8)
            self.d_round = Line(width=sp(2))
            Color(1, .45, .38, 0.8)
            self.d_w = Line(width=sp(2))

        self.expand = MDSlider(
            MDSliderHandle(),
            value=self.i__cr, min=0, max=0.4, width=sp(180), size_hint_x=None
        )
        self.add_widget(self.expand)

        self.expand.bind(value=self.update_round)
        self.expand_flag: bool = True

        self.update_badge()

    def register(self):
        """
            注册4个按键
        :return:
        """
        for _ in ['up', 'down', 'left', 'right']:
            if getattr(self, f"i__code_{_}", -1) != UnifiedKeys.UK_UNKNOWN.code:
                self.idm.registered_indicators[UnifiedKeys.get_by_code(getattr(self, f"i__code_{_}"))] = self

    def update_pos(self, *args):
        """
            更新位置，需要同步更新外部圆及调整器
        :param args:
        :return:
        """
        super().update_pos()
        self.d_round.circle = (*self.center, self.i__cr * self.idm.height)
        self.indicator_icon.center = self.center
        self.expand.center = (self.center_x, self.center_y - sp(60))
        self.d_w.points = (
            *self.center,
            self.center_x, (self.i__cw + self.i__cr) * self.idm.height + self.center_y
        )

    def update_round(self, instance, value):
        """
            更新范围
        :param instance:
        :param value:
        :return:
        """
        if self.expand_flag:
            self.i__cr = value
        else:
            self.i__cw = value

        self.d_round.circle = (*self.center, self.i__cr * self.idm.height)
        self.d_w.points = (
            *self.center,
            self.center_x, (self.i__cw + self.i__cr) * self.idm.height + self.center_y
        )

    def pop_uk(self):
        """
            删除按键
        :return:
        """
        for code in [
            self.i__code_up, self.i__code_down, self.i__code_left, self.i__code_right
        ]:
            uk = UnifiedKeys.get_by_code(code)
            if uk in self.idm.registered_indicators:
                self.idm.registered_indicators.pop(uk, None)

    def on_touch_down(self, touch):
        if self.expand.collide_point(*touch.pos):
            self.expand.on_touch_down(touch)
            return True
        else:
            return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.expand.collide_point(*touch.pos):
            self.expand.on_touch_move(touch)
            return True
        else:
            return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.expand.collide_point(*touch.pos):
            self.expand.on_touch_up(touch)
            return True
        else:
            return super().on_touch_up(touch)

    def create__dropdown_menu(self) -> MDDropdownMenu:
        """
            增加切换滑动调整目标功能
        :return:
        """
        mdm = super().create__dropdown_menu()

        items = mdm.items
        mdm.items = items + [
            dict(text='切换滑动调整目标', leading_icon='sync',
                 on_release=lambda *args: mdm.dismiss() or self.switch_expand())
        ]
        return mdm

    def switch_expand(self):
        """
            切换调整目标
        :return:
        """
        self.expand_flag = not self.expand_flag
        self.expand.value = self.i__cr if self.expand_flag else self.i__cw

    def update_badge(self):
        """
            更新显示文本
        :return:
        """
        text = ''
        set_i = 0
        for name in ['up', 'down', 'left', 'right']:
            _uk = UnifiedKeys.get_by_code(getattr(self, f"i__code_{name}"))
            if _uk != UnifiedKeys.UK_UNKNOWN:

                if set_i == 2:
                    text += '\n'
                    set_i = -1
                else:
                    set_i += 1

                text += f' {name.upper()}:{_uk.value if _uk.value else _uk.code} '

        self.indicator_badge.text = text

    def create__setup_dialog(self):
        """
            配置面板
        :return:
        """
        sd = SettingDialog(self.IStyle.name)
        content = MDGridLayout(cols=4, adaptive_height=True, spacing=sp(15))
        sd.container.add_widget(content)

        def register_key(key_name: str, uk: UnifiedKey) -> bool:
            """
                注册按键
            :param key_name:
            :param uk:
            :return:
            """
            if uk is None:
                create_snack(f"获取按键错误，请重试！", color=MYCombineColors.red, duration=1).open()
                return False

            if uk in self.idm.registered_indicators:
                create_snack(f"按键 {uk.value} 重复！", color=MYCombineColors.red, duration=1).open()
                return False

            else:
                now_uk = UnifiedKeys.get_by_code(getattr(self, key_name))
                if now_uk in self.idm.registered_indicators:
                    self.idm.registered_indicators.pop(now_uk)
                setattr(self, key_name, uk.code)
                self.idm.registered_indicators[uk] = self
                self.update_badge()
                return True

        for _ in ['up', 'down', 'left', 'right']:
            content.add_widget(MDLabel(text=_.upper(), size_hint=(None, 1), width=sp(60)))
            content.add_widget(SetUKButton(
                UnifiedKeys.get_by_code(getattr(self, f"i__code_{_}")),
                partial(register_key, f"i__code_{_}"))
            )

        time_content = MDGridLayout(cols=2, adaptive_height=True, spacing=sp(15))
        sd.container.add_widget(time_content)

        time_content.add_widget(MDLabel(text='激活等待时间', size_hint=(None, 1), width=sp(100)))
        tf = MDTextField(MDTextFieldHintText(text='秒数'), text=str(self.i__cw_wait), mode='filled')

        tf.bind(text=partial(self.get_validate, self, 'i__cw_wait', float))
        time_content.add_widget(tf)

        sd.open()

    @property
    def udlr(self) -> list[UnifiedKey]:
        """
            十字键按键列表
        :return:
        """
        return [self.u, self.d, self.l, self.r]

    @property
    @cache
    def h2w(self) -> float:
        """
            计算长宽比例
        :return:
        """
        vs = self.proxy_reactor.mouse_handler.video_screen
        return vs.height / vs.width

    def on_key_down(self, *args, **kwargs):
        """
            按键按下事件，如未按下，现按下十字键中心
        :param args:
        :param kwargs:
        :return:
        """
        if not self.is_pressed:
            self.proxy_reactor.ca.f_touch_spr(Action.DOWN, self.spr, self.tid)
            # 等待下按生效
            time.sleep(2 / 60)
            self.c_spr = ScalePointR(self.i__x, self.i__y, self.i__r)
            self.is_pressed = True

        self.move()

    @property
    def pressed_keys(self) -> list[UnifiedKey]:
        """
            当前按下键
        :return:
        """
        return [_ for _ in self.udlr if _ in self.proxy_reactor.pressed]

    def up_action(self, *args):
        """
            等待时间后向上移动
        :param args:
        :return:
        """
        _pressed = self.pressed_keys
        if self.u in _pressed and len(_pressed) == 1:
            self.c_spr = ScalePointR(self.i__x, self.i__y - self.i__cw - self.i__cr, self.i__r)
            self.proxy_reactor.ca.f_touch_spr(Action.MOVE, self.c_spr, self.tid)

    def move(self):
        """
            移动功能，判断按键计算摇杆位置
        :return:
        """
        pressed_keys = self.pressed_keys

        if len(pressed_keys) == 0:
            self.proxy_reactor.ca.f_touch_spr(
                Action.RELEASE, self.c_spr, self.tid
            )
            self.is_pressed = False
            return

        x, y = 0.0, 0.0

        if self.u in pressed_keys:
            y -= self.i__cr
            Clock.schedule_once(self.up_action, self.i__cw_wait)

        if self.d in pressed_keys:
            y += self.i__cr

        if self.l in pressed_keys:
            x -= self.i__cr * self.h2w

        if self.r in pressed_keys:
            x += self.i__cr * self.h2w

        self.c_spr = ScalePointR(self.i__x + x, self.i__y + y, self.i__r)
        self.proxy_reactor.ca.f_touch_spr(Action.MOVE, self.c_spr, self.tid)

    def on_key_up(self, *args, **kwargs):
        """
            按键释放事件
        :param args:
        :param kwargs:
        :return:
        """
        self.move()


class IndicatorManager(MDRelativeLayout):

    IndicatorButtonCls = [
        IButtonInstantly,
        IButtonRepeat,
        IButtonHold,
        IButtonSwitch,
        IButtonAim, IButtonWatch,
        IButtonCross
    ]

    cfg_storage = JsonStore(Param.PATH_CONFIGS.joinpath('ky_indicators.json'))

    def __init__(self, connect_session, **kwargs):
        """
            指示器管理器
        :param kwargs:
        """
        super(IndicatorManager, self).__init__(**kwargs)
        self.cfg_name = None
        self.registered_indicators = {}
        self.cs = connect_session
        self.screen: MDScreen = MDScreen(name=f"__indicator_manager_{uuid.uuid4()}")
        self.screen.add_widget(self)

        with self.screen.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = Rectangle()

    def update_pos(self, *args):
        """
            更新位置信息
        :param args:
        :return:
        """
        try:
            self.size = self.screen.size
            self.rect.size = self.screen.manager.size
            self.pos = self.screen.manager.pos
        except Exception as e:
            ...

    def on_touch_down(self, *args):
        """
            新增功能
        :return:
        """
        if len(args) > 1:
            touch = args[1]
        else:
            touch = args[0]

        if touch.button == 'right' or touch.is_double_tap:
            is_in = super(IndicatorManager, self).on_touch_down(touch)
            if not is_in:
                self.create__menu(touch.pos)
            return True
        else:
            return super(IndicatorManager, self).on_touch_down(touch)

    def get_spr(self, pos) -> ScalePointR:
        """
            获取点的spr
        :param pos:
        :return:
        """
        return ScalePointR(
            (pos[0] - self.x) / self.width,
            1 - (pos[1] - self.y) / self.height,
            self.cs.rotation
        )

    def create__menu(self, pos):
        """
            创建菜单栏
        :param pos:
        :return:
        """
        spr = self.get_spr(self.to_window(*pos))

        menu_items = []
        if self.cfg_name is not None:
            menu_items += [
                dict(
                    text=f"保存 <{self.cfg_name}>", leading_icon='content-save-outline',
                    on_release=lambda *args: mdm.dismiss() or self.save_cfg() or create_snack(
                        '配置文件已保存', color=MYCombineColors.green, duration=1
                    ).open()
                ),
            ]

            for btn_cls in self.IndicatorButtonCls:
                menu_items += [
                    dict(text=btn_cls.IStyle.name, leading_icon=btn_cls.IStyle.icon,
                         on_release=lambda *args, bc=btn_cls: mdm.dismiss() or bc(
                             indicator_manager=self, i__x=spr.x, i__y=spr.y, i__r=spr.r
                         ))
                ]

        menu_items += [
            dict(text='创建配置文件', leading_icon='file-cog-outline',
                 on_release=lambda *args: mdm.dismiss() or self.create_cfg()),
            dict(text='加载配置文件', leading_icon='file-cog-outline',
                 on_release=lambda *args: mdm.dismiss() or self.list_cfgs())
        ]

        if self.cfg_name:
            menu_items.append(dict(
                text='删除当前配置', leading_icon='delete', on_release=lambda *args: mdm.dismiss() or self.delete_cfg()),
            )
            menu_items.append(dict(
                text='启动映射', leading_icon='play', on_release=lambda *args: mdm.dismiss() or self.cs.start_proxy(
                    self.cfg_name, self.registered_indicators
                )
            ))

        menu_items.append(dict(
            text='关闭', leading_icon='close', on_release=lambda *args: mdm.dismiss() or self.close())
        )

        caller = MDWidget(pos=Window.mouse_pos, size_hint=(None, None), size=(1, 1))
        mdm = MDDropdownMenu(caller=caller, items=menu_items)
        mdm.open()
        del caller

    def close(self, *args):
        """
            关闭按键映射器
        :param args:
        :return:
        """
        self.cleanup()

        self.cs.manager.current = self.cs.screen.name
        self.cs.manager.remove_widget(self.screen)

        # 恢复侧边栏及底部栏功能
        self.cs.manager.gui.side_panel.disabled = False
        self.cs.manager.gui.bottom_bar.disabled = False
        self.cs.manager.btn_mouse.disabled = False
        self.cs.manager.btn_keyboard.disabled = False
        self.cs.manager.update_indicator_status()

        create_snack('退出映射编辑模式', color=MYCombineColors.orange).open()

    def cleanup(self, auto_save: bool = True):
        """
            切换前清除数据及状态
        :return:
        """
        if auto_save and self.cfg_name:
            self.save_cfg()

        self.clear_widgets()
        self.registered_indicators = {}
        self.cfg_name = None

    @property
    def cfg_key(self) -> str:
        """
            配置文件存储Key
        :return:
        """
        package, info = self.cs.my_device.get_current_package_info(has_app_info=False)
        return f"{self.cs.my_device.adb_dev.serial}_{package.package_name}_{self.cfg_name}"

    def create_cfg(self):
        """
            创建配置文件
        :return:
        """
        def _save():
            if ipt.text is None or ipt.text == '':
                ipt.error = True
            else:
                mdd.dismiss()
                self.cleanup()
                self.cfg_name = ipt.text

        ipt = MDTextField(mode='filled')

        container = MDDialogContentContainer(MDLabel(text='配置名'), ipt, orientation='vertical', spacing=sp(10))

        mdd = MDDialog(
            MDDialogHeadlineText(text='创建配置文件'),
            container,
            MDDialogButtonContainer(
                MDWidget(),
                MDButton(
                    MDButtonText(text='关闭'), style='text',
                    on_release=lambda *args: mdd.dismiss()
                ),
                MDButton(
                    MDButtonText(text='创建'), style='text',
                    on_release=lambda *args: mdd.dismiss() or _save()
                )
            )
        )
        mdd.open()

    def delete_cfg(self):
        """
            删除配置文件
        :return:
        """
        if self.cfg_name:
            self.cfg_storage.delete(self.cfg_key)
            create_snack(f"{self.cfg_name} 配置文件已删除", color=MYCombineColors.red, duration=2).open()

        self.cleanup(auto_save=False)

    def list_cfgs(self, callback: Callable = None):
        """
            列出当前存在配置文件
        :return:
        """
        items = []

        filter_key = self.cfg_key.replace(f'{self.cfg_name}', '')

        for key in self.cfg_storage.keys():
            if key.startswith(filter_key):
                cfg_name = key.split('_')[-1]
                items.append(dict(
                    text=cfg_name, leading_icon='file-cog-outline',
                    on_release=lambda *args, cn=cfg_name: mdm.dismiss() or (
                        self.load_cfg(cn) if callback is None else callback(cn))
                ))

        if len(items) == 0:
            create_snack(f"无配置文件，请先创建！", color=MYCombineColors.orange, duration=2).open()
            return

        caller = MDWidget(pos=Window.mouse_pos, size_hint=(None, None), size=(1, 1))
        mdm = MDDropdownMenu(caller=caller, items=items)
        mdm.open()
        del caller

    def load_cfg(self, cfg_name: str, *args):
        """
            加载配置文件
        :param cfg_name:
        :param args:
        :return:
        """
        if self.cfg_name is None:
            self.cfg_name = cfg_name

        _cfg_key = self.cfg_key

        if not self.cfg_storage.exists(_cfg_key.replace(self.cfg_name, cfg_name)):
            create_snack(f"{cfg_name} 不存在!", color=MYCombineColors.red).open()

        self.cleanup(auto_save=False)
        self.cfg_name = cfg_name

        try:
            indicators = self.cfg_storage.get(_cfg_key.replace(self.cfg_name, cfg_name))['indicators']
            for indicator_obj_dict in indicators:
                for ibc in self.IndicatorButtonCls:
                    if indicator_obj_dict['i__tpt'] == ibc.TPT:
                        ibc(obj_dict=indicator_obj_dict, indicator_manager=self)
                        continue

        except Exception as e:
            create_snack(f'{cfg_name} 配置文件错误！\n{e}', color=MYCombineColors.red, duration=4).open()

    def save_cfg(self, *args):
        """
            保存配置文件
        :param args:
        :return:
        """

        if self.cfg_name is None:
            return

        cfg_list = []

        cross = []

        for uk, indicator in self.registered_indicators.items():

            if indicator.TPT == TouchPointType.Cross:
                if uk.code in cross:
                    continue
                else:
                    cross.append(indicator.i__code_up)
                    cross.append(indicator.i__code_down)
                    cross.append(indicator.i__code_left)
                    cross.append(indicator.i__code_right)

            cfg_list.append(indicator.dump())

        self.cfg_storage.put(self.cfg_key, indicators=cfg_list)


class ProxyReactor(MDWidget):

    def __init__(self,
                 cfg_name: str,
                 registered_indicators: dict[UnifiedKey, Indicator],
                 ca: ControlAdapter,
                 mouse_handler: MouseHandler,
                 **kwargs):
        """
            按键映射处理器
        :param cfg_name:
        :param registered_indicators:
        :param ca:
        :param mouse_handler:
        :param kwargs:
        """
        super().__init__(**kwargs)

        self.cfg_name = cfg_name

        self.pressed = []
        self.touch_points = {}

        self.ca = ca
        self.mouse_handler: MouseHandler = mouse_handler
        self.kb = None

        self.reg_idt = registered_indicators

        # indicator注入pr
        for uk, indicator in self.reg_idt.items():
            indicator.tid = self.get_random_touch_id(record=indicator)
            setattr(indicator, 'proxy_reactor', self)

        self.mouse_button_map = {
            Button.left: UnifiedKeys.UK_MOUSE_L,
            Button.right: UnifiedKeys.UK_MOUSE_R,
            Button.middle: UnifiedKeys.UK_MOUSE_WHEEL
        }

        self.indicator_aim : IButtonAim | None = None

    def activate(self):
        """
            激活
        :return:
        """
        self.kb = Window.request_keyboard(self.close_keyboard, self)
        self.kb.bind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)

    def deactivate(self):
        """
            失活
        :return:
        """
        self.close_keyboard()
        if self.indicator_aim:
            self.indicator_aim.deactivate()

    def close(self):
        """
            关闭
        :return:
        """
        self.close_keyboard()
        if self.indicator_aim:
            self.indicator_aim.deactivate()
        create_snack(f"退出映射模式", color=MYCombineColors.orange, duration=2).open()

    def close_keyboard(self, *args):
        """
            关闭键盘
        :return:
        """
        self.pressed = []
        self.kb.unbind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)
        self.kb.release()

    def get_random_touch_id(self, record: Any | None = None) -> int:
        """
            获取随机Touch ID
        :return:
        """
        while True:
            _touch_id = random.randrange(0x413 + 300, 0x413 + 500)
            if _touch_id not in self.touch_points:
                if record is not None:
                    self.touch_points[_touch_id] = record
                return _touch_id

    def on_key_down(self, keyboard_instance, key, text, modifiers):
        """
            按下事件
        :param keyboard_instance:
        :param key:
        :param text:
        :param modifiers:
        :return:
        """
        uk = KeyMapper.ky2uk(key[0])
        if uk in self.pressed:
            return

        if uk == UnifiedKeys.UK_KB_ESCAPE:
            # 安全键，退出
            self.close()

        self.pressed.append(uk)

        uk in self.reg_idt and Clock.schedule_once(self.reg_idt[uk].on_key_down, 0)

    def on_key_up(self, keyboard_instance, key, *args):
        """
            释放事件
        :param keyboard_instance:
        :param key:
        :return:
        """
        uk = KeyMapper.ky2uk(key[0])
        if uk in self.pressed:
            self.pressed.remove(uk)

        uk in self.reg_idt and Clock.schedule_once(self.reg_idt[uk].on_key_up, 0)
