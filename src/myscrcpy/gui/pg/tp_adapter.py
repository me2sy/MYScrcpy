# -*- coding: utf-8 -*-
"""
    Touch Proxy Adapter
    ~~~~~~~~~~~~~~~~~~
    按键映射适配器

    Log:
        2024-08-26 1.4.0 Me2sY  适配新Core,配置文件中 unified_key改用对应名称

        2024-07-31 1.1.1 Me2sY  适配新Controller

        2024-07-28 1.0.0 Me2sY  发布初版

        2024-07-24 0.3.0 Me2sY
            1.适配 Scrcpy Server 2.5
            2.新增 UHID Mouse，可以在界面内显示鼠标指针

        2024-07-21 0.2.2 Me2sY  新增 TouchWatch 观察按钮

        2024-07-10 0.2.1 Me2sY
            1. Aim新增fast_attack 选项，选中后变为repeat点击
            2. Cross新增1s上推延迟

        2024-07-07 0.2.0 Me2sY
            重构，适配新架构。
            完成 Mouse 及 TouchAim 编写
"""

__author__ = 'Me2sY'
__version__ = '1.4.0'

__all__ = [
    'TouchType',
    'TouchProxyAdapter'
]

import random
import time
from enum import Enum
import pathlib
from typing import Set

from loguru import logger
import pygame

from myscrcpy.utils import ScalePoint, ScalePointR, Coordinate, Action, CfgHandler, UnifiedKey, UnifiedKeys, KeyMapper
from myscrcpy.utils import ROTATION_HORIZONTAL
from myscrcpy.core import *


class TouchType(Enum):
    KEY_CLICK = 'key_click'
    KEY_PRESS = 'key_press'
    KEY_REPEAT = 'key_repeat'
    KEY_SCOPE = 'key_scope'
    KEY_CROSS = 'key_cross'

    KEY_AIM = 'key_aim'
    KEY_WATCH = 'key_watch'

    MOUSE_TOUCH = 'mouse_touch'


class TouchProxy:
    """
        触摸映射
    """

    NEED_LOOP = False
    NEED_MOVE = False

    def __init__(
            self,
            tpa: 'TouchProxyAdapter',
            touch_type: TouchType,
            touch_x: float,
            touch_y: float,
            *args, **kwargs
    ):
        self.tpa = tpa
        self.control = self.tpa.session.ca

        self.touch_type = touch_type
        self.touch_x = touch_x
        self.touch_y = touch_y

        self.touch_id = self.tpa.create_touch_id()

        self.args = args
        self.kwargs = kwargs

        self.sp = ScalePoint(touch_x, touch_y)

        self.frame_coord = self.tpa.session.va.coordinate.d

        self._r = self.tpa.session.va.coordinate.rotation == ROTATION_HORIZONTAL
        self.spr = ScalePointR(touch_x, touch_y, self._r)

        self.last_down_ms = time.time()
        self.last_release_ms = time.time()
        self.is_touched = False
        self.is_pressed = False

        self.need_loop = kwargs.get('need_loop', self.NEED_LOOP)
        self.need_move = kwargs.get('need_move', self.NEED_MOVE)

        self.on: bool = kwargs.get('on', True)

    @staticmethod
    def check_time(check_time, threshold_ms) -> bool:
        return ((time.time() - check_time) * 1000) > threshold_ms

    def set_on(self, on: bool):
        self.on = on
        if not self.on:
            self.key_release()

    def action(self, action: Action):
        self.control.f_touch_spr(
            action=action, touch_id=self.touch_id,
            scale_point_r=self.spr
        )

    def touch_down(self):
        self.action(Action.DOWN)
        self.last_down_ms = time.time()
        self.is_touched = True

    def touch_release(self):
        self.action(Action.RELEASE)
        self.last_release_ms = time.time()
        self.is_touched = False

    def touch_move(self, scale_point: ScalePoint):
        self.spr = ScalePointR(*scale_point, self._r)
        self.action(Action.MOVE)

    def pg_loop_handler(self, *args, **kwargs):
        ...

    def move_handler(self, *args, **kwargs):
        ...

    def key_down(self):
        self.touch_down()
        self.is_pressed = True

    def key_release(self):
        if self.is_pressed:
            self.touch_release()
        self.is_pressed = False
        self.need_loop = False
        self.need_move = False


class TouchPress(TouchProxy):
    """
        持续按压
    """

    def pg_event_handler(self, event: pygame.event.Event, *args, **kwargs):
        if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
            self.key_down()
        elif event.type in [pygame.KEYUP, pygame.MOUSEBUTTONUP]:
            self.key_release()


class TouchClick(TouchProxy):
    """
        快速单击，不等待按键抬起动作
    """

    def __init__(
            self,
            tpa: 'TouchProxyAdapter', touch_type: TouchType, touch_x: float, touch_y: float,
            release_ms: int,
            *args, **kwargs):
        super().__init__(tpa, touch_type, touch_x, touch_y, *args, **kwargs)
        self.release_ms = release_ms

    def pg_event_handler(self, event: pygame.event.Event, *args, **kwargs):
        if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
            self.key_down()
            self.need_loop = True
        elif self.is_touched and event.type in [pygame.KEYUP, pygame.MOUSEBUTTONUP]:
            self.key_release()

    def pg_loop_handler(self, *args, **kwargs):
        if self.is_touched and self.check_time(self.last_down_ms, self.release_ms):
            self.key_release()


class TouchRepeat(TouchProxy):
    """
        按压时持续点击
    """

    def __init__(
            self,
            tpa: 'TouchProxyAdapter', touch_type: TouchType, touch_x: float, touch_y: float,
            release_ms: int,
            interval_ms: int,
            *args, **kwargs):
        super().__init__(tpa, touch_type, touch_x, touch_y, *args, **kwargs)
        self.release_ms = release_ms
        self.interval_ms = interval_ms

    def pg_event_handler(self, event: pygame.event.Event, *args, **kwargs):
        if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
            self.key_down()
            self.need_loop = True
        elif event.type in [pygame.KEYUP, pygame.MOUSEBUTTONUP]:
            self.key_release()

    def pg_loop_handler(self, *args, **kwargs):
        if self.need_loop and self.is_pressed:
            if self.is_touched:
                if self.check_time(self.last_down_ms, self.interval_ms):
                    self.touch_release()
            else:
                if self.check_time(self.last_release_ms, self.release_ms):
                    self.touch_down()


class TouchScope(TouchProxy):
    """
        范围映射
    """

    Y_FIX = 0.07

    def __init__(
            self,
            tpa: 'TouchProxyAdapter', touch_type: TouchType, touch_x: float, touch_y: float,
            sc_joystick_r: float,
            pmin: list,
            pmax: list,
            *args, **kwargs):

        super().__init__(tpa, touch_type, touch_x, touch_y, *args, **kwargs)

        self._spr = self.spr

        self.sc_joystick_r = sc_joystick_r

        self.pmin = ScalePoint(*pmin)
        self.pmax = ScalePoint(*pmax)

        self.el_center = ScalePoint(
            (self.pmax.x + self.pmin.x) / 2,
            (self.pmax.y + self.pmin.y) / 2,
        )

        self.y_fix = 0.07
        self.a = (self.pmax.x - self.pmin.x) / 2
        self.b = (self.pmax.y - self.pmin.y) / 2

    def pg_event_handler(self, event: pygame.event.Event, *args, **kwargs):
        if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
            self.spr = self._spr
            self.key_down()
            self.need_move = True
            time.sleep(0.02)
            self.touch_move(self.cal_move_pos(kwargs.get('coord').to_scale_point(*pygame.mouse.get_pos())))

        elif event.type in [pygame.KEYUP, pygame.MOUSEBUTTONUP]:
            self.key_release()

        elif self.need_move and event.type == pygame.MOUSEMOTION:
            self.touch_move(self.cal_move_pos(kwargs.get('mouse_pos')))

    def cal_move_pos(self, mouse_scale_point: ScalePoint) -> ScalePoint:
        # 2024-06-15 17:26:02 TODO Me2sY
        # At least Not Very Precise but tired.
        # 涉及到投影 及空间转换 相机高度等
        # 此处简化处理
        gc_sp = ScalePoint(0.5, 0.5 + self.y_fix)
        ms_sp = mouse_scale_point
        ec_sp = self.el_center

        if ms_sp.y <= gc_sp.y:
            xr = (ms_sp.x - gc_sp.x) / self.a
            yr = (ms_sp.y - gc_sp.y) / (self.b - (ec_sp.y - gc_sp.y))
        else:
            xr = (ms_sp.x - gc_sp.x) / self.a
            yr = (ms_sp.y - gc_sp.y) / (self.b + (ec_sp.y - gc_sp.y))

        x = xr * self.sc_joystick_r
        y = yr * (self.sc_joystick_r * self.frame_coord['width'] / self.frame_coord['height'])

        return self.sp + ScalePoint(x, y)


class TouchCross(TouchProxy):
    """
        十字
    """

    def __init__(
            self,
            tpa: 'TouchProxyAdapter', touch_type: TouchType, touch_x: float, touch_y: float,
            k_up: str,
            k_down: str,
            k_left: str,
            k_right: str,
            up_scale: float,
            sc_joystick_r: float,
            *args, **kwargs):
        super().__init__(tpa, touch_type, touch_x, touch_y, *args, **kwargs)

        self.k_up = KeyMapper.uk2pg(UnifiedKeys.filter_name(k_up))
        self.k_down = KeyMapper.uk2pg(UnifiedKeys.filter_name(k_down))
        self.k_left = KeyMapper.uk2pg(UnifiedKeys.filter_name(k_left))
        self.k_right = KeyMapper.uk2pg(UnifiedKeys.filter_name(k_right))

        self.up_scale = up_scale
        self.sc_joystick_r = sc_joystick_r

        self.x = self.sc_joystick_r
        self.y = self.sc_joystick_r * self.frame_coord['width'] / self.frame_coord['height']

        self.need_loop = True

        self._sp = self.sp
        self._spr = self.spr

        self.up_hold_ms = None

    def pg_event_handler(self, event: pygame.event.Event, *args, **kwargs):
        if event.type == pygame.KEYDOWN:
            self.need_loop = True

    def pg_loop_handler(self, *args, **kwargs):
        pressed_key = pygame.key.get_pressed()

        up = pressed_key[self.k_up]
        down = pressed_key[self.k_down]
        left = pressed_key[self.k_left]
        right = pressed_key[self.k_right]

        if up or down or left or right:
            if not self.is_pressed:
                self.is_pressed = True
                self.spr = self._spr
                self.touch_down()
                time.sleep(0.05)

            if up and self.up_hold_ms is None:
                self.up_hold_ms = time.time()

            if not up:
                self.up_hold_ms = None

            x = self.sp.x

            if left:
                x -= self.x
            if right:
                x += self.x

            y = self.sp.y
            if up:
                y -= (
                    self.y if self.up_hold_ms is None else
                    self.y * self.up_scale if self.check_time(self.up_hold_ms, 800) else
                    self.y
                )
            if down:
                y += self.y

            if up and down:
                y = self.sp.y

            self.touch_move(ScalePoint(x, y))

        else:
            if self.is_pressed:
                self.key_release()
                self.sp = self._sp
                self.spr = self._spr
            self.up_hold_ms = None


class TouchAim(TouchProxy):
    """
        视角控制
    """

    def __init__(
            self,
            tpa: 'TouchProxyAdapter',
            touch_type: TouchType, touch_x: float, touch_y: float,
            attack_touch_x: float, attack_touch_y: float, attack_unified_key: UnifiedKey,
            a: float, b: float,
            *args, **kwargs
    ):
        super().__init__(tpa, touch_type, touch_x, touch_y)
        self.a = a
        self.b = b
        self._sp = self.sp
        self._spr = self.spr

        if kwargs.get('fast_attack', True):
            self.attack = self.tpa.register_tp(dict(
                touch_type=TouchType.KEY_REPEAT,
                touch_x=attack_touch_x,
                touch_y=attack_touch_y,
                unified_key=attack_unified_key,
                release_ms=40, interval_ms=10,
                on=False
            ))
        else:
            self.attack = self.tpa.register_tp(dict(
                touch_type=TouchType.KEY_PRESS,
                touch_x=attack_touch_x,
                touch_y=attack_touch_y,
                unified_key=attack_unified_key,
                on=False
            ))

        self.active = False
        self.slow_scale = kwargs.get('slow_scale', 0.2)

    def pg_event_handler(self, event: pygame.event.Event, *args, **kwargs):

        if event.type == pygame.KEYDOWN:
            self.active = not self.active

            pygame.event.set_grab(self.active)
            pygame.mouse.set_visible(not self.active)
            self.need_move = self.active
            self.need_loop = self.active
            self.attack.set_on(self.active)

            if self.active:
                self.tpa.tp_aim = self

                self.tpa.tps[UnifiedKeys.UK_MOUSE_L] = self.attack
                self.sp = self._sp
                self.spr = self._spr
                self.key_down()

                if self.tpa.device.info.is_uhid_supported:
                    self.control.f_uhid_mouse_create()


            else:
                self.tpa.tp_aim = None
                self.tpa.tps[UnifiedKeys.UK_MOUSE_L] = self.tpa.mouse_tp
                self.key_release()
                pygame.mouse.set_pos(self.tpa.coord.to_point(ScalePoint(0.5, 0.5)))

        elif self.active and event.type == pygame.MOUSEMOTION:

            # Press LSHIFT Show UHID Mouse
            uhid_mouse = pygame.key.get_mods() & pygame.KMOD_LSHIFT
            if uhid_mouse and self.tpa.device.info.is_uhid_supported:
                self.attack.set_on(False)
                self.control.f_uhid_mouse_input(
                    event.rel[0], event.rel[1], left_button=pygame.mouse.get_pressed()[0]
                )
                return
            else:
                self.attack.set_on(True)

            slow = pygame.key.get_mods() & pygame.KMOD_LCTRL

            self.sp += ScalePoint(
                event.rel[0] / self.tpa.coord.width * self.a * (self.slow_scale if slow else 1),
                event.rel[1] / self.tpa.coord.height * self.b * (self.slow_scale if slow else 1)
            )

            self.touch_move(self.sp)

            if abs(self.sp.x - self._sp.x) > 0.08 or abs(self.sp.y - self._sp.y) > 0.05:
                self._reset_aim()

    def _reset_aim(self):
        if self.active:
            self.key_release()
            self.sp = self._sp
            self.spr = self._spr
            self.key_down()
            self.need_move = True
            self.need_loop = True

    def pg_loop_handler(self, *args, **kwargs):

        if pygame.key.get_mods() & pygame.KMOD_LSHIFT:
            self.control.f_uhid_mouse_input(
                0, 0, left_button=pygame.mouse.get_pressed()[0]
            )
            return

        # Fix
        # if pygame.mouse.get_pressed()[0]:
        #     self.sp += ScalePoint(0, 0.0002)
        #     self.touch_move(self.sp)

        if self.active and self.check_time(self.last_release_ms, 500):
            self._reset_aim()


class TouchMouse(TouchProxy):
    """
        鼠标触摸
    """

    def __init__(
            self, tpa: 'TouchProxyAdapter',
            touch_type: TouchType, touch_x: float = 0.5, touch_y: float = 0.5,
            *args, **kwargs
    ):
        super().__init__(tpa, touch_type, touch_x, touch_y, *args, **kwargs)
        self.touch_id = 0x413

    def pg_event_handler(self, event: pygame.event.Event, *args, **kwargs):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = self.tpa.coord.to_scale_point(*event.pos)
            self.spr = ScalePointR(*mouse_pos, self._r)
            self.key_down()
            self.need_move = True

        elif event.type == pygame.MOUSEBUTTONUP:
            self.key_release()

        elif self.need_move and event.type == pygame.MOUSEMOTION:
            self.touch_move(kwargs.get('mouse_pos'))


class TouchWatch(TouchProxy):
    """
        观察模式
    """

    def __init__(self, tpa: 'TouchProxyAdapter', touch_type: TouchType, touch_x: float, touch_y: float, *args,
                 **kwargs):

        super().__init__(tpa, touch_type, touch_x, touch_y, *args, **kwargs)
        self._sp = self.sp
        self._spr = self.spr

    def pg_event_handler(self, event: pygame.event.Event, *args, **kwargs):
        if event.type == pygame.KEYDOWN:
            self.spr = self._spr
            self.sp = self._sp
            self.key_down()
            self.need_move = True

            if self.tpa.tp_aim is None:
                if pygame.mouse.get_visible():
                    pygame.mouse.set_visible(False)
                if not pygame.event.get_grab():
                    pygame.event.set_grab(True)
            else:
                self.tpa.tp_aim.active = False

        elif event.type == pygame.KEYUP:
            self.key_release()
            if self.tpa.tp_aim is None:
                if not pygame.mouse.get_visible():
                    pygame.mouse.set_visible(True)
                if pygame.event.get_grab():
                    pygame.event.set_grab(False)
                    pygame.mouse.set_pos(self.tpa.coord.to_point(ScalePoint(0.5, 0.5)))
            else:
                self.tpa.tp_aim.active = True

        elif self.need_move and event.type == pygame.MOUSEMOTION:
            self.sp += ScalePoint(
                event.rel[0] / self.tpa.coord.width * 0.1,
                event.rel[1] / self.tpa.coord.height * 0.1,
            )
            self.touch_move(self.sp)


class TouchProxyAdapter:
    """
        触摸代理适配器
    """

    TOUCH_ID_START = 100
    TOUCH_ID_RANGE = 300

    CLS_REFLECTS = {
        TouchType.KEY_PRESS: TouchPress,
        TouchType.KEY_CLICK: TouchClick,
        TouchType.KEY_REPEAT: TouchRepeat,
        TouchType.KEY_SCOPE: TouchScope,
        TouchType.KEY_AIM: TouchAim,
        TouchType.KEY_WATCH: TouchWatch
    }

    def __init__(self, session: Session, device: AdvDevice, coord: Coordinate, cfg_path: pathlib.Path):
        self.session = session
        self.device = device

        self.tp_ids: Set[int] = set()
        self.cfg_path = cfg_path
        self.coord: Coordinate = coord

        self.mouse_tp = TouchMouse(self, TouchType.MOUSE_TOUCH)

        self.tps = {}
        self.load_cfg()

        self.tp_aim = False

    def load_cfg(self, cfg_path: pathlib.Path | None = None):
        """
            加载配置文件
        :param cfg_path:
        :return:
        """

        if cfg_path:
            self.cfg_path = cfg_path

        self.tp_ids = set()

        for _ in self.tps.values():
            del _

        self.tps = {}

        tpl = CfgHandler.load(self.cfg_path)['touch_proxy']
        for tpd in tpl:
            try:
                self.register_tp(tpd)
            except Exception as e:
                logger.error(f"Register TouchProxy failed: {e}")

        # 配置鼠标左键点击功能
        self.tps[UnifiedKeys.UK_MOUSE_L] = self.mouse_tp

    def register_tp(self, tpd: dict) -> TouchProxy:
        """
            注册 touch proxy
        :param tpd:
        :return:
        """
        tp = None
        touch_type = TouchType(tpd.pop('touch_type'))
        if touch_type in [
            TouchType.KEY_PRESS, TouchType.KEY_CLICK, TouchType.KEY_REPEAT,
            TouchType.KEY_SCOPE, TouchType.KEY_AIM, TouchType.KEY_WATCH
        ]:
            tp = self.CLS_REFLECTS[touch_type](self, touch_type, **tpd)
            self.tps[UnifiedKeys.filter_name(tpd.get('unified_key'))] = tp

        elif touch_type == TouchType.KEY_CROSS:
            tp = TouchCross(self, touch_type, **tpd)
            self.tps[UnifiedKeys.filter_name(tpd.get('k_up'))] = tp
            self.tps[UnifiedKeys.filter_name(tpd.get('k_down'))] = tp
            self.tps[UnifiedKeys.filter_name(tpd.get('k_left'))] = tp
            self.tps[UnifiedKeys.filter_name(tpd.get('k_right'))] = tp

        return tp

    def create_touch_id(self) -> int:
        """
            创建唯一 touch id
        :return:
        """
        while True:
            _id = random.randint(self.TOUCH_ID_START, self.TOUCH_ID_START + self.TOUCH_ID_RANGE)
            if _id not in self.tp_ids and _id not in [0x0413]:
                self.tp_ids.add(_id)
                return _id

    def event_handler(self, event: pygame.event.Event, *args, **kwargs):
        """
            py事件处理器
        :param event:
        :param args:
        :param kwargs:
        :return:
        """
        if event.type in [pygame.KEYDOWN, pygame.KEYUP]:
            uk = KeyMapper.pg2uk(event.key)
            if uk in self.tps:
                _ = self.tps[uk]
                if not _.on:
                    return
                _.pg_event_handler(event, coord=self.coord, *args, **kwargs)

        elif event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]:
            uk = KeyMapper.pg2uk(event.button)
            if uk in self.tps:
                _ = self.tps[uk]
                if not _.on:
                    return
                _.pg_event_handler(event, coord=self.coord, *args, **kwargs)

        elif event.type == pygame.MOUSEMOTION:
            mouse_pos = self.coord.to_scale_point(*event.pos)
            for tp in [_ for _ in self.tps.values() if _.need_move and _.on]:
                try:
                    tp.pg_event_handler(event, mouse_pos=mouse_pos, *args, **kwargs)
                except Exception as e:
                    logger.error(f"Unexpected Move Event Error: {e}")

    def loop_event_handler(self):
        """
            循环事件处理器
        :return:
        """
        for tp in self.tps.values():
            if tp.need_loop:
                try:
                    tp.pg_loop_handler()
                except Exception as e:
                    logger.error(e)
