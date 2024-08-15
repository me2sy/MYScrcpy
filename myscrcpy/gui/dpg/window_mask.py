# -*- coding: utf-8 -*-
"""
    Mask Window
    ~~~~~~~~~~~~~~~~~~
    定义控制映射

    Log:
        2024-08-15 1.1.2 Me2sY  修复部分缺陷

        2024-07-31 1.1.1 Me2sY  适配新Controller

        2024-07-28 1.0.0 Me2sY  发布初版

        2024-07-21 0.2.1 Me2sY  新增 TouchWatch 观察按钮

        2024-06-30 0.2.0 Me2sY  重构，变成ScalePoint，实现Resize等功能。

        2024-06-27 0.1.0 Me2sY  创建，实现控制映射配置功能
"""

__author__ = 'Me2sY'
__version__ = '1.1.2'

__all__ = [
    'WindowTwin', 'TouchProxyIndicatorFactory'
]

import pathlib
import time

import dearpygui.dearpygui as dpg
from loguru import logger

from myscrcpy.controller import DeviceController

from myscrcpy.gui.dpg.indicator import *

from myscrcpy.gui.dpg.video_controller import DpgVideoController
from myscrcpy.utils import Coordinate, Point, ScalePoint, UnifiedKey, CfgHandler, Param
from myscrcpy.gui.pg.tp_adapter import TouchType

TWIN_POS = Point(136, 10)


class WindowTwin:
    """
        双生窗口
        底层用于绘制图像
        上层用于绘制指示器
        解决DPG绘制无法重叠问题
    """
    WIN_COORD_FIX = Coordinate(
        Param.INT_LEN_WIN_BORDER * 2,
        Param.INT_LEN_WIN_BORDER * 2 + Param.INT_LEN_WIN_TITLE_HEIGHT,
    )

    def __init__(
            self,
            device: DeviceController,
            on_close=None
    ):
        self.device = device
        self.dvc = DpgVideoController(device)

        self.tag_win_frame = dpg.generate_uuid()
        self.tag_win_mask = dpg.generate_uuid()
        self.tag_win_ctrl = dpg.generate_uuid()

        self.tag_texture_frame = dpg.generate_uuid()
        self.tag_dl_frame = dpg.generate_uuid()
        self.tag_layer_tps = dpg.generate_uuid()
        self.tag_image_frame = dpg.generate_uuid()

        self.tag_mouse_dbc = dpg.generate_uuid()

        self.win_cfg = dict(
            pos=TWIN_POS, no_move=True, no_scrollbar=True, no_collapse=True, no_scroll_with_mouse=True,
            **(self.dvc.coord_draw + self.WIN_COORD_FIX).d
        )

        self.tpi_factory = TouchProxyIndicatorFactory(self, device)

        self.on_close = on_close

    @property
    def win_title(self) -> str:
        return f"TPEditor {self.dvc.coord_draw.width} x {self.dvc.coord_draw.height}"

    def callback_resize(self, sender, app_data):
        w = dpg.get_item_width(self.tag_win_mask)
        h = dpg.get_item_height(self.tag_win_mask)

        self.dvc.resize_handler(
            sender, self.tag_win_mask, {'fix_coord': Coordinate(
                -self.WIN_COORD_FIX.width, -self.WIN_COORD_FIX.height
            )}
        )

        dpg.configure_item(self.tag_win_frame, **Coordinate(w, h).d)
        dpg.configure_item(self.tag_win_mask, label=self.win_title)

        self.tpi_factory.resize(self.dvc.coord_draw)

    def init(self):

        with dpg.window(tag=self.tag_win_frame, **self.win_cfg):
            with dpg.drawlist(**self.dvc.coord_draw.d, tag=self.tag_dl_frame):
                with dpg.draw_layer():
                    self.dvc.draw_image()
                with dpg.draw_layer(tag=self.tag_layer_tps):
                    ...

        def _close():
            dpg.delete_item(self.tag_win_frame)
            dpg.delete_item(self.tag_win_mask)
            dpg.delete_item(self.tpi_factory.tag_win_ctrl)
            if self.on_close:
                self.on_close()

        with dpg.window(
                tag=self.tag_win_mask, label=self.win_title, no_background=True, **self.win_cfg, on_close=_close
        ):
            ...

        with dpg.item_handler_registry() as rs_hr:
            dpg.add_item_resize_handler(callback=self.callback_resize)
        dpg.bind_item_handler_registry(self.tag_win_mask, rs_hr)

        with dpg.handler_registry(tag=self.tag_mouse_dbc):
            dpg.add_mouse_double_click_handler(dpg.mvMouseButton_Left, callback=self.create_item)

    def _get_mouse_point(self) -> None | Point:
        try:
            if not dpg.is_item_hovered(self.tag_win_mask):
                return
        except Exception:
            return

        x, y = dpg.get_mouse_pos(local=True)

        mp = Point(
            x - Param.INT_LEN_WIN_BORDER,
            y - Param.INT_LEN_WIN_BORDER
        )

        if mp.x < 0 or mp.y < 0:
            return

        return mp

    def create_item(self):
        mouse_pos = self._get_mouse_point()
        if mouse_pos is None:
            return None

        self.tpi_factory.create_item(mouse_pos)


MODEL_WIN_CFG = dict(
    modal=True, no_move=True, no_resize=True, no_collapse=True, no_scrollbar=True, no_scroll_with_mouse=True,
    pos=[500, 300]
)


class TouchProxyIndicatorFactory:
    """
        触摸代理工厂类
    """
    def __init__(
            self, win_twin: WindowTwin, device: DeviceController
    ):
        self.win_twin = win_twin
        self.device = device
        self.draw_parent = win_twin.tag_win_mask
        self.draw_coord = win_twin.dvc.coord_draw
        self.indicators = []
        self.keys = set()
        self.editing_indicator = None
        self.editing_cache = None

        self.last_cfg_path = None

        self.tag_win_ctrl = dpg.generate_uuid()
        self.tag_win_choose_type = dpg.generate_uuid()
        self.tag_group_btns = dpg.generate_uuid()

        self.tag_tab = dpg.generate_uuid()
        self.tag_tab_main = dpg.generate_uuid()
        self.tag_tab_edit = dpg.generate_uuid()

        self.tag_txt_cfg = dpg.generate_uuid()

        self.is_editing = False
        self.init_ctrl_panel()

        self.itp = None

    def init_ctrl_panel(self):
        with dpg.window(
                tag=self.tag_win_ctrl, label='Ctrl Panel', pos=Point(4, 10),
                autosize=True, no_move=True, no_resize=True, no_close=True, no_collapse=True
        ):
            btn_cfg = dict(width=100, height=30)

            dpg.add_button(label='Reload', **btn_cfg, callback=self.reload)
            dpg.add_button(label='Resize', **btn_cfg, callback=self.frame_resize)
            dpg.add_separator()

            with dpg.tab_bar(tag=self.tag_tab):
                with dpg.tab(label='main', tag=self.tag_tab_main):
                    dpg.add_text('TPConfig:')
                    dpg.add_text('Load or Create', tag=self.tag_txt_cfg)
                    dpg.add_button(label='Load', **btn_cfg, callback=self.load_cfg)
                    dpg.add_button(label='Save', **btn_cfg, callback=self.save_this)
                    dpg.add_button(label='Save_As', **btn_cfg, callback=self.save_as)
                    dpg.add_separator()
                    dpg.add_button(label='CLEAR', **btn_cfg, callback=lambda: self.clear(True))

                    dpg.add_separator()
                    dpg.add_text('Buttons:')
                    with dpg.group(tag=self.tag_group_btns):
                        pass

                with dpg.tab(label='edit', tag=self.tag_tab_edit, show=False):
                    dpg.add_button(label='Save TP', **btn_cfg, callback=self.save_tp)
                    dpg.add_button(label='Cancel', **btn_cfg, callback=self.cancel)

    def reload(self):
        self.win_twin.dvc.loop()

    def frame_resize(self):
        dpg.set_item_width(self.win_twin.tag_win_mask, self.win_twin.dvc.coord_frame.width)
        dpg.set_item_height(self.win_twin.tag_win_mask, self.win_twin.dvc.coord_frame.height)

    def clear(self, with_confirm: bool = False):
        """
            清空
        :return:
        """

        def _clear():
            self.indicators = []
            self.keys = set()
            self.editing_indicator = None
            self.editing_cache = None
            self.is_editing = False
            self.cancel()
            self.load_tp_buttons()
            self.draw_tps()
            try:
                dpg.delete_item(tag_win_cf)
            except Exception:
                pass

        if with_confirm:
            with dpg.window(**MODEL_WIN_CFG) as tag_win_cf:
                dpg.add_text('Clear?')
                dpg.add_button(label='Confirm', width=-1, height=30, callback=_clear)
        else:
            _clear()

    def draw_tps(self):
        """
            绘制 TP 指示器
        :return:
        """
        dpg.delete_item(self.win_twin.tag_layer_tps, children_only=True)

        for ind_type, ind_obj, kwargs in self.indicators:
            try:
                dpg.draw_circle(
                    ind_obj.pos, 25, color=(255, 0, 0), fill=(246, 246, 246, 100),
                    parent=self.win_twin.tag_layer_tps
                )
                dpg.draw_circle(
                    ind_obj.pos, 2, thickness=1, color=(255, 0, 0), parent=self.win_twin.tag_layer_tps
                )

                txt_cfg = dict(size=18, color=(0, 0, 0), parent=self.win_twin.tag_layer_tps)
                if ind_type == TouchType.KEY_CROSS:

                    d = ind_obj.to_value()
                    dpg.draw_text(ind_obj.pos + Point(-5, -25), UnifiedKey(d['k_up']).name, **txt_cfg)
                    dpg.draw_text(ind_obj.pos + Point(-5, 5), UnifiedKey(d['k_down']).name, **txt_cfg)
                    dpg.draw_text(ind_obj.pos + Point(-18, -10), UnifiedKey(d['k_left']).name, **txt_cfg)
                    dpg.draw_text(ind_obj.pos + Point(9, -10), UnifiedKey(d['k_right']).name, **txt_cfg)

                elif ind_type == TouchType.KEY_AIM:
                    dpg.draw_text(ind_obj.pos + Point(-5, 0), ind_obj.uk.name, **txt_cfg)
                    dpg.draw_text(ind_obj.ind_attack.pos + Point(-5, 5), ind_obj.ind_attack.uk.name, **txt_cfg)
                    dpg.draw_circle(
                        ind_obj.ind_attack.pos, 25, color=(255, 0, 0), fill=(246, 246, 246, 100),
                        parent=self.win_twin.tag_layer_tps
                    )
                    dpg.draw_circle(
                        ind_obj.ind_attack.pos, 2, thickness=1, color=(255, 0, 0),
                        parent=self.win_twin.tag_layer_tps
                    )

                elif ind_type == TouchType.KEY_WATCH:
                    dpg.draw_text(ind_obj.pos + Point(-5, 0), 'W_' + ind_obj.uk.name, **txt_cfg)

                else:
                    dpg.draw_text(ind_obj.pos + Point(-5, 0), ind_obj.uk.name, **txt_cfg)

            except Exception as e:
                logger.error(e)

    def resize(self, new_coord: Coordinate):
        """
            Not Very Precision
        :param new_coord:
        :return:
        """
        for ind_type, ind_obj, kwargs in self.indicators:
            ind_obj.update(new_coordinate=new_coord)

        self.draw_tps()

        if self.is_editing:
            self.editing_indicator[1].update(new_coordinate=new_coord)

    def load_cfg(self):
        """
            加载 Cfg
        :return:
        """

        def _load_file(sender, appdata):
            self.clear()
            path = pathlib.Path(appdata['file_path_name'])
            self.last_cfg_path = path
            cfg = CfgHandler.load(path)['touch_proxy']

            for _ in cfg:
                try:
                    touch_type = TouchType(_.pop('touch_type'))
                    if touch_type == TouchType.KEY_CROSS:
                        _['k_up'] = UnifiedKey(_.pop('k_up'))
                        _['k_down'] = UnifiedKey(_.pop('k_down'))
                        _['k_left'] = UnifiedKey(_.pop('k_left'))
                        _['k_right'] = UnifiedKey(_.pop('k_right'))
                    else:
                        _['unified_key'] = UnifiedKey(_.pop('unified_key'))

                    touch_x = _.pop('touch_x')
                    touch_y = _.pop('touch_y')

                    pos = self.win_twin.dvc.coord_draw.to_point(ScalePoint(touch_x, touch_y))
                    self.create_tp(None, None, [touch_type, pos, _], draw=False)
                    self.save_tp()

                except Exception as e:
                    logger.error(e)
                    self.cancel()

            # Update Cfg Name
            dpg.set_value(self.tag_txt_cfg, path.stem)

        with dpg.file_dialog(
                label='Load Touch Proxy Cfg Files', width=800, height=500, callback=_load_file,
                default_path=Param.PATH_TPS.__str__(),
                modal=True, file_count=10
        ):
            dpg.add_file_extension('.json', custom_text='')

    def save_as(self):
        """
            保存配置文件
        :return:
        """

        if len(self.indicators) == 0:
            with dpg.window(**MODEL_WIN_CFG):
                dpg.add_text('Set Some TPS First!')

        tag_ipt_file_name = dpg.generate_uuid()

        def _save():
            file_name = dpg.get_value(tag_ipt_file_name)
            if file_name is None or file_name == '':
                return

            dpg.delete_item(save_win)
            time.sleep(0.5)
            self._save_cfg(Param.PATH_TPS.joinpath(file_name + '.json'))

        with dpg.window(
                **MODEL_WIN_CFG, label='Save To'
        ) as save_win:
            dpg.add_input_text(
                label='FileName', on_enter=True, callback=_save, tag=tag_ipt_file_name,
                default_value='' if self.last_cfg_path is None else self.last_cfg_path.stem,
                width=-65
            )
            with dpg.group(horizontal=True):
                btn_cfg = dict(width=90, height=35)
                dpg.add_button(label='Save', callback=_save, **btn_cfg)
                dpg.add_button(label='Cancel', callback=lambda: dpg.delete_item(save_win), **btn_cfg)

    def save_this(self):
        if len(self.indicators) == 0:
            with dpg.window(**MODEL_WIN_CFG):
                dpg.add_text('Set Some TPS First!')

        if self.last_cfg_path is None:
            self.save_as()
        else:
            self._save_cfg(self.last_cfg_path)

    def _save_cfg(self, save_path: pathlib.Path):
        """
            保存 Cfg 文件
        :param save_path: 保存路径
        :return:
        """

        save_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_dict = {'touch_proxy': []}
        for ind_type, ind_obj, kwargs in self.indicators:
            values = ind_obj.to_value()
            values['touch_type'] = ind_type.value
            for key in ['release_ms', 'interval_ms']:
                if key in kwargs:
                    values[key] = kwargs[key]
            cfg_dict['touch_proxy'].append(values)
        CfgHandler.save(save_path, cfg_dict)
        self.last_cfg_path = save_path
        dpg.set_value(self.tag_txt_cfg, self.last_cfg_path.stem)

        with dpg.window(label='Success', **MODEL_WIN_CFG) as tag_win_ok:
            dpg.add_text(f"Saved to {save_path}")
            dpg.add_button(label='Ok', width=-1, height=40, callback=lambda: dpg.delete_item(tag_win_ok))

    def save_tp(self):
        """
            保存 Touch Proxy
        :return:
        """

        def _set_key_first():
            with dpg.window(**MODEL_WIN_CFG, label='Warning') as _w:
                dpg.add_text('Set Key First!')
                dpg.add_button(label='Close', width=80, height=35, callback=lambda: dpg.delete_item(_w))
            return

        def _key_repeat(_k_code):
            with dpg.window(label='Warning', **MODEL_WIN_CFG) as _w:
                dpg.add_text(f"Key > {UnifiedKey(_k_code).name} < Exists!")
                dpg.add_button(label='Close', width=80, height=35, callback=lambda: dpg.delete_item(_w))

        def _aim_repeat():
            with dpg.window(label='Warning', **MODEL_WIN_CFG) as _w:
                dpg.add_text(f"An Aim TouchProxy Already Exists!")
                dpg.add_button(label='Close', width=80, height=35, callback=lambda: dpg.delete_item(_w))

        keys = []

        t_type, ind_obj, kwargs = self.editing_indicator

        if t_type == TouchType.KEY_CROSS:
            for k, v in ind_obj.to_value().items():
                if k.startswith('k_'):
                    if v is None or v == UnifiedKey.SETKEY:
                        _set_key_first()
                        return
                    else:
                        if v in keys:
                            _key_repeat(v)
                            return
                        else:
                            keys.append(v)

        elif t_type == TouchType.KEY_AIM:
            for _ind_type, _ind_obj, _kwargs in self.indicators:
                if _ind_type == TouchType.KEY_AIM:
                    _aim_repeat()
                    return
            key_value = ind_obj.to_value().get('unified_key', None)
            if key_value is None or key_value == UnifiedKey.SETKEY:
                _set_key_first()
                return
            else:
                if key_value in keys:
                    _key_repeat(key_value)
                    return
                keys.append(key_value)

            key_value = ind_obj.to_value().get('attack_unified_key', None)
            if key_value is None or key_value == UnifiedKey.SETKEY:
                _set_key_first()
                return
            else:
                if key_value in keys:
                    _key_repeat(key_value)
                    return
                keys.append(key_value)

        else:
            key_value = ind_obj.to_value().get('unified_key', None)
            if key_value is None or key_value == UnifiedKey.SETKEY:
                _set_key_first()
                return
            else:
                if key_value in keys:
                    _key_repeat(key_value)
                    return
                keys.append(key_value)

        for k_code in keys:
            if k_code in self.keys:
                _key_repeat(k_code)
                return

        for k in keys:
            self.keys.add(k)

        for key, _tag in kwargs.items():
            if key.find('_ms') != -1:
                kwargs[key] = dpg.get_value(_tag)

        self.indicators.append((t_type, ind_obj, kwargs))
        self.editing_cache = None
        self.cancel()

    def cancel(self):
        """
            取消
        :return:
        """

        self.is_editing = False
        self.editing_indicator = None

        # Cancel When Editing
        if self.editing_cache:
            self.indicators.append(self.editing_cache)
            self.editing_cache = None

        dpg.configure_item(self.tag_tab_main, show=True)
        dpg.set_value(self.tag_tab, self.tag_tab_main)
        dpg.configure_item(self.tag_tab_edit, show=False)
        dpg.delete_item(self.win_twin.tag_win_mask, children_only=True)

        if self.itp:
            try:
                self.itp.delete()
            except Exception:
                pass
            self.itp = None

        self.draw_tps()
        self.load_tp_buttons()

    def load_tp_buttons(self):
        """
            绘制 TouchProxy 对应 Buttons
        :return:
        """
        dpg.delete_item(self.tag_group_btns, children_only=True)
        for index, _ in enumerate(self.indicators):
            ind_type, ind_obj, kwargs = _
            with dpg.group(horizontal=True, parent=self.tag_group_btns):
                if ind_type == TouchType.KEY_CROSS:
                    dpg.add_button(label=f"Cross", width=60, height=20, user_data=index, callback=self.edit_tp)

                elif ind_type == TouchType.KEY_AIM:
                    dpg.add_button(label='Aim', width=60, height=20, user_data=index, callback=self.edit_tp)

                elif ind_type == TouchType.KEY_WATCH:
                    dpg.add_button(
                        label='W_' + ind_obj.uk.name, width=60, height=20, user_data=index, callback=self.edit_tp
                    )

                else:
                    dpg.add_button(label=ind_obj.uk.name, width=60, height=20, user_data=index, callback=self.edit_tp)

                dpg.add_button(label='x', width=25, height=20, user_data=index, callback=self.delete_tp)

    def delete_tp(self, sender, app_data, user_data):
        """
            删除 Touch Proxy
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        ind_type, ind_obj, kwargs = self.indicators.pop(user_data)

        # 清除 Key Code 占用
        if isinstance(ind_obj, IndicatorCross):
            for k, v in ind_obj.to_value().items():
                if k.startswith('k_'):
                    self.keys.discard(v)

        elif isinstance(ind_obj, IndicatorAim):
            self.keys.discard(ind_obj.uk.value)
            self.keys.discard(ind_obj.ind_attack.uk.value)

        else:
            self.keys.discard(ind_obj.uk.value)

        self.draw_tps()
        self.load_tp_buttons()

    def edit_tp(self, sender, app_data, user_data):
        """
            编辑 Touch Proxy
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """

        ind_type, ind_obj, kwargs = self.indicators.pop(user_data)
        self.editing_cache = (ind_type, ind_obj, kwargs)

        kwargs.update(ind_obj.to_value())

        if ind_type == TouchType.KEY_CROSS:
            for k, v in ind_obj.to_value().items():
                if k.startswith('k_'):
                    self.keys.discard(v)
                    kwargs.update({k: UnifiedKey(v)})

        elif ind_type == TouchType.KEY_AIM:
            self.keys.discard(ind_obj.uk.value)
            self.keys.discard(ind_obj.ind_attack.uk.value)
            kwargs.update({'unified_key': ind_obj.uk, 'attack_unified_key': ind_obj.ind_attack.uk})

        else:
            self.keys.discard(ind_obj.uk.value)
            kwargs.update({'unified_key': ind_obj.uk})

        self.draw_tps()

        self.create_tp(None, ind_obj, [
            ind_type, self.win_twin.dvc.coord_draw.to_point(ind_obj.locator.scale_point), kwargs
        ])

    def create_tp(self, sender, app_data, user_data, draw: bool = True):
        """
            Create New Touch Proxy
        :param sender:
        :param app_data:
        :param user_data:
        :param draw:
        :return:
        """

        itp = None

        touch_type, pos, default_values = user_data
        if sender is not None:
            dpg.delete_item(self.tag_win_choose_type)

        self.is_editing = True

        # Hide Main tab
        dpg.configure_item(self.tag_tab_edit, show=True)
        dpg.set_value(self.tag_tab, self.tag_tab_edit)
        dpg.configure_item(self.tag_tab_main, show=False)

        if touch_type in [TouchType.KEY_PRESS, TouchType.KEY_WATCH]:
            itp = IndicatorTouchPoint(self.draw_parent, Locator(
                self.win_twin.dvc.coord_draw.to_scale_point(pos.x, pos.y),
                self.win_twin.dvc.coord_draw,
            ), **default_values)
            self.editing_indicator = (touch_type, itp, {})

        elif touch_type in [TouchType.KEY_CLICK, TouchType.KEY_REPEAT]:

            kwargs = {}

            itp = IndicatorTouchPoint(self.draw_parent, Locator(
                self.win_twin.dvc.coord_draw.to_scale_point(pos.x, pos.y),
                self.win_twin.dvc.coord_draw
            ), **default_values)
            release_ms = dpg.add_input_int(
                label='release_ms', default_value=default_values.get('release_ms', 30), width=85,
                parent=self.draw_parent
            )
            itp.locator.register(
                release_ms,
                lambda loc: dpg.configure_item(release_ms, pos=loc.to_item_pos(fix_point=Point(30, -35)))
            )
            itp.ind_btn_close.register({release_ms, })
            kwargs['release_ms'] = release_ms

            # key repeat append interval ms
            if touch_type == TouchType.KEY_REPEAT:
                interval_ms = dpg.add_input_int(
                    label='interval_ms', default_value=default_values.get('interval_ms', 100), width=85,
                    parent=self.draw_parent
                )
                itp.locator.register(
                    interval_ms,
                    lambda loc: dpg.configure_item(interval_ms, pos=loc.to_item_pos(fix_point=Point(30, -8)))
                )
                itp.ind_btn_close.register({interval_ms, })
                kwargs['interval_ms'] = interval_ms

            self.editing_indicator = (touch_type, itp, kwargs)

        elif touch_type == TouchType.KEY_SCOPE:

            e_sp = ScalePoint(0.5, 0.5)

            if 'pmin' in default_values:
                sp_min = ScalePoint(*default_values['pmin'])
                sp_max = ScalePoint(*default_values['pmax'])
                e_sp = ScalePoint((sp_min.x + sp_max.x) / 2, (sp_min.y + sp_max.y) / 2)
                default_values['a'] = (sp_max.x - sp_min.x) / 2
                default_values['b'] = (sp_max.y - sp_min.y) / 2

            itp = IndicatorScope(
                self.draw_parent,
                Locator(self.win_twin.dvc.coord_draw.to_scale_point(pos.x, pos.y), self.win_twin.dvc.coord_draw),
                Locator(e_sp, self.win_twin.dvc.coord_draw),
                **default_values
            )
            self.editing_indicator = (touch_type, itp, {})

        elif touch_type == TouchType.KEY_CROSS:
            itp = IndicatorCross(
                self.draw_parent,
                Locator(self.win_twin.dvc.coord_draw.to_scale_point(pos.x, pos.y), self.win_twin.dvc.coord_draw),
                **default_values
            )
            self.editing_indicator = (touch_type, itp, {})

        elif touch_type == TouchType.KEY_AIM:

            attack_sp = ScalePoint(0.1, 0.1)

            if 'attack_touch_x' in default_values:
                attack_sp = ScalePoint(default_values['attack_touch_x'], default_values['attack_touch_y'])
                default_values['attack_unified_key'] = UnifiedKey(default_values['attack_unified_key'])

            itp = IndicatorAim(
                self.draw_parent,
                Locator(self.win_twin.dvc.coord_draw.to_scale_point(pos.x, pos.y), self.win_twin.dvc.coord_draw),
                Locator(attack_sp, self.win_twin.dvc.coord_draw),
                **default_values
            )
            self.editing_indicator = (touch_type, itp, {})

        if itp is None:
            self.cancel()
            return

        itp.ind_btn_close.callback = self.cancel

        if draw:
            itp.draw()

        self.itp = itp

    def create_item(self, mouse_pos: Point):
        """
            Create New Touch Proxy After Double Click
        :param mouse_pos:
        :return:
        """

        if self.is_editing:
            return

        btn_cfg = dict(width=120, height=35)

        # Create Type Choose Window
        with dpg.window(
                modal=True, no_resize=True, no_move=True, no_title_bar=True, no_collapse=True,
                pos=mouse_pos + TWIN_POS, tag=self.tag_win_choose_type
        ):
            dpg.add_text('Choose a type')
            dpg.add_separator()
            for touch_type in TouchType:
                dpg.add_button(
                    label=f"{touch_type.name}", **btn_cfg,
                    user_data=(touch_type, mouse_pos, {}),
                    callback=lambda s, a, u: self.create_tp(s, a, u)
                )
            dpg.add_separator()
            dpg.add_button(label='Cancel', **btn_cfg, callback=lambda: dpg.delete_item(self.tag_win_choose_type))
