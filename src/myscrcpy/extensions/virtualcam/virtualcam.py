# -*- coding: utf-8 -*-
"""
    虚拟摄像头插件
    ~~~~~~~~~~~~~~~~~~
    
    Log:
        2024-10-14 0.1.2 Me2sY
            1. 支持选择区域
            2. 添加状态提醒及区域显示

        2024-09-29 0.1.1 Me2sY 适配新回调

        2024-09-26 0.1.0 Me2sY 创建
"""

__author__ = 'Me2sY'
__version__ = '0.1.2'

__all__ = ['VirtualCam']

import time

import numpy as np
from loguru import logger
from PIL import Image
import av
import dearpygui.dearpygui as dpg
import pyvirtualcam

from myscrcpy.core import AdvDevice, Session, ExtInfo
from myscrcpy.gui.dpg.dpg_extension import DPGExtension, VDCheckBox, VDCombo, VDDragInt, VDColorPicker
from myscrcpy.gui.dpg.dpg_extension_cls import ActionCallbackParam
from myscrcpy.utils import Coordinate, Action, Point


class VirtualCam(DPGExtension):

    PLATFORM_SUPPORT_VC = {
        dpg.mvPlatform_Windows: ['auto', 'obs', 'unitycapture'],
        dpg.mvPlatform_Linux: ['auto', 'v4l2loopback'],
        dpg.mvPlatform_Apple: ['auto', 'obs']
    }

    def __init__(self, ext_info: ExtInfo, window):
        super().__init__(ext_info, window)
        self.support_vc = self.PLATFORM_SUPPORT_VC[dpg.get_platform()]

        self.support_cv2 = False
        self.trans = {'raw': lambda x: x}
        try:
            import cv2
            from .transform import gray, cartoon, edges
            self.support_cv2 = True

            self.trans.update({
                'gray': gray,
                'cartoon': cartoon,
                'edges': edges
            })

        except ImportError as e:
            logger.info(f"Import error -> {e}")
            logger.warning(f"If you want to transform, CV2 need to be installed!")

        self.camera: pyvirtualcam.Camera | None = None

    def start(self):
        """
            启动
        :return:
        """

        self.session: Session | None = None

        self.coord: Coordinate = Coordinate(-1, -1)
        self.coord_sess: Coordinate = Coordinate(-1, -1)

        self.tag_preview = dpg.generate_uuid()
        self.tag_win_preview = dpg.generate_uuid()

        self.color_bg = (0, 0, 0,)

        self.draw()

    def device_connect(self, adv_device: AdvDevice, session: Session):
        """
            设备连接
        :param adv_device:
        :param session:
        :return:
        """
        self.session: Session = session

        if self.session and self.session.is_video_ready:
            self.coord_session = self.session.va.coordinate
            dpg.configure_item(self.tag_tl_x, max_value=self.coord_session.width)
            dpg.configure_item(self.tag_tl_y, max_value=self.coord_session.height)
            dpg.configure_item(
                self.tag_br_x, max_value=self.coord_session.width, default_value=self.coord_session.width)
            dpg.configure_item(
                self.tag_br_y, max_value=self.coord_session.height, default_value=self.coord_session.height)

            self.draw_info()

    def draw_info(self):

        dpg.delete_item(self.tag_layer, children_only=True)

        if self.camera:
            dpg.draw_text(
                [10, 10], 'Rec Pause' if self.vdi_pause() else 'Rec',
                color=[255, 0, 0, 200],
                parent=self.tag_layer, size=28
            )

        if not self.vdi_rect():
            return

        _cpm_coord = Coordinate(*dpg.get_item_rect_size(dpg.get_item_parent(self.tag_layer)))
        _sess_coord = self.session.va.coordinate

        point_tl, point_br = self.get_tlbr()

        point_tl_draw = _cpm_coord.to_point(_sess_coord.to_scale_point(*point_tl))
        point_br_draw = _cpm_coord.to_point(_sess_coord.to_scale_point(*point_br))

        dpg.draw_rectangle(
            point_tl_draw, point_br_draw, color=[255, 0, 0, 255], parent=self.tag_layer
        )

    def device_disconnect(self):
        """
            设备断联
        :return:
        """
        self.stop_vcam()
        self.session = None

    def stop(self):
        self.stop_vcam()

    def callback_video_frame_update(self, frame: av.VideoFrame, frame_n: int):
        """
            Video Frame 回写驱动Camera画面更新
        :param frame:
        :param frame_n:
        :return:
        """
        if not self.required_video_frame:
            return

        try:
            if self.camera:
                self.draw_info()

                _send_frame = self.convert_camera_frame(frame)

                _coord_camera = Coordinate(self.camera.width, self.camera.height)
                _coord_frame = Coordinate.from_np_shape(_send_frame.shape)
                if _coord_camera == _coord_frame:
                    self.camera.send(_send_frame)

                    if dpg.does_item_exist(self.tag_preview):
                        try:
                            dpg.set_value(self.tag_preview, _send_frame.ravel() / np.float32(255))
                        except:
                            pass
                else:
                    self.required_video_frame = False

                    if _coord_frame == _coord_camera.rotate():
                        if self._start_camera():
                            if dpg.does_item_exist(self.tag_win_preview):
                                dpg.delete_item(self.tag_win_preview)
                                dpg.delete_item(self.tag_preview)
                                self.show_preview()
                            self.required_video_frame = True
                        else:
                            raise RuntimeError('Restart Failed')

        except Exception as e:
            msg = f"Virtual Camera Stop by {e}"
            logger.error(msg)
            self.show_message(msg)
            self.stop_vcam()

    def start_vcam(self):
        """
            开始投射虚拟摄像头
        :return:
        """
        if self._start_camera():
            dpg.configure_item(self.tag_tab_ready, show=False)
            dpg.configure_item(self.tag_tab_running, show=True)
            self.required_video_frame = True

    def get_tlbr(self) -> tuple[Point, Point]:
        """
            获取绘制方框
        :return:
        """
        return Point.to_uldr(
            Point(dpg.get_value(self.tag_tl_x), dpg.get_value(self.tag_tl_y)),
            Point(dpg.get_value(self.tag_br_x), dpg.get_value(self.tag_br_y))
        )

    def _start_camera(self) -> bool:
        """
            主进程
        :return:
        """
        if not self.session or not self.session.is_video_ready:
            self.show_message(f"Video Session Not Ready!")
            return False

        _backend = self.vdi_backend.get_value()
        _backend = None if _backend == 'auto' else _backend

        frame = self.session.va.get_video_frame()

        if self.vdi_raw.get_value():
            point_tl, point_br = self.get_tlbr()
            self.coord = Coordinate(
                point_br.x - point_tl.x, point_br.y - point_tl.y
            )
        else:
            self.coord = Coordinate(self.vdi_width(), self.vdi_height())
        try:
            if self.camera:
                _ = self.camera
                self.camera = None
                _.close()
                time.sleep(1)

            self.camera = pyvirtualcam.Camera(**self.coord.d, fps=self.vdi_fps(), backend=_backend)
            self.callback_video_frame_update(frame, -1)
            self.show_message(f"Virtual Camera Recoding {self.coord.width}x{self.coord.height}")
        except Exception as e:
            logger.warning(f"Create Virtual Camera Error: {e}")
            self.show_message(str(e))
            self.stop_vcam()
            return False

        return True

    def stop_vcam(self):
        """
            结束投射虚拟摄像头
        :return:
        """
        self.required_video_frame = False
        self.camera and self.camera.close()
        self.camera = None

        dpg.does_item_exist(self.tag_preview) and dpg.delete_item(self.tag_preview)
        dpg.does_item_exist(self.tag_win_preview) and dpg.delete_item(self.tag_win_preview)

        dpg.configure_item(self.tag_tab_ready, show=True)
        dpg.configure_item(self.tag_tab_running, show=False)

        self.show_message('Virtual Camera Stop')
        self.draw_info()

    def _fix_scale(self, raw_img: Image.Image) -> np.ndarray:
        """
            将图像缩放至合适
        :return:
        """
        _img = Image.new('RGB', self.coord.t, color=self.color_bg)
        max_coord = Coordinate(raw_img.width, raw_img.height).get_max_coordinate(
            self.coord.width, self.coord.height
        )
        if max_coord != Coordinate(raw_img.width, raw_img.height):
            raw_img = raw_img.resize(max_coord.t)

        _img.paste(
            raw_img,((_img.width - raw_img.width) // 2, (_img.height - raw_img.height) // 2),
        )
        return np.array(_img, dtype='uint8')

    def convert_camera_frame(self, frame: av.VideoFrame) -> np.ndarray:
        """
            适配 Camera Frame
        :return:
        """

        point_tl, point_br = self.get_tlbr()

        _img = frame.to_image().crop([*point_tl, *point_br])

        # 尺寸处理
        if self.vdi_raw():  # 原始输出
            # _np_frame = frame.to_ndarray(format='rgb24')
            _np_frame = np.array(_img)
        else:               # 比例输出
            _np_frame = self._fix_scale(_img)

        # CV2 转换
        return self.cv2_trans(_np_frame)

    def cv2_trans(self, output_frame: np.ndarray) -> np.ndarray:
        """
            cv2 效果转换
        :param output_frame:
        :return:
        """
        if not self.support_cv2:
            return output_frame

        return self.trans.get(self.vdi_trans_mode(), lambda x: x)(output_frame)

    def show_preview(self):
        """
            显示输出预览窗口
        :return:
        """
        if self.camera:
            def stop():
                if dpg.does_item_exist(self.tag_win_preview):
                    dpg.delete_item(self.tag_win_preview)
                if dpg.does_item_exist(self.tag_preview):
                    dpg.delete_item(self.tag_preview)

            with dpg.texture_registry() as tag_texture:
                dpg.add_raw_texture(
                    **self.coord.d, format=dpg.mvFormat_Float_rgb, tag=self.tag_preview,
                    default_value=[]
                )

            with dpg.window(label='Camera Output Preview', no_collapse=True, no_resize=True) as self.tag_win_preview:

                max_coord = self.coord.get_max_coordinate(500, 500)

                dpg.add_image(self.tag_preview, **max_coord.d)
                dpg.add_separator()
                dpg.add_button(label='Close', width=-1, height=35, callback=stop)

            self.callback_video_frame_update(self.session.va.get_video_frame(), -1)

    def pause(self, sender, app_data, user_data):
        """
            暂停
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        self.required_video_frame = not app_data
        dpg.configure_item(user_data, speed=0 if app_data else 1)
        self.show_message(f"Virtual Camera {'Paused' if app_data else 'Continued'}")
        self.draw_info()

    def callback_set_color(self, sender, app_data, user_data):
        """
            设置 背景填充颜色
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        _color = self.vdi_color.get_value()
        self.color_bg = (_color[0], _color[1], _color[2])

    def cb_draw_info(self, sender, app_data, user_data):
        self.draw_info()

    def draw(self):
        """
            绘制界面
        :return:
        """
        self.register_pad()
        self.tag_layer = self.register_layer()

        with dpg.group(parent=self.tag_pad):
            with dpg.tab_bar():

                # Prepare Tab
                with dpg.tab(label='Ready') as self.tag_tab_ready:
                    with dpg.group(horizontal=True):
                        self.vdi_raw = VDCheckBox(self, 'Raw').draw()
                        self.vdi_backend = VDCombo(self, 'Backend', self.support_vc, width=-80).draw()

                    with dpg.group(horizontal=True):
                        self.vdi_width = VDDragInt(self, 'size.width', 'X', width=40).draw()
                        self.vdi_height = VDDragInt(self, 'size.height', '', width=40).draw()
                        self.vdi_fps = VDDragInt(self, 'Fps', width=40).draw()

                    dpg.add_separator()

                    with dpg.group(horizontal=True):
                        dpg.add_text('TL:')
                        with dpg.tooltip(dpg.last_item()):
                            dpg.add_text("Top Left")
                        self.tag_tl_x = dpg.add_drag_int(
                            label='x', min_value=0, width=50, clamped=True, callback=self.cb_draw_info)
                        self.tag_tl_y = dpg.add_drag_int(
                            min_value=0, width=50, clamped=True, callback=self.cb_draw_info)
                        self.vdi_rect = VDCheckBox(self, 'Rect', callback=self.cb_draw_info).draw()

                    with dpg.group(horizontal=True):
                        dpg.add_text('BR:')
                        with dpg.tooltip(dpg.last_item()):
                            dpg.add_text("Bottom Right")
                        self.tag_br_x = dpg.add_drag_int(
                            label='x', min_value=0, width=50, clamped=True, callback=self.cb_draw_info)
                        self.tag_br_y = dpg.add_drag_int(
                            min_value=0, width=50, clamped=True, callback=self.cb_draw_info)

                    dpg.add_button(label='Start', callback=self.start_vcam, width=-1, height=35)

                # Running Tab
                with dpg.tab(label='Running', show=False) as self.tag_tab_running:

                    with dpg.group(horizontal=True):
                        tag_running_indicator = dpg.add_loading_indicator(show=True, color=[255, 0, 0], radius=1)
                        self.vdi_pause = VDCheckBox(
                            self, 'Pause', callback=self.pause, user_data=tag_running_indicator
                        ).draw()
                        self.vdi_trans_mode = VDCombo(
                            self, 'trans.mode', label='Trans',
                            items=list(self.trans.keys()) if self.support_cv2 else ['raw'], width=-40
                        ).draw()

                    with dpg.tree_node(label='Background Color'):
                        self.vdi_color = VDColorPicker(
                            self, 'color.bg', label='', callback=self.callback_set_color,
                            no_side_preview=True, width=210,
                        ).draw()
                        self.callback_set_color(None, None, None)

                    dpg.add_separator()
                    with dpg.group(horizontal=True):
                        dpg.add_button(label='Preview', callback=self.show_preview, width=-80, height=35)
                        dpg.add_button(label='Stop', callback=self.stop_vcam, width=80, height=35)

    @DPGExtension.CallbackActionFilter(need_first_signal=True)
    def callback_key_switch(self, acp: ActionCallbackParam):
        """
            Start / Stop
        :param acp:
        :return:
        """
        if self.camera:
            self.stop_vcam()
        else:
            self.start_vcam()

    @DPGExtension.CallbackActionFilter(need_first_signal=True)
    def callback_key_switch_pause(self, acp: ActionCallbackParam):
        """
            Switch Recording/Pause
        :param acp:
        :return:
        """
        self.vdi_pause(not self.vdi_pause(), callback=True)

    @DPGExtension.CallbackActionFilter([Action.DOWN, Action.RELEASE], need_first_signal=True)
    def callback_key_pause(self, acp: ActionCallbackParam):
        """
            Press then Pause
        :param acp:
        :return:
        """
        if acp.action == Action.DOWN:
            self.vdi_pause(True, callback=True)
        elif acp.action == Action.RELEASE:
            self.vdi_pause(False, callback=True)
