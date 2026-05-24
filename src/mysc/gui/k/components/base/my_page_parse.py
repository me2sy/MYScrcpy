# -*- coding: utf-8 -*-
"""
    my_page_parse
    ~~~~~~~~~~~~~~~~~~

    VAC 屏幕右侧的折叠式页面解析侧栏 + Inspector 模式。

    点击 ControlLayer 上的眼睛图标 → 面板从右侧滑出，显示当前页面
    uiautomator2 dump 出来的原始 hierarchy XML（用 xml.dom.minidom 缩进后）。
    再次点击眼睛、面板内 × 关闭按钮或 close() 调用即收起。

    Inspector 模式（面板打开时）：
      * 屏幕区域（VAC）的触摸不再发到设备控制 —— ControlLayer 在 touch2proxy 入口
        判断 panel.is_open 并拦截，吃掉所有 touch 事件；
      * 在屏幕上点击 → 通过 spr 坐标换算成设备像素坐标 → 在元素树中找到 bounds
        包含该点的最深（面积最小）元素 → 把 TextInput 光标移到 XML 中对应的
        `[x1,y1][x2,y2]` 处，TextInput 自动滚动到该位置。
      * 关闭面板即恢复正常控制。

    实现：作为 Main 横向 BoxLayout 的最后一个子组件，size_hint_x=None，width 在
    0（收起）↔ PANEL_EXPANDED_WIDTH_DP（展开）之间用 Animation 切换。dump + parse
    + minidom 缩进走后台线程，结果回 UI 线程渲染，避免阻塞 GUI。

    XML 解析复用 mysc.mcp_service.server 的 `_parse_to_node` / `_walk_with_ancestors`
    （后者只用于建立"bounds → 元素"索引供 inspector 命中查找），app-agnostic。
"""

__author__ = 'Me2sY'
__version__ = '0.3.0'

__all__ = ['PageParsePanel']

import xml.dom.minidom
from threading import Thread
from typing import Optional

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty
from kivy.uix.textinput import TextInput
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.divider import MDDivider
from kivymd.uix.label import MDLabel

from mysc.gui.k.components.base.my_snack_bar import MYSnackBarInfo, MYSnackBarWarning
from mysc.gui.k.defs import init_language

_ = init_language()


PANEL_EXPANDED_WIDTH_DP = 380
PANEL_ANIM_DURATION = 0.18


class PageParsePanel(MDBoxLayout):
    """
        VAC 旁边的页面解析侧栏。默认宽度为 0（隐形），调用 toggle/open 后展开。

        is_open 用 Kivy BooleanProperty，外部（例如眼睛按钮）可 .bind(is_open=...)
        在状态变化时同步切换图标 / 颜色。
    """

    is_open = BooleanProperty(False)

    def __init__(self, main, **kwargs):
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('size_hint_x', None)
        super().__init__(**kwargs)
        self.main = main
        self.width = 0
        self.padding = dp(8)
        self.spacing = dp(4)

        self._current_serial: Optional[str] = None
        self._screen_w: int = 0
        self._screen_h: int = 0
        # inspector 命中查找用，每项形如 {'depth': int, 'bounds': [x1,y1,x2,y2]}
        self._elements: list[dict] = []
        # 打开面板时把 OS Window 扩宽这么多像素，关闭时缩回，避免 VAC 区域被挤压。
        self._window_grew_px: int = 0

        # 标题栏：Title + 右侧 × 关闭
        title_row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=dp(36), spacing=dp(4),
        )
        title_row.add_widget(MDLabel(
            text=_('Page Parse'), font_style='Title',
            halign='left', valign='middle',
        ))
        title_row.add_widget(MDIconButton(
            icon='refresh', size_hint_x=None,
            on_release=lambda *_a: self.refresh(),
        ))
        title_row.add_widget(MDIconButton(
            icon='close', size_hint_x=None,
            on_release=lambda *_a: self.close(),
        ))
        self.add_widget(title_row)
        self.add_widget(MDDivider())

        # 头部信息
        self.header = MDLabel(
            text='', font_style='Label', halign='left',
            size_hint_y=None, adaptive_height=True,
        )
        self.add_widget(self.header)
        self.add_widget(MDDivider())

        # 原始 XML 视图：只读 TextInput，自带垂直滚动 + 选择/复制。
        self.xml_view = TextInput(
            text='',
            readonly=True,
            multiline=True,
            font_size=sp(11),
            background_color=(0.12, 0.12, 0.12, 1),
            foreground_color=(0.95, 0.95, 0.95, 1),
            cursor_color=(1, 0.55, 0.10, 1),
            selection_color=(1, 0.55, 0.10, 0.4),
            size_hint=(1, 1),
        )
        self.add_widget(self.xml_view)

    # -------------------- 展开 / 收起 --------------------

    def toggle(self, my_device) -> None:
        """眼睛图标点击入口：展开则收起，反之则展开 + 拉解析。"""
        if self.is_open:
            self.close()
        else:
            self.open(my_device)

    def open(self, my_device) -> None:
        if self.is_open:
            return
        self.is_open = True
        self._current_serial = (
            getattr(my_device, 'serial_no', None)
            or getattr(getattr(my_device, 'adb_device', None), 'serial', None)
        )
        self._refresh()

        target = int(dp(PANEL_EXPANDED_WIDTH_DP))
        # 同步加宽 OS Window：面板独占新增宽度，VAC 内容区像素宽度保持不变。
        # 用 main.is_changing_sp 抑制 on_window_resize 把"程序加的宽"误存为用户偏好。
        self._grow_window(target)

        Animation.cancel_all(self, 'width')
        Animation(
            width=target,
            duration=PANEL_ANIM_DURATION, t='out_quad',
        ).start(self)

    def close(self) -> None:
        if not self.is_open:
            return
        self.is_open = False
        Animation.cancel_all(self, 'width')
        # 与 open 对称：先把面板宽度动画到 0，动画结束再把 OS Window 缩回。
        # 之前是动画前立刻 shrink_window，导致 VAC 被瞬间挤窄再随面板动画拉回，
        # 视觉上明显卡顿。
        # 注：用 Clock.schedule_once 而不是 Animation.on_complete —— 后者从动画 tick
        # 内同步触发，里面再改 Window.size 会和当前帧的布局/渲染叠在一起，曾观察到
        # native 层 access violation（0xC0000005）。
        Animation(width=0, duration=PANEL_ANIM_DURATION, t='out_quad').start(self)
        Clock.schedule_once(
            lambda *_a: self._shrink_window(),
            PANEL_ANIM_DURATION + 0.02,
        )

    def _grow_window(self, px: int) -> None:
        if px <= 0:
            return
        self._window_grew_px = px
        was_changing = getattr(self.main, 'is_changing_sp', False)
        self.main.is_changing_sp = True
        try:
            Window.size = (Window.width + px, Window.height)
        finally:
            self.main.is_changing_sp = was_changing

    def _shrink_window(self) -> None:
        if self._window_grew_px <= 0:
            return
        px = self._window_grew_px
        self._window_grew_px = 0
        was_changing = getattr(self.main, 'is_changing_sp', False)
        self.main.is_changing_sp = True
        try:
            Window.size = (max(200, Window.width - px), Window.height)
        finally:
            self.main.is_changing_sp = was_changing

    # -------------------- 解析 / 渲染 --------------------

    def refresh(self) -> None:
        """重新拉一次解析（× 旁边的 refresh 按钮，或外部按需触发）。"""
        if self.is_open and self._current_serial:
            self._refresh()

    def _refresh(self) -> None:
        """
            后台拉 dump_hierarchy 原始 XML + 走 view tree 收集每个节点的 bounds
            （仅用于 inspector 命中），主线程把 minidom 缩进后的 XML 灌进 TextInput。
        """
        serial = self._current_serial
        self.header.text = _('Loading…')
        self.xml_view.text = ''
        self._elements = []

        def _work():
            try:
                from mysc.mcp_service.device import get_device
                from mysc.mcp_service.server import (
                    _parse_to_node, _walk_with_ancestors, _build_page_path,
                )
                d = get_device(serial)
                xml_text, root, wsize = _parse_to_node(d)
                try:
                    cur = d.app_current() or {}
                except Exception:
                    cur = {}

                elements: list[dict] = []
                for node, ancestors in _walk_with_ancestors(root):
                    rect = node.rect
                    if not rect:
                        continue
                    x1, y1 = rect.x, rect.y
                    x2, y2 = x1 + rect.width, y1 + rect.height
                    elements.append({
                        'depth': len(ancestors),
                        'bounds': [x1, y1, x2, y2],
                    })

                # dump_hierarchy 返回的是单行无缩进 XML —— 用 minidom 缩进展示。
                try:
                    dom = xml.dom.minidom.parseString(xml_text)
                    pretty = dom.toprettyxml(indent='  ')
                    # minidom 会插入纯空白文本节点 → 输出大量空行，过滤掉。
                    pretty = '\n'.join(
                        line for line in pretty.splitlines() if line.strip()
                    )
                except Exception:
                    pretty = xml_text

                screen = {
                    'package': cur.get('package', '') or '',
                    'activity': cur.get('activity', '') or '',
                    'page': _build_page_path(cur.get('activity', '') or ''),
                    'width': wsize.width,
                    'height': wsize.height,
                    'elements': elements,
                    'xml': pretty,
                }
            except Exception as ex:
                msg = str(ex)
                Clock.schedule_once(lambda *_a, m=msg: self._render_error(m), 0)
                return
            Clock.schedule_once(lambda *_a, s=screen: self._render(s), 0)

        Thread(target=_work, daemon=True).start()

    def _render_error(self, msg: str) -> None:
        self.header.text = f"[parse_failed]\n{msg}"
        self.xml_view.text = ''
        self._elements = []

    def _render(self, screen: dict) -> None:
        package = screen.get('package') or '?'
        activity = screen.get('activity') or '?'
        page = screen.get('page') or '?'
        elements = screen.get('elements') or []

        self._screen_w = int(screen.get('width') or 0)
        self._screen_h = int(screen.get('height') or 0)
        self._elements = elements

        size_text = f"{self._screen_w or '?'}×{self._screen_h or '?'}"
        self.header.text = (
            f"package: {package}\n"
            f"activity: {activity}\n"
            f"page: {page}\n"
            f"size: {size_text}    nodes: {len(elements)}\n"
            f"{_('Tap on the device screen to inspect elements')}"
        )

        self.xml_view.text = screen.get('xml') or ''
        # 灌完文本把光标拉回开头，避免 TextInput 默认停在末尾。
        self.xml_view.cursor = (0, 0)

    # -------------------- Inspector 选中 --------------------

    @property
    def screen_w(self) -> int:
        return self._screen_w

    @property
    def screen_h(self) -> int:
        return self._screen_h

    def find_element_at(self, spr_x: float, spr_y: float) -> Optional[dict]:
        """
            根据 spr 坐标返回包含该点的最深（面积最小）元素 dict，没命中返 None。
            select_at 的"安静版"：不弹 snackbar、不滚动；供鼠标 hover 高亮使用。
        """
        if not self._elements or self._screen_w <= 0 or self._screen_h <= 0:
            return None
        device_x = spr_x * self._screen_w
        device_y = spr_y * self._screen_h
        best: Optional[dict] = None
        best_area = float('inf')
        best_depth = -1
        for el in self._elements:
            bounds = el.get('bounds')
            if not bounds or len(bounds) < 4:
                continue
            x1, y1, x2, y2 = bounds
            if not (x1 <= device_x <= x2 and y1 <= device_y <= y2):
                continue
            depth = el.get('depth') or 0
            area = max(0, x2 - x1) * max(0, y2 - y1)
            if depth > best_depth or (depth == best_depth and area < best_area):
                best_depth = depth
                best_area = area
                best = el
        return best

    def select_at(self, spr_x: float, spr_y: float) -> bool:
        """
            根据 spr 坐标（VAC 控件相对坐标，0~1）反查最深匹配元素，把 XML 光标
            移到 `[x1,y1][x2,y2]` 处，TextInput 自动把该行滚到可见。
            未渲染、未命中、命中都各发一次 snackbar，方便诊断。
        """
        if not self._elements:
            MYSnackBarWarning('inspector: no elements (still loading?)')
            return False
        if self._screen_w <= 0 or self._screen_h <= 0:
            MYSnackBarWarning('inspector: screen size unknown')
            return False

        device_x = spr_x * self._screen_w
        device_y = spr_y * self._screen_h
        el = self.find_element_at(spr_x, spr_y)
        if el is None:
            MYSnackBarWarning(f'inspector: no element at ({int(device_x)}, {int(device_y)})')
            return False

        bounds = el.get('bounds') or []
        if len(bounds) < 4:
            MYSnackBarInfo('→ matched (no bounds)')
            return True

        x1, y1, x2, y2 = bounds
        needle = f'[{x1},{y1}][{x2},{y2}]'
        # Android dump 中 bounds 一般唯一，find 第一处即对应节点；找不到就只发 snackbar。
        text = self.xml_view.text
        idx = text.find(needle)
        if idx >= 0:
            # 把整个 <node ... bounds="..." .../> 开头标签选中：从 idx 向前找 '<'，
            # 向后找首个 '>'。光标先挪到 start，TextInput 会自动滚到可见，再 select_text
            # 用 selection_color（橙色）高亮整段。
            start = text.rfind('<', 0, idx)
            if start < 0:
                start = idx
            end = text.find('>', idx)
            end = idx + len(needle) if end < 0 else end + 1
            try:
                self.xml_view.cursor = self.xml_view.get_cursor_from_index(start)
                self.xml_view.select_text(start, end)
            except Exception:
                pass
        MYSnackBarInfo(f'→ {needle}')
        return True
