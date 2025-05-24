# -*- coding: utf-8 -*-
"""
    main
    ~~~~~~~~~~~~~~~~~~
    
    Log:
        2025-05-24 3.2.1 Me2sY  重置配置文件位置

        2025-05-09 3.2.0 Me2sY  增加配置文件窗口

        2025-04-21 0.1.0 Me2sY 创建
"""

__author__ = 'Me2sY'
__version__ = '3.2.1'

__all__ = []

from dataclasses import dataclass, field
from functools import partial
import json
import threading

from adbutils import AdbDevice, adb

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import sp
from kivy.storage.dictstore import DictStore
from kivy.config import Config

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout

from myscrcpy.gui.k import FONT_ZH, create_snack, MYCombineColors, StoredConfig, MYColor
from myscrcpy.gui.k.components.bottom_bar import BottomBar
from myscrcpy.gui.k.components.side_panel import SidePanel
from myscrcpy.gui.k.components.device_panel import DevicePanel, WifiConnectDialog
from myscrcpy.gui.k.components.connect_manager import ConnectManager
from myscrcpy.gui.k.handler.device_handler import MYDevice
from myscrcpy.utils import Param

Config.set('kivy', 'exit_on_escape', 0)
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')


@dataclass
class MainConfig(StoredConfig):
    """
        MainAppConfig
    """

    _STORAGE_KEY = 'main'

    # 连接历史
    connect_history: list[tuple[str, str]] = field(default_factory=list)


class MainGui(MDBoxLayout):

    DICT_STORE = DictStore(Param.PATH_CONFIGS / 'mysc__main.dsf')

    def __init__(self, app: 'MainGuiApp', **kwargs):
        super(MainGui, self).__init__(**kwargs)

        self.app = app

        self.orientation = 'vertical'

        self.main_cfg = MainConfig.load(self.DICT_STORE)

        self.bottom_bar = BottomBar(self.cb__connect_device, self.cb__bottom_bar)
        self.side_panel = SidePanel(self.app.theme_cls.primaryColor, self.cb__side_panel)

        self.main_box = MDBoxLayout(orientation='horizontal')
        self.add_widget(self.main_box)

        self.connect_manager = ConnectManager(self, self.main_cfg, self.rotation_callback, size_hint=(1, 1))

        self.main_box.add_widget(self.side_panel)
        self.main_box.add_widget(self.connect_manager)

        self.add_widget(self.bottom_bar)

        self.side_panel.add_widget(self.connect_manager.create__indicator_button())
        self.side_panel.add_widget(self.connect_manager.create__keyboard_button())
        self.side_panel.add_widget(self.connect_manager.create__mouse_button())
        self.side_panel.add_widget(self.connect_manager.create__screen_switch_button())

        Window.set_title('MYScrcpy - Me2sY')
        Window.size = (450, 650)

        def set_bottom_bar_status(*args):
            if self.connect_manager.is_empty:
                self.bottom_bar.on_no_device_connected()
            else:
                self.bottom_bar.on_device_connected()

        self.connect_manager.bind(current=set_bottom_bar_status)

        if self.app.config.getboolean('RunEnv', 'auto_reconnect'):
            Clock.schedule_once(self.auto_reconnect, 1)

    def auto_reconnect(self, *args):
        """
            登录时自动重连上次连接设备
        :param args:
        :return:
        """
        try:
            serial, cfg_name = self.main_cfg.connect_history[0]
            for _ in adb.device_list():
                if serial == _.serial:
                    self.cb__connect_device(_, cfg_name)
                    break
        except:
            ...

    def cb__connect_device(self, device: AdbDevice, cfg_name: str):
        """
            设备连接回调
        :param device:
        :param cfg_name:
        :return:
        """
        create_snack(f"{device.serial}\n设备连接中", color=MYCombineColors.orange).open()
        Clock.schedule_once(partial(self._connect, device, cfg_name), 1)

    def _connect(self, device: AdbDevice, cfg_name: str, *args):
        """
            创建连接
        :param device:
        :param cfg_name:
        :param args:
        :return:
        """
        # 清除原有Session及Screen
        cs = self.connect_manager.start_session(MYDevice(device), cfg_name)
        self.connect_manager.current = cs.session_name

    def cb__side_panel(self, adb_code: int, *args):
        """
            Side Panel 发送 ADB 控制指令
        :param adb_code:
        :return:
        """
        if self.connect_manager.current_session:
            threading.Thread(
                target=self.connect_manager.current_session.my_device.adb_dev.keyevent, args=(adb_code,)
            ).start()

    def rotation_callback(self, *args): ...

    def cb__bottom_bar(self, func_name: str, btn_instance):
        """
            Bottom Bar Button Function Callback
        :param func_name:
        :param btn_instance:
        :return:
        """
        if func_name == self.bottom_bar.CALLBACK_SETTINGS:
            self.app.open_settings()

        elif func_name == self.bottom_bar.CALLBACK_EDIT_CFG:    # 编辑当前配置文件
            DevicePanel(
                self.connect_manager.current_session.my_device.adb_dev,
                self.cb__connect_device,
                self.connect_manager.current_session.cfg_name,
                delete_callback=self.cb__bottom_bar_delete
            ).open()

        elif func_name == self.bottom_bar.CALLBACK_CLOSE_DEVICE:    # 关闭当前连接
            self.connect_manager.stop_current_session()

            create_snack(f"连接关闭", color=MYCombineColors.orange).open()

        elif func_name == self.bottom_bar.CALLBACK_LIST_SESSION:    # 选择Session
           self.connect_manager.create__cs_list_dropdown(btn_instance).open()

        elif func_name == self.bottom_bar.CALLBACK_FIT_SIZE:        # 调整界面大小
            self.connect_manager.create__resize_dropdown(btn_instance).open()

        elif func_name == self.bottom_bar.CALLBACK_HISTORY:         # 连接历史
            self.connect_manager.create__history_dropdown(btn_instance).open()

        elif func_name == self.bottom_bar.CALLBACK_WIFI:            # 连接 WIFI ADB
            WifiConnectDialog().open()

    def cb__bottom_bar_delete(self, my_device: MYDevice, cfg_name: str):
        """
            删除配置文件
        :param my_device:
        :param cfg_name:
        :return:
        """
        session_name = f"{my_device.connect_serial}_{cfg_name}"
        self.connect_manager.stop_session(session_name)
        create_snack(f"{my_device.connect_serial} {cfg_name} 已删除", color=MYCombineColors.red).open()


class MainGuiApp(MDApp):
    """
        App
    """

    def build(self):

        # 颜色风格
        _style = self.config.getdefault('RunEnv', 'theme_style', 'Light')
        if _style == '黑暗':
            _style = 'Dark'
        else:
            _style = 'Light'

        self.theme_cls.theme_style = _style

        # 设置字体
        self.theme_cls.font_styles[FONT_ZH] = {
            "large": {
                "line-height": 1.4,
                "font-name": FONT_ZH,
                "font-size": sp(13),
            },
            "medium": {
                "line-height": 1.3,
                "font-name": FONT_ZH,
                "font-size": sp(12),
            },
            "small": {
                "line-height": 1.2,
                "font-name": FONT_ZH,
                "font-size": sp(11),
            },
        }

        self.title = 'MYScrcpy - Me2sY'
        self.icon = Param.PATH_STATICS_ICON.__str__()


        Window.clearcolor = MYColor.grey
        Window.raise_window()
        Window.show()
        self.main_gui = MainGui(self)
        return self.main_gui

    def build_config(self, config):
        """
            配置项
        :param config:
        :return:
        """
        config.setdefaults('RunEnv', {
            'auto_reconnect': True,
            'theme_style': 'Light'
        })

    def build_settings(self, settings):
        """
            配置界面
        :param settings:
        :return:
        """
        config_json = [
            {
                "type": "title",
                "title": "运行配置"
            },
            {
                "type": "bool",
                "title": "自动重连",
                "desc": "启动后自动重连上次设备",
                "section": "RunEnv",
                "key": "auto_reconnect"
            },
            {
                "type": "options",
                "title": "界面风格",
                "desc": "明亮/黑暗",
                "section": "RunEnv",
                "key": "theme_style",
                "options": ["明亮", "黑暗"]
            }
        ]
        settings.add_json_panel('MYScrcpy', self.config, data=json.dumps(config_json))

    def on_config_change(self, config, section, key, value):
        """
            配置文件修改
        :param config:
        :param section:
        :param key:
        :param value:
        :return:
        """
        if config is self.config:
            if section == 'RunEnv' and key == 'theme_style':
                self.theme_cls.theme_style = 'Light' if value == '明亮' else 'Dark'

    def get_application_config(self, defaultpath='%(appdir)s/%(appname)s.ini'):
        """
            更改默认配置文件位置，避免权限问题导致无法写入
        :param defaultpath:
        :return:
        """
        return super(MainGuiApp, self).get_application_config(
            Param.PATH_CONFIGS.__str__() + '/%(appname)s.ini')


def run():
    MainGuiApp().run()


if __name__ == '__main__':
    MainGuiApp().run()