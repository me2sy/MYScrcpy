# -*- coding: utf-8 -*-
"""
    鼠标处理器
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-10-13 1.6.6 Me2sY  修复获取Touchpoint缺陷

        2024-09-28 1.6.4 Me2sY  完善鼠标事件，适配ActionCallbackParam回调传参

        2024-09-27 1.6.3 Me2sY
            1. 新增 required handler，支持插件独占回调事件
            2. 新增 TouchPoint

        2024-09-23 1.6.0 Me2sY
            1. 解决 DPG 卡死问题，MouseMoveHandler delete 后 导致 DPG 卡死
            2. 升级结构，适配 Extensions

        2024-09-01 1.4.2 Me2sY
            1.创建，处理鼠标事件
            2.新增 右键收拾功能，模拟两点触控功能
"""

__author__ = 'Me2sY'
__version__ = '1.6.6'

__all__ = [
    'GesAction', 'TouchPoint',
    'MouseHandler'
]

from dataclasses import dataclass
from enum import IntEnum
from functools import partial
import random
import time
from typing import Callable, Tuple, Dict, List

import dearpygui.dearpygui as dpg
from loguru import logger
import moosegesture

from myscrcpy.core import Session, AdvDevice
from myscrcpy.gui.dpg.components.vc import CPMVC
from myscrcpy.gui.dpg.dpg_extension_cls import ActionCallbackParam
from myscrcpy.utils import Action, ScalePointR, ADBKeyCode, UnifiedKeys


@dataclass
class GesAction:
    """
        手势动作
    """
    receiver: str
    gestures: str
    action_name: str
    action: Callable


class SecondPoint:
    """
        生成第二个点，用于缩放，旋转等二指操作
    """

    def __init__(self, touch_id: int, draw_handler, cpm_vc: CPMVC):
        """
            生成第二个点
        :param touch_id:
        """
        self.spr: ScalePointR | None = None
        self.is_active = False
        self.show_layer = None
        self.touch_id = touch_id

        self.draw_handler = draw_handler
        self.cpm_vc = cpm_vc
        self.tag_point = dpg.generate_uuid()

    def start(self, *args, **kwargs):
        """
            进入监控状态
        :param draw_handler:
        :param user_data:
        :param args:
        :param kwargs:
        :return:
        """

        self.stop()

        self.is_active = True
        self.show_layer = self.cpm_vc.tag_layer_sec_point
        self.spr = self.draw_handler.track_sprs[0]
        self.show(self.draw_handler.track[0])

    def stop(self):
        """
            停止监控状态
        :param draw_handler:
        :param user_data:
        :param args:
        :param kwargs:
        :return:
        """
        if dpg.does_item_exist(self.tag_point):
            dpg.delete_item(self.tag_point)
        self.is_active = False

    def show(self, pos):
        """
            显示点位置
        :param pos:
        :return:
        """
        dpg.draw_circle(
            pos, radius=10,
            color=(15, 15, 15, 150), fill=(200, 200, 200, 150),
            thickness=2, parent=self.show_layer, tag=self.tag_point
        )

    def click(self, session: Session):
        """
            点击
        :param session:
        :return:
        """
        session.ca.f_touch_spr(Action.DOWN.value, self.spr, touch_id=self.touch_id)

    def release(self, session: Session):
        """
            释放
        :param session:
        :return:
        """
        session.ca.f_touch_spr(Action.RELEASE.value, self.spr, touch_id=self.touch_id)


class DrawHandler:

    MAX_SPACE_N = 3

    SPACE_MYSC = 0

    GA_UNKNOWN = GesAction('mysc', '', 'UNKNOWN', lambda *args, **kwargs: ...)

    def __init__(self, vm, cpm_vc: CPMVC):
        """
            手势处理器
        :param vm: ValueManager
        """
        self.space = vm.register('msh.space', 1)
        self.cpm_vc = cpm_vc

        self.track = []
        self.track_sprs = []
        self.ges_action_proxy: Dict[int, Dict[str, GesAction]] = {
            _: {} for _ in range(self.MAX_SPACE_N)
        }

        ga_switch = GesAction('mysc', 'DR', 'Switch Mouse Space', partial(self.switch_space))
        ga_switch_next = GesAction('mysc', 'DR|L', 'Last Mouse Space',  partial(self.space_step, -1))
        ga_switch_back = GesAction('mysc', 'DR|R', 'NExt Mouse Space',  partial(self.space_step, 1))

        for _ in range(self.MAX_SPACE_N):
            self.register_ges_action(_, ga_switch)
            self.register_ges_action(_, ga_switch_next)
            self.register_ges_action(_, ga_switch_back)

    def switch_space(self, space: int = None):
        """
            切换控制空间
        :param space:
        :return:
        """
        if space is None:
            self.space(
                self.space() + (
                    (-self.MAX_SPACE_N + 1) if (self.space() + 1) == self.MAX_SPACE_N else 1
                )
            )
        elif type(space) is int and 0 <= space < self.MAX_SPACE_N:
            self.space(space)
        else:
            return

    def space_step(self, step: int = 1):
        """
            上下切换 space
        :param step:
        :return:
        """
        self.space(max(0, min(self.MAX_SPACE_N - 1, self.space() + step)))

    def click(self):
        """
            点击事件
        :return:
        """

        # 开始记录路线
        self.track.append(dpg.get_drawing_mouse_pos())
        self.track_sprs.append(self.cpm_vc.spr())

        # 情况提示页面
        dpg.delete_item(self.cpm_vc.tag_layer_track, children_only=True)
        dpg.delete_item(self.cpm_vc.tag_layer_msg, children_only=True)

        # 绘制起始点
        dpg.draw_circle(
            dpg.get_drawing_mouse_pos(), radius=5,
            color=(15, 15, 15, 150), fill=(200, 200, 200, 150), thickness=2,
            parent=self.cpm_vc.tag_layer_track
        )

    def release(self):
        """
            释放事件
        :return:
        """
        # 解析鼠标手势，回调对应方法
        ges_actions, ga = self.get_method()
        ga.action()

        # 清空提示框
        dpg.delete_item(self.cpm_vc.tag_layer_track, children_only=True)
        dpg.delete_item(self.cpm_vc.tag_layer_msg, children_only=True)

        # 清空路线缓存
        self.track.clear()
        self.track_sprs.clear()

    def move(self):
        """
            移动事件
        :return:
        """
        self.track.append(dpg.get_drawing_mouse_pos())
        self.track_sprs.append(self.cpm_vc.spr())

        # 绘制移动线
        if len(self.track) >= 2:
            dpg.draw_line(
                self.track[-1], self.track[-2],
                parent=self.cpm_vc.tag_layer_track, thickness=3, color=[
                    random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
                ]
            )

        # 解析鼠标手势 进行功能提示
        if len(self.track) >= 3:
            ges_actions, ga = self.get_method()
            dpg.delete_item(self.cpm_vc.tag_layer_msg, children_only=True)

            dpg.draw_rectangle(
                [10, 10], [260, 40],
                fill=(240, 238, 220, 200), color=(240, 238, 220, 200),
                parent=self.cpm_vc.tag_layer_msg
            )

            msg = f"SP:{self.space()} > "

            dpg.draw_text(
                [12, 12], msg + '|'.join(ges_actions)[-8:] + ' ' + ga.action_name, size=22, color=(0, 0, 0, 255),
                parent=self.cpm_vc.tag_layer_msg
            )

    def get_method(self) -> Tuple[List[str], GesAction]:
        """
            解析鼠标手势，获取相应方法
            使用 Moosegesture
            https://github.com/asweigart/moosegesture
        :return:
        """

        if len(self.track) >= 3:
            ges_action = moosegesture.getGesture(self.track)
            return ges_action, self.ges_action_proxy[self.space()].get('|'.join(ges_action), self.GA_UNKNOWN)
        else:
            return ['Draw More'], self.GA_UNKNOWN

    def register_ges_action(self, space: int, action: GesAction):
        """
            注册手势
        :param space:
        :param action:
        :return:
        """

        if space < 0 or space >= self.MAX_SPACE_N or type(space) is not int:
            raise KeyError(f"Register to  {' / '.join([str(_) for _ in range(1, self.MAX_SPACE_N)])} Space Only!")

        _action = self.ges_action_proxy[space].get(action.gestures)
        if _action is not None and _action.receiver != action.receiver:
            logger.warning(f"Mouse Gestures {_action.gestures} is registered by {_action.receiver}")
            return

        self.ges_action_proxy[space][action.gestures] = action


class TouchPoint:
    """
        Touch点对象
        独立的 Touch ID, 实现触摸模拟功能
    """

    def __init__(self, touch_id, touch_spr_function: Callable):
        self.touch_id = touch_id
        self.touch_spr_function = touch_spr_function
        self.sprs = []
        self.is_down: bool = False

    def down(self, spr: ScalePointR):
        """
            触摸按下
        :param spr:
        :return:
        """
        self.touch_spr_function(Action.DOWN.value, spr, touch_id=self.touch_id)
        self.is_down = True
        self.sprs.append(spr)

    def move_to(self, spr: ScalePointR):
        """
            移动至
        :param spr:
        :return:
        """
        if not self.is_down:
            return

        self.touch_spr_function(Action.MOVE.value, spr, touch_id=self.touch_id)
        self.sprs.append(spr)

    def move_rel(self, spr: ScalePointR):
        """
            相对移动
        :param spr:
        :return:
        """
        if not self.is_down:
            return

        _spr = self.sprs[-1] + spr
        self.touch_spr_function(Action.MOVE.value, _spr, touch_id=self.touch_id)
        self.sprs.append(_spr)

    def release(self):
        """
            触摸释放
        :return:
        """
        self.touch_spr_function(Action.RELEASE.value, self.sprs[-1], touch_id=self.touch_id)
        self.is_down = False
        self.sprs = []


class MouseHandler:
    """
        鼠标事件处理器
    """

    class Mode(IntEnum):
        UHID = 0
        TOUCH = 1

    def __init__(self, vm, cpm_vc: CPMVC):

        self.cpm_vc = cpm_vc
        self.enabled = True

        self.vm = vm

        self.adv_device: AdvDevice = None
        self.session: Session = None

        self.mode = self.vm.register('msh.mode', self.Mode.TOUCH)

        self.touch_id = self.vm.register(
            'msh.touch_id', 0x0413, rewrite=False, set_kv=True
        )
        self.touch_id_wheel = self.vm.register(
            'msh.touch_id_wheel', 0x0413 + 50, rewrite=False, set_kv=True
        )
        self.touch_id_sec = self.vm.register(
            'msh.touch_id_sec', 0x0413 + 100, rewrite=False, set_kv=True
        )

        self.handler_draw = DrawHandler(self.vm, cpm_vc)

        self.right_point = SecondPoint(self.touch_id() + 10, self.handler_draw, cpm_vc)

        self.tag_hr = dpg.generate_uuid()

        self.touch_points = {}

        self.is_control_required = False
        self.controller = None
        self.control_callback: Callable[[ActionCallbackParam], None] = None

        with dpg.handler_registry(tag=self.tag_hr):
            dpg.add_mouse_click_handler(callback=self.click_event_handler, user_data=Action.DOWN)
            dpg.add_mouse_release_handler(callback=self.release_event_handler, user_data=Action.RELEASE)
            dpg.add_mouse_wheel_handler(callback=self.wheel_event_handler, user_data=Action.ROLL)
            dpg.add_mouse_move_handler(callback=self.move_event_handler, user_data=Action.MOVE)
            dpg.add_mouse_drag_handler(callback=self.drag_event_handler, user_data=Action.DRAG)
            dpg.add_mouse_double_click_handler(callback=self.db_click_event_handler, user_data=Action.DB_CLICK)
            dpg.add_mouse_down_handler(callback=self.pressed_event_handler, user_data=Action.PRESSED)

    def get_random_touch_id(self) -> int:
        """
            获取随机Touch ID
        :return:
        """
        while True:
            _touch_id = random.randrange(0x413 + 150, 0x413 + 300)
            if _touch_id not in self.touch_points:
                return _touch_id

    def register_touch_point(self, module_name, touch_id: int | None = None) -> TouchPoint | None:
        """
            注册并获取 touch point
        :param module_name:
        :param touch_id:
        :return:
        """
        if self.session and self.session.is_control_ready:
            if touch_id is None:
                touch_id = self.get_random_touch_id()
            else:
                if touch_id in self.touch_points:
                    logger.warning(f"Touch Id {touch_id} already registered by {self.touch_points[touch_id][0]}")
                    return None

            tp = TouchPoint(touch_id, self.session.ca.f_touch_spr)

            self.touch_points[touch_id] = (module_name, tp)

            return tp

    def required_control(self, controller: str, control_callback: Callable[[ActionCallbackParam], None]) -> bool:
        """
            请求独占控制
        :return:
        """
        if self.is_control_required:
            return False

        self.is_control_required = True
        self.controller = controller
        self.control_callback = control_callback
        return True

    def release_control(self):
        """
            释放请求
        :return:
        """
        self.is_control_required = False
        self.controller = None
        self.control_callback = None
        dpg.delete_item(self.cpm_vc.tag_layer_mouse, children_only=True)

    def device_connect(self, adv_device: AdvDevice, session: Session):
        """
            设备连接
        :param adv_device:
        :param session:
        :return:
        """
        self.adv_device = adv_device
        self.session = session

        self.register_system_gesture()

    def device_disconnect(self):
        """
            关闭监听
        :return:
        """
        self.adv_device = None
        self.session = None
        self.release_control()

    def register_ges_action(self, space: int, action: GesAction):
        """
            注册手势
        :param space:
        :param action:
        :return:
        """
        self.handler_draw.register_ges_action(space, action)

    def register_system_gesture(self):
        """
            注册 系统 手势
        :return:
        """
        # 注册全局功能
        ga_back = GesAction(
            'mysc', 'L', 'Back', partial(self.adv_device.adb_dev.keyevent, ADBKeyCode.BACK.value)
        )
        ga_home = GesAction(
            'mysc', 'U', 'Home', partial(self.adv_device.adb_dev.keyevent, ADBKeyCode.HOME.value)
        )
        ga_apps = GesAction(
            'mysc', 'UL', 'Apps', partial(self.adv_device.adb_dev.keyevent, ADBKeyCode.APP_SWITCH.value)
        )

        ga_msp = GesAction('mysc', 'UR', 'Make Second Point', self.right_point.start)

        ga_ssp = GesAction('mysc', 'DL', 'Stop Second Point', self.right_point.stop)

        for _ in range(DrawHandler.MAX_SPACE_N):
            for ga in [ga_back, ga_home, ga_apps, ga_msp, ga_ssp]:
                self.handler_draw.register_ges_action(_, ga)

        # 注册 Space 0 功能
        ga_screen_shot = GesAction(
            'mysc', 'R', 'ScreenShot', partial(self.adv_device.adb_dev.keyevent, ADBKeyCode.KB_PRINTSCREEN.value)
        )
        ga_c2d = GesAction(
            'mysc', 'D', 'CopyToDevice', partial(self.adv_device.adb_dev.keyevent, ADBKeyCode.KB_PRINTSCREEN.value)
        )
        ga_play = GesAction(
            'mysc', 'R|U', 'Play/Pause',
            partial(self.adv_device.adb_dev.keyevent, ADBKeyCode.KB_MEDIA_PLAY_PAUSE.value)
        )
        ga_m_prev = GesAction(
            'mysc', 'R|UL', 'Media Prev',
            partial(self.adv_device.adb_dev.keyevent, ADBKeyCode.KB_MEDIA_PREV_TRACK.value)
        )
        ga_m_next = GesAction(
            'mysc', 'R|UR', 'Media Next',
            partial(self.adv_device.adb_dev.keyevent, ADBKeyCode.KB_MEDIA_NEXT_TRACK.value)
        )

        ga_mute = GesAction(
            'mysc', 'R|D', 'Mute',
            partial(self.adv_device.adb_dev.keyevent, ADBKeyCode.KB_VOLUME_MUTE.value)
        )
        ga_v_up = GesAction(
            'mysc', 'R|DL', 'Volume Up',
            partial(self.adv_device.adb_dev.keyevent, ADBKeyCode.KB_VOLUME_MUTE.value)
        )
        ga_v_down = GesAction(
            'mysc', 'R|DR', 'Volume Down',
            partial(self.adv_device.adb_dev.keyevent, ADBKeyCode.KB_VOLUME_MUTE.value)
        )

        for ga in [ga_screen_shot, ga_c2d, ga_play, ga_m_next, ga_m_prev, ga_mute, ga_v_up, ga_v_down]:
            self.handler_draw.register_ges_action(DrawHandler.SPACE_MYSC, ga)

    @staticmethod
    def after_control_required(func):
        """
            Safe Run With Status Check and Try/Except
        :param func:
        :return:
        """
        def wrapper(self, sender, app_data, user_data, *args, **kwargs):
            try:
                if self.session is None or not self.cpm_vc.is_hovered():
                    return False

                if self.is_control_required:
                    self.cpm_vc.draw_mouse(self.controller)

                    # 2024-09-28 1.6.4 Me2sY  统一化回调函数传参
                    acp = MouseHandler.callback2action(sender, app_data, user_data)
                    if acp:
                        return self.control_callback(acp)
                    else:
                        return False

                if not self.session.is_control_ready:
                    return False

                return func(self, sender, app_data, user_data, *args, **kwargs)

            except Exception as e:
                logger.error(f"MouseHandler Error")
                logger.exception(e)
        return wrapper

    KEY_MAPPER = {
        dpg.mvMouseButton_Left: UnifiedKeys.UK_MOUSE_L,
        dpg.mvMouseButton_Right: UnifiedKeys.UK_MOUSE_R,
        dpg.mvMouseButton_Middle: UnifiedKeys.UK_MOUSE_WHEEL,
    }

    @staticmethod
    def callback2action(sender, app_data, user_data: Action) -> ActionCallbackParam | None:
        """
            将回调转为ActionCallbackParam
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        action_data = None
        is_first = True
        if user_data in [Action.DOWN, Action.RELEASE, Action.DB_CLICK]:
            uk = MouseHandler.KEY_MAPPER.get(app_data)

        elif user_data == Action.ROLL:
            uk = UnifiedKeys.UK_MOUSE_WHEEL_UP if app_data > 0 else UnifiedKeys.UK_MOUSE_WHEEL_DOWN
            action_data = app_data

        elif user_data == Action.MOVE:
            uk = UnifiedKeys.UK_MOUSE_MOVE
            action_data = app_data
            is_first = False

        elif user_data == [Action.PRESSED, Action.DRAG]:
            uk = MouseHandler.KEY_MAPPER.get(app_data[0])
            action_data = app_data[1:]
            if len(action_data) == 1 and action_data[0] == 0.0:
                is_first = True
            else:
                is_first = False
        else:
            return None

        return ActionCallbackParam(
            action=user_data, uk=uk, action_data=action_data, app_data=app_data, is_first=is_first
        )

    @after_control_required
    def move_event_handler(self, sender, app_data, user_data, *args, **kwargs):
        """
            移动事件处理器
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """

        # 左键按下，则模拟 TOUCH
        if dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
            self.session.ca.f_touch_spr(Action.MOVE.value, self.cpm_vc.spr(), touch_id=self.touch_id())

        # 右键按下，进行Draw
        if dpg.is_mouse_button_down(dpg.mvMouseButton_Right):
            self.handler_draw.move()

    @after_control_required
    def click_event_handler(self, sender, app_data, user_data, *args, **kwargs):
        """
            单击(按下)事件处理器
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """

        # 左键
        if app_data == dpg.mvMouseButton_Left:
            if self.right_point.is_active:
                self.right_point.click(self.session)

            self.session.ca.f_touch_spr(Action.DOWN.value, self.cpm_vc.spr(), touch_id=self.touch_id())

        # 右键
        if app_data == dpg.mvMouseButton_Right:
            self.handler_draw.click()

    @after_control_required
    def release_event_handler(self, sender, app_data, user_data, *args, **kwargs):
        """
            释放按键处理器
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        # 左键
        if app_data == dpg.mvMouseButton_Left:
            if self.right_point.is_active:
                self.right_point.release(self.session)

            self.session.ca.f_touch_spr(Action.RELEASE.value, self.cpm_vc.spr(), touch_id=self.touch_id())

        # 右键
        if app_data == dpg.mvMouseButton_Right:
            self.handler_draw.release()

    @after_control_required
    def wheel_event_handler(self, sender, app_data, user_data, *args, **kwargs):
        """
            滚轮事件处理器，Wheel为上下滚动，Ctrl + Wheel为缩放操作
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """

        if type(app_data) is not int:
            return

        vc_draw_coord = self.cpm_vc.coord_draw

        move_dis = vc_draw_coord.width // 8

        m_pos = dpg.get_drawing_mouse_pos()
        fir_pos = [m_pos[0] + move_dis, m_pos[1] + move_dis]
        sec_pos = [m_pos[0] - move_dis, m_pos[1] - move_dis]

        # 每次移动距离
        step = 1 * (1 if app_data > 0 else -1)

        if dpg.is_key_down(dpg.mvKey_Control):  # Ctrl Press Then Wheel to Zoom

            self.session.ca.f_touch_spr(
                Action.DOWN.value, vc_draw_coord.to_scale_point_r(*sec_pos), touch_id=self.touch_id_sec(),
            )

            # First Point
            self.session.ca.f_touch_spr(
                Action.DOWN.value, vc_draw_coord.to_scale_point_r(*fir_pos), touch_id=self.touch_id_wheel()
            )

            # 移动距离
            dis = vc_draw_coord.width // 20
            t = 0.08 / dis
            for i in range(dis):
                next_pos = [m_pos[0] + move_dis - i * step, m_pos[1] + move_dis - i * step]

                self.session.ca.f_touch_spr(
                    Action.MOVE.value, vc_draw_coord.to_scale_point_r(*next_pos), touch_id=self.touch_id_wheel()
                )
                time.sleep(t)
        else:  # Wheel to swipe
            self.session.ca.f_touch_spr(
                Action.DOWN.value, vc_draw_coord.to_scale_point_r(*m_pos), touch_id=self.touch_id_wheel()
            )
            dis = vc_draw_coord.height // 15
            t = 0.05 / dis
            for i in range(dis):
                next_pos = [m_pos[0], m_pos[1] + i * step]
                self.session.ca.f_touch_spr(
                    Action.MOVE.value, vc_draw_coord.to_scale_point_r(*next_pos), touch_id=self.touch_id_wheel()
                )
                time.sleep(t)

        # Release Click
        self.session.ca.f_touch_spr(
            Action.RELEASE.value, vc_draw_coord.to_scale_point_r(*next_pos), touch_id=self.touch_id_wheel()
        )

        self.session.ca.f_touch_spr(
            Action.RELEASE.value, vc_draw_coord.to_scale_point_r(*sec_pos), touch_id=self.touch_id_sec()
        )

    @after_control_required
    def db_click_event_handler(self, sender, app_data, user_data, *args, **kwargs):
        """
            双击事件处理器器
            一次性事件
        :param sender:
        :param app_data:
        :param user_data:
        :param args:
        :param kwargs:
        :return:
        """

    @after_control_required
    def drag_event_handler(self, sender, app_data, user_data, *args, **kwargs):
        """
            Drag 事件处理器
            循环回调
        :param sender:
        :param app_data:
        :param user_data:
        :param args:
        :param kwargs:
        :return:
        """

    @after_control_required
    def pressed_event_handler(self, sender, app_data, user_data, *args, **kwargs):
        """
            按压 事件处理器
            循环回调
        :param sender:
        :param app_data:
        :param user_data:
        :param args:
        :param kwargs:
        :return:
        """
