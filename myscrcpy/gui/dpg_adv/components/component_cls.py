# -*- coding: utf-8 -*-
"""
    DearPyGui 组件基类
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-15 1.3.0 Me2sY  发布初版

        2024-08-14 0.1.1 Me2sY  新增 TempModal, Static

        2024-08-11 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '1.3.0'

__all__ = [
    'Component',
    'ValueController', 'ValueObj',
    'ValueComponent',
    'TempModal', 'Static'
]

from functools import partial
from typing import NamedTuple, Any

import dearpygui.dearpygui as dpg

from myscrcpy.utils import Param, ValueManager


class Component:
    """
        组件抽象类
        继承后 实现 setup_inner 方法绘制组件界面
        实现 default_container 或者 设置 DEFAULT_CONTAINER_ADD_METHOD 指定组建外部包裹container
    """

    DEFAULT_CONTAINER_ADD_METHOD = None

    def __init__(self, parent_container=None, *args, **kwargs):
        self.tag_container = parent_container() if parent_container is not None else self.default_container()()

    def draw(self, *args, **kwargs):
        dpg.delete_item(self.tag_container, children_only=True)
        dpg.push_container_stack(self.tag_container)
        self.setup_inner(*args, **kwargs)
        dpg.pop_container_stack()
        return self

    def close(self):
        dpg.delete_item(self.tag_container)

    @classmethod
    def default_container(cls, parent=None):
        if cls.DEFAULT_CONTAINER_ADD_METHOD is None:
            raise NotImplementedError()
        return cls.create_container(cls.DEFAULT_CONTAINER_ADD_METHOD, parent=parent)

    def setup_inner(self, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def create_container(cls, dpg_container_add_method, parent=None, *args, **kwargs):
        return partial(
            dpg_container_add_method,
            parent=dpg.last_container() if parent is None else parent,
            *args, **kwargs
        )

    def update(self, *args, **kwargs):
        raise NotImplementedError


class ValueObj(NamedTuple):
    """
        DearPyGui Value
    """

    tag: str
    v_type: type
    attr: str

    def get_value(self):
        return dpg.get_value(self.tag)

    def set_value(self, value):
        if isinstance(value, self.v_type):
            dpg.set_value(self.tag, value)
        else:
            raise TypeError(f"Set {self.attr} {value} Error, Type {self.v_type} Need")


class ValueController:
    """
        DearPyGui Value 控制器
        用于加载、保持、控制数值
    """

    TYPE_MAPPER = {
        str: dpg.add_string_value,
        int: dpg.add_int_value,
        float: dpg.add_float_value,
        bool: dpg.add_bool_value,
    }

    def __init__(self):
        self._values = {}

    def register(self, attr_name: str, default_value):
        _type = type(default_value)
        if _type not in self.TYPE_MAPPER:
            raise TypeError(f"Register {attr_name} Error, Type {_type} Not Support!")

        with dpg.value_registry():
            self._values[attr_name] = ValueObj(self.TYPE_MAPPER[_type](default_value=default_value), _type, attr_name)

    def tag(self, attr_name: str) -> str | int:
        return self._values[attr_name].tag

    def set_value(self, attr_name: str, value):
        self._values[attr_name].set_value(value)

    def set_default_value(self, attr_name: str, value):
        if attr_name not in self._values:
            self.register(attr_name, value)

    def get_value(self, attr_name: str):
        return self.get_value_obj(attr_name).get_value()

    def get_value_obj(self, attr_name: str) -> ValueObj:
        return self._values[attr_name]

    def get_attrs(self) -> list[str]:
        return list(self._values.keys())

    def dump(self) -> dict[str, Any]:
        return {attr: value.get_value() for attr, value in self._values.items()}

    def load(self, values: dict[str, Any]):
        for attr, value in values.items():
            try:
                self.set_value(attr, value)
            except KeyError:
                self.register(attr, value)


class ValueComponent(Component):
    """
        支持 ValueControl/ValueManager 组件
        绑定内部组件 source 至 self.value_controller.tag(attr_name)
        重写 update 方法，操作数据类，进行组件显示更新等
    """

    VM_NAME = None

    def __init__(self, value_controller: ValueController = None, parent_container=None, *args, **kwargs):
        super().__init__(parent_container, *args, **kwargs)
        self.value_controller = ValueController() if value_controller is None else value_controller
        self.vm = ValueManager(self.VM_NAME)

    def update(self, *args, **kwargs):
        raise NotImplementedError


class TempModal:
    """
        临时窗口
    """
    @classmethod
    def draw_loading(cls, msg: str, *args, **kwargs) -> int | str:
        """
            绘制 加载窗口
        """
        with dpg.window(
            modal=True, no_scrollbar=True, no_resize=True, no_title_bar=True, no_move=True, autosize=True,
            **kwargs
        ) as tag_win:
            dpg.add_loading_indicator()
            dpg.add_text(default_value=msg)
        return tag_win

    @classmethod
    def draw_msg_box(cls, *args, **kwargs) -> int | str:
        """
            绘制消息窗口
        """
        with dpg.window(modal=True, no_move=True, no_resize=True, no_title_bar=True, **kwargs) as tag_win:
            for _ in args:
                _(parent=tag_win)
            dpg.add_separator()
            dpg.add_button(label='Close', width=-1, height=35, callback=lambda: dpg.delete_item(tag_win))
        return tag_win


class Static:
    """
        静态文件管理类
    """

    ICONS = {}

    @classmethod
    def load(cls):
        with dpg.texture_registry():
            for icon_file in Param.PATH_STATICS_ICONS.glob('*.png'):
                w, h, c, d = dpg.load_image(icon_file.__str__())
                cls.ICONS[icon_file.stem] = dpg.add_static_texture(width=w, height=h, default_value=d)


if __name__ == '__main__':

    class TestCase(ValueComponent):

        DEFAULT_CONTAINER_ADD_METHOD = dpg.add_group

        # You can also override this class method
        # @classmethod
        # def default_container(cls, parent=None):
        #     return cls.create_container(
        #         dpg.add_group, parent=parent,
        #         horizontal=True                   # dpg.Group Kwargs
        #     )
        # Or Just passthrough parent_container to Create

        def setup_inner(self, pass_args, *args, **kwargs):

            self.value_controller.register(
                'test_int_0', 666
            )

            dpg.add_input_int(label='Target', enabled=False, source=self.value_controller.tag('test_int_0'))
            dpg.add_drag_int(label='Drag', source=self.value_controller.tag('test_int_0'))
            dpg.add_text(default_value=f"Pass Args: {pass_args}")


    import dearpygui.dearpygui as dpg
    dpg.create_context()

    with dpg.window(width=600, height=300) as win:

        TestCase().draw(pass_args='This is Pass Args')

    dpg.create_viewport(title='Test Case For Component And ValueController')

    dpg.set_primary_window(win, True)

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.stop_dearpygui()
    dpg.destroy_context()
