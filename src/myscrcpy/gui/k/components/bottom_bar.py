# -*- coding: utf-8 -*-
"""
    bottom_bar
    ~~~~~~~~~~~~~~~~~~
    底部栏

    Log:
        2025-05-24 3.2.1 Me2sY
            1.重写 resize 方法，屏蔽 Kivy BUG
            2.增加友好提示，提示启动 ADB

        2025-05-06 3.2.0 Me2sY  去除单独中文引用

        2025-04-21 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '3.2.1'

__all__ = [
    "BottomBar"
]

import datetime
from functools import partial
from typing import Callable, Any

from adbutils import AdbDevice

from kivy import Logger
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import sp
from kivy.uix.widget import Widget

from kivymd.uix.appbar import MDBottomAppBar, MDActionBottomAppBarButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText, MDButtonIcon
from kivymd.uix.dialog import (
    MDDialog, MDDialogHeadlineText, MDDialogSupportingText, MDDialogIcon, MDDialogContentContainer,
    MDDialogButtonContainer
)
from kivymd.uix.divider import MDDivider
from kivymd.uix.list import MDListItem, MDListItemLeadingIcon, MDListItemSupportingText, MDListItemHeadlineText
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.scrollview import MDScrollView

from myscrcpy.gui.k import create_snack, MYCombineColors
from myscrcpy.gui.k.components.device_panel import DevicePanel
from myscrcpy.gui.k.handler.device_handler import MYDevice, DeviceConnectMode
from myscrcpy.utils import Param


def list_cfgs(serial_no: str):
    """
        列出配置文件
    :param serial_no:
    :return:
    """
    return [[fp.stem.split('_')[2], fp] for fp in Param.PATH_CONFIGS.glob(f"ky_{serial_no}_*.json")]


class DeviceConnectionConfigList(MDDialog):

    def __init__(self, device: AdbDevice, selected_callback: Callable[[AdbDevice, str], None], **kwargs):
        """
            设备连接配置文件列表
        :param device:
        :param selected_callback:
        :param kwargs:
        """
        super().__init__(**kwargs)

        self.device = device
        self.selected_callback = selected_callback

        self.add_widget(MDDialogIcon(icon="file-cog-outline"))
        self.add_widget(MDDialogHeadlineText(text=device.serial))
        self.add_widget(MDDialogSupportingText(text='创建或选择配置文件'))

        container = MDDialogContentContainer(MDDivider(), orientation='vertical')

        layout_scroll = MDScrollView(do_scroll_x=False, size_hint=(1, None), height=sp(180))
        self.layout_items = MDBoxLayout(adaptive_height=True, orientation='vertical')
        layout_scroll.add_widget(self.layout_items)

        self.load_cfg_items()

        container.add_widget(layout_scroll)
        container.add_widget(MDDivider())

        self.add_widget(container)

        self.add_widget(
            MDDialogButtonContainer(
                MDButton(MDButtonIcon(icon='plus'), MDButtonText(text="创建"), on_press=self._create),
                Widget(),
                MDButton(
                    MDButtonIcon(icon='close', theme_icon_color='Custom', icon_color='red'),
                    MDButtonText(text="关闭", theme_text_color='Custom', text_color='red'),
                    on_press=self.dismiss,
                ),
            )
        )

    def load_cfg_items(self):
        """
            加载并绘制配置文件
        :return:
        """

        self.layout_items.clear_widgets()

        for cfg_name, cfg_fp in list_cfgs(self.device.serial):
            item = MDListItem(
                MDListItemLeadingIcon(icon='file-cog-outline'),
                MDListItemHeadlineText(text=cfg_name),
                MDListItemSupportingText(
                    text=f"创建时间:{datetime.datetime.fromtimestamp(cfg_fp.stat().st_ctime).strftime('%Y-%m-%d %H:%M:%S')}",
                ), divider=True,
                pos_hint={'center_x': .5, 'center_y': .5},
            )
            item.bind(on_press=lambda ins, _=cfg_name, __=item: self._select(_, __), )
            self.layout_items.add_widget(item)

    def _select(self, cfg_name: str, item: MDListItem):
        """
            生成操作菜单菜单
        :param cfg_name:
        :return:
        """
        items = [
            dict(
                text='发起连接', leading_icon='link',
                on_release=lambda _=cfg_name: mdm.dismiss() or self.dismiss() or self.selected_callback(self.device, _)
            ),
            dict(
                text='编辑配置', leading_icon='file-edit-outline',
                on_release=lambda _=cfg_name: mdm.dismiss() or self.dismiss() or self._edit(_)
            ),
            dict(
                text='删除配置', leading_icon='delete',
                on_release=lambda _=cfg_name: mdm.dismiss() or self._delete(_)
            ),
        ]
        mdm = MDDropdownMenu(caller=item, items=items)
        mdm.open()

    def _delete(self, cfg_name: str):
        """
            删除配置文件
        :param cfg_name:
        :return:
        """
        def delete(*args):
            fp = Param.PATH_CONFIGS.joinpath(f"ky_{self.device.serial}_{cfg_name}.json")
            fp.unlink()
            self.load_cfg_items()
            Logger.warning(f"Config file deleted: {fp}")
            dialog.dismiss()

        btn_cancel = MDButton(MDButtonText(text='取消'))

        dialog = MDDialog(
            MDDialogHeadlineText(text=f"删除 {cfg_name} ?"),
            MDDialogButtonContainer(
                Widget(),
                btn_cancel,
                MDButton(
                    MDButtonText(text='确认', theme_text_color='Custom', text_color='red'),
                    on_release=delete
                ),
            )
        )
        btn_cancel.bind(on_release=dialog.dismiss)
        dialog.open()

    def _create(self, *args):
        """
            创建新配置
        :return:
        """
        self.dismiss()
        i = 1
        while Param.PATH_CONFIGS.joinpath(f"ky_{self.device.serial}_Default{i}.json").exists():
            i += 1
        cfg_name = 'Default' + str(i)
        dp = DevicePanel(self.device, connect_callback=self.selected_callback, cfg_name=cfg_name, is_new=True)
        dp.open()

    def _edit(self, cfg_name: str):
        """
            编辑配置文件
        :param cfg_name:
        :return:
        """
        DevicePanel(self.device, connect_callback=self.selected_callback, cfg_name=cfg_name).open()


Builder.load_string('''
#:kivy 2.3.0
#:import MDActionBottomAppBarButton kivymd.uix.appbar.MDActionBottomAppBarButton

<BottomBar>:
    height: dp(66)

    MDFabBottomAppBarButton:
        id: connection_button
        icon: "cellphone"
        on_press: root.select_device(self)
        style: "small"
        size: dp(30), dp(30)
''')


class BottomBar(MDBottomAppBar):

    CALLBACK_SETTINGS = 'cogs'
    CALLBACK_WIFI = 'wifi-plus'
    CALLBACK_HISTORY = 'history'

    CALLBACK_EDIT_CFG = 'file-cog-outline'
    CALLBACK_LIST_SESSION = 'list-box'
    CALLBACK_FIT_SIZE = 'resize'
    CALLBACK_CLOSE_DEVICE = 'close-box'

    MODE_MOBILE = 1
    MODE_NONE = 0

    def __init__(self,
                 selected_callback: Callable[[AdbDevice, str], None],
                 action_callback: Callable[[str, Any], None], **kwargs):
        """
            底部栏，提供共用功能按键
        :param selected_callback:
        :param action_callback:
        :param kwargs:
        """
        super().__init__(**kwargs)

        self.height = sp(35)

        self.selected_callback = selected_callback
        self.action_callback = action_callback
        self.action_items = [
            MDActionBottomAppBarButton(
                icon=_, on_release=lambda *args, cb=_: self.action_callback(cb, args[0])
            ) for _ in [
                self.CALLBACK_SETTINGS, self.CALLBACK_WIFI, self.CALLBACK_HISTORY
            ]
        ]

        self.mode = self.MODE_NONE

    def on_size(self, *args) -> None:
        """
            2025-05-24 3.2.1 Me2sY 暂时屏蔽 Kivy Resize Bug
        :param args:
        :return:
        """
        try:
            super().on_size(*args)
        except Exception:
            ...

    def select_device(self, caller):
        """
            选择设备
        :param caller:
        :return:
        """
        items = []

        def _open(*args, **kwargs):
            create_snack('加载设备列表中\n请耐心等待', MYCombineColors.orange, duration=1).open()

        Clock.schedule_once(_open, 0)
        Clock.schedule_once(partial(self._select_device, caller), 0.5)

    def _select_device(self, caller, *args):
        items = []
        for device in MYDevice.list_devices():
            items.append({
                'text': device.connect_serial + (
                    '/' + device.serial if device.connect_mode == DeviceConnectMode.WLAN else ''
                ),
                'leading_icon': 'wifi' if device.connect_mode == DeviceConnectMode.WLAN else 'usb',
                'on_release': lambda _d=device: menu.dismiss() or self.select_cfg(_d, menu)
            })

        menu = MDDropdownMenu(caller=caller, items=items, hor_growth='left')
        menu.open()

    def select_cfg(self, device: MYDevice, menu: MDDropdownMenu):
        """
            选择配置文件窗口
        :param device:
        :param menu:
        :return:
        """
        DeviceConnectionConfigList(device.adb_dev, self.load_cfg).open()

    def load_cfg(self, device: AdbDevice, cfg_name: str):
        """
            加载配置文件
        :param device:
        :param cfg_name:
        :return:
        """
        self.selected_callback(device, cfg_name)
        self.on_device_connected()

    def on_device_connected(self):
        """
            添加功能按钮
        :return:
        """
        if self.mode == self.MODE_NONE:
            self.action_items = [
                MDActionBottomAppBarButton(
                    icon=_, on_release=lambda i, func=_: self.action_callback(func, i)
                ) for _ in [
                    self.CALLBACK_SETTINGS, self.CALLBACK_WIFI, self.CALLBACK_HISTORY,
                    self.CALLBACK_EDIT_CFG, self.CALLBACK_LIST_SESSION,
                    self.CALLBACK_FIT_SIZE,
                    self.CALLBACK_CLOSE_DEVICE
                ]
            ]
            self.mode = self.MODE_MOBILE

    def on_no_device_connected(self):
        """
            隐藏功能按钮
        :return:
        """
        if self.mode == self.MODE_MOBILE:
            self.action_items = [
                MDActionBottomAppBarButton(
                    icon=_, on_release=lambda *args, cb=_: self.action_callback(
                        cb, args[0]
                    )
                ) for _ in [
                    self.CALLBACK_SETTINGS, self.CALLBACK_WIFI, self.CALLBACK_HISTORY
                ]
            ]
            self.mode = self.MODE_NONE
