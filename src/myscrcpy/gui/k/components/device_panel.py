# -*- coding: utf-8 -*-
"""
    device_panel
    ~~~~~~~~~~~~~~~~~~
    
    Log:
        2025-05-09 3.2.0 Me2sY
            1.将AdvDevice 切换至 MYDevice
            2.2025-05-10 去掉单独中文引用

        2025-04-21 0.1.0 Me2sY 创建，懒了;)，没做KivyMD美观处理
"""

__author__ = 'Me2sY'
__version__ = '3.2.0'

__all__ = [
    'load_cfg', 'DevicePanel', 'WifiConnectDialog'
]

from functools import partial
import threading
from typing import Callable
import re

from adbutils import adb, AdbDevice

from kivy import Logger
from kivy.clock import Clock
from kivy.metrics import sp
from kivy.storage.jsonstore import JsonStore
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.layout import Layout
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from kivymd.uix.button import MDButton, MDButtonText, MDButtonIcon
from kivymd.uix.dialog import MDDialog, MDDialogIcon, MDDialogHeadlineText, MDDialogSupportingText, \
    MDDialogContentContainer, MDDialogButtonContainer
from kivymd.uix.divider import MDDivider
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
from kivymd.uix.textfield import MDTextField, MDTextFieldMaxLengthText, MDTextFieldHintText

from myscrcpy.core import VideoArgs, CameraArgs, AudioArgs, ControlArgs, AudioAdapter
from myscrcpy.gui.k.handler.device_handler import MYDevice
from myscrcpy.utils import Param
from myscrcpy.gui.k import MYStyledButton, MYCombineColors, IntInput, create_snack


def load_cfg(serial: str, cfg_name: str) -> tuple[bool, tuple[VideoArgs, AudioArgs, ControlArgs] | None]:
    """
        加载配置文件
    :param serial:
    :param cfg_name:
    :return:
    """
    fp = Param.PATH_CONFIGS.joinpath(f"ky_{serial}_{cfg_name}.json")
    if not fp.exists():
        return False, None
    else:
        js = JsonStore(fp.__str__())
        video_args = VideoArgs.load(**js.get('va'))
        audio_args = AudioArgs.load(**js.get('aa'))
        control_args = ControlArgs.load(**js.get('ca'))

    return True, (video_args, audio_args, control_args,)


class WifiConnectDialog(MDDialog):

    def __init__(self, **kwargs):
        """
            连接无线设备窗口
        :param kwargs:
        """
        super().__init__(**kwargs)

        self.add_widget(MDDialogIcon(icon='wifi-plus'))
        self.add_widget(MDDialogHeadlineText(text='连接无线设备'))
        self.add_widget(MDDialogSupportingText(text='连接前确保设备已开启ADB无线端口'))

        container = MDDialogContentContainer(MDDivider(), orientation='vertical')

        self.ipt = MDTextField(
            MDTextFieldHintText(text='格式 x.x.x.x:xxx'),
            MDTextFieldMaxLengthText(max_text_length=21),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            multiline=False, mode='filled'
        )
        container.add_widget(self.ipt)

        self.add_widget(container)

        self.add_widget(
            MDDialogButtonContainer(
                MDButton(
                    MDButtonIcon(icon='connection'),
                    MDButtonText(text="连接"), on_press=self.connect,
                ),
                Widget(),
                MDButton(
                    MDButtonIcon(icon='close', theme_icon_color='Custom', icon_color='red'),
                    MDButtonText(text="关闭", theme_text_color='Custom', text_color='red'),
                    on_press=self.dismiss,
                ),
            )
        )

    @staticmethod
    def validation(ip_port: str) -> bool:
        """
            校验输入格式
        :param ip_port:
        :return:
        """
        pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):([0-9]{1,5})$'
        f = bool(re.match(pattern, ip_port))
        if f:
            ip, port = ip_port.split(':')
            if int(port) < 0 or int(port) > 65535:
                f = False
        return f

    def connect(self, *args):
        """
            创建连接
        :param args:
        :return:
        """

        text = self.ipt.text
        if not self.validation(text):
            self.ipt.error = True
            create_snack('格式错误', color=MYCombineColors.red).open()

        else:
            self.dismiss()
            threading.Thread(target=adb.connect, args=(text, 5)).start()
            create_snack('尝试连接中\n请稍等后选择', color=MYCombineColors.green).open()


class DeviceInfo(GridLayout):

    item_height = sp(30)

    class KeyLabel(Label):

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.size_hint = (None, None)
            self.width = sp(80)
            self.height = DeviceInfo.item_height

    def __init__(self, my_device: MYDevice, wifi_callback: Callable, **kwargs):
        """
            显示设备信息
        :param my_device:
        :param kwargs:
        """
        super().__init__(**kwargs)

        self.height = self.item_height * 3

        self.device = my_device
        self.wifi_callback = wifi_callback

        self.cols = 4

        self.add_widget(self.KeyLabel(text='serial:'))
        self.add_widget(Label(text=f"{self.device.adb_dev.serial}", font_size=sp(11)))

        for key in ['brand', 'release', 'model']:
            self.add_widget(self.KeyLabel(text=f"{key}:"))
            self.add_widget(Label(text=f"{getattr(self.device.device_info, key)}", font_size=sp(11)))

        self.add_widget(self.KeyLabel(text='wlan:'))
        self.add_widget(Label(text=f"{self.device.wlan_ip}", font_size=sp(11)))

        self.port = IntInput(hint_text='Wifi Port', size_hint=(None, 1), width=sp(80))

        port = self.device.port
        if port:
            self.port.text = str(port)

        self.add_widget(self.port)
        self.add_widget(
            Button(text='启动无线', on_press=self.connect_wifi, size_hint=(.9, 1))
        )

    def connect_wifi(self, *args):
        """
            开启 TCPIP 模式
        :param args:
        :return:
        """
        if self.port.text != '':
            port = int(self.port.text)
            if port < 0 or port > 65535:
                Logger.warning(f"Error: Port {port} is out of range")
            else:
                addr = self.device.wlan_ip + ':' + str(port)
                self.wifi_callback(addr)
                self.device.adb_dev.tcpip(port)
                threading.Thread(target=adb.connect, args=(addr,)).start()
                create_snack('开启无线端口并尝试连接\n请稍等后重新选择').open()


class ArgsPanel(TabbedPanelItem):

    item_height = sp(45)

    def __init__(self, connect_args, **kwargs):
        """
            配置面板
        :param connect_args:
        :param kwargs:
        """
        super().__init__(**kwargs)

        self.args = connect_args

        # 定义Scroll Grid View
        self.layout = GridLayout(cols=2, spacing=sp(5), padding=sp(2), size_hint_y=None)
        self.layout.bind(minimum_height=self.layout.setter('height'))

        scroll_view = ScrollView(do_scroll_x=False)
        scroll_view.add_widget(self.layout)
        self.add_widget(scroll_view)

        # 添加激活按钮
        self.add_activate()

    def add_item(self, name: str, content: Widget | Layout):
        """
            添加选项
        :param name:
        :param content:
        :return:
        """
        self.layout.add_widget(
            Label(text=name, size_hint=(None, None), width=sp(90), height=self.item_height)
        )
        self.layout.add_widget(content)

    def add_activate(self):
        """
            添加激活按钮
        :return:
        """
        btn_activated = Switch(
            active=self.args.is_activate, size_hint=(None, None), width=sp(100), height=self.item_height
        )
        btn_activated.bind(active=lambda instance, value: setattr(self.args, 'is_activate', value))
        self.add_item('连接', btn_activated)


class VideoArgsPanel(ArgsPanel):

    def __init__(self, video_args: VideoArgs, real_max_size:int = 2560, **kwargs):
        """
            视频连接参数
        :param video_args:
        :param real_max_size:
        :param kwargs:
        """
        super().__init__(connect_args=video_args, **kwargs)
        self.text = '视频配置'

        self.add_max_size(real_max_size)
        self.add_fps()
        self.add_video_codec()
        self.add_source()

    def add_max_size(self, real_max_size: int):
        """
            添加 Max Size 控件
        :param real_max_size:
        :return:
        """

        def set_value(*args):
            if len(args) < 2:
                instance = args[0]
                value = instance.text
            else:
                instance, value = args

            try:
                _value = int(value)

                if _value < 0:
                    Logger.warning(f"Error: Value {value} is out of range")
                    raise ValueError

                _value = min(_value, real_max_size)
                self.args.max_size = _value

                if instance == max_size_slider:
                    max_size_ipt.text = str(_value)
                else:
                    max_size_slider.value = _value

            except:
                instance.text = str(int(max_size_slider.value))

        max_size_ipt = IntInput(
            text=f"{self.args.max_size}", size_hint_x=None, width=sp(50), multiline=False, on_text_validate=set_value
        )

        max_size_slider = Slider(min=0, max=real_max_size, value=self.args.max_size, step=1)
        max_size_slider.bind(value=set_value)

        content_layout = BoxLayout(size_hint=(1, None), height=self.item_height)
        content_layout.add_widget(max_size_ipt)
        content_layout.add_widget(max_size_slider)

        self.add_item('max_size\n(0为全屏)', content_layout)

    def add_fps(self):
        """
            FPS 控件
        :return:
        """

        def set_value(*args):
            if len(args) < 2:
                instance = args[0]
                value = instance.text
            else:
                instance, value = args

            try:
                _value = int(value)

                _fps = max(1, min(480, _value))

                self.args.fps = _fps

                if instance == fps_slider:
                    fps_label_ipt.text = str(_fps)
                else:
                    fps_slider.value = _fps

            except:
                instance.text = str(int(fps_slider.value))

        fps_label_ipt = IntInput(
            text=f"{self.args.fps}", size_hint_x=None, width=sp(50), multiline=False,
            on_text_validate=set_value
        )
        fps_slider = Slider(min=1, max=480, value=self.args.fps, step=1)
        fps_slider.bind(value=set_value)

        content_layout = BoxLayout(size_hint=(1, None), height=self.item_height)
        content_layout.add_widget(fps_label_ipt)
        content_layout.add_widget(fps_slider)

        self.add_item('fps', content_layout)

    def add_video_codec(self):
        """
            添加 Video Codec
        :return:
        """
        codecs = (VideoArgs.CODEC_H264, VideoArgs.CODEC_H265,)
        spinner = Spinner(
            text=self.args.video_codec, values=codecs, size_hint=(1, None), height=self.item_height,
            # option_cls=ZHOption
        )
        spinner.bind(text=lambda instance, value: setattr(self.args, 'video_codec', value))
        self.add_item('Codec', spinner)

    def add_source(self):
        """
            添加视频来源
        :return:
        """
        def set_source(tabbed_panel, item):
            """
                设置来源
            :param tabbed_panel:
            :param item:
            :return:
            """
            self.args.video_source = VideoArgs.SOURCE_DISPLAY if item == screen_panel else VideoArgs.SOURCE_CAMERA
            if self.args.video_source == VideoArgs.SOURCE_CAMERA:
                camera_args = CameraArgs()
                try:
                    if not cmd_ipt.text == '':
                        for arg in cmd_ipt.text.split(' '):
                            k, v = arg.split('=')
                            k = k[2:].replace('-', '_')

                            if k == 'camera_id':
                                camera_args.camera_id = int(v)
                            elif k == 'camera_fps':
                                camera_args.camera_fps = int(v)
                            elif k == 'camera_ar':
                                camera_args.camera_ar = str(v)
                            elif k == 'camera_size':
                                camera_args.camera_size = str(v)
                            else:
                                continue
                except Exception as e:
                    Logger.warning(f"Parser Camera Cmd Error: {e}")
                self.args.camera = camera_args
            else:
                self.args.camera = None

        source_tab = TabbedPanel(
            do_default_tab=False, size_hint_y=None, height=self.item_height * 2,
            tab_height=self.item_height, tab_width=sp(50)
        )
        source_tab.bind(current_tab=set_source)

        screen_panel = TabbedPanelItem(text='屏幕')
        camera_panel = TabbedPanelItem(text='摄像头')

        source_tab.add_widget(screen_panel)
        source_tab.add_widget(camera_panel)

        cmd_ipt = TextInput(multiline=False, hint_text='--camera-id=1 ... 参考Scrcpy格式')

        # 解析 Camera 启动命令
        if self.args.video_source == VideoArgs.SOURCE_CAMERA:
            cmd = ''
            for key, value in self.args.camera.dump().items():
                cmd += f"--{key.replace('_', '-')}={value} "
            cmd_ipt.text = cmd

        camera_panel.add_widget(cmd_ipt)

        Clock.schedule_once(partial(
            source_tab.switch_to,
            screen_panel if self.args.video_source == VideoArgs.SOURCE_DISPLAY else camera_panel,
        ), 0)

        self.add_item('图像来源', source_tab)


class AudioArgsPanel(ArgsPanel):

    def __init__(self, audio_args: AudioArgs, **kwargs):
        super().__init__(connect_args=audio_args, **kwargs)
        self.text = '音频配置'

        self.output_device = None

        self.add_source()
        self.add_codec()
        self.add_device()

    def add_source(self):
        """
            添加音频来源
        :return:
        """
        source = (AudioArgs.SOURCE_OUTPUT, AudioArgs.SOURCE_MIC,)
        spinner = Spinner(text=self.args.audio_source, values=source, size_hint=(1, None), height=self.item_height)
        spinner.bind(text=lambda instance, value: setattr(self.args, 'audio_source', value))
        self.add_item('音频来源', spinner)

    def add_codec(self):
        """
            添加音频解码器
        :return:
        """
        codec = (AudioArgs.CODEC_RAW, AudioArgs.CODEC_FLAC, AudioArgs.CODEC_OPUS)
        spinner = Spinner(text=self.args.audio_codec, values=codec, size_hint=(1, None), height=self.item_height)
        spinner.bind(text=lambda instance, value: setattr(self.args, 'audio_codec', value))
        self.add_item('Codec', spinner)

    def add_device(self):
        """
            添加播放设备选择
        :return:
        """
        devices = AudioAdapter.get_output_devices()
        devices_name = [_['name'] for _ in devices]

        if self.args.device_index is None:
            device = AudioAdapter.get_default_device()
        else:
            device = AudioAdapter.get_output_device_info_by_index(self.args.device_index)

        audio_device = Spinner(text=device['name'], values=devices_name)

        audio_device.bind(text=lambda instance, value: setattr(
            self.args, 'device_index', AudioAdapter.get_device_index_by_name(value)
        ))

        self.add_item('播放设备', audio_device)


class ControlArgsPanel(ArgsPanel):

    def __init__(self, control_args: ControlArgs, **kwargs):
        """
            控制参数
        :param control_args:
        :param kwargs:
        """
        super().__init__(connect_args=control_args, **kwargs)

        self.text = '控制配置'

        self.add_screen_status()
        self.add_clipboard()

    def add_screen_status(self):
        """
            连接时屏幕状态
        :return:
        """
        status = (ControlArgs.STATUS_KEEP, ControlArgs.STATUS_OFF, ControlArgs.STATUS_ON, )
        spinner = Spinner(text=self.args.screen_status, values=status, size_hint=(1, None), height=self.item_height)
        spinner.bind(text=lambda instance, value: setattr(self.args, 'screen_status', value))
        self.add_item('屏幕状态', spinner)

    def add_clipboard(self):
        """
            开启剪贴板回写功能
        :return:
        """
        btn_clipboard = Switch(
            active=self.args.clipboard, size_hint=(None, None), width=sp(100), height=self.item_height
        )
        btn_clipboard.bind(active=lambda instance, value: setattr(self.args, 'clipboard', value))
        self.add_item('同步剪切板', btn_clipboard)


class DevicePanel(ModalView):

    def __init__(self,
                 adb_device: AdbDevice,
                 connect_callback: Callable,
                 cfg_name: str,
                 is_new: bool = False,
                 delete_callback: Callable = None,
                 **kwargs
                 ):
        """
            设备连接面板
        :param adb_device:
        :param connect_callback:
        :param cfg_name:
        :param is_new:
        :param delete_callback:
        :param kwargs:
        """

        is_exists, args = load_cfg(adb_device.serial, cfg_name)
        if not is_exists:
            if not is_new:
                MDSnackbar(
                    MDSnackbarText(text=f"配置文件 {cfg_name} 不存在"), y=sp(24),
                    pos_hint={'center_x': 0.5}, size_hint_x=.5,
                ).open()
                raise FileNotFoundError(f"配置文件 {cfg_name} 不存在")
            else:
                args = (VideoArgs(), AudioArgs(), ControlArgs())

        super(DevicePanel, self).__init__(**kwargs)

        self.my_device = MYDevice(adb_device)
        self.cfg_name = cfg_name
        self.connect_callback = connect_callback
        self.delete_callback = delete_callback

        self.video_args, self.audio_args, self.control_args = args

        self.size_hint = (.9, .9)

        self.layout = BoxLayout(orientation='vertical', spacing=sp(2))

        self.tabs = TabbedPanel(do_default_tab=False, pos_hint={'x': .02}, size_hint_x=.96)

        self.video_args_panel = VideoArgsPanel(
            self.video_args, real_max_size=self.my_device.coord(reload=True).max_size)
        self.audio_args_panel = AudioArgsPanel(self.audio_args)
        self.control_args_panel = ControlArgsPanel(self.control_args)

        self.tabs.add_widget(self.video_args_panel)
        self.tabs.add_widget(self.audio_args_panel)
        self.tabs.add_widget(self.control_args_panel)

        self.add_widget(self.layout)

        self.layout.add_widget(DeviceInfo(my_device=self.my_device, size_hint=(.95, None), wifi_callback=self.wifi_connect))

        self.layout.add_widget(self.tabs)

        # 配置
        self.ipt_cfg = TextInput(text=self.cfg_name, size_hint=(1, 1), multiline=False)
        btn_save = MYStyledButton(
            text='保存', size_hint=(None, 1), width=sp(80), style=MYCombineColors.green, on_release=self.save_cfg
        )
        btn_del = MYStyledButton(
            text='删除', size_hint=(None, 1), width=sp(80), style=MYCombineColors.red, on_release=self.delete_cfg
        )
        layout_cfg = BoxLayout(size_hint=(1, None), height=sp(30), spacing=sp(5))
        layout_cfg.add_widget(Label(text='当前配置:', size_hint_x=None, width=sp(80)))
        layout_cfg.add_widget(self.ipt_cfg)
        layout_cfg.add_widget(btn_save)
        layout_cfg.add_widget(btn_del)
        self.layout.add_widget(layout_cfg)

        # 底部按钮
        layout_cc = BoxLayout(size_hint=(1, None), height=sp(30), spacing=sp(5))
        btn_close = MYStyledButton(
            text='关闭', style=MYCombineColors.red, size_hint=(None, 1), width=sp(70), on_release=self.dismiss)
        btn_connect = MYStyledButton(text='连接', size_hint=(1, 1), on_release=self.connect)
        layout_cc.add_widget(btn_close)
        layout_cc.add_widget(btn_connect)
        self.layout.add_widget(layout_cc)

    def connect(self, *args):
        """
            发起连接
        :param args:
        :return:
        """
        self.save_cfg(wait_n=0)
        self.connect_callback(self.my_device.adb_dev, self.cfg_name)
        self.dismiss()

    def wifi_connect(self, addr: str):
        """
            连接无线设备
        :param addr:
        :return:
        """
        self.dismiss()
        result = adb.connect(f'{addr}')
        create_snack(f"ADB Connect {addr}\n{result}").open()

    def delete_cfg(self, *args):
        """
            删除当前配置
        :param args:
        :return:
        """
        def _delete(*args):
            pop.dismiss()
            self.dismiss()
            fp = Param.PATH_CONFIGS.joinpath(f"ky_{self.my_device.adb_dev.serial}_{self.cfg_name}.json")
            fp.unlink()
            self.delete_callback and self.delete_callback(self.my_device, self.cfg_name)
            Logger.warning(f"Config file deleted: {fp}")

        content_box = BoxLayout(orientation='vertical')
        content_box.add_widget(Label(text=f"确认删除 {self.cfg_name} 配置文件?"))

        btn_box = BoxLayout(orientation='horizontal', spacing=sp(2))
        btn_box.add_widget(MYStyledButton(text='删除', style=MYCombineColors.red, on_release=_delete))
        cancel_btn = MYStyledButton(text='取消')
        btn_box.add_widget(cancel_btn)

        content_box.add_widget(btn_box)

        pop = Popup(title='确认删除配置?', auto_dismiss=False, size_hint=(.9, None), height=sp(120), content=content_box)

        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    def save_cfg(self, *args, wait_n: float=2.0):
        """
            保存当前配置
        :param args:
        :param wait_n:
        :return:
        """

        if self.ipt_cfg.text == '':
            self.ipt_cfg.text = self.cfg_name
        elif self.ipt_cfg.text != self.cfg_name:
            self.cfg_name = self.ipt_cfg.text

        fp = Param.PATH_CONFIGS.joinpath(f"ky_{self.my_device.adb_dev.serial}_{self.cfg_name}.json")

        pop = Popup(
            title='保存配置文件',
            content=Label(text=f'{self.cfg_name} 文件保存至\n{fp.__str__()}', font_size=sp(10)),
            auto_dismiss=False, size_hint=(.9, None), height=sp(120),
        )
        pop.open()

        js = JsonStore(fp.__str__())
        js.put('va', **self.video_args_panel.args.dump())
        js.put('aa', **self.audio_args_panel.args.dump())
        js.put('ca', **self.control_args_panel.args.dump())

        Clock.schedule_once(pop.dismiss, wait_n)
