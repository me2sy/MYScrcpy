# -*- coding: utf-8 -*-
"""
    指示器
    ~~~~~~~~~~~~~~~~~~


    Log:
        2024-07-28 1.0.0 Me2sY  发布初版

        2024-07-10 0.3.2 Me2sY
            新增 KwargsWindow
            用于配置其他参数

        2024-07-07 0.3.1 Me2sY  新增 IndicatorAim, 用于视角控制

        2024-06-30 0.3.0 Me2sY  重构，改用 Locator 统一控制Item Draw 位置

        2024-06-22 0.2.0 Me2sY  重构，改用控件保留相应属性

        2024-06-21 0.1.2 Me2sY  优化结构

        2024-06-20 0.1.1 Me2sY  完成类编写

        2024-06-18 0.1.0 Me2sY  创建，从 TPEditor 中抽离
"""

__author__ = 'Me2sY'
__version__ = '1.0.0'

__all__ = [
    'Locator', 'Indicator',
    'IndicatorFixedCrossLine', 'IndicatorScaleCrossLine',
    'IndicatorTouchPoint', 'IndicatorJoystick',
    'IndicatorScope', 'IndicatorCross',
    'IndicatorAim'
]

import threading
from collections.abc import Iterable
from typing import Set, Callable

import pygame
from loguru import logger

import dearpygui.dearpygui as dpg

from myscrcpy.utils import ScalePoint, Coordinate, Point, Param, UnifiedKey, UnifiedKeyMapper


class Locator:
    """
        定位器，用于控件定位、移动、缩放等
    """
    X_BORDER_N = 1
    Y_BORDER_N = 1

    FIX_WIDTH = Param.INT_LEN_WIN_BORDER * X_BORDER_N
    FIX_HEIGHT = Param.INT_LEN_WIN_BORDER * Y_BORDER_N + Param.INT_LEN_WIN_TITLE_HEIGHT

    def __init__(
            self,
            scale_point: ScalePoint,
            coord: Coordinate,
            fix_point: Point = None
    ):
        """
            定义定位器，定位器控制注册控件坐标位置及转换
        :param scale_point: 比例点
        :param coord: 坐标系
        :param fix_point: 绘制偏移
        """
        self.scale_point = scale_point
        self.coord = coord
        self.fix_point = fix_point if fix_point else Point(self.FIX_WIDTH, self.FIX_HEIGHT)

        self.move_callback = {}

    def register(self, obj, move_callback_method):
        """
            组件注册，统一位置管理
        :param obj: 组件对象
        :param move_callback_method: 组件移动方法
        :return:
        """
        self.move_callback[id(obj)] = move_callback_method

    def unregister(self, obj):
        """
            注销
        :param obj:
        :return:
        """
        try:
            self.move_callback.pop(id(obj))
        except KeyError:
            pass

    def to_item_pos(self, auto_fix: bool = True, fix_point: Point = None) -> Point:
        """
            dpg中 item与draw 起始坐标不同，此函数返回item坐标点
        :param auto_fix:
        :param fix_point:
        :return:
        """
        fix_point = fix_point if fix_point else Point(0, 0)
        if auto_fix:
            fix_point += self.fix_point
        return self.coord.to_point(self.scale_point) + fix_point

    def to_draw_pos(self, fix_point: Point = None) -> Point:
        """
            返回 draw组件坐标点
        :param fix_point:
        :return:
        """
        fix_point = fix_point if fix_point else Point(0, 0)
        return self.coord.to_point(self.scale_point) + fix_point

    def update(
            self,
            new_scale_point: ScalePoint = None,
            new_coordinate: Coordinate = None,
            x: float = None,
            y: float = None,
    ):
        """
            更新所有组件位置
        """
        if new_scale_point:
            self.scale_point = new_scale_point

        if x:
            self.scale_point = ScalePoint(x, self.scale_point.y)

        if y:
            self.scale_point = ScalePoint(self.scale_point.x, y)

        if new_coordinate:
            self.coord = new_coordinate

        _error_keys = []
        for _, method in self.move_callback.items():
            try:
                method(self)
            except SystemError as se:
                logger.error(f"{_}, {method}, {se}")
                _error_keys.append(_)

        for _ in _error_keys:
            self.move_callback.pop(_)

    @property
    def touch_xy(self) -> dict:
        return dict(
            touch_x=self.scale_point.x,
            touch_y=self.scale_point.y
        )


class Indicator:
    """
        指示器
    """

    def __init__(
            self,
            parent: int | str,
            locator: Locator,
            fix_point: Point = None,
            auto_register_to_loc: bool = True,
            *args, **kwargs
    ):
        """
            指示器，用于绘制TouchProxy在界面中位置
        :param parent: 绘制的父控件tag
        :param locator: 定位器
        :param fix_point: 绘制偏移
        :param auto_register_to_loc: 自动注册
        :param args:
        :param kwargs:
        """
        self.parent = parent

        self.alive = True

        self.args = args
        self.kwargs = kwargs

        self.fix_point = fix_point if fix_point else Point(0, 0)

        self.locator = locator
        if auto_register_to_loc:
            self.locator.register(self, self.move)

    @property
    def tags(self) -> Set[str | int]:
        _tags = set()
        for k, v in self.__dict__.items():
            if k.startswith('tag_'):
                if isinstance(v, set):
                    _tags = _tags | v
                else:
                    _tags.add(v)
            elif k.startswith('ind_'):
                _tags = _tags | v.tags
            elif k.startswith('kw_'):
                _tags.add(v.tag)
        return _tags

    @property
    def inds(self) -> Set['Indicator']:
        _inds = set()
        for k, v in self.__dict__.items():
            if k.startswith('ind_'):
                _inds.add(v)
        return _inds

    def delete(self):
        self.alive = False
        self.locator.unregister(self)
        for item in self.tags:
            try:
                dpg.delete_item(item)
            except Exception as e:
                pass

    def draw(self, *args, **kwargs):
        raise NotImplementedError

    def move(self, locator: Locator, *args, **kwargs):
        pass

    def to_value(self, *args, **kwargs) -> dict:
        raise NotImplementedError

    @property
    def d(self) -> dict:
        return {}


class ButtonClose(Indicator):
    """
        Close Button Indicator
        New Item Need to call register method, then control by close button
    """

    def __init__(self, parent: int | str, locator: Locator, *args, **kwargs):
        super().__init__(parent, locator, *args, **kwargs)

        self.tag_btn_close = dpg.generate_uuid()
        self.tag_close = set()
        self.registered_ind = set()

        self.callback = kwargs.get('close_callback', None)

    def register(self, tags):
        if isinstance(tags, set):
            self.tag_close = self.tag_close | tags
        elif isinstance(tags, str) or isinstance(tags, int):
            self.tag_close.add(tags)
        elif isinstance(tags, Indicator) or issubclass(tags, Indicator):
            self.tag_close = self.tag_close | tags.tags
        elif isinstance(tags, Iterable):
            for _ in tags:
                self.register(_)

    def register_indicator(self, obj):
        if isinstance(obj, Indicator) or issubclass(obj, Indicator):
            self.registered_ind.add(obj)
            self.register(obj)

    def draw(self, *args, **kwargs):
        dpg.add_button(
            label='X', tag=self.tag_btn_close, callback=self.delete, small=True,
            parent=self.parent
        )

    def move(self, locator: Locator, *args, **kwargs):
        dpg.configure_item(self.tag_btn_close, pos=locator.to_item_pos(fix_point=self.fix_point))

    def delete(self):
        super().delete()
        for _ in self.registered_ind:
            self.locator.unregister(_)

        if self.callback:
            self.callback()


class ButtonPosition(Indicator):
    """
        Button To set X and Y
    """

    def __init__(self, parent: int | str, locator: Locator, *args, **kwargs):
        super().__init__(parent, locator, *args, **kwargs)

        self.tag_btn_position = dpg.generate_uuid()
        self.tag_x = dpg.generate_uuid()
        self.tag_y = dpg.generate_uuid()
        self.tag_tooltip = dpg.generate_uuid()
        self.tag_txt_tooltip = dpg.generate_uuid()

    @property
    def tooltip_msg(self) -> str:
        _scp = self.locator.to_draw_pos()
        return f"x:{_scp.x:>.0f} y:{_scp.y:>.0f} | {self.locator.coord}"

    def draw(self, *args, **kwargs):
        dpg.add_button(label='xy', tag=self.tag_btn_position, parent=self.parent)
        with dpg.popup(self.tag_btn_position, mousebutton=dpg.mvMouseButton_Left):
            drag_cfg = dict(min_value=0, max_value=1, speed=0.0005, clamped=True)
            dpg.add_drag_float(
                tag=self.tag_x, label='x', default_value=self.locator.scale_point.x, **drag_cfg,
                callback=lambda s, a: self.locator.update(x=a)
            )
            dpg.add_drag_float(
                tag=self.tag_y, label='y', default_value=self.locator.scale_point.y, **drag_cfg,
                callback=lambda s, a: self.locator.update(y=a)
            )
        with dpg.tooltip(self.tag_btn_position, tag=self.tag_tooltip):
            dpg.add_text(self.tooltip_msg, tag=self.tag_txt_tooltip)

    def move(self, locator: Locator, *args, **kwargs):
        dpg.configure_item(self.tag_btn_position, pos=locator.to_item_pos(fix_point=self.fix_point))
        dpg.set_value(self.tag_txt_tooltip, self.tooltip_msg)


class ButtonKeySetter(Indicator):
    """
        Button to set proxy key
        Use pygame to get pygame key code
    """

    def __init__(
            self, parent: int | str, locator: Locator,
            unified_key: UnifiedKey | None = UnifiedKey(-1),
            *args, **kwargs
    ):
        super().__init__(parent, locator, *args, **kwargs)
        self.unified_key = unified_key if unified_key is not None else UnifiedKey(-1)
        self.tag_btn_key = dpg.generate_uuid()

    def set_unified_key(self, unified_key: UnifiedKey):
        self.unified_key = unified_key
        dpg.configure_item(self.tag_btn_key, label=self.unified_key.name)

    def _init_pygame_window(self):
        pygame.init()
        pygame.display.set_mode((340, 50))
        pygame.display.set_caption('Press Any Key to Set KeyCode.')
        run = True
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)
        clock = pygame.time.Clock()
        while run:
            for event in pygame.event.get(
                    [pygame.KEYUP, pygame.MOUSEBUTTONUP]
            ):
                self.unified_key = UnifiedKeyMapper.pg2uk(event.key if event.type == pygame.KEYUP else event.button)
                run = False
                break
            clock.tick(30)
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        pygame.quit()
        self.set_unified_key(self.unified_key)

    def _init_pg_thread(self):
        threading.Thread(target=self._init_pygame_window).start()

    def draw(self):
        dpg.add_button(
            label=self.unified_key.name, tag=self.tag_btn_key, parent=self.parent,
            callback=self._init_pg_thread
        )

    def move(self, locator: Locator, *args, **kwargs):
        dpg.configure_item(self.tag_btn_key, pos=locator.to_item_pos(fix_point=self.fix_point))

    def to_value(self, *args, **kwargs) -> dict:
        return dict(
            unified_key=self.unified_key.value,
        )


class ButtonRadius(Indicator):
    """
        Button To set Radius
    """

    def __init__(
            self, parent: int | str, locator: Locator,
            scale_x_radius: float,
            callback: Callable,
            *args, **kwargs
    ):
        super().__init__(parent, locator, *args, **kwargs)
        self.scale_x_radius = scale_x_radius

        self.tag_btn_radius = dpg.generate_uuid()
        self.tag_dfloat_radius = dpg.generate_uuid()

        self.callback = callback

    @property
    def button_label(self) -> dict:
        return dict(
            label=f"R: <{self.radius}>"
        )

    @property
    def radius(self) -> int:
        return round(self.locator.coord.width * self.scale_x_radius)

    def value_changed(self, sender, app_data):
        self.scale_x_radius = app_data
        self.callback(self.radius)
        dpg.configure_item(self.tag_btn_radius, **self.button_label)

    def draw(self):
        dpg.add_button(**self.button_label, tag=self.tag_btn_radius, parent=self.parent)
        with dpg.popup(self.tag_btn_radius, mousebutton=dpg.mvMouseButton_Left):
            dpg.add_drag_float(
                label='r', max_value=1, min_value=0.001, speed=0.001,
                callback=self.value_changed, default_value=self.scale_x_radius, tag=self.tag_dfloat_radius,
                clamped=True
            )

    def move(self, locator: Locator, *args, **kwargs):
        dpg.configure_item(self.tag_btn_radius, pos=locator.to_item_pos(fix_point=self.fix_point))
        self.value_changed(None, self.scale_x_radius)

    def to_value(self, *args, **kwargs) -> dict:
        return dict(
            radius=self.scale_x_radius,
        )


class ButtonAB(Indicator):
    """
        Button To set Ellipse A and B
    """

    def __init__(
            self, parent: int | str, locator: Locator,
            callback: Callable,
            a: float = 0.25,
            b: float = 0.25,
            *args, **kwargs):
        super().__init__(parent, locator, *args, **kwargs)
        self.callback = callback
        self._a = a
        self._b = b

        self.tag_btn_ab = dpg.generate_uuid()
        self.tag_dfloat_a = dpg.generate_uuid()
        self.tag_dfloat_b = dpg.generate_uuid()

        self.tag_tooltip = dpg.generate_uuid()
        self.tag_txt_tooltip = dpg.generate_uuid()

    @property
    def a(self) -> int:
        return round(self.locator.coord.width * self._a)

    @property
    def b(self) -> int:
        return round(self.locator.coord.height * self._b)

    @property
    def scale_a(self) -> float:
        return self._a

    @property
    def scale_b(self) -> float:
        return self._b

    @property
    def tooltip_text(self) -> str:
        return f"a:{self.a} b:{self.b}"

    def value_changed(self, sender, app_data, user_data):
        if sender:
            self.__setattr__(user_data, app_data)
        self.callback(self.a, self.b)
        dpg.set_value(self.tag_txt_tooltip, self.tooltip_text)

    def draw(self, *args, **kwargs):
        dpg.add_button(label='ab', tag=self.tag_btn_ab, parent=self.parent)
        with dpg.popup(self.tag_btn_ab, mousebutton=dpg.mvMouseButton_Left):
            cfg = dict(
                min_value=self.kwargs.get('min_value', 0.001),
                max_value=self.kwargs.get('max_value', 1.0),
                speed=0.001,
                clamped=True,
            )

            dpg.add_drag_float(
                label='a', **cfg, callback=self.value_changed, default_value=self._a, tag=self.tag_dfloat_a,
                user_data='_a'
            )
            dpg.add_drag_float(
                label='b', **cfg, callback=self.value_changed, default_value=self._b, tag=self.tag_dfloat_b,
                user_data='_b'
            )
        with dpg.tooltip(self.tag_btn_ab, tag=self.tag_tooltip):
            dpg.add_text(self.tooltip_text, tag=self.tag_txt_tooltip)

    def move(self, locator: Locator, *args, **kwargs):
        dpg.configure_item(self.tag_btn_ab, pos=locator.to_item_pos(fix_point=self.fix_point))
        self.value_changed(None, None, None)


class IndicatorFixedCrossLine(Indicator):
    """
        CrossLine Fixed Length
    """

    COLOR_LINE = (255, 0, 0, 150)

    def __init__(
            self,
            parent: int | str, locator: Locator,
            width: int, height: int,
            *args, **kwargs
    ):
        super().__init__(parent, locator, *args, **kwargs)
        self.width = width
        self.height = height

        self.tag_line_x = dpg.generate_uuid()
        self.tag_line_y = dpg.generate_uuid()

    def draw(self, *args, **kwargs):
        _pos = self.locator.to_draw_pos()
        line_cfg = dict(
            parent=self.parent,
            color=kwargs.get('color', self.COLOR_LINE),
            thickness=kwargs.get('thickness', 1),
        )
        # X Line
        dpg.draw_line(
            tag=self.tag_line_x, **line_cfg,
            p1=[_pos.x, _pos.y - self.height // 2],
            p2=[_pos.x, _pos.y + self.height // 2],
        )
        # Y Line
        dpg.draw_line(
            tag=self.tag_line_y, **line_cfg,
            p1=[_pos.x - self.width // 2, _pos.y],
            p2=[_pos.x + self.width // 2, _pos.y]
        )

    def move(self, locator: Locator, *args, **kwargs):
        dpg.delete_item(self.tag_line_x)
        dpg.delete_item(self.tag_line_y)
        self.draw()


class IndicatorScaleCrossLine(Indicator):
    """
        CrossLine Scale
    """

    COLOR_LINE = (255, 0, 0, 150)

    def __init__(
            self,
            parent: int | str, locator: Locator,
            s_width: float, s_height: float,
            *args, **kwargs
    ):
        super().__init__(parent, locator, *args, **kwargs)
        self.s_width = s_width
        self.s_height = s_height

        self.tag_line_x = dpg.generate_uuid()
        self.tag_line_y = dpg.generate_uuid()

    def draw(self, *args, **kwargs):
        _pos = self.locator.to_draw_pos()
        line_cfg = dict(
            parent=self.parent,
            color=kwargs.get('color', self.COLOR_LINE),
            thickness=kwargs.get('thickness', 1),
        )
        # X Line
        dpg.draw_line(
            tag=self.tag_line_x, **line_cfg,
            p1=[_pos.x, _pos.y - self.s_height * self.locator.coord.height // 2],
            p2=[_pos.x, _pos.y + self.s_height * self.locator.coord.height // 2],
        )
        # Y Line
        dpg.draw_line(
            tag=self.tag_line_y, **line_cfg,
            p1=[_pos.x - self.s_width * self.locator.coord.width // 2, _pos.y],
            p2=[_pos.x + self.s_width * self.locator.coord.width // 2, _pos.y]
        )

    def move(self, locator: Locator, *args, **kwargs):
        dpg.delete_item(self.tag_line_x)
        dpg.delete_item(self.tag_line_y)
        self.draw(*args, **kwargs)


class CombinedIndicator(Indicator):

    def update(self, *args, **kwargs):
        self.locator.update(*args, **kwargs)

    @property
    def uk(self) -> UnifiedKey:
        return self.ind_btn_key.unified_key

    @property
    def pos(self) -> Point:
        return self.locator.to_draw_pos()


class KwargsSetter:

    def __init__(self, kwarg_name: str, kwargs, default_value):
        self.kwarg_name = kwarg_name
        self.value = kwargs.get(kwarg_name, default_value)
        self.tag_setter = dpg.generate_uuid()

    def draw(self, parent, *args, **kwargs):
        ...

    @property
    def d(self) -> dict:
        return {
            self.kwarg_name: self.value,
        }


class BoolSetter(KwargsSetter):

    def draw(self, parent, *args, **kwargs):
        def _set_value(sender, app_data):
            self.value = app_data

        dpg.add_checkbox(
            label=self.kwarg_name, default_value=self.value,
            tag=self.tag_setter, parent=parent,
            callback=_set_value,
            **kwargs
        )


class FloatSetter(KwargsSetter):

    def draw(self, parent, *args, **kwargs):
        def _set_value(sender, app_data):
            self.value = app_data

        dpg.add_input_float(
            label=self.kwarg_name, default_value=self.value,
            tag=self.tag_setter, parent=parent,
            callback=_set_value,
            **kwargs
        )


class KwargWindow:
    """
        用于设置 独立值
    """

    WINDOW_DEFAULTS = dict(
        label='Item',
        width=120, pos=[5, 220],
        no_scrollbar=True, no_collapse=True, no_close=True, no_resize=True
    )

    def __init__(self):
        self.tag_win = dpg.generate_uuid()
        self.setters = set()

    def draw(self, **kwargs):
        self.tag_win = kwargs.setdefault('tag', self.tag_win)

        for k, v in self.WINDOW_DEFAULTS.items():
            kwargs.setdefault(k, v)

        with dpg.window(**kwargs):

            dpg.add_text('Kwargs:')

            for _ in self.setters:
                try:
                    _.draw(self.tag)
                except Exception as e:
                    logger.exception(e)

    @property
    def tag(self) -> str | int:
        return self.tag_win

    def register_setter(self, setter: KwargsSetter, draw=False):
        if setter not in self.setters:
            self.setters.add(setter)
            if draw:
                try:
                    setter.draw(self.tag)
                except Exception as e:
                    pass

    @property
    def d(self) -> dict:
        _d = {}
        for _ in self.setters:
            _d.update(_.d)
        return _d


class IndicatorTouchPoint(CombinedIndicator):
    """
        Touch Point Indicator
    """

    COLOR_CENTER_CIRCLE = (0, 255, 0)
    COLOR_CENTER_FILL = (249, 213, 50, 100)
    COLOR_TEXT = (15, 15, 15)

    INDICATOR_RADIUS = 15

    def __init__(
            self, parent: int | str,
            locator: Locator,
            *args, **kwargs
    ):
        super().__init__(parent, locator, *args, **kwargs)

        self.ind_btn_close = ButtonClose(self.parent, self.locator, fix_point=Point(-32, -6), **kwargs)
        self.ind_btn_pos = ButtonPosition(self.parent, self.locator, fix_point=Point(-10, -35))
        self.ind_btn_key = ButtonKeySetter(
            self.parent, self.locator, fix_point=Point(-8, 16), unified_key=kwargs.get('unified_key', UnifiedKey(-1)),
        )
        self.ind_cl = IndicatorFixedCrossLine(
            self.parent, self.locator,
            width=self.INDICATOR_RADIUS, height=self.INDICATOR_RADIUS,
        )

        self.tag_circle_center = dpg.generate_uuid()

        self.ind_btn_close.register_indicator(self.ind_btn_pos)
        self.ind_btn_close.register_indicator(self.ind_btn_key)
        self.ind_btn_close.register_indicator(self.ind_cl)
        self.ind_btn_close.register_indicator(self)

    def draw(self, *args, **kwargs):
        dpg.draw_circle(
            parent=self.parent, tag=self.tag_circle_center,
            center=self.locator.to_draw_pos(), radius=self.INDICATOR_RADIUS, thickness=1,
            color=self.COLOR_CENTER_CIRCLE, fill=self.COLOR_CENTER_FILL
        )
        self.ind_btn_close.draw()
        self.ind_btn_key.draw()
        self.ind_btn_pos.draw()
        self.ind_cl.draw()
        self.locator.update()

    def move(self, locator: Locator, *args, **kwargs):
        super().move(locator)
        dpg.configure_item(self.tag_circle_center, center=self.locator.to_draw_pos())

    def to_value(self, *args, **kwargs) -> dict:
        return {
            **self.locator.touch_xy,
            **self.ind_btn_key.to_value(),
        }


class IndicatorJoystick(IndicatorTouchPoint):
    COLOR_EDGE = (0, 255, 0)
    COLOR_FILL = (1, 1, 1, 30)

    def __init__(
            self,
            parent: int | str, locator: Locator,
            sc_joystick_r: float = 0.05,
            *args, **kwargs):
        super().__init__(parent, locator, *args, **kwargs)

        self.tag_circle_edge = dpg.generate_uuid()

        self.ind_btn_r = ButtonRadius(
            parent, locator, sc_joystick_r, callback=self.r_changed,
            fix_point=Point(30, -6)
        )

        self.ind_btn_close.register_indicator(self.ind_btn_r)
        self.ind_btn_close.register_indicator(self)

    def r_changed(self, radius: int):
        dpg.configure_item(self.tag_circle_edge, radius=radius)

    def draw(self, *args, **kwargs):
        dpg.draw_circle(
            parent=self.parent, tag=self.tag_circle_edge,
            center=self.locator.to_draw_pos(), radius=self.ind_btn_r.radius,
            color=self.COLOR_EDGE, fill=self.COLOR_FILL
        )
        self.ind_btn_r.draw()
        super().draw(*args, **kwargs)

    def move(self, locator: Locator, *args, **kwargs):
        super().move(locator)
        dpg.configure_item(self.tag_circle_edge, center=self.locator.to_draw_pos())

    def to_value(self, *args, **kwargs) -> dict:
        d = super().to_value()
        d.update({
            'sc_joystick_r': self.ind_btn_r.scale_x_radius,
        })
        return d


class IndicatorEllipse(CombinedIndicator):
    COLOR_ELLIPSE = (255, 150, 0)
    COLOR_E_FILL = (239, 239, 239, 30)

    def __init__(self,
                 parent: int | str, locator: Locator,
                 a: float = 0.25, b: float = 0.25,
                 *args, **kwargs):
        super().__init__(parent, locator, *args, **kwargs)

        self.ind_btn_position = ButtonPosition(parent, locator, fix_point=Point(-10, -35))
        self.ind_btn_ab = ButtonAB(parent, locator, fix_point=Point(30, -6), callback=self.ab_changed, a=a, b=b)
        self.ind_cl = IndicatorFixedCrossLine(parent, locator, 15, 15)

        self.tag_ellipse = dpg.generate_uuid()

    def ab_changed(self, a, b):
        dpg.configure_item(
            self.tag_ellipse,
            **self.to_ellipse_points(
                self.locator.to_draw_pos(), a, b
            )
        )

    @staticmethod
    def to_ellipse_points(position: Point, a: int, b: int) -> dict:
        return {
            'pmin': Point(position.x - a, position.y - b),
            'pmax': Point(position.x + a, position.y + b),
        }

    def draw(self, *args, **kwargs):
        dpg.draw_ellipse(
            parent=self.parent, tag=self.tag_ellipse,
            **self.to_ellipse_points(
                self.locator.to_draw_pos(),
                self.ind_btn_ab.a, self.ind_btn_ab.b
            ),
            color=self.COLOR_ELLIPSE, fill=self.COLOR_E_FILL
        )
        self.ind_btn_ab.draw()
        self.ind_btn_position.draw()
        self.ind_cl.draw()

        self.locator.update()

    def move(self, locator: Locator, *args, **kwargs):
        dpg.configure_item(
            self.tag_ellipse,
            **self.to_ellipse_points(
                self.locator.to_draw_pos(), self.ind_btn_ab.a, self.ind_btn_ab.b
            )
        )

    def to_value(self, *args, **kwargs) -> dict:
        return {
            'pmin': [
                self.locator.scale_point.x - self.ind_btn_ab._a,
                self.locator.scale_point.y - self.ind_btn_ab._b,
            ],
            'pmax': [
                self.locator.scale_point.x + self.ind_btn_ab._a,
                self.locator.scale_point.y + self.ind_btn_ab._b,
            ]
        }


class IndicatorScope(IndicatorJoystick):
    """
        Scope Indicator
    """

    def __init__(
            self, parent: int | str, locator: Locator,
            e_locator: Locator, a: float = 0.25, b: float = 0.25,
            *args, **kwargs):
        super().__init__(parent, locator, *args, **kwargs)

        self.ind_ellipse = IndicatorEllipse(parent, e_locator, a, b)

        for ind in self.ind_ellipse.inds:
            self.ind_btn_close.register_indicator(ind)
        self.ind_btn_close.register_indicator(self.ind_ellipse)

    def draw(self, *args, **kwargs):
        super().draw(*args, **kwargs)
        self.ind_ellipse.draw()

    def update(self, *args, **kwargs):
        self.locator.update(*args, **kwargs)
        self.ind_ellipse.locator.update(*args, **kwargs)

    def to_value(self, *args, **kwargs) -> dict:
        d = super().to_value()
        d.update({
            **self.ind_ellipse.to_value()
        })
        return d


class IndicatorCross(CombinedIndicator):

    def __init__(
            self, parent: int | str, locator: Locator,
            sc_joystick_r: float = 0.05,
            k_up: UnifiedKey = UnifiedKey(UnifiedKey.W.value),
            k_down: UnifiedKey = UnifiedKey(UnifiedKey.S.value),
            k_left: UnifiedKey = UnifiedKey(UnifiedKey.A.value),
            k_right: UnifiedKey = UnifiedKey(UnifiedKey.D.value),
            up_scale: float = 1.0,
            *args, **kwargs
    ):
        super().__init__(parent, locator, *args, **kwargs)

        self.ind_btn_close = ButtonClose(self.parent, self.locator, fix_point=Point(-25, -6), **kwargs)
        self.ind_btn_pos = ButtonPosition(self.parent, self.locator, fix_point=Point(5, -6))
        self.ind_cl = IndicatorFixedCrossLine(
            self.parent, self.locator,
            width=15, height=15,
        )
        self.ind_btn_r = ButtonRadius(
            self.parent, self.locator, sc_joystick_r, self.r_changed, fix_point=Point(35, 25)
        )
        self.ind_btn_k_up = ButtonKeySetter(
            self.parent, locator, fix_point=Point(-8, -60), unified_key=k_up
        )
        self.ind_btn_k_down = ButtonKeySetter(
            self.parent, locator, fix_point=Point(-8, 40), unified_key=k_down
        )
        self.ind_btn_k_left = ButtonKeySetter(
            self.parent, locator, fix_point=Point(-55, -8), unified_key=k_left
        )
        self.ind_btn_k_right = ButtonKeySetter(
            self.parent, locator, fix_point=Point(40, -8), unified_key=k_right
        )

        self.tag_circle_edge = dpg.generate_uuid()
        self.tag_line_scale = dpg.generate_uuid()
        self.tag_ipt_up_scale = dpg.generate_uuid()

        self.up_scale = up_scale

        self.ind_btn_close.register_indicator(self.ind_btn_r)
        self.ind_btn_close.register_indicator(self.ind_btn_pos)
        self.ind_btn_close.register_indicator(self.ind_cl)
        self.ind_btn_close.register_indicator(self.ind_btn_k_up)
        self.ind_btn_close.register_indicator(self.ind_btn_k_down)
        self.ind_btn_close.register_indicator(self.ind_btn_k_left)
        self.ind_btn_close.register_indicator(self.ind_btn_k_right)
        self.ind_btn_close.register_indicator(self)

    def r_changed(self, radius):
        dpg.configure_item(self.tag_circle_edge, radius=radius)
        self.scale_changed(None, self.up_scale)

    def scale_changed(self, sender, app_data):
        self.up_scale = app_data
        _pos = self.locator.to_draw_pos()
        dpg.configure_item(
            self.tag_line_scale,
            p1=_pos, p2=_pos + Point(0, -round(self.ind_btn_r.radius * self.up_scale)),
        )

    def draw(self, *args, **kwargs):
        _pos = self.locator.to_draw_pos()

        self.ind_btn_close.draw()
        self.ind_btn_pos.draw()
        self.ind_btn_r.draw()
        self.ind_btn_k_up.draw()
        self.ind_btn_k_down.draw()
        self.ind_btn_k_left.draw()
        self.ind_btn_k_right.draw()
        self.ind_cl.draw()

        dpg.add_input_float(
            parent=self.parent, tag=self.tag_ipt_up_scale,
            default_value=self.up_scale, min_value=1.0, max_value=5.0,
            callback=self.scale_changed, width=100, step=0.02, step_fast=0.1
        )

        dpg.draw_circle(
            parent=self.parent, tag=self.tag_circle_edge,
            center=_pos, radius=self.ind_btn_r.radius,
            color=[255, 0, 0, 200]
        )

        dpg.draw_line(
            parent=self.parent, tag=self.tag_line_scale,
            p1=_pos, p2=_pos + Point(0, -round(self.ind_btn_r.radius * self.up_scale)),
            color=(255, 150, 50, 50), thickness=3
        )

        self.locator.update()

    def move(self, locator: Locator, *args, **kwargs):
        _pos = self.locator.to_draw_pos()

        dpg.configure_item(
            self.tag_circle_edge,
            center=_pos, radius=self.ind_btn_r.radius,
        )

        dpg.configure_item(
            self.tag_line_scale,
            p1=_pos, p2=_pos + Point(0, -round(self.ind_btn_r.radius * self.up_scale)),
        )

        dpg.configure_item(
            self.tag_ipt_up_scale,
            pos=self.locator.to_item_pos(fix_point=Point(35, -30))
        )

    def to_value(self, *args, **kwargs) -> dict:
        return {
            **self.locator.touch_xy,
            'k_up': self.ind_btn_k_up.unified_key.value,
            'k_down': self.ind_btn_k_down.unified_key.value,
            'k_left': self.ind_btn_k_left.unified_key.value,
            'k_right': self.ind_btn_k_right.unified_key.value,
            'up_scale': round(self.up_scale, 6),
            'sc_joystick_r': round(self.ind_btn_r.scale_x_radius, 6),
        }


class IndicatorAim(IndicatorTouchPoint):
    """
        Aim Indicator
    """

    def __init__(
            self,
            parent: int | str,
            locator: Locator,
            aim_locator: Locator,
            a: float = 0.1, b: float = 0.1,
            attack_unified_key: UnifiedKey = UnifiedKey.M_LEFT,
            *args, **kwargs
    ):
        super().__init__(parent, locator, *args, **kwargs)

        self.ind_attack = IndicatorTouchPoint(parent, aim_locator, unified_key=attack_unified_key)
        self.ind_btn_ab = ButtonAB(
            parent, locator, callback=self.ab_changed, a=a, b=b, fix_point=Point(20, -8),
        )

        self.ind_btn_close.register_indicator(self.ind_attack)
        self.ind_btn_close.register_indicator(self.ind_btn_ab)
        self.ind_btn_close.register_indicator(self)

        self.kw_win = KwargWindow()

        self.kw_win.register_setter(BoolSetter('fast_attack', kwargs, True))
        self.kw_win.register_setter(FloatSetter('slow_scale', kwargs, 0.2))

        self.ind_btn_close.register(self)

    def ab_changed(self, a, b):
        pass

    def draw(self, *args, **kwargs):
        self.ind_btn_ab.draw()
        self.ind_attack.draw()
        super().draw(*args, **kwargs)
        self.kw_win.draw(label='Aim Settings')

    def update(self, *args, **kwargs):
        self.locator.update(*args, **kwargs)
        self.ind_attack.locator.update(*args, **kwargs)

    def to_value(self, *args, **kwargs) -> dict:
        d = super().to_value()

        attack = self.ind_attack.to_value()

        d.update({
            **{
                'attack_touch_x': attack['touch_x'],
                'attack_touch_y': attack['touch_y'],
                'attack_unified_key': attack['unified_key'],
                'a': self.ind_btn_ab.scale_a,
                'b': self.ind_btn_ab.scale_b,
            },
            **self.kw_win.d
        })

        return d
