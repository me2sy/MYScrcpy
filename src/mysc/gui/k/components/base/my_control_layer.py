# -*- coding: utf-8 -*-
"""
    my_control_layer
    ~~~~~~~~~~~~~~~~~~
    
    Log:
        2026-02-12 0.1.0 Me2sY 创建
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = ['ControlLayer']

from functools import wraps
from typing import ClassVar, Optional, Callable

from kivy.core.window import Window
from kivy.graphics import Color, Line
from kivy.input.providers.mouse import MouseMotionEvent
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import MDDialog, MDDialogHeadlineText, MDDialogContentContainer, MDDialogButtonContainer
from kivymd.uix.divider import MDDivider
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.relativelayout import MDRelativeLayout
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
from kivymd.uix.widget import MDWidget

from mysc.core.control import ControlAdapter
from mysc.core.device import MYDevice
from mysc.gui.k import KeyMapper
from mysc.gui.k.components.base.my_proxy import ProxyGroup, EnumMode, JSProxyGroup, ProxyDict
from mysc.gui.k.components.base.my_snack_bar import MYSnackBarError, MYSnackBarSuccess, MYSnackBarInfo
from mysc.gui.k.components.controller.keyboard import MYKeyboardController, ActionCallback
from mysc.gui.k.components.controller.mouse import MYMouseController
from mysc.gui.k.defs import CombineColors, init_language
from mysc.utils.keys import UnifiedKey, UnifiedKeys, EnumAction
from mysc.utils.vector import ScalePointR

_ = init_language()


class MYDialogName(MDDialog):
    """
        新建/编辑 对话框
    """
    def __init__(
            self,
            cb__confirm: Callable[[str], None],
            default_name: Optional[str] = None,
            **kwargs
    ):
        super().__init__(**kwargs)

        self.cb__confirm = cb__confirm

        if default_name:
            self.add_widget(MDDialogHeadlineText(text=_('Changed Name')))
        else:
            self.add_widget(MDDialogHeadlineText(text=_('New Proxy Group')))

        self.widget_name = MDTextField(
            MDTextFieldHintText(text=_('File Name')),
            text='' if default_name is None else default_name,
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            multiline=False, mode='filled'
        )

        self.add_widget(MDDialogContentContainer(
            MDDivider(),
            self.widget_name,
            orientation='vertical'
        ))
        self.widget_btn_create = MDButton(
            MDButtonText(text=_('Confirm')),
            on_release = self._confirm, style='text'
        )
        self.add_widget(MDDialogButtonContainer(
            MDWidget(),
            MDButton(
                MDButtonText(text=_('Close')),
                on_release=self.dismiss, style='text'
            ),
            self.widget_btn_create
        ))

    def _confirm(self, *args):
        """
            确认回调
        :param args:
        :return:
        """
        self.dismiss()
        if self.widget_name.text != '':
            self.cb__confirm(self.widget_name.text)


class ControlLayer(MDRelativeLayout):
    """
        控制层
    """

    MouseUKMap: ClassVar[dict[str, UnifiedKey]] = {
        'left': UnifiedKeys.UK_MOUSE_L,
        'right': UnifiedKeys.UK_MOUSE_R,
        'scrollup': UnifiedKeys.UK_MOUSE_WHEEL_UP,
        'scrolldown': UnifiedKeys.UK_MOUSE_WHEEL_DOWN,
        'middle': UnifiedKeys.UK_MOUSE_WHEEL
    }

    @property
    def proxy_group_cfgs(self) -> dict[str, JSProxyGroup]:
        """
            所有配置文件
        :return:
        """
        return {_cfg.save_key: _cfg for _cfg in JSProxyGroup.obj_glob()}

    def __init__(self, screen, **kwargs):
        super().__init__(
            size_hint=(1, 1), pos_hint={'center_x': .5, 'center_y': .5}, **kwargs
        )
        self.screen = screen
        self.nav = self.screen.nav
        self.cb__current_direction = self.screen.get_direction
        self.my_device: MYDevice = self.screen.my_device
        self.ca: ControlAdapter = self.screen.sess.ca
        self.is_light = self.my_device.adb_device.is_screen_on()

        self.my_mouse_controller: MYMouseController = MYMouseController(self)
        self.my_keyboard_controller: MYKeyboardController = MYKeyboardController(
            self.my_device, screen.cfg, self.nav, self.ca, self.cb__keyboard_proxy
        )

        self.current_proxy_group: Optional[ProxyGroup] = None

        self.bind(size=self.bind__update_sp, center=self.bind__update_sp)

        self.mode: EnumMode = EnumMode.CONTROL

        self.pressed_keys: set[UnifiedKey] = set()

        # Inspector 模式 hover 轮廓：面板打开时鼠标在屏幕上滑动 → 指针下元素动态描边。
        # 懒初始化，关闭时只是把 alpha 置 0；canvas instructions 留着复用。
        self._hover_color: Optional[Color] = None
        self._hover_line: Optional[Line] = None
        self._hover_window_bound: bool = False

    def cb__screen_light(self, caller):
        """
            开启/关闭屏幕显示
        :param caller:
        :return:
        """
        self.ca.f_set_screen(self.is_light)
        self.is_light = not self.is_light

    def bind__update_sp(self, *args):
        """
            Size Position 回调
        :return:
        """
        if self.current_proxy_group is None: return

        # 更新位置
        current_direction = self.cb__current_direction()
        for proxy in self.current_proxy_group.proxies:
            proxy.update_pos(self, current_direction)

    def cb__button_menu(self, caller):
        """
            选择、编辑按钮回调
        :param caller:
        :return:
        """
        if self.mode == EnumMode.EDIT:
            menu_items = [
                dict(
                    text=_('Save'), leading_icon='content-save-outline', on_release=lambda *_args:
                    menu.dismiss() or self.current_proxy_group.dump() or MYSnackBarSuccess(_('Saved'))
                ),
                dict(
                    text=_('Exit Edit Mode'), leading_icon='exit-to-app',
                    on_release=lambda *args: menu.dismiss() or self.cb__close_edit_mode()
                ),
            ]

        else:
            menu_items = [
                dict(
                    text=_('Create'), leading_icon='file-plus-outline',
                    on_release=lambda *_args: menu.dismiss() or self.new_proxy_group()
                ),
            ]

            # 当前选定代理组，则显示编辑及删除
            if self.current_proxy_group is not None:
                menu_items.append(dict(
                    text=_('Edit') + f" {self.current_proxy_group.cfg.save_key}", leading_icon='file-edit',
                    on_release=lambda *_args: menu.dismiss() or self.edit_proxy_group(),
                ))
                menu_items.append(dict(
                    text=_('Delete') + f" {self.current_proxy_group.cfg.save_key}", leading_icon='delete',
                    on_release=lambda *_args: menu.dismiss() or self.del_proxy_group(),
                ))

            def load_proxy_group(_cfg):
                pg = ProxyGroup(self, JSProxyGroup.load(_cfg.save_key))
                pg.load(self.cb__current_direction())
                self.switch_proxy_group(pg)

            # 代理列表，点击加载
            for cfg in JSProxyGroup.obj_glob():
                if self.current_proxy_group is not None and cfg.save_key == self.current_proxy_group.cfg.save_key: continue
                menu_items.append(dict(
                    text=cfg.save_key, leading_icon='chevron-right',
                    on_release=lambda *_args, _cfg=cfg: menu.dismiss() or load_proxy_group(_cfg)
                ))

            menu_items.append(dict(
                text=_('Close'), leading_icon='close-circle',
                on_release=lambda *_args: menu.dismiss() or self.switch_proxy_group(),
            ))

        menu = MDDropdownMenu(caller=caller, items=menu_items)
        menu.open()

    def request_keyboard(self):
        """
            请求键盘监听
        :return:
        """
        self._keyboard = Window.request_keyboard(self.keyboard_closed, self)
        self._keyboard.bind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)

    def keyboard_closed(self):
        """
            关闭键盘监听
        :return:
        """
        try:
            self._keyboard.unbind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)
            self._keyboard.release()
        except:
            ...

    def cb__keyboard_proxy(self, my_keyboard_controller: MYKeyboardController, action_callback: ActionCallback):
        """
            虚拟键盘按键 Proxy 模式按键回调
        :param my_keyboard_controller:
        :param action_callback:
        :return:
        """
        if self.current_proxy_group is None: return

        if action_callback.action == EnumAction.DOWN: self.current_proxy_group.on_key_down(
            action_callback.uk, action_callback.modifiers, self.ca
        )
        else: self.current_proxy_group.on_key_up(
            action_callback.uk, action_callback.modifiers, self.ca
        )

    def activate(self):
        """
            激活
        :return:
        """
        self.ca and self.nav.add_main_button('brightness-6', self.cb__screen_light)
        self.nav.add_main_button('arrow-decision', self.cb__button_menu)

        self.request_keyboard()
        self.my_mouse_controller.activate()
        self.my_keyboard_controller.activate()

        # 紧贴 keyboard 主按钮下方 —— 点击 toggle 主界面右侧的页面解析侧栏
        self.eye_btn = self.nav.add_main_button(
            'eye-outline', lambda *_a: self.cb__show_page_parse(),
        )
        self.eye_btn.theme_bg_color = 'Custom'
        self.eye_btn.theme_icon_color = 'Custom'

        # 监听 panel.is_open（BooleanProperty）：状态变 → 立刻同步图标 + 颜色。
        # 这样无论用户从眼睛 / 面板 × / deactivate 关闭都能正确反映。
        panel = getattr(self.screen.main, 'parse_panel', None)
        if panel is not None:
            panel.bind(is_open=self._on_panel_open_changed)
            self._on_panel_open_changed(panel, panel.is_open)

        self.current_proxy_group and self.current_proxy_group.activate()

    def _on_panel_open_changed(self, _panel, is_open: bool) -> None:
        """眼睛按钮：open=填充图标+蓝色高亮，closed=轮廓图标+白色低调。
        同时 toggle 鼠标 hover 轮廓的 Window 监听。"""
        btn = getattr(self, 'eye_btn', None)
        if btn is not None:
            if is_open:
                btn.icon = 'eye'
                btn.md_bg_color = CombineColors.blue.value[0]
                btn.icon_color = CombineColors.blue.value[1]
            else:
                btn.icon = 'eye-outline'
                btn.md_bg_color = CombineColors.white.value[0]
                btn.icon_color = CombineColors.white.value[1]

        if is_open:
            self._enable_hover_outline()
        else:
            self._disable_hover_outline()

    # -------------------- Inspector hover 轮廓 --------------------

    def _ensure_hover_canvas(self) -> None:
        """懒创建 canvas.after 上的 Color + Line。alpha 控制显隐，避免反复增删指令。"""
        if self._hover_line is not None:
            return
        with self.canvas.after:
            self._hover_color = Color(0.10, 0.55, 1.00, 0)
            self._hover_line = Line(rectangle=(0, 0, 0, 0), width=1.5)

    def _enable_hover_outline(self) -> None:
        self._ensure_hover_canvas()
        if not self._hover_window_bound:
            Window.bind(mouse_pos=self._on_inspector_mouse_pos)
            self._hover_window_bound = True

    def _disable_hover_outline(self) -> None:
        if self._hover_window_bound:
            try:
                Window.unbind(mouse_pos=self._on_inspector_mouse_pos)
            except Exception:
                pass
            self._hover_window_bound = False
        if self._hover_color is not None:
            self._hover_color.a = 0

    def _hide_hover(self) -> None:
        if self._hover_color is not None:
            self._hover_color.a = 0

    def _on_inspector_mouse_pos(self, _window, pos) -> None:
        """Window mouse_pos 回调：把指针下元素 bounds 换算回本地坐标，更新 Line 矩形。"""
        panel = self._inspector_panel()
        if panel is None or not getattr(panel, 'is_open', False):
            self._hide_hover()
            return
        if self.width <= 0 or self.height <= 0:
            self._hide_hover()
            return

        # window 坐标 → ControlLayer 本地坐标（self 自身坐标系，左下原点）
        try:
            ox, oy = self.to_window(0, 0)
        except Exception:
            self._hide_hover()
            return
        local_x = pos[0] - ox
        local_y = pos[1] - oy
        if not (0 <= local_x <= self.width and 0 <= local_y <= self.height):
            self._hide_hover()
            return

        # 与 touch2proxy 一致的 spr 换算（y 翻转）
        spr_x = local_x / self.width
        spr_y = 1 - local_y / self.height

        el = panel.find_element_at(spr_x, spr_y)
        bounds = el.get('bounds') if el else None
        if not bounds or len(bounds) < 4:
            self._hide_hover()
            return

        dw = panel.screen_w
        dh = panel.screen_h
        if dw <= 0 or dh <= 0:
            self._hide_hover()
            return

        x1, y1, x2, y2 = bounds
        rx = (x1 / dw) * self.width
        ry = (1 - y2 / dh) * self.height
        rw = max(1.0, ((x2 - x1) / dw) * self.width)
        rh = max(1.0, ((y2 - y1) / dh) * self.height)
        self._hover_line.rectangle = (rx, ry, rw, rh)
        self._hover_color.a = 0.95

    def cb__show_page_parse(self):
        """
            眼睛图标回调：toggle 主界面右侧的页面解析侧栏。

            面板由 Main 持有（self.screen.main.parse_panel），dump + parse + 渲染
            全部在面板内部完成（后台线程 + Clock.schedule_once 回 UI 线程）。
            重复点击眼睛图标、面板内 × 关闭按钮、或离开 VAC 都会收起。
            按钮图标 / 颜色由 _on_panel_open_changed 通过 bind 自动同步。
        """
        panel = getattr(self.screen.main, 'parse_panel', None)
        if panel is None:
            MYSnackBarError('parse_panel_missing')
            return
        panel.toggle(self.my_device)

    def deactivate(self):
        """
            失活
        :return:
        """
        Window.release_keyboard(self.keyboard_closed)
        self.my_mouse_controller.deactivate()
        self.my_keyboard_controller.deactivate()
        self.current_proxy_group and self.current_proxy_group.deactivate()

        # 离开 VAC 时连带收起页面解析侧栏，避免回到列表页时仍占据空间。
        # 同时 unbind 眼睛按钮的状态回调，避免下次 activate 重复绑定。
        panel = getattr(self.screen.main, 'parse_panel', None)
        if panel is not None:
            panel.unbind(is_open=self._on_panel_open_changed)
            panel.close()
        self._disable_hover_outline()
        self.eye_btn = None

    # ------------------------------------------------
    # Proxy Group 相关
    # ------------------------------------------------

    def switch_proxy_group(self, proxy_group: Optional[ProxyGroup] = None):
        """
            切换 Proxy Group
        :param proxy_group:
        :return:
        """
        if self.current_proxy_group:
            self.current_proxy_group.dump()
            self.current_proxy_group.deactivate()
            self.clear_widgets(proxy for proxy in self.current_proxy_group.proxies)

        self.current_proxy_group = proxy_group

        if self.current_proxy_group:
            self.current_proxy_group.activate()

        self.mode = EnumMode.CONTROL

    def new_proxy_group(self):
        """
            创建 Proxy Group
        :return:
        """
        def cb__new(name: str):
            """
                创建新 Proxy Group
            :param name:
            :return:
            """
            if name in self.proxy_group_cfgs:
                MYSnackBarError(f"{name} already exists!")
                return

            self.switch_proxy_group(ProxyGroup(self, JSProxyGroup(save_key=name)))

        MYDialogName(cb__new).open()

    def del_proxy_group(self):
        """
            删除代理组
        :return:
        """
        if self.current_proxy_group:
            cfg = self.current_proxy_group.cfg
            self.switch_proxy_group()
            cfg.delete()

    def edit_proxy_group(self):
        """
            编辑代理组
        :return:
        """
        if self.current_proxy_group is None: return
        if self.mode == EnumMode.EDIT: return

        self.clear_widgets(proxy for proxy in self.current_proxy_group.proxies)

        current_direction = self.cb__current_direction()

        for proxy in self.current_proxy_group.proxies:
            self.add_widget(proxy)
            proxy.update_pos(self, current_direction)

        self.mode = EnumMode.EDIT

        MYSnackBarInfo(_("Edit Mode"))

    def cb__close_edit_mode(self):
        """
            退出编辑模式
        :return:
        """
        self.mode = EnumMode.CONTROL
        self.clear_widgets(proxy for proxy in self.current_proxy_group.proxies)
        self.current_proxy_group.dump()
        self.current_proxy_group.load(self.cb__current_direction())
        self.request_keyboard()

        MYSnackBarInfo(_("Control Mode"))

    def new_menu(self, pos):
        """
            新建菜单
        :param pos:
        :return:
        """
        spr = ScalePointR(
            (pos[0] - self.x) / self.width, 1 - (pos[1] - self.y) / self.height, self.cb__current_direction()
        )

        menu_items = [
            dict(
                text=_('Save') + f" <{self.current_proxy_group.cfg.save_key}>", leading_icon='content-save-outline',
                on_release=lambda *args:
                mdm.dismiss() or self.current_proxy_group.dump() or MYSnackBarSuccess(_('Saved'))
            ),
        ]

        def add_proxy(_cls):
            mdm.dismiss()
            proxy_instance = self.current_proxy_group.add_proxy(_cls, spr)
            self.add_widget(proxy_instance)

        # 遍历控件类型，添加选项
        for proxy_cls in ProxyDict.values():
            menu_items += [
                dict(
                    text=proxy_cls.NAME, leading_icon=proxy_cls.ICON,
                    on_release=lambda *args, bc=proxy_cls: add_proxy(bc)
                )
            ]

        menu_items += [
            dict(
                text=_('Exit Edit Mode'), leading_icon='exit-to-app',
                on_release=lambda *args: mdm.dismiss() or self.cb__close_edit_mode()
            )
        ]

        caller = MDWidget(pos=Window.mouse_pos, size_hint=(None, None), size=(1, 1))
        mdm = MDDropdownMenu(caller=caller, items=menu_items)
        mdm.open()
        del caller


    # ----------------------------------------------------------
    # Signals
    # ----------------------------------------------------------

    def _inspector_panel(self):
        """侧栏 Inspector：打开时屏幕禁控、点击改为选元素。"""
        return getattr(self.screen.main, 'parse_panel', None)

    def _inspector_active(self) -> bool:
        panel = self._inspector_panel()
        return panel is not None and getattr(panel, 'is_open', False)

    @staticmethod
    def touch2proxy(func):
        """
            判断点击在控件内，同时生成SPR
        :param func:
        :return:
        """
        @wraps(func)
        def wrapper(self, touch):
            # 判断在点内
            if func.__name__ == 'on_touch_down' and not self.collide_point(*touch.pos): return None

            # 增加点 SPR 属性
            touch.ud['spr'] = ScalePointR(
                (touch.x - self.pos[0]) / self.width,
                1 - (touch.y - self.pos[1]) / self.height,
                self.cb__current_direction()
            )
            touch.ud['local_pos'] = self.to_local(*touch.pos)

            # Inspector 模式：吃掉所有屏幕触摸，down 时换算 spr → 设备坐标拉
            # 元素树中"包含该点的最深节点"高亮到面板。move/up 不再处理任何控制。
            if self._inspector_active():
                if func.__name__ == 'on_touch_down':
                    self._inspector_panel().select_at(
                        touch.ud['spr'].x, touch.ud['spr'].y,
                    )
                return True

            # 增加鼠标触控控制
            if self.current_proxy_group is None:
                return getattr(self.my_mouse_controller, func.__name__)(touch)

            return func(self, self.MouseUKMap.get(touch.button), touch)

        return wrapper

    @touch2proxy
    def on_touch_down(self, uk: UnifiedKey, touch: MouseMotionEvent):
        """
            触摸按下事件
        :param uk:
        :param touch:
        :return:
        """
        if self.current_proxy_group.on_touch_down(self.mode, uk, touch, self.ca): return True

        # 新建菜单
        if self.mode == EnumMode.EDIT and uk == UnifiedKeys.UK_MOUSE_R:
            self.new_menu(touch.pos)
            return True

        return None

    @touch2proxy
    def on_touch_up(self, uk: UnifiedKey, touch: MouseMotionEvent):
        """
            触摸抬起事件
        :param uk:
        :param touch:
        :return:
        """
        return self.current_proxy_group.on_touch_up(self.mode, uk, touch, self.ca)

    @touch2proxy
    def on_touch_move(self, uk: UnifiedKey,  touch: MouseMotionEvent):
        """
            触摸移动事件
        :param uk:
        :param touch:
        :return:
        """
        return self.current_proxy_group.on_touch_move(self.mode, uk, touch, self.ca)

    @staticmethod
    def key2proxy(func):
        """
            将按键转为 UnifiedKey
        :param func:
        :return:
        """
        @wraps(func)
        def wrapper(self, keyboard, keycode, *args, **kwargs):

            if self.mode == EnumMode.EDIT: return None

            if len(args) > 0:
                modifiers = args[1]
            else:
                modifiers = Window.modifiers

            uk = KeyMapper.ky2uk(keycode[0])

            if func.__name__ == 'on_key_down':
                # 记录按下键
                if uk not in self.pressed_keys: self.pressed_keys.add(uk)

                # 防抖
                # if uk in self.pressed_keys: return None
                # else: self.pressed_keys.add(uk)
            else:
                if uk in self.pressed_keys: self.pressed_keys.remove(uk)

            return getattr(self.my_keyboard_controller, func.__name__)(uk, keycode[0], modifiers)

        return wrapper

    @key2proxy
    def on_key_down(self, uk: UnifiedKey, modifiers):
        """
            按键按下事件
        :param uk:
        :param modifiers:
        :return:
        """
        return self.current_proxy_group.on_key_down(uk, modifiers, self.ca)

    @key2proxy
    def on_key_up(self, uk: UnifiedKey, modifiers):
        """
        按键释放事件
        :param uk:
        :param modifiers:
        :return:
        """
        return self.current_proxy_group.on_key_up(uk, modifiers, self.ca)
