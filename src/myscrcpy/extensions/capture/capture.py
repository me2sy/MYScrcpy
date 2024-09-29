# -*- coding: utf-8 -*-
"""
    截图插件
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-09-29 0.1.2 Me2sY
            1.适配新回调方法，增加条件过滤器
            2.增加调整截图框功能

        2024-09-27 0.1.1 Me2sY
            1.新增 Camera 截图模式
            2.新增 Select 选择截图模式

        2024-09-17 0.1.0 Me2sY 创建，适配 1.6.0 框架体系
"""

__author__ = 'Me2sY'
__version__ = '0.1.2'

__all__ = [
    'Capture'
]

import random
from functools import wraps

import dearpygui.dearpygui as dpg

from myscrcpy.core import AdvDevice, Session, VideoArgs
from myscrcpy.gui.dpg.dpg_extension import *
from myscrcpy.utils import Coordinate, ScalePoint, Point, Action, Param, UnifiedKeys

from .cpm import CPMPreview, CPMImages, CPMSelect


class Capture(DPGExtension):
    """
        截图工具
    """

    MODE_MAGNIFIER = 'magnifier'
    MODE_CUT = 'cut'

    ADJ_MODE_POS = 'pos'
    ADJ_MODE_WH = 'w/h'

    def start(self):
        """
            注册Layer Pad 及 Menu
            初始化参数 绘制界面
        :return:
        """

        self.tag_layer_crossline = self.register_layer()

        self.tag_layer_scale = self.register_layer()

        self.tag_group = dpg.generate_uuid()

        self.tag_handler_io = dpg.generate_uuid()
        self.tag_handler_resize = dpg.generate_uuid()
        self.tag_handler_hover = dpg.generate_uuid()

        self.tag_rect = dpg.generate_uuid()

        self.coord_dl = None

        self.mouse_sp = None
        self.lock_mouse_sp = None
        self.sp_fix = None
        self.cut_img_raw = None
        self.cut_img = None
        self.cut_img_rect = None

        self.adv_device = None
        self.session = None
        self.is_camera = False

        self.path_save = Param.PATH_TEMP
        self.img_drawing = None

        self.cpm_preview = CPMPreview(Coordinate(240, 240))

        self.is_fast_preview = False

        self.cpm_images = CPMImages()

        self.draw_pad()

        with dpg.handler_registry(tag=self.tag_handler_io, show=False):
            dpg.add_mouse_move_handler(callback=self.draw_cross)

    def stop(self):
        """
            清除插件
        :return:
        """
        for _ in [
            self.tag_layer_crossline, self.tag_layer_scale, self.tag_menu, self.tag_pad,
            self.tag_handler_io, self.tag_handler_resize
        ]:
            if _ is not None:
                try:
                    dpg.delete_item(_)
                except Exception:
                    ...

        self.tag_pad = None
        self.tag_menu = None

    def device_connect(self, adv_device: AdvDevice, session: Session):
        """
            设备连接
        :param adv_device:
        :param session:
        :return:
        """
        if not session.is_video_ready:
            return False

        self.adv_device = adv_device
        self.session = session
        self.is_camera = self.session.va.conn.args.video_source == VideoArgs.SOURCE_CAMERA

        dpg.configure_item(self.tag_handler_io, show=True)

        with dpg.item_handler_registry(tag=self.tag_handler_resize):
            dpg.add_item_resize_handler(callback=self.resize_callback)
        dpg.bind_item_handler_registry(self.window.cpm_vc.tag_dl, self.tag_handler_resize)

        self.draw_scale()
        dpg.configure_item(self.tag_layer_scale, show=self.vdi_enabled.get_value())

        self.is_select = False
        self.select : CPMSelect | None = None

    def device_disconnect(self):
        """
            设备断联
        :return:
        """
        self.adv_device = None
        self.session = None
        self.is_camera = False

        if dpg.does_item_exist(self.tag_handler_io):
            dpg.configure_item(self.tag_handler_io, show=False)

        if dpg.does_item_exist(self.tag_handler_resize):
            dpg.delete_item(self.tag_handler_resize)

        dpg.configure_item(self.tag_layer_scale, show=False)
        self.is_select = False
        if self.select:
            self.select.clear()
            self.select = None

    def device_rotation(self, video_coord: Coordinate):
        """
            设备旋转
        :param video_coord:
        :return:
        """
        if self.adv_device:
            device_coord = self.adv_device.coord_device(video_coord.rotation)
            self.vdi_ss_width.configure(max_value=device_coord.width // 2)
            self.vdi_ss_height.configure(max_value=device_coord.height // 2)

    def resize_callback(self):
        """
            若视频大小变化，则重新绘制刻度
        :return:
        """
        self.draw_scale()

    def draw_cross(self):
        """
            绘制十字线
        :return:
        """
        if dpg.does_item_exist(self.tag_layer_crossline):
            dpg.delete_item(self.tag_layer_crossline, children_only=True)

        if self.session is None or self.is_select:
            return

        tag_dl = self.window.cpm_vc.tag_dl

        self.img_sess = self.session.va.get_image()
        self.coord_video = Coordinate(self.img_sess.width, self.img_sess.height)

        if self.vdi_enabled.get_value() and dpg.is_item_hovered(tag_dl):
            x, y = dpg.get_drawing_mouse_pos()
            w, h = dpg.get_item_rect_size(tag_dl)

            self.mouse_sp = ScalePoint(x / w, y / h)

            if self.vdi_lock_rect.get_value():
                if self.lock_mouse_sp is None:
                    self.lock_mouse_sp = self.mouse_sp
            else:
                self.lock_mouse_sp = self.mouse_sp

            self.coord_dl = Coordinate(w, h)

            self.coord_dev = self.adv_device.coord_device(self.coord_dl.rotation)

            dev_point = self.coord_dev.to_point(self.mouse_sp)

            msg = f"x/w:{x:>4.0f}/{w:<4} Dev: {dev_point.x:>4}/{self.coord_dev.width}\n"
            msg += f"y/h:{y:>4.0f}/{h:<4} Dev: {dev_point.y:>4}/{self.coord_dev.height}\n"
            msg += f"Scale:{x/w:>.4f}:{y/h:>.4f}"

            dpg.set_value(self.tag_info, msg)

            color = [
                random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255
            ] if self.vdi_random_color.get_value() else self.vdi_color.get_value()

            if self.vdi_show_cross.get_value():
                dl_cfg = {
                    'color': color,
                    'thickness': self.vdi_thickness.get_value(),
                    'parent': self.tag_layer_crossline
                }

                dpg.draw_line([x, 0], [x, h], **dl_cfg)
                dpg.draw_line([0, y], [w, y], **dl_cfg)

            self.draw_rect(color)
            self.draw_texture()

    def draw_rect(self, color):
        """
            绘制截图指示器
        :param x:
        :param y:
        :param color:
        :param dev_coord:
        :param mouse_sp:
        :return:
        """
        if self.vdi_show_rect.get_value():

            rec_w = self.vdi_ss_width.get_value()
            rec_h = self.vdi_ss_height.get_value()

            if self.vdi_cut_raw.get_value():
                if self.is_camera:
                    ws = rec_w / self.coord_video.width
                    hs = rec_h / self.coord_video.height
                else:
                    ws = rec_w / self.coord_dev.width
                    hs = rec_h / self.coord_dev.height
                pmin = self.coord_dl.to_point(self.lock_mouse_sp + ScalePoint(-ws, -hs))
                pmax = self.coord_dl.to_point(self.lock_mouse_sp + ScalePoint(ws, hs))

            else:
                mp = self.coord_dl.to_point(self.lock_mouse_sp)
                pmin = Point(mp.x - rec_w, mp.y - rec_h)
                pmax = Point(mp.x + rec_w, mp.y + rec_h)

            dpg.does_item_exist(self.tag_rect) and dpg.delete_item(self.tag_rect)
            dpg.draw_rectangle(pmin, pmax, parent=self.tag_layer_crossline, thickness=1, color=color, tag=self.tag_rect)

    def draw_texture(self):
        """
            绘制预览图像
        :return:
        """

        length = 240

        # 放大镜模式
        if self.vdi_mode.get_value() == self.MODE_MAGNIFIER:

            img_p = self.coord_video.to_point(self.mouse_sp)

            half_l = int(length // 2)
            sl = round(length * self.vdi_scale.get_value())
            nl = int(sl // 2 - length // 2)
            nr = int(sl // 2 + length // 2)

            draw_img = self.img_sess.crop([
                (img_p.x - half_l), (img_p.y - half_l), (img_p.x + half_l), (img_p.y + half_l)
            ]).resize(
                (sl, sl)
            ).crop(
                (nl, nl, nr, nr)
            )

        else:
            # 截图模式

            cw = self.vdi_ss_width.get_value()
            ch = self.vdi_ss_height.get_value()

            if self.vdi_cut_raw.get_value():

                if self.is_camera:
                    raw_s = ScalePoint(cw / self.coord_video.width, ch / self.coord_video.height)
                else:
                    raw_s = ScalePoint(cw / self.coord_dev.width, ch / self.coord_dev.height)

                min_p = self.coord_video.to_point(self.lock_mouse_sp - raw_s)
                max_p = self.coord_video.to_point(self.lock_mouse_sp + raw_s)

            else:

                rel_s = ScalePoint(cw / self.coord_dl.width, ch / self.coord_dl.height)

                min_p = self.coord_video.to_point(self.lock_mouse_sp - rel_s)
                max_p = self.coord_video.to_point(self.lock_mouse_sp + rel_s)

            draw_img = self.img_sess.crop([*min_p, *max_p]).resize((cw * 2, ch * 2))

        self.cpm_preview.update(draw_img)

    def enabled(self, sender, app_data, user_data):
        """
            切换开关
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        if not app_data:
            dpg.delete_item(self.tag_layer_crossline, children_only=True)

        dpg.configure_item(self.tag_layer_scale, show=self.vdi_enabled.get_value())

    def draw_pad(self):
        """
            绘制控制面板
        :return:
        """

        # 注册面板空间
        self.register_pad()

        with dpg.group(parent=self.tag_pad, tag=self.tag_group):

            with dpg.group(horizontal=True):
                self.vdi_enabled = VDCheckBox(self, 'Enabled', callback=self.enabled).draw()
                self.vdi_show_cross = VDCheckBox(self, 'ss.show_cross', label='Cross').draw()
                self.vdi_show_rect = VDCheckBox(self, 'ss.show_rect', label='Rect').draw()

            dpg.add_separator()

            self.tag_info = dpg.add_text(default_value='Points Info')

            with dpg.collapsing_header(label='Preview', bullet=True, default_open=True):

                self.cpm_preview.draw_dl_image()

                dpg.add_separator()

                with dpg.group(horizontal=True):

                    self.vdi_scale = VDKnobFloat(self, 'Scale', min_value=1.0, max_value=8.0).draw()

                    with dpg.group():

                        with dpg.group(horizontal=True):
                            self.vdi_cut_raw = VDCheckBox(self, 'ss.cut_raw', label='Raw').draw()
                            with dpg.tooltip(dpg.last_item()):
                                dpg.add_text(f"Cut Raw Image Or on Screen")

                            self.vdi_lock_rect = VDCheckBox(self, 'ss.lock_rect', label='Lock').draw()
                            with dpg.tooltip(dpg.last_item()):
                                dpg.add_text(f"Lock Capture Rect")

                        with dpg.group(horizontal=True):
                            self.vdi_mode = VDCombo(
                                self, 'ss.mode', items=[self.MODE_MAGNIFIER, self.MODE_CUT],
                                label='Mode', width=60
                            ).draw()
                            self.vdi_adj_mode = VDCombo(
                                self, 'ss.adjust_mode', items=[self.ADJ_MODE_POS, self.ADJ_MODE_WH],
                                label='RM', width=60
                            ).draw()
                            with dpg.tooltip(dpg.last_item()):
                                dpg.add_text(f"Adjust Mode(Pos or Width/Height)")
                                dpg.add_text(f"Use W/S/A/D to change pos or width/height. E changed the mode")

                        with dpg.group(horizontal=True):
                            cfg = {
                                'width': 60,
                                'min_value': 1,
                                'max_value': 9999,
                            }
                            self.vdi_ss_width = VDDragInt(self, 'ss.width', label='w/2', **cfg).draw()
                            self.vdi_ss_height = VDDragInt(self, 'ss.height', label='h/2', **cfg).draw()

                with dpg.tree_node(label='draw details'):
                    with dpg.group(horizontal=True):
                        self.vdi_random_color = VDCheckBox(
                            self, 'color.random', 'RC'
                        ).draw()
                        with dpg.tooltip(dpg.last_item()):
                            dpg.add_text(f"Random Color")

                        self.vdi_thickness = VDSliderInt(
                            self, 'Thickness', min_value=1, max_value=10, width=100
                        ).draw()
                    self.vdi_color = VDColorPicker(
                        self, 'color.cross', no_side_preview=True, width=210, alpha_bar=True,
                    ).draw()

            self.cpm_images.draw()

    def draw_scale(self):
        """
            绘制刻度
        :return:
        """
        if dpg.does_item_exist(self.tag_layer_scale):
            dpg.delete_item(self.tag_layer_scale, children_only=True)

        w, h = dpg.get_item_rect_size(self.window.cpm_vc.tag_dl)

        cfg = {
            'color': [252, 85, 49, 200],
            'parent': self.tag_layer_scale,
            'thickness': 1
        }

        length = 30

        points = [
            # V
            {'p1': [w // 2, 0], 'p2': [w // 2, length]},
            {'p1': [w // 2, h // 2 - length], 'p2': [w // 2, h // 2 + length]},
            {'p1': [w // 2, h], 'p2': [w // 2, h - length]},

            # H
            {'p1': [0, h // 2], 'p2': [length, h // 2]},
            {'p1': [w // 2 - length, h // 2], 'p2': [w // 2 + length, h // 2]},
            {'p1': [w, h // 2], 'p2': [w - length, h // 2]},
        ]

        for _ in points:
            dpg.draw_line(**_, **cfg)

    @staticmethod
    def filter_ready(func):
        """
            确定当前状态
        :param func:
        :return:
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            if args[0].vdi_enabled() and args[0].window.cpm_vc.is_hovered():
                return func(*args, **kwargs)
        return wrapper

    @DPGExtension.CallbackActionFilter(Action.DOWN, need_first_signal=True)
    def callback_key_switch(self, acp: ActionCallbackParam):
        """
            开关
        :param acp:
        :return:
        """
        status = self.vdi_enabled.switch(callback=True)
        self.show_message(f"Capture > {'Enabled' if status else 'Disabled'}")
        if not status and self.is_select:
            self.is_select = False
            if self.select:
                self.select.clear()
                self.select = None
            self.release_mouse_control()

    def screen_shot(self):
        """
            截图
        :return:
        """

        if self.is_select:
            return

        w = self.vdi_ss_width.get_value()
        h = self.vdi_ss_height.get_value()

        # 2024-09-27 0.1.1 Me2sY  获取摄像头数据
        if self.is_camera:
            self.cut_img_raw = self.session.va.get_image()
        else:
            self.cut_img_raw = self.adv_device.u2d.screenshot()

        coord_cut = Coordinate(self.cut_img_raw.width, self.cut_img_raw.height)

        if self.vdi_cut_raw.get_value():

            if self.is_camera:
                sp = ScalePoint(w / coord_cut.width, h / coord_cut.height)
                ulp = self.lock_mouse_sp - sp
                drp = self.lock_mouse_sp + sp
                img = self.cut_img_raw.crop([*coord_cut.to_point(ulp), *coord_cut.to_point(drp)])
            else:
                mouse_p = coord_cut.to_point(self.lock_mouse_sp)
                img = self.cut_img_raw.crop([mouse_p.x - w, mouse_p.y - h, mouse_p.x + w, mouse_p.y + h])

        else:

            sc = ScalePoint(w / self.coord_dl.width, h / self.coord_dl.height)

            cut_min_p = coord_cut.to_point(self.lock_mouse_sp - sc)
            cut_max_p = coord_cut.to_point(self.lock_mouse_sp + sc)

            img = self.cut_img_raw.crop([*cut_min_p, *cut_max_p])

        if img.width != w * 2 or img.height != h * 2:
            img = img.resize((w * 2, h * 2))

        image_item = self.cpm_images.add_image(img)

        self.show_message(f"Capture > Image {image_item.name} Captured!")

    @DPGExtension.CallbackActionFilter(Action.DOWN)
    @filter_ready
    def callback_key_screenshot(self, acp: ActionCallbackParam):
        """
            截图
        :param acp:
        :return:
        """
        self.lock_mouse_sp and self.screen_shot()

    @DPGExtension.CallbackActionFilter(Action.DOWN, need_first_signal=True)
    @filter_ready
    def callback_key_lock_rect(self, acp: ActionCallbackParam):
        """
            锁定 Rect
        :param acp:
        :return:
        """
        self.show_message(f"Capture > Rect {'Freeze' if self.vdi_lock_rect.switch() else 'Free'}")

    def callback_mg_switch(self):
        """
            Mouse gestures switch callback function
        :return:
        """
        status = self.vdi_enabled.switch(callback=True)
        self.show_message(f"Capture > {'Enabled' if status else 'Disabled'}")

    @DPGExtension.CallbackActionFilter(Action.DOWN, need_first_signal=True)
    @filter_ready
    def callback_key_select(self, acp: ActionCallbackParam):
        """
            切换框选截图模式
        :param acp:
        :return:
        """
        if self.is_select:  # 关闭 select 模式
            self.is_select = False
            self.release_mouse_control()
            if self.select:
                self.select.clear()
        else:
            self.is_select = self.get_mouse_control()
        self.show_message(f"Capture > Select Mode {'Enabled' if self.is_select else 'Disabled'}")

    @DPGExtension.CallbackActionFilter([Action.DOWN, Action.MOVE, Action.RELEASE])
    @filter_ready
    def callback_mouse_handler(self, acp: ActionCallbackParam):
        """
            左键框选截图
        :param acp:
        :return:
        """
        if acp.action == Action.DOWN and acp.uk == UnifiedKeys.UK_MOUSE_L:
            self.select = CPMSelect(self.register_layer(), self.window.is_paused)
            self.window.is_paused = True

        elif acp.action == Action.MOVE and dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
            self.select.draw()

        elif acp.action == Action.RELEASE and acp.uk == UnifiedKeys.UK_MOUSE_L:  # 释放并截图
            self.select_screen_shot(*self.select.get_scale_points())
            self.select.clear()
            self.window.is_paused = self.select.window_pause

    def select_screen_shot(self, sp_start: ScalePoint, sp_end: ScalePoint):
        """
            Select 模式 截图
        :param sp_start:
        :param sp_end:
        :return:
        """
        if self.is_camera:
            cut_img_raw = self.session.va.get_image()
        else:
            cut_img_raw = self.adv_device.u2d.screenshot()

        raw_coord = Coordinate(cut_img_raw.width, cut_img_raw.height)

        s_start = raw_coord.to_point(sp_start)
        s_end = raw_coord.to_point(sp_end)
        ul, dr = Point.to_uldr(s_start, s_end)
        cp = dr - ul
        if cp.x == 0 or cp.y == 0:
            return

        image_item = self.cpm_images.add_image(
            cut_img_raw.crop([*ul, *dr])
        )

        self.show_message(f"Capture > Image {image_item.name} Captured!")

    @DPGExtension.CallbackActionFilter(Action.DOWN, need_first_signal=True)
    @filter_ready
    def callback_key_adjust_mode(self, acp: ActionCallbackParam):
        """
            调整模式
        :param acp:
        :return:
        """
        mode = {
                self.ADJ_MODE_WH: self.ADJ_MODE_POS,
                self.ADJ_MODE_POS: self.ADJ_MODE_WH
        }.get(self.vdi_adj_mode())
        self.vdi_adj_mode(mode)
        self.show_message(f"Capture > Adjust Mode {mode}")

    def adjust_rect(self, move_sp: ScalePoint | None = None):
        """
            调整截图框
        :param move_sp:
        :return:
        """
        self.lock_mouse_sp += (move_sp if move_sp else ScalePoint(0, 0))
        self.draw_rect([random.randrange(0, 255) for _ in range(3)])
        self.draw_texture()

    @DPGExtension.CallbackActionFilter(Action.DOWN)
    @filter_ready
    def callback_key_adjust_up(self, acp: ActionCallbackParam):
        """
            调整选定框 向上 或 增大高度
        :param acp:
        :return:
        """
        if self.is_select:
            if self.select:
                if self.vdi_adj_mode() == self.ADJ_MODE_POS:
                    self.select.adjust(Point(0, -1), Point(0, -1))
                else:
                    self.select.adjust(Point(0, -1), Point(0, 1))
            return
        else:
            _sp = None
            if self.vdi_adj_mode() == self.ADJ_MODE_POS:
                _sp = ScalePoint(0, - 1 / self.coord_dl.height)
            elif self.vdi_adj_mode() == self.ADJ_MODE_WH:
                self.vdi_ss_height(self.vdi_ss_height() + 1)
            self.adjust_rect(_sp)

    @DPGExtension.CallbackActionFilter(Action.DOWN)
    @filter_ready
    def callback_key_adjust_down(self, acp: ActionCallbackParam):
        """
            调整选定框 向下 或 减小高度
        :param acp:
        :return:
        """
        if self.is_select:
            if self.select:
                if self.vdi_adj_mode() == self.ADJ_MODE_POS:
                    self.select.adjust(Point(0, 1), Point(0, 1))
                else:
                    self.select.adjust(Point(0, 1), Point(0, -1))
            return
        else:
            _sp = None
            if self.vdi_adj_mode() == self.ADJ_MODE_POS:
                _sp = ScalePoint(0, 1 / self.coord_dl.height)
            elif self.vdi_adj_mode() == self.ADJ_MODE_WH:
                self.vdi_ss_height(self.vdi_ss_height() - 1)
            self.adjust_rect(_sp)

    @DPGExtension.CallbackActionFilter(Action.DOWN)
    @filter_ready
    def callback_key_adjust_left(self, acp: ActionCallbackParam):
        """
            调整选定框 向左 或 减小宽度
        :param acp:
        :return:
        """
        if self.is_select:
            if self.select:
                if self.vdi_adj_mode() == self.ADJ_MODE_POS:
                    self.select.adjust(Point(-1, 0), Point(-1, 0))
                else:
                    self.select.adjust(Point(1, 0), Point(-1, 0))
            return
        else:
            _sp = None
            if self.vdi_adj_mode() == self.ADJ_MODE_POS:
                _sp = ScalePoint(- 1 / self.coord_dl.width, 0)
            elif self.vdi_adj_mode() == self.ADJ_MODE_WH:
                self.vdi_ss_width(self.vdi_ss_width() - 1)
            self.adjust_rect(_sp)

    @DPGExtension.CallbackActionFilter(Action.DOWN)
    @filter_ready
    def callback_key_adjust_right(self, acp: ActionCallbackParam):
        """
            调整选定框 向右 或 增大宽度
        :param acp:
        :return:
        """
        if self.is_select:
            if self.select:
                if self.vdi_adj_mode() == self.ADJ_MODE_POS:
                    self.select.adjust(Point(1, 0), Point(1, 0))
                else:
                    self.select.adjust(Point(-1, 0), Point(1, 0))
            return
        else:
            _sp = None
            if self.vdi_adj_mode() == self.ADJ_MODE_POS:
                _sp = ScalePoint(1 / self.coord_dl.width, 0)
            elif self.vdi_adj_mode() == self.ADJ_MODE_WH:
                self.vdi_ss_width(self.vdi_ss_width() + 1)
            self.adjust_rect(_sp)
