# -*- coding: utf-8 -*-
"""
    鼠标处理器
    ~~~~~~~~~~~~~~~~~~
    

    Log:
         2024-09-01 1.4.2 Me2sY
            1.创建，处理鼠标事件
            2.新增 右键收拾功能，模拟两点触控功能

"""

__author__ = 'Me2sY'
__version__ = '1.4.2'

__all__ = [
    'GesAction', 'MouseHandlerUserData',
    'MouseHandler'
]

from dataclasses import dataclass
import random
import time
from typing import Callable, Tuple, Dict, List

import dearpygui.dearpygui as dpg
import moosegesture

from myscrcpy.core import Session
from myscrcpy.utils import Action, ScalePointR, Coordinate


@dataclass
class GesAction:
    """
        手势动作
    """
    action_name: str
    action: Callable


@dataclass
class MouseHandlerUserData:
    """
        Mouse事件回调参数
    """
    active: Callable[[], bool]
    spr: Callable[[], ScalePointR]
    draw_coord: Callable[[], Coordinate]
    layer_track: str | int
    layer_msg: str | int
    layer_sec_point: str | int


class SecondPoint:
    """
        生成第二个点，用于缩放，旋转等二指操作
    """

    def __init__(self, touch_id: int):
        """
            生成第二个点
        :param touch_id:
        """
        self.spr: ScalePointR | None = None
        self.is_active = False
        self.show_layer = None
        self.touch_id = touch_id

    def start(self, draw_handler, user_data: MouseHandlerUserData, *args, **kwargs):
        """
            进入监控状态
        :param draw_handler:
        :param user_data:
        :param args:
        :param kwargs:
        :return:
        """

        self.stop(draw_handler, user_data)

        self.is_active = True
        self.show_layer = user_data.layer_sec_point
        self.spr = draw_handler.track_sprs[0]
        self.show(draw_handler.track[0])

    def stop(self, draw_handler, user_data, *args, **kwargs):
        """
            停止监控状态
        :param draw_handler:
        :param user_data:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            dpg.delete_item(self.tag_point)
        except:
            pass
        self.is_active = False

    def show(self, pos):
        """
            显示点位置
        :param pos:
        :return:
        """
        self.tag_point = dpg.draw_circle(
            pos, radius=10, color=(15, 15, 15, 150), fill=(200, 200, 200, 150), thickness=2, parent=self.show_layer
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


ga_unknown = GesAction('UNKNOWN', lambda *args, **kwargs: ...)


class DrawHandler:

    def __init__(self, ges_action_proxy: Dict[str, GesAction]):
        """
            手势处理器
        :param ges_action_proxy:
        """

        self.track = []
        self.track_sprs = []
        self.ges_action_proxy = ges_action_proxy

    def click(self, user_data: MouseHandlerUserData):
        """
            点击事件
        :param user_data:
        :return:
        """

        # 开始记录路线
        self.track.append(dpg.get_drawing_mouse_pos())
        self.track_sprs.append(user_data.spr())

        # 情况提示页面
        dpg.delete_item(user_data.layer_track, children_only=True)
        dpg.delete_item(user_data.layer_msg, children_only=True)

        # 绘制起始点
        dpg.draw_circle(
            dpg.get_drawing_mouse_pos(), radius=5,
            color=(15, 15, 15, 150), fill=(200, 200, 200, 150), thickness=2,
            parent=user_data.layer_track
        )

    def release(self, user_data: MouseHandlerUserData):
        """
            释放事件
        :param user_data:
        :return:
        """
        # 解析鼠标手势，回调对应方法
        ges_actions, ga = self.get_method()
        ga.action(self, user_data)

        # 清空提示框
        dpg.delete_item(user_data.layer_track, children_only=True)
        dpg.delete_item(user_data.layer_msg, children_only=True)

        # 清空路线缓存
        self.track.clear()
        self.track_sprs.clear()

    def move(self, user_data: MouseHandlerUserData):
        """
            移动事件
        :param user_data:
        :return:
        """
        self.track.append(dpg.get_drawing_mouse_pos())
        self.track_sprs.append(user_data.spr())

        # 绘制移动线
        if len(self.track) >= 2:
            dpg.draw_line(
                self.track[-1], self.track[-2],
                parent=user_data.layer_track, thickness=3, color=[
                    random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
                ]
            )

        # 解析鼠标手势 进行功能提示
        if len(self.track) >= 3:
            ges_actions, ga = self.get_method()
            dpg.delete_item(user_data.layer_msg, children_only=True)

            dpg.draw_rectangle(
                [10, 10], [260, 40],
                fill=(240, 238, 220, 200), color=(240, 238, 220, 200),
                parent=user_data.layer_msg
            )
            dpg.draw_text(
                [12, 12], '|'.join(ges_actions)[-5:] + ' ' + ga.action_name, size=24, color=(0, 0, 0, 255),
                parent=user_data.layer_msg
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
            return ges_action, self.ges_action_proxy.get('|'.join(ges_action), ga_unknown)
        else:
            return ['Draw More'], ga_unknown


class MouseHandler:
    """
        鼠标事件处理器
    """

    def __init__(self, session: Session, right_callback_proxy: Dict[str, GesAction]):
        """
            鼠标事件处理器
            通过定义 {
                '方向': GesAction(提示内容, 回调方法)
            }
            实现右键画线激活相应功能
        :param session:
        :param right_callback_proxy:
        """

        self.session = session

        self.touch_id = 0x0413 + 521
        self.touch_id_wheel = self.touch_id + 20
        self.touch_id_sec = self.touch_id + 30

        self.right_point = SecondPoint(self.touch_id + 10)

        ga_msp = GesAction('Make Second Point', self.right_point.start)
        right_callback_proxy['UR'] = ga_msp

        ga_ssp = GesAction('Stop Second Point', self.right_point.stop)
        right_callback_proxy['DL'] = ga_ssp

        self.handler_draw = DrawHandler(right_callback_proxy)

        self.tag_hr = dpg.generate_uuid()
        self.tag_mouse_click = dpg.generate_uuid()
        self.tag_mouse_release = dpg.generate_uuid()
        self.tag_mouse_move = dpg.generate_uuid()
        self.tag_wheel = dpg.generate_uuid()

    def __del__(self):
        self.close()

    def close(self):
        """
            关闭监听
        :return:
        """
        for k, v in self.__dict__.items():
            if k.startswith('tag_'):
                try:
                    dpg.delete_item(v)
                except:
                    ...

    def move_event_handler(self, sender, app_data, user_data: MouseHandlerUserData):
        """
            移动事件处理器
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """

        if not user_data.active() or not self.session.is_control_ready:
            return

        # 左键按下，则模拟 TOUCH
        if dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
            self.session.ca.f_touch_spr(Action.MOVE.value, user_data.spr(), touch_id=self.touch_id)

        # 右键按下，进行Draw
        if dpg.is_mouse_button_down(dpg.mvMouseButton_Right):
            self.handler_draw.move(user_data)

    def click_event_handler(self, sender, app_data, user_data: MouseHandlerUserData):
        """
            单击(按下)事件处理器
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """

        if not user_data.active() or not self.session.is_control_ready:
            return

        # 左键
        if app_data == dpg.mvMouseButton_Left:
            if self.right_point.is_active:
                self.right_point.click(self.session)

            self.session.ca.f_touch_spr(Action.DOWN.value, user_data.spr(), touch_id=self.touch_id)

        # 右键
        if app_data == dpg.mvMouseButton_Right:
            self.handler_draw.click(user_data)

    def release_event_handler(self, sender, app_data, user_data: MouseHandlerUserData):
        """
            释放按键处理器
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        if not self.session.is_control_ready:
            return

        # 左键
        if app_data == dpg.mvMouseButton_Left:
            if self.right_point.is_active:
                self.right_point.release(self.session)

            self.session.ca.f_touch_spr(Action.RELEASE.value, user_data.spr(), touch_id=self.touch_id)

        # 右键
        if app_data == dpg.mvMouseButton_Right:
            self.handler_draw.release(user_data)

    def wheel_event_handler(self, sender, app_data, user_data: MouseHandlerUserData):
        """
            滚轮事件处理器，Wheel为上下滚动，Ctrl + Wheel为缩放操作
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """

        if not user_data.active() or not self.session.is_control_ready or not isinstance(app_data, int):
            return

        vc_draw_coord = user_data.draw_coord()

        move_dis = vc_draw_coord.width // 14

        m_pos = dpg.get_drawing_mouse_pos()
        fir_pos = [m_pos[0] + move_dis, m_pos[1] + move_dis]
        sec_pos = [m_pos[0] - move_dis, m_pos[1] - move_dis]

        # 每次移动距离
        step = 1 * (1 if app_data > 0 else -1)

        if dpg.is_key_down(dpg.mvKey_Control):      # Ctrl Press Then Wheel to Zoom

            # First Point
            self.session.ca.f_touch_spr(
                Action.DOWN.value, vc_draw_coord.to_scale_point_r(*fir_pos), touch_id=self.touch_id_wheel
            )

            # Second Point
            self.session.ca.f_touch_spr(
                Action.DOWN.value, vc_draw_coord.to_scale_point_r(*sec_pos), touch_id=self.touch_id_sec,
            )

            # 移动距离
            dis = vc_draw_coord.width // 20
            t = 0.08 / dis
            for i in range(dis):
                next_pos = [m_pos[0] + move_dis - i * step, m_pos[1] + move_dis - i * step]

                self.session.ca.f_touch_spr(
                    Action.MOVE.value, vc_draw_coord.to_scale_point_r(*next_pos), touch_id=self.touch_id_wheel
                )
                time.sleep(t)
        else:                       # Wheel to swipe
            self.session.ca.f_touch_spr(
                Action.DOWN.value, vc_draw_coord.to_scale_point_r(*m_pos), touch_id=self.touch_id_wheel
            )
            dis = vc_draw_coord.height // 15
            t = 0.05 / dis
            for i in range(dis):
                next_pos = [m_pos[0], m_pos[1] + i * step]
                self.session.ca.f_touch_spr(
                    Action.MOVE.value, vc_draw_coord.to_scale_point_r(*next_pos), touch_id=self.touch_id_wheel
                )
                time.sleep(t)

        # Release Click
        self.session.ca.f_touch_spr(
            Action.RELEASE.value, vc_draw_coord.to_scale_point_r(*next_pos), touch_id=self.touch_id_wheel
        )

        self.session.ca.f_touch_spr(
            Action.RELEASE.value, vc_draw_coord.to_scale_point_r(*sec_pos), touch_id=self.touch_id_sec
        )
