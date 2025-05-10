# -*- coding: utf-8 -*-
"""
    side_panel
    ~~~~~~~~~~~~~~~~~~
    
    Log:
        2025-05-10 3.2.0 Me2sY  定版

        2025-04-22 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '3.2.0'

__all__ = [
    'SidePanel'
]

from typing import Callable

from kivy.metrics import sp

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFabButton, MDIconButton
from kivymd.uix.divider import MDDivider
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.scrollview import MDScrollView

from myscrcpy.gui.k import MYCombineColors
from myscrcpy.utils import ADBKeyCode


class ScrollButton(MDIconButton):
    def __init__(self, color: MYCombineColors = None, **kwargs):
        super().__init__(**kwargs)
        self.style = 'tonal'
        self.pos_hint = {'center_x': .5}

        if color:
            self.theme_bg_color = 'Custom'
            self.md_bg_color = color.value[0]
            self.theme_icon_color = 'Custom'
            self.icon_color = color.value[1]


class SidePanel(MDGridLayout):

    SPACING = sp(2)
    PADDING = sp(2)

    def __init__(self, primary_color, btn_callback:Callable[[...], None], **kwargs):
        """
            侧边栏，提供针对当前Screen设备功能按键
        :param primary_color:
        :param btn_callback:
        :param kwargs:
        """
        super().__init__(**kwargs)

        self.callback = btn_callback

        # 定义基础属性
        self.cols = 1
        self.adaptive_size = True
        self.size_hint = (None, 1)

        self.spacing = self.SPACING
        self.padding = self.SPACING
        self.md_bg_color = primary_color

        self.add_widget(MDFabButton(icon='apps', style='small', on_release=lambda *args: self.callback(ADBKeyCode.APP_SWITCH)))
        self.add_widget(MDFabButton(icon='home', style='small', on_release=lambda *args: self.callback(ADBKeyCode.HOME)))
        self.add_widget(MDFabButton(icon='arrow-left', style='small', on_release=lambda *args: self.callback(ADBKeyCode.BACK)))

        self.add_widget(MDDivider())

        layout_scroll = MDScrollView(do_scroll_x=False, size_hint_x=1)
        self.layout_items = MDBoxLayout(adaptive_height=True, orientation='vertical', spacing=sp(5), padding=self.PADDING)
        layout_scroll.add_widget(self.layout_items)

        self.add_widget(layout_scroll)

        for btn in [
            dict(icon='power', color=MYCombineColors.red, on_release=lambda *args: self.callback(ADBKeyCode.POWER)),
            dict(icon='bell', color=MYCombineColors.grey, on_release=lambda *args: self.callback(ADBKeyCode.NOTIFICATION)),
            dict(icon='cog', color=MYCombineColors.grey, on_release=lambda *args: self.callback(ADBKeyCode.SETTINGS)),

            dict(icon='play-pause', color=MYCombineColors.orange, on_release=lambda *args: self.callback(ADBKeyCode.KB_MEDIA_PLAY_PAUSE)),
            dict(icon='skip-next', color=MYCombineColors.orange, on_release=lambda *args: self.callback(ADBKeyCode.KB_MEDIA_NEXT_TRACK)),
            dict(icon='skip-previous', color=MYCombineColors.orange, on_release=lambda *args: self.callback(ADBKeyCode.KB_MEDIA_PREV_TRACK)),

            dict(icon='microphone-off', color=MYCombineColors.green, on_release=lambda *args: self.callback(ADBKeyCode.MIC_MUTE)),
            dict(icon='volume-mute', color=MYCombineColors.green, on_release=lambda *args: self.callback(ADBKeyCode.KB_VOLUME_MUTE)),
            dict(icon='volume-plus', color=MYCombineColors.green, on_release=lambda *args: self.callback(ADBKeyCode.KB_VOLUME_UP)),
            dict(icon='volume-minus', color=MYCombineColors.green, on_release=lambda *args: self.callback(ADBKeyCode.KB_VOLUME_DOWN)),

            dict(icon='camera', color=MYCombineColors.yellow, on_release=lambda *args: self.callback(ADBKeyCode.CAMERA)),
            dict(icon='magnify-plus', color=MYCombineColors.yellow, on_release=lambda *args: self.callback(ADBKeyCode.ZOOM_IN)),
            dict(icon='magnify-minus', color=MYCombineColors.yellow, on_release=lambda *args: self.callback(ADBKeyCode.ZOOM_OUT)),

            dict(icon='brightness-7', color=MYCombineColors.blue, on_release=lambda *args: self.callback(ADBKeyCode.BRIGHTNESS_UP)),
            dict(icon='brightness-5', color=MYCombineColors.blue, on_release=lambda *args: self.callback(ADBKeyCode.BRIGHTNESS_DOWN)),

            dict(icon='cellphone-screenshot', color=MYCombineColors.grey, on_release=lambda *args: self.callback(ADBKeyCode.KB_PRINTSCREEN)),
            dict(icon='assistant', color=MYCombineColors.grey, on_release=lambda *args: self.callback(ADBKeyCode.VOICE_ASSIST)),
            dict(icon='web', color=MYCombineColors.grey, on_release=lambda *args: self.callback(ADBKeyCode.EXPLORER)),
            dict(icon='calculator', color=MYCombineColors.grey, on_release=lambda *args: self.callback(ADBKeyCode.CALCULATOR)),
            dict(icon='calendar', color=MYCombineColors.grey, on_release=lambda *args: self.callback(ADBKeyCode.CALENDAR)),
            dict(icon='phone', color=MYCombineColors.grey, on_release=lambda *args: self.callback(ADBKeyCode.CALL)),
            dict(icon='contacts', color=MYCombineColors.grey, on_release=lambda *args: self.callback(ADBKeyCode.CONTACTS)),
        ]:
            self.layout_items.add_widget(ScrollButton(**btn))

        self.add_widget(MDDivider())

if __name__ == '__main__':
    from kivymd.app import MDApp

    class Example(MDApp):
        def build(self):

            def cb(*args):
                print(args)

            return MDBoxLayout(
                SidePanel(self.theme_cls.primaryColor, cb),
                MDScreen(
                    md_bg_color=self.theme_cls.secondaryContainerColor,
                ),
            )

    Example().run()