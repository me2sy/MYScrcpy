# -*- coding: utf-8 -*-
"""
    my_list
    ~~~~~~~~~~~~~~~~~~
    
    Log:
        2026-01-26 0.1.0 Me2sY 创建
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = [
    'ListItemBase',
    'ListItemConfig', 'ListItemDivider', 'ListItemSection',
    'MYList'
]

from enum import Enum
from typing import Optional, Any, Type

from kivy.metrics import sp
from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.divider import MDDivider
from kivymd.uix.dropdownitem import MDDropDownItem, MDDropDownItemText
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.segmentedbutton import MDSegmentedButton, MDSegmentedButtonItem, MDSegmentButtonLabel
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText, MDTextFieldHelperText

from mysc.gui.k.defs import init_language

_ = init_language()


class ListItemBase(ButtonBehavior, MDBoxLayout):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.orientation = 'horizontal'
        self.adaptive_height = True


class ListItemConfig(ListItemBase):
    """
        配置项
    """

    def __init__(
            self,
            key: str,
            value_type: Type[
                bool | str | int | float | Enum
            ],
            value: Optional[Any] = None,
            label: Optional[str] = None,
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.key = key
        self.value_type = value_type
        self.value = value
        self.label = label or key

        self.value_widget = None

        if self.value_type is bool:
            self.add_widget(MDLabel(text=self.label, size_hint_x=0.7))
            self.value_widget = MDSwitch()
            if self.value is not None:
                self.value_widget.active = self.value
            self.bind(on_release=lambda *_args: self.value_widget.dispatch('on_release'))
            self.value_widget.bind(active=lambda _w, _nv: self.__setattr__('value', _nv))

        elif self.value_type is str:
            self.value_widget = MDTextField(
                MDTextFieldHintText(text=self.label),
                MDTextFieldHelperText(text=_('Str')),
                mode='filled'
            )
            if self.value:
                self.value_widget.text = self.value
            self.value_widget.bind(
                text=lambda _w, _nv: self.__setattr__(
                    'value', self.value_type(_nv) if _nv != '' else None
                )
            )

        elif self.value_type is int:
            self.value_widget = MDTextField(
                MDTextFieldHintText(text=self.label),
                MDTextFieldHelperText(text=_('Int')),
                mode='filled', input_filter='int', input_type='number'
            )
            if self.value:
                self.value_widget.text = str(self.value)
            self.value_widget.bind(
                text=lambda _w, _nv: self.__setattr__(
                    'value', self.value_type(_nv) if _nv != '' else None
                )
            )

        elif self.value_type is float:
            self.value_widget = MDTextField(
                MDTextFieldHintText(text=self.label),
                MDTextFieldHelperText(text=_('Float')),
                mode='filled', input_filter='float', input_type='number'
            )
            if self.value:
                self.value_widget.text = str(self.value)
            self.value_widget.bind(text=lambda _w, _nv: self.__setattr__(
                'value', self.value_type(_nv) if _nv != '' else None
            ))

        elif issubclass(self.value_type, Enum):

            self.add_widget(MDLabel(text=self.label, size_hint_x=0.3))

            if len(self.value_type) < 4:
                self.value_widget = MDSegmentedButton()

                def on_click(button):
                    if button.v_item == self.value:
                        button.active = False
                        self.value = None
                    else:
                        self.value = button.v_item

                for item in self.value_type:
                    _btn_item = MDSegmentedButtonItem(
                        MDSegmentButtonLabel(text=str(item)),
                        on_release=on_click
                    )
                    _btn_item.v_item = item
                    self.value_widget.add_widget(_btn_item)
                    if item == self.value:
                        _btn_item.active = True

            else:

                def on_click(selected_item):
                    menu_items = [{
                        'text': str(enum_item),
                        'on_release': lambda x=enum_item: dropdown_menu.dismiss() or menu_callback(x)
                    } for enum_item in self.value_type]
                    dropdown_menu = MDDropdownMenu(caller=selected_item, items=menu_items)
                    dropdown_menu.open()

                def menu_callback(enum_item):
                    self.value = enum_item
                    self.selected_item.text = str(enum_item)

                self.value_widget = MDDropDownItem(on_release=on_click)
                self.selected_item = MDDropDownItemText()
                self.value_widget.add_widget(self.selected_item)

                if self.value is not None:
                    self.selected_item.text = str(self.value)
                else:
                    self.selected_item.text = self.label

        else:
            raise TypeError(f"{self.value_type} is not supported.")

        self.add_widget(self.value_widget)


class ListItemDivider(ListItemBase):
    """
        Divider
    """
    def __init__(self, divider: Optional[Any] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_widget(MDDivider() if divider is None else divider)


class ListItemSection(ListItemBase):
    """
        Section
    """
    def __init__(self, key: str, button, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_widget(MDLabel(text=key, size_hint_x=0.5))
        self.add_widget(button)
        self.bind(on_release=lambda *_args: button.dispatch('on_release'))


class MYList(MDScrollView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.do_scroll_x = False
        self.layout = MDBoxLayout(adaptive_height=True, spacing=sp(25), padding=sp(10), orientation='vertical')
        self.add_widget(self.layout)

        self.items: list[ListItemBase] = []

    def add_list_item(self, item: ListItemBase):
        """
            增加Item
        :param item:
        :return:
        """
        self.items.append(item)
        self.layout.add_widget(item)

    def insert_list_item(self, index: int, item: ListItemBase):
        """
            插入Item
        :param index:
        :param item:
        :return:
        """
        self.items.insert(index, item)
        self.layout.add_widget(item, index=index)

    def remove_list_item(self, item: ListItemBase):
        """
            移除Item
        :param item:
        :return:
        """
        if item in self.items:
            self.items.remove(item)
            self.layout.remove_widget(item)

    def clear(self):
        """
            清空
        :return:
        """
        self.items = []
        self.layout.clear_widgets()

    def to_dict(self) -> dict:
        """
            输出列表字典值
        :return:
        """
        return {item.key: item.value for item in self.items if isinstance(item, ListItemConfig)}
