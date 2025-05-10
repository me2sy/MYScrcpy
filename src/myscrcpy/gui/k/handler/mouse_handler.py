# -*- coding: utf-8 -*-
"""
    mouse_handler
    ~~~~~~~~~~~~~~~~~~
    
    Log:
        2025-04-24 3.2.0 Me2sY
            1. 创建
            2. 2025-05-09 AdvDevice切换 MYDevice
"""

__author__ = 'Me2sY'
__version__ = '3.2.0'

__all__ = [
    'MouseHandlerMode',
    'MouseHandler', 'MouseHandlerConfig',
    'GesAction'
]

from dataclasses import dataclass, field, asdict
from enum import IntEnum
from functools import wraps, partial
import random
import time
from typing import Callable, Dict, Tuple, List

from kivy.core.window import Window
from kivy.graphics import Line, Color, Rectangle, Ellipse
from kivy.metrics import Metrics, sp
from kivy.uix.modalview import ModalView
from kivy.uix.widget import Widget
from kivy.core.text import Label
from kivy.logger import Logger

import moosegesture
from pynput import mouse

from myscrcpy.core import ControlAdapter
from myscrcpy.utils import ScalePointR, Action
from myscrcpy.gui.k import StoredConfig, create_snack, MYCombineColors
from myscrcpy.gui.k.handler.keyboard_handler import ActionCallback
from myscrcpy.gui.k.handler.device_handler import MYDevice
from myscrcpy.gui.k.components.video_screen import VideoScreen


@dataclass
class GesAction:
    """
        手势动作
    """
    receiver: str
    gestures: str
    action_name: str
    action: Callable


class MouseHandlerMode(IntEnum):
    UHID = 0
    TOUCH = 1


@dataclass
class MouseHandlerConfig(StoredConfig):
    """
        MouseHandler Config
    """
    _STORAGE_KEY = 'mouse_handler'

    mode: MouseHandlerMode = field(default=MouseHandlerMode.TOUCH)
    touch_id_main: int = 0x413
    touch_id_wheel: int = 0x413 + 50
    touch_id_sec: int = 0x413 + 100
    running: bool = True

    # gesture handler
    gh_space: int = 0
    gh_line_width: int = 5

    # UHID Mouse
    um_mouse_id: int = 2
    um_move_speed: float = 1.5


class GesActionPromptModel(ModalView):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.auto_dismiss = False
        self.size_hint = (.3, .3)
        self.pos_hint = {'x_center': .5, 'y_center': .5}

        self.opacity = 0.1


class GestureHandler:

    MAX_SPACE_N = 1

    GA_UNKNOWN = GesAction('mysc', '', '未知指令', lambda *args, **kwargs: ...)

    def __init__(self, cfg: MouseHandlerConfig, draw_widget):
        """
            手势处理器
        :param cfg:
        :param draw_widget:
        """
        self.cfg = cfg
        self.draw_widget = draw_widget

        self.ges_action_proxy: Dict[int, Dict[str, GesAction]] = {
            _: {} for _ in range(self.MAX_SPACE_N)
        }

        # 生成提升文本
        self.label = Label(font_size=sp(30))
        self.label.text = ''
        self.label.refresh()

        # 定义手势切换动作并注册
        ga_switch = GesAction('mysc', 'DR', '鼠标空间', partial(self.switch_space))
        ga_switch_next = GesAction('mysc', 'DR|L', '上一空间',  partial(self.space_step, -1))
        ga_switch_back = GesAction('mysc', 'DR|R', '下一空间',  partial(self.space_step, 1))

        for _ in range(self.MAX_SPACE_N):
            self.register_gesture_action(_, ga_switch)
            self.register_gesture_action(_, ga_switch_next)
            self.register_gesture_action(_, ga_switch_back)

        self.last_start_pos = None

    def switch_space(self, space: int = None):
        """
            切换控制空间
        :param space:
        :return:
        """
        if space is None:
            self.cfg.gh_space = self.cfg.gh_space + (-self.MAX_SPACE_N + 1 if (self.cfg.gh_space + 1 == self.MAX_SPACE_N) else 1)

        elif type(space) is int and 0 <= space < self.MAX_SPACE_N:
            self.cfg.gh_space = space

        self.cfg.save()

    def space_step(self, step: int = 1):
        """
            上下切换 space
        :param step:
        :return:
        """
        self.cfg.gh_space = max(0, min(self.MAX_SPACE_N - 1, self.cfg.gh_space + step))
        self.cfg.save()

    def register_gesture_action(self, space: int, action: GesAction):
        """
            注册手势
        :param space:
        :param action:
        :return:
        """
        if space < 0 or space >= self.MAX_SPACE_N or type(space) is not int:
            raise KeyError(f"Register to  {' / '.join([str(_) for _ in range(1, self.MAX_SPACE_N)])} Space Only!")

        _action = self.ges_action_proxy[space].get(action.gestures)
        if _action and _action.receiver != action.receiver:
            Logger.warning(f"Mouse Gestures {_action.gestures} is registered by {_action.receiver}")
            return

        self.ges_action_proxy[space][action.gestures] = action

    def touch_down(self, touch):
        """
            手势起始
        :param touch:
        :return:
        """
        if touch.button == 'right':
            with self.draw_widget.canvas.after:
                Color(*(random.random(), 1, 1), a=.9, mode='hsv')
                touch.ud['line'] = Line(points=(touch.x, touch.y), width=self.cfg.gh_line_width)
                self.rect = Rectangle(pos=(
                    self.draw_widget.pos[0] + sp(10), self.draw_widget.pos[1] + self.draw_widget.size[1] - sp(38),
                ), texture=self.label.texture
                )

            self.last_start_pos = touch.pos
            self.last_start_spr = touch.ud['spr']

    def touch_move(self, touch):
        """
            手势移动
        :param touch:
        :return:
        """
        if touch.button == 'right' and touch.ud.get('line'):
            touch.ud['line'].points += [touch.x, touch.y]
            ges_actions, ga = self.get_gesture_action(touch.ud['line'].points)
            self.label.text = '>'.join(ges_actions) + ' | ' + ga.action_name
            self.label.refresh()
            self.rect.size = (sp(len(self.label.text) * 17), sp(38))
            self.rect.texture = self.label.texture

    def touch_up(self, touch):
        """
            判断手势并执行功能
        :param touch:
        :return:
        """
        line = touch.ud.get('line')
        if line and touch.button == 'right':
            ges_actions, ga = self.get_gesture_action(line.points)
            self.label.text = ''
            self.label.refresh()
            ga.action()

            self.draw_widget.canvas.after.remove(line)
            self.draw_widget.canvas.after.remove(self.rect)

    def get_gesture_action(self, points) -> Tuple[List[str], GesAction]:
        """
            解析鼠标手势，获取相应方法
            使用 Moosegesture
            https://github.com/asweigart/moosegesture
        :return:
        """
        if len(points) >= 3:
            ges_action = moosegesture.getGesture(
                [[int(points[i]), -int(points[i + 1])] for i in range(0, len(points), 2)]
            )
            return ges_action, self.ges_action_proxy[self.cfg.gh_space].get('|'.join(ges_action), self.GA_UNKNOWN)
        else:
            return ['Draw More'], self.GA_UNKNOWN


class SecondPoint:

    POINT_SIZE = 16

    def __init__(self, touch_id: int, draw_widget, gesture_handler):
        """
            第二个点 用于双指功能
        :param touch_id:
        :param draw_widget:
        :param gesture_handler:
        """
        self.touch_id = touch_id
        self.draw_widget = draw_widget
        self.gesture_handler = gesture_handler

        self.is_active = False
        self.spr: ScalePointR
        self.pos: Tuple[int, int]

    def activate(self):
        """
            激活点
        :return:
        """
        self.deactivate()

        self.is_active = True
        pos = self.gesture_handler.last_start_pos
        spr = self.gesture_handler.last_start_spr

        with self.draw_widget.canvas.after:
            Color(1, 1, 0)
            self.ellipse = Ellipse(
                pos=(pos[0] - self.POINT_SIZE / 2, pos[1] - self.POINT_SIZE / 2),
                size=(self.POINT_SIZE, self.POINT_SIZE)
            )
            self.pos = pos
            self.spr = spr

    def deactivate(self):
        """
            取消激活
        :return:
        """
        self.is_active = False
        self.spr = None
        self.pos = None
        try:
            self.draw_widget.canvas.after.remove(self.ellipse)
        except:
            ...


class TouchHandler:

    def __init__(
            self,
            cfg: MouseHandlerConfig,
            control_adapter: ControlAdapter,
            control_widget,
            right_point: SecondPoint,
        ):
        """
            触摸控制器
        :param cfg:
        :param control_adapter:
        :param control_widget:
        """
        self.cfg = cfg
        self.ca = control_adapter
        self.cw = control_widget
        self.right_point = right_point

    def touch_down(self, touch):
        """
            按下事件
        :param touch:
        :return:
        """
        if touch.button == 'left':
            # 第二个点
            if self.right_point.is_active:
                self.ca.f_touch_spr(
                    Action.DOWN.value,
                    self.right_point.spr,
                    self.right_point.touch_id
                )

            self.ca.f_touch_spr(
                Action.DOWN.value,
                touch.ud['spr'],
                touch_id=self.cfg.touch_id_main
            )

    def touch_move(self, touch):
        """
            移动事件
        :param touch:
        :return:
        """
        if touch.button == 'left':
            self.ca.f_touch_spr(
                Action.MOVE.value,
                touch.ud['spr'],
                touch_id=self.cfg.touch_id_main
            )

    def touch_up(self, touch):
        """
            释放事件
        :param touch:
        :return:
        """
        if touch.button == 'left':
            if self.right_point.is_active:
                self.ca.f_touch_spr(
                    Action.RELEASE.value,
                    self.right_point.spr,
                    self.right_point.touch_id
                )

            self.ca.f_touch_spr(
                Action.RELEASE.value,
                touch.ud['spr'],
                touch_id=self.cfg.touch_id_main
            )


class WheelHandler:

    def __init__(
            self,
            cfg: MouseHandlerConfig,
            control_adapter: ControlAdapter,
            control_widget
    ):
        """
            滚轮控制器
        :param cfg:
        :param control_adapter:
        :param control_widget:
        """
        self.cfg = cfg
        self.ca = control_adapter
        self.cw = control_widget

    def touch_down(self, touch):
        """
            Wheel
            翻页功能
            Ctrl + Wheel 放大缩小功能
        :param touch:
        :return:
        """

        if touch.button in ['scrollup', 'scrolldown']:

            spr = touch.ud['spr']

            is_swipe = 'ctrl' in Window.modifiers

            sec_spr = spr + ScalePointR(
                        -0.1 if touch.button == 'scrolldown' else -0.2,
                        0.1 if touch.button == 'scrolldown' else 0.2,
                        spr.r
                    )

            if is_swipe:
                # 第二个点
                self.ca.f_touch_spr(Action.DOWN.value, sec_spr, self.cfg.touch_id_wheel + 5)

            self.ca.f_touch_spr(Action.DOWN.value, spr, self.cfg.touch_id_wheel)

            for _ in range(15):
                _spr = spr + ScalePointR(
                    0.004 * _ * (1 if touch.button == 'scrolldown' else -1) if is_swipe else 0,
                    0.008 * _ * (1 if touch.button == 'scrollup' else -1),
                    spr.r
                )
                self.ca.f_touch_spr(Action.MOVE.value, _spr, self.cfg.touch_id_wheel)
                time.sleep(0.01)

            self.ca.f_touch_spr(
                Action.RELEASE.value, _spr, self.cfg.touch_id_wheel
            )

            if is_swipe:
                self.ca.f_touch_spr(Action.RELEASE.value, sec_spr, self.cfg.touch_id_wheel + 5)


@dataclass
class MouseButtonStatus:

    left_button: bool = False
    right_button: bool = False
    middle_button: bool = False


class UHIDMouseHandler:

    def __init__(
            self, cfg: MouseHandlerConfig, control_adapter: ControlAdapter, device: MYDevice
    ):
        self.cfg: MouseHandlerConfig = cfg
        self.ca: ControlAdapter = control_adapter
        self.device: MYDevice = device

        self.is_supported = self.device.device_info.is_uhid_supported

        self.x: int = 1
        self.y: int = 1

        self.mouse_controller = mouse.Controller()
        self.mb_status = MouseButtonStatus()
        self.activated: bool = False

        if self.is_supported:
            self.ca.f_uhid_mouse_create(mouse_id=self.cfg.um_mouse_id)


    def activate(self):
        """
            激活 UHID 鼠标
        :return:
        """
        if self.is_supported and not self.activated:

            self.x = Window.left + Window.width / Metrics.density // 2
            self.y = Window.top + Window.height / Metrics.density // 2

            self.mouse_controller.position = (self.x, self.y)

            Window.bind(mouse_pos=self.move)
            Window.show_cursor = False
            Window.grab_mouse()

            self.activated = True

        else:
            Logger.warning(f"UHID Mouse Not Supported!")

    def deactivate(self):
        """
            取消激活
        :return:
        """
        if self.is_supported and self.activated:
            Window.unbind(mouse_pos=self.move)
            Window.ungrab_mouse()
            Window.show_cursor = True
            self.mb_status = MouseButtonStatus()
            self.activated = False

    def move(self, instance, pos, *args, **kwargs):
        """
            监测 Windows Mouse Pos 改变事件
        :param instance:
        :param pos:
        :return:
        """

        pos = self.mouse_controller.position

        if 'dx' in kwargs and 'dy' in kwargs:
            dx, dy = kwargs['dx'], kwargs['dy']
        else:
            # 计算偏移值
            dx, dy = pos[0] - self.x, pos[1] - self.y

        if 'dx' not in kwargs:
            # 锁定归位
            self.mouse_controller.position = (self.x, self.y)

        try:
            self.ca.f_uhid_mouse_input(
                min(max(int(dx * self.cfg.um_move_speed), -127), 127),
                min(max(int(dy * self.cfg.um_move_speed), -127), 127),
                **asdict(self.mb_status), ignore_repeat=True)
        except:
            ...

    def touch_down(self, touch):
        """
            按键事件，配置mb_status
        :param touch:
        :return:
        """
        if not self.activated:
            return

        btn = {
            'left': 'left_button',
            'right': 'right_button',
            'middle': 'middle_button'
        }.get(touch.button, None)

        if btn:
            setattr(self.mb_status, btn, True)

        self.ca.f_uhid_mouse_input(
            0, 0,
            **asdict(self.mb_status),
            wheel_motion=0 if touch.button not in ['scrolldown', 'scrollup'] else
            (1 if touch.button == 'scrolldown' else -1),
        )

    def touch_up(self, touch):
        """
            按键释放
        :param touch:
        :return:
        """
        if not self.activated:
            return

        btn = {
            'left': 'left_button',
            'right': 'right_button',
            'middle': 'middle_button'
        }.get(touch.button, None)

        if btn:
            setattr(self.mb_status, btn, False)

        self.ca.f_uhid_mouse_input(0, 0, **asdict(self.mb_status))


class MouseHandler(Widget):
    """
        鼠标事件处理器
    """

    def __init__(
            self,
            cfg: MouseHandlerConfig, video_screen: VideoScreen, control_adapter: ControlAdapter, device: MYDevice,
            **kwargs
    ):
        super(MouseHandler, self).__init__(**kwargs)

        self.cfg: MouseHandlerConfig = cfg
        self.cfg.mode = MouseHandlerMode.TOUCH
        self.video_screen: VideoScreen = video_screen
        self.ca: ControlAdapter = control_adapter
        self.device: MYDevice = device

        self.gesture_handler = GestureHandler(self.cfg, video_screen)
        self.right_point = SecondPoint(
            self.cfg.touch_id_sec,
            self.video_screen,
            self.gesture_handler
        )
        self.touch_handler = TouchHandler(self.cfg, self.ca, video_screen, self.right_point)
        self.wheel_handler = WheelHandler(self.cfg, self.ca, video_screen)
        self.uhid_mouse_handler = UHIDMouseHandler(self.cfg, self.ca, self.device)

        if self.cfg.mode == MouseHandlerMode.UHID:
            self.uhid_mouse_handler.activate()

        # 注册第二个点功能
        self.gesture_handler.register_gesture_action(
            0, GesAction(
                'mysc', 'UR', '两点模式',
                self.right_point.activate
            )
        )
        self.gesture_handler.register_gesture_action(
            0, GesAction(
                'mysc', 'DL', '停止两点模式',
                self.right_point.deactivate
            )
        )

    def switch_mode_callback(self, action: ActionCallback):
        if action.action == Action.RELEASE:
            self.switch_mode()

    def switch_mode(self, mode: MouseHandlerMode | None = None):
        """
            切换 Mode
        :param mode:
        :return:
        """
        if mode is not None and mode == self.cfg.mode:
            return

        if mode:
            self.cfg.mode = mode
        else:
            self.cfg.mode = MouseHandlerMode.UHID if self.cfg.mode == MouseHandlerMode.TOUCH else MouseHandlerMode.TOUCH

        # UHID Mode
        if self.cfg.mode == MouseHandlerMode.UHID:
            if not self.device.device_info.is_uhid_supported:
                Logger.warning(f"Device UHID Mode Not Supported")
                self.cfg.mode = MouseHandlerMode.TOUCH
            else:
                self.uhid_mouse_handler.activate()

        else:
            self.uhid_mouse_handler.deactivate()

        self.cfg.save()
        create_snack(f"鼠标 {'触摸' if self.cfg.mode == MouseHandlerMode.TOUCH else 'UHID'} 模式，(F9切换)",
                     color=MYCombineColors.orange if self.cfg.mode == MouseHandlerMode.TOUCH else MYCombineColors.blue,
                     duration=1).open()

    def start(self):
        self.cfg.running = True
        self.cfg.save()

    def stop(self):
        self.cfg.running = False
        self.cfg.save()

    def get_random_touch_id(self) -> int:
        """
            获取随机Touch ID
        :return:
        """
        while True:
            _touch_id = random.randrange(0x413 + 150, 0x413 + 300)
            if _touch_id not in self.touch_points:
                return _touch_id

    @staticmethod
    def in_widget(func):
        """
            装饰函数 判断当前状态
        :param func:
        :return:
        """
        @wraps(func)
        def wrapper(self, instance, touch):
            if not self.video_screen.collide_point(*touch.pos):
                return
            return func(self, instance, touch)
        return wrapper

    @staticmethod
    def prepare(func):
        """
            装饰函数 判断当前状态
        :param func:
        :return:
        """
        @wraps(func)
        def wrapper(self, instance, touch):
            if not self.cfg.running:
                return

            # 计算点ScalePointR
            touch.ud['spr'] = ScalePointR(
                (touch.x - self.video_screen.pos[0]) / self.video_screen.width,
                # Y轴倒置
                1 - (touch.y - self.video_screen.pos[1]) / self.video_screen.height,
                self.video_screen.rotation
            )
            return func(self, instance, touch)
        return wrapper

    @in_widget
    @prepare
    def touch_down(self, instance, touch):
        """
            按下事件
        :param instance:
        :param touch:
        :return:
        """

        if self.cfg.mode == MouseHandlerMode.UHID:
            self.uhid_mouse_handler.touch_down(touch)

        elif self.cfg.mode == MouseHandlerMode.TOUCH:
            self.touch_handler.touch_down(touch)
            self.gesture_handler.touch_down(touch)
            self.wheel_handler.touch_down(touch)

    @in_widget
    @prepare
    def touch_move(self, instance, touch):
        """
            移动事件
        :param instance:
        :param touch:
        :return:
        """

        if self.cfg.mode == MouseHandlerMode.UHID:
            ...

        elif self.cfg.mode == MouseHandlerMode.TOUCH:
            self.touch_handler.touch_move(touch)
            self.gesture_handler.touch_move(touch)

    @prepare
    def touch_up(self, instance, touch):
        """
            存在外部释放情况，不使用 @in_widget
        :param instance:
        :param touch:
        :return:
        """

        if self.cfg.mode == MouseHandlerMode.UHID:
            self.uhid_mouse_handler.touch_up(touch)

        elif self.cfg.mode == MouseHandlerMode.TOUCH:

            self.touch_handler.touch_up(touch)
            self.gesture_handler.touch_up(touch)
