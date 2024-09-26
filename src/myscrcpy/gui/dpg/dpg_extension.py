# -*- coding: utf-8 -*-
"""
    DPG Extensions
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-09-26 1.6.2 Me2sY 完善回调方法，优化部分方法

        2024-09-24 1.6.1 Me2sY 修复 Linux 下 Viewport 过大导致界面错误

        2024-09-19 1.6.0 Me2sY
            1. 创建，DPG专用插件
            2. 新增 VmDPGItem 及 具体对象类，用于创建受 ValueManager 管理的 dpg item
            3. 新增 MouseGesture Key 注册功能
"""

__author__ = 'Me2sY'
__version__ = '1.6.2'

__all__ = [
    'ValueObj', 'ValueManager',
    'DPGExtension', 'DPGExtensionManager', 'DPGExtManagerWindow', 'ViewportCoordManager',
    'VmDPGItem',
    'VDCheckBox',
    'VDInputInt', 'VDInputFloat', 'VDInputText',
    'VDSliderInt', 'VDDragInt',
    'VDColorPicker',
    'VDKnobFloat',
    'VDCombo'
]


from abc import ABCMeta
from dataclasses import dataclass
from functools import partial
import threading
from typing import Any, Callable, Iterable, NamedTuple

import dearpygui.dearpygui as dpg
from av import VideoFrame
from loguru import logger

from myscrcpy.core.extension import Extension, ExtInfo, RegisteredExtension, ExtensionManager
from myscrcpy.utils import KeyValue, KVManager, UnifiedKeys, Action, UnifiedKey, Coordinate
from myscrcpy.gui.dpg.mouse_handler import GesAction


@dataclass
class ValueObj:
    """
        Value 数据类
    """

    tag: str | None
    v_type: type
    attr: str
    value: Any = None

    def get_value(self) -> Any:
        """
            获取值，若为DPG值，则去 value item 获取，否则取 ValueObj Value值
        :return:
        """
        if self.tag:
            self.value = dpg.get_value(self.tag)
        return self.value

    def set_value(self, value):
        """
            设置值
        :param value:
        :return:
        """
        if type(value) is self.v_type:
            self.value = value
            self.tag and dpg.set_value(self.tag, value)
        else:
            raise TypeError(f"Set {self.attr} {value} Error, Type {self.v_type} Need")

    @property
    def is_dpg_value(self) -> bool:
        return self.tag is not None


class ValueManager:
    """
        DearPyGui Value 管理器
        用于加载、保持、控制数值
    """

    KV_HEADER = 'VM-'

    # DPG 支持 string / int / float / bool Value Type
    # 其他无法注册，使用标准值管理

    TYPE_MAPPER = {
        str: dpg.add_string_value,
        int: dpg.add_int_value,
        float: dpg.add_float_value,
        bool: dpg.add_bool_value,
    }

    def __init__(self, kv: KVManager, load_kvs: bool = True):
        """
            值控制器
        :param kv:
        :param load_kvs:
        """
        self._values = {}
        self.kv = kv

        if load_kvs:
            self.load_kvs()

    def __call__(self, attr_name: str) -> Any:
        return self.get_value(attr_name)

    def __iter__(self):
        return iter(self._values.items())

    def register(self, attr_name: str, default_value, rewrite: bool = False, set_kv: bool = True) -> 'ValueHolder':
        """
            注册一个 attr_name 的 Value 值
        :param attr_name:
        :param default_value:
        :param rewrite:  重写数据
        :param set_kv:   保存至 KV 库
        :return:
        """
        if attr_name not in self._values.keys():
            _type = type(default_value)
            with dpg.value_registry():
                self._values[attr_name] = ValueObj(
                    tag=self.TYPE_MAPPER.get(_type, lambda default_value: None)(default_value=default_value),
                    v_type=_type, attr=attr_name, value=default_value
                )
            set_kv and self.set_to_kv(attr_name, default_value)

        elif rewrite:
            self.set_value(attr_name, default_value, set_kv=set_kv)

        return ValueHolder(self, attr_name)

    def get_tag(self, attr_name: str) -> str | int | None:
        """
            获取 attr 对应 dpg.value tag
        :param attr_name:
        :return:
        """
        return self._values[attr_name].tag

    def set_to_kv(self, attr_name: str, value):
        """
            保存至 kv
        :param attr_name:
        :param value:
        :return:
        """
        self.kv.set(f"{self.KV_HEADER}{attr_name}", value)

    def set_value(self, attr_name: str, value, set_kv: bool = False):
        """
            设置值
        :param attr_name:
        :param value:
        :param set_kv:
        :return:
        """
        self._values[attr_name].set_value(value)
        set_kv and self.set_to_kv(attr_name, value)

    def get_value(self, attr_name: str):
        """
            获取值
        :param attr_name:
        :return:
        """
        return self.get_value_obj(attr_name).get_value()

    def get_value_obj(self, attr_name: str) -> ValueObj:
        """
            获取值对象
        :param attr_name:
        :return:
        """
        return self._values[attr_name]

    def get_attrs(self) -> list[str]:
        """
            获取值列表
        :return:
        """
        return list(self._values.keys())

    def dump(self) -> dict[str, Any]:
        """
            Dump Data
        :return:
        """
        return {attr: value.get_value() for attr, value in self._values.items()}

    def load(self, values: dict[str, Any], rewrite: bool = False, set_kv: bool = False, parent_attr: str = None):
        """
            Load Data
        :param values:
        :param rewrite:
        :param set_kv:
        :param parent_attr:
        :return:
        """
        for attr, value in values.items():
            attr_name = attr if parent_attr is None else f"{parent_attr}.{attr}"

            # 扁平化
            if type(value) is dict:
                self.load(value, rewrite=rewrite, set_kv=set_kv,parent_attr=attr_name)
            else:
                self.register(attr_name, value, rewrite=rewrite, set_kv=set_kv)

    def load_kvs(self, rewrite: bool = True):
        """
            从 KVManager 加载 ValueRegister
        :return:
        """
        for kv in self.kv.query(f"{self.KV_HEADER}%"):
            self.register(kv.key[len(self.KV_HEADER):], kv.value, rewrite=rewrite, set_kv=False)

    def save_kvs(self):
        """
            保存 vr数据 至 KVManager
        :return:
        """
        self.kv.set_many([
            KeyValue(
                f"{self.KV_HEADER}{attr}", value_obj.get_value()
            ) for attr, value_obj in self._values.items()
        ])


class ValueHolder(NamedTuple):
    """
        实际引用类
    """

    vm: ValueManager
    attr_name: str

    def __call__(self, *args, **kwargs) -> Any:
        """
            Pass Value to Set
            otherwise get value
        :param args:
        :param kwargs:
        :return:
        """
        if len(args) > 0:
            self.vm.set_value(self.attr_name, args[0], set_kv=kwargs.get('set_kv', True))
            return args[0]
        else:
            return self.vm.get_value(self.attr_name)

    def get_value(self):
        """
            获取值
        :return:
        """
        return self.vm.get_value(self.attr_name)

    def set_value(self, value, set_kv: bool = True):
        """
            设置值
        :param value:
        :param set_kv:
        :return:
        """
        self.vm.set_value(self.attr_name, value, set_kv=set_kv)

    def get_tag(self):
        """
            获取 Tag
        :return:
        """
        return self.vm.get_tag(self.attr_name)

    def set_to_kv(self, value: Any):
        """
            存储 KV 值
        :param value:
        :return:
        """
        self.vm.set_to_kv(self.attr_name, value)


@dataclass
class KeyInfo:
    """
        按键信息
    """
    name: str
    space: int
    uk_name: str
    desc: str = ''

    @property
    def vm_name(self) -> str:
        return f"keys.{self.name}"


@dataclass
class MouseGestureInfo:
    """
        鼠标手势信息
    :return:
    """
    name: str
    space: int
    gestures: str
    desc: str = ''

    @property
    def vm_name(self) -> str:
        return f"gestures.{self.name}"


class DPGExtension(Extension, metaclass=ABCMeta):
    """
        DearPyGui Extension
        新增DPG专用方法
    """

    def __init__(self, ext_info: ExtInfo, window):
        super().__init__(ext_info)
        self.window = window
        self.value_manager = ValueManager(self.kv, load_kvs=True)

        # 加载默认值
        self.value_manager.load(self.ext_info.settings, rewrite=False, set_kv=True)

        self.keys = {}
        self.load_keys()

        self.load_mouse_ges()

        # 插件允许注册 一个侧边控制面板，一个Menu
        self.tag_pad = None
        self.tag_menu = None

        self.required_loop = False
        self.required_video_frame = False

    def __del__(self):
        try:
            self.value_manager.save_kvs()
        except Exception:
            ...

    def load_mouse_ges(self):
        """
            加载鼠标手势
        :return:
        """
        for key_name, value in self.ext_info.raw.get('mouse_ga', {}).items():
            try:
                mg = MouseGestureInfo(name=key_name, **value)
            except Exception as e:
                logger.error(f"Load Mouse GestureInfo Error: {e}")
                continue

            mg.gestures = self.value_manager.register(key_name, mg.gestures, rewrite=False, set_kv=True)
            self.register_mouse_gesture_callback(mg, f"callback_mg_{key_name}")

    def register_mouse_gesture_callback(self, mg: MouseGestureInfo, function_name: str) -> bool:
        """
            注册鼠标手势功能
        :param mg:
        :param function_name:
        :return:
        """
        if not hasattr(self, function_name):
            setattr(
                self, function_name, lambda: logger.warning(f"Mouse Gesture {mg.name} Not Defined Function!")
            )

        ga = GesAction(
            self.ext_info.ext_module,
            mg.gestures if type(mg) is str else mg.gestures(),
            mg.name,
            getattr(self, function_name)
        )

        self.window.mouse_handler.register_ges_action(mg.space, ga)
        return True

    def load_keys(self):
        """
            加载按键
        :return:
        """

        for key_name, key_info in self.ext_info.raw.get('keys', {}).items():
            try:
                ki = KeyInfo(name=key_name, **key_info)
            except Exception as e:
                logger.error(f"Load Key {key_name} Error -> {e}")
                continue

            ki.uk_name = self.value_manager.register(ki.vm_name, ki.uk_name, rewrite=False, set_kv=True).get_value()

            # Inject key function
            # rewritten callback_key_xxx to defined your function
            self.register_key_callback(ki, f"callback_key_{key_name}")
            self.keys[ki.vm_name] = ki

    def register_key_callback(self, key_info: KeyInfo, function_name: str) -> bool:
        """
            注册按键功能
        :param key_info:
        :param function_name:
        :return:
        """
        if not hasattr(self, function_name):
            setattr(
                self, function_name,
                partial(
                    lambda _self, unified_key, action: logger.info(f"Key > {unified_key} | {action}"),
                    self
                )
            )
            logger.warning(f"Key {key_info.name} Not Defined Function!")

        uk = UnifiedKeys.filter_name(key_info.uk_name)
        if uk is None:
            logger.error(f"Load Key {key_info.name} Error -> UnifiedKey Not Found! Check Key Name!")
            return False

        self.window.keyboard_handler.register_ctrl_key_callback(
            self.ext_info.ext_module, key_info.space, uk, getattr(self, function_name)
        )
        return True

    def register_pad(self) -> str | int:
        """
            注册控制面板
            返回面板TAG
        :return:
        """
        if self.tag_pad is not None:
            try:
                dpg.delete_item(self.tag_pad)
            except Exception:
                ...

        self.tag_pad = dpg.add_collapsing_header(label=f"{self.ext_info.ext_name}", parent=self.window.tag_ext_pad)

        return self.tag_pad

    def register_menu(self) -> str | int:
        """
            注册 Menu
        :return:
        """
        if self.tag_menu is not None:
            try:
                dpg.delete_item(self.tag_menu)
            except Exception:
                ...

        self.tag_menu = dpg.add_menu(label=self.ext_info.ext_name, parent=self.window.tag_ext_menu)

        return self.tag_menu

    def register_layer(self) -> str | int:
        """
            注册显示layer
        :return:
        """
        return self.window.cpm_vc.register_layer()

    def loop(self):
        """
           When DPG Loop, Make A Threading then Call This Function
           Set self.required_loop to True
        :return:
        """
        ...

    def show_message(self, message: str):
        """
            显示信息
        :param message:
        :return:
        """
        self.window.cpm_bottom.show_message(message)

    def video_frame_update_callback(self, video_frame: VideoFrame, frame_n: int):
        """
            视频更新回调
        :param video_frame:
        :param frame_n:
        :return:
        """
        ...


class DPGExtensionManager(ExtensionManager):
    """
        DearPyGui ExtensionManager
        注册时 传入 window 对象
    """

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.kv = KVManager('dpg_ext_manager')
        self.value_manager = ValueManager(self.kv, load_kvs=True)

    def register_extensions(self):
        """
            注册全部插件
        :return:
        """
        for module, reg_ext in self.extensions.items():
            ext_obj = self.register_extension(reg_ext)
            if self.value_manager.register(f"{module}.enabled", False, set_kv=True):
                try:
                    ext_obj.start()
                    reg_ext.is_activated = True
                except Exception as e:
                    logger.error(f"Register Extension {module} Error")
                    logger.exception(e)

    def register_extension(self, registered_ext: RegisteredExtension) -> Extension:
        """
            注册 DPG 插件
        :param registered_ext:
        :param window:
        :return:
        """
        try:
            try:
                registered_ext.ext_obj = registered_ext.ext_cls(ext_info=registered_ext.ext_info, window=self.window)
                return registered_ext.ext_obj

            except Exception as e:
                logger.error(f"Register Extension Error")
                logger.exception(e)
                if issubclass(registered_ext.ext_cls, Extension):
                    registered_ext.ext_obj = registered_ext.ext_cls(ext_info=registered_ext.ext_info)
                    return registered_ext.ext_obj
        except Exception as e:
            logger.error(f"DPGExtensionManager Register {registered_ext.ext_info.ext_module} Error -> {e}")

    def loop_call(self):
        """
            循环调用
        :return:
        """
        for registered_ext in self.extensions.values():
            if registered_ext.is_activated and registered_ext.ext_obj.required_loop:
                threading.Thread(target=registered_ext.ext_obj.loop).start()

    def video_frame_update_callback(self, video_frame: VideoFrame, frame_n: int):
        """
            视频帧更新回调
        :param video_frame:
        :param frame_n:
        :return:
        """
        for registered_ext in self.extensions.values():
            if registered_ext.is_activated and registered_ext.ext_obj.required_video_frame:
                threading.Thread(
                    target=registered_ext.ext_obj.video_frame_update_callback, args=(video_frame, frame_n)
                ).start()


class DPGExtManagerWindow:
    """
        插件管理窗口
    """

    def __init__(self, dpg_ext_manager: DPGExtensionManager):
        self.manager = dpg_ext_manager

        self.tag_win = dpg.generate_uuid()
        self.tag_table = dpg.generate_uuid()
        self.tag_filter = dpg.generate_uuid()

    def draw(self):
        """
            绘制管理窗口
        :return:
        """
        with dpg.window(label='DPG Extension Manager', tag=self.tag_win):
            self.tag_filter = dpg.add_input_text(
                label="Filter", user_data=self.tag_table, width=-40,
                callback=lambda s, a, u: dpg.set_value(self.tag_table, dpg.get_value(s))
            )
            with dpg.table(tag=self.tag_table, policy=dpg.mvTable_SizingFixedFit, delay_search=True):
                dpg.add_table_column(label='enabled')
                dpg.add_table_column(label='name & info')
                dpg.add_table_column(label='version')
                dpg.add_table_column(label='author')
                dpg.add_table_column(label='settings')

        self.load()

    def enable_extension(self, sender, app_data, user_data):
        """
            开启/关闭 插件
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """

        ext_key, reg_ext, is_enabled_value = user_data

        is_enabled_value(app_data)

        if app_data:
            reg_ext.ext_obj.start()
        else:
            reg_ext.ext_obj.stop()

    def load(self):
        """
            绘制 Table
        :return:
        """

        dpg.delete_item(self.tag_table, children_only=True, slot=1)

        for ext_module, reg_ext in self.manager:

            ext_key = f"{ext_module}.enabled"

            is_enabled = self.manager.value_manager.register(
                ext_key, False, rewrite=False, set_kv=True
            )

            with dpg.table_row(parent=self.tag_table, filter_key=f"{ext_module}"):

                dpg.add_checkbox(
                    user_data=(ext_key, reg_ext, is_enabled),
                    callback=self.enable_extension,
                    source=is_enabled.get_tag()
                )

                dpg.add_text(reg_ext.ext_info.ext_name)

                with dpg.tooltip(dpg.last_item()):
                    with dpg.group(horizontal=True):
                        dpg.add_text(f"{'loaded':>10}:")
                        dpg.add_text(str(reg_ext.ext_module))

                    for _ in [
                        'ext_module', 'ext_md5', 'ext_path',
                        'email', 'web', 'contact', 'desc'
                    ]:
                        if reg_ext.ext_info.__getattribute__(_) != '':
                            with dpg.group(horizontal=True):
                                dpg.add_text(f"{_:>10}:")
                                dpg.add_text(reg_ext.ext_info.__getattribute__(_))

                dpg.add_text(reg_ext.ext_info.version)
                dpg.add_text(reg_ext.ext_info.author)

                dpg.add_button(label='>', user_data=reg_ext, callback=self.draw_settings_editor, width=65)

    def draw_settings_editor(self, sender, app_data, user_data: RegisteredExtension):
        """
            绘制 设置编辑器
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        if user_data.ext_obj is not None:

            with dpg.window(label=f"{user_data.ext_info.ext_name} Configs") as tag_win:

                tag_cfg_table = dpg.generate_uuid()

                dpg.add_input_text(
                    label=f"Filter", user_data=tag_cfg_table, width=-40,
                    callback=lambda s, a, u: dpg.set_value(tag_cfg_table, dpg.get_value(s))
                )

                with dpg.table(policy=dpg.mvTable_SizingFixedFit, delay_search=True, tag=tag_cfg_table):

                    dpg.add_table_column(label='item')
                    dpg.add_table_column(label='value')

                    vm: ValueManager = user_data.ext_obj.value_manager

                    for attr_name, value_obj in vm:
                        with dpg.table_row(filter_key=f"{attr_name}"):
                            dpg.add_text(attr_name)

                            # 自定义按键
                            if attr_name.startswith('keys.'):
                                dpg.add_combo(
                                    list(UnifiedKeys.get_keyboard_keys().keys()),
                                    source=value_obj.tag, width=128
                                )

                            if value_obj.v_type is str:
                                dpg.add_input_text(source=value_obj.tag)

                            elif value_obj.v_type is int:
                                dpg.add_input_int(source=value_obj.tag, width=150)

                            elif value_obj.v_type is float:
                                dpg.add_input_float(source=value_obj.tag, width=150)

                            elif value_obj.v_type is bool:
                                dpg.add_checkbox(source=value_obj.tag)

                            else:
                                try:
                                    dpg.add_text(default_value=str(value_obj.value))
                                except Exception as e:
                                    dpg.add_text(default_value='Value Not Editable')
                dpg.add_separator()
                dpg.add_button(label='Save', callback=lambda: vm.save_kvs(), width=-1, height=30)
                dpg.add_button(label='Close', callback=lambda: dpg.delete_item(tag_win), width=-1, height=30)

        else:
            logger.success(f"{user_data.ext_info.ext_name} Not Registered")


class VmDPGItem(metaclass=ABCMeta):
    """
        DPG Item With Value Manager Auto Control
    """

    DPG_DRAW_METHOD = None

    def __init__(
            self, ext: DPGExtension, value_or_name: ValueHolder | str,
            label: str = None, callback: Callable = None,
            **kwargs
    ):
        """
            Init DPG item
        :param ext: extension obj
        :param value:
        :param label: item label
        :param callback: callback function
        :param kwargs: item kwargs
        """

        if self.DPG_DRAW_METHOD is None:
            raise NotImplementedError(f"{self.__class__.__name__}.DPG_DRAW_METHOD is not defined")

        self.ext = ext
        self.value = value_or_name if type(value_or_name) is ValueHolder else ValueHolder(
            self.ext.value_manager, value_or_name
        )

        self.tag = dpg.generate_uuid()

        self.kwargs = {
            'tag': self.tag, 'label': str(label) if label is not None else self.value.attr_name,
            'source': self.value.get_tag(),
            'callback': self.callback,
        }

        self.register_callback = callback

        self.kwargs.update(kwargs)

    def __call__(self, *args, callback: Callable | bool = None, **kwargs) -> Any:
        if len(args) > 0:
            self.set_value(args[0], callback=callback)
        return self.get_value()

    def callback(self, sender, app_data, user_data):
        """
            save and call real callback function
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        self.value.set_to_kv(app_data)
        if self.register_callback:
            self.register_callback(sender, app_data, user_data)

    def draw(self, parent: int | str | None = None) -> 'VmDPGItem':
        """
            绘制
        :param parent:
        :return:
        """
        try:
            dpg.delete_item(self.tag)
        except Exception as e:
            ...

        parent and self.kwargs.update({'parent': parent})

        self.__class__.DPG_DRAW_METHOD(**self.kwargs)

        return self

    def get_value(self):
        """
            获取值
        :return:
        """
        return self.value.get_value()

    def set_value(self, value, callback: Callable | bool = None):
        """
            设置值
        :param value:
        :param callback: None With no Callback / Callable will callback / True will Call Item Callback
        :return:
        """
        self.value.set_value(value, set_kv=True)

        if callback is None:
            return

        args = [self.tag, value, self.kwargs.get('user_data', None)]

        if type(callback) is bool and callback:
            _callback = self.kwargs.get('callback')
            if _callback is None:
                return
            _callback(*args)
            return

        if callable(callback):
            callback(*args)

    def configure(self, **kwargs):
        """
            Configure DPG item. Rewrite dpg.configure_item function
        :param kwargs:
        :return:
        """
        self.kwargs.update(kwargs)
        dpg.configure_item(self.tag, **kwargs)

    @property
    def tag_item(self) -> int | str:
        """
            Item Tag
        :return:
        """
        return self.tag

    @property
    def tag_source(self) -> int | str:
        """
            Value Bind Source Tag
        :return:
        """
        return self.value.get_tag()


class VDCheckBox(VmDPGItem):

    DPG_DRAW_METHOD = dpg.add_checkbox

    def switch(self, status: bool = None, callback: Callable | bool = None) -> bool:
        """
            开关
        :param status: 传入则置该位，否则为切换
        :param callback: 传入则发起回调
        :return:
        """
        if status is None:
            _ = self.get_value()
        else:
            _ = status
        self.set_value(not _, callback)
        return not _


class VDInputInt(VmDPGItem):

    DPG_DRAW_METHOD = dpg.add_input_int


class VDInputFloat(VmDPGItem):

    DPG_DRAW_METHOD = dpg.add_input_float


class VDInputText(VmDPGItem):

    DPG_DRAW_METHOD = dpg.add_input_text


class VDSliderInt(VmDPGItem):

    DPG_DRAW_METHOD = dpg.add_slider_int


class VDDragInt(VmDPGItem):

    DPG_DRAW_METHOD = dpg.add_drag_int


class VDColorPicker(VmDPGItem):

    DPG_DRAW_METHOD = dpg.add_color_picker

    def draw(self, parent: int | str | None = None) -> 'VmDPGItem':

        try:
            dpg.delete_item(self.tag)
        except Exception as e:
            ...

        parent and self.kwargs.update({'parent': parent})

        del self.kwargs['source']

        self.kwargs['default_value'] = self.value.get_value()

        self.__class__.DPG_DRAW_METHOD(**self.kwargs)

        return self

    def callback(self, sender, app_data, user_data):
        """
            Color Back is RGBA 0..1 Float
            Convert To RGBA 0..255 uint
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        self.value.set_value([round(_ * 255) for _ in app_data], True)

        if self.register_callback:
            self.register_callback(sender, app_data, user_data)


class VDKnobFloat(VmDPGItem):

    DPG_DRAW_METHOD = dpg.add_knob_float


class VDCombo(VmDPGItem):

    DPG_DRAW_METHOD = dpg.add_combo

    def __init__(self, ext: DPGExtension, value_or_name: ValueHolder | str, items: Iterable, **kwargs):
        super().__init__(ext, value_or_name, **kwargs)
        self.kwargs['items'] = items


class ViewportCoordManager:
    """
        坐标管理器，用于统一管理 DPG Viewport Resize 事件
        同时过滤调整是回调波动
    """

    def __init__(self):

        self.tag_vp = 1

        self.vp_coord: Coordinate = Coordinate(-1, -1)
        self.vpc_coord: Coordinate = Coordinate(-1, -1)

        self.fix_w = -1
        self.fix_h = -1

        self.stable_coord = None

        self.resize_callbacks = []

        dpg.set_viewport_resize_callback(self._callback)

    def _callback(self, sender, app_data, user_data):
        """
            回调，处理DPG Viewport Resize 回调
        :param sender:
        :param app_data:
        :return:
        """

        self.tag_vp = sender

        if self.fix_w == -1:
            self.fix_w = dpg.get_viewport_width() - dpg.get_viewport_client_width()
            self.fix_h = dpg.get_viewport_height() - dpg.get_viewport_client_height()

        if self.fix_vp_size(Coordinate(app_data[0], app_data[1])):
            return

        vpc_coord = Coordinate(app_data[2], app_data[3])

        if vpc_coord != self.vpc_coord:
            _old = self.vpc_coord
            self.vpc_coord = vpc_coord
            self.vp_coord = Coordinate(app_data[0], app_data[1])
            self.resize_callback(_old, vpc_coord)

    def fix_vp_size(self, vp_coord: Coordinate) -> bool:
        """
            Viewport 缩小至指定值后，会卡住界面
            修复此缺陷
        """
        fix = False
        if vp_coord.width < dpg.get_viewport_min_width() + 8:
            dpg.set_viewport_width(
                vp_coord.width + 16
            )
            fix = True
        if vp_coord.height < dpg.get_viewport_min_height() + 8:
            dpg.set_viewport_height(
                vp_coord.height + 16
            )
            fix = True

        return fix

    def resize_callback(self, old_coord: Coordinate, new_coord: Coordinate):
        """
            Resize Callback After Stabled
        :param old_coord:
        :param new_coord:
        :return:
        """
        for callback in self.resize_callbacks:
            callback(old_coord, new_coord)

    def set_viewport_client_size(self, new_coord: Coordinate):
        """
            设置 Viewport Client Size
        :param new_coord:
        :return:
        """
        # 2024-09-24 1.6.1 Me2sY 修复Linux下 Viewport过大导致界面错误
        if new_coord.width > dpg.get_viewport_max_width() or new_coord.height > dpg.get_viewport_max_height():
            logger.warning(f"Too Large Viewport Size {new_coord}")
            return

        if new_coord == self.vpc_coord:
            return

        dpg.configure_viewport(
            self.tag_vp, width=new_coord.width + self.fix_w, height=new_coord.height + self.fix_h,
            user_data=True
        )

    def register_resize_callback(self, callback: Callable[[Coordinate, Coordinate], None]):
        """
            注册回调函数
        :param callback:
        :return:
        """
        self.resize_callbacks.append(callback)
