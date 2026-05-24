# -*- coding: utf-8 -*-
"""
    my_screen
    ~~~~~~~~~~~~~~~~~~
    
    Log:
        2026-01-26 0.1.0 Me2sY 创建
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = [
    'MYScreen',
    'MYScreenList',
]

import uuid
from typing import ClassVar

from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.divider import MDDivider
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

from mysc.gui.k.components.base.my_list import MYList
from mysc.gui.k.components.base.my_navigation import MYNavigation


class MYScreen(MDScreen):
    """
        基本Screen
    """

    @property
    def is_current(self) -> bool:
        return self.manager.current_screen is self

    def __init__(self, nav: MYNavigation, main, **kwargs):

        self.nav = nav
        self.main = main

        kwargs.setdefault('name', uuid.uuid4().hex)
        super().__init__(**kwargs)

    def active(self):
        """
            激活当前屏幕
        :return:
        """
        self.manager.current = self.name

    def cb__close(self, caller):
        """
            退出并返回前序界面
        :return:
        """
        self.manager.switch_to(self.manager.get_screen(self.manager.previous()))

    def add_close_button(self):
        """
            添加退出按钮
        :return:
        """
        self.nav.add_main_button('close', self.cb__close)

    def cb__go_back(self, caller):
        """
            返回
        :param caller:
        :return:
        """
        self.manager.current = self.manager.previous()

    def add_go_back_button(self):
        """

        :return:
        """
        self.nav.add_main_button('arrow-left', self.cb__close)


class MYScreenList(MYScreen):
    """
        Screen with Title and List
    """

    TITLE: ClassVar[str] = ''

    def __init__(self, nav: MYNavigation, main, **kwargs):

        title = kwargs.get('title', self.TITLE)
        kwargs.pop('title', None)

        super().__init__(nav, main, **kwargs)

        self.layout = MDBoxLayout(orientation='vertical', padding=[dp(10), dp(2), dp(10), dp(10)], spacing=dp(4))
        self.add_widget(self.layout)

        """
            标题栏
        """
        self.layout.add_widget(
            MDLabel(
                text=title, halign='center', valign='middle',
                font_style='Title', role='small', bold=True,
                size_hint_y=None, height=dp(24),
            )
        )
        self.layout.add_widget(MDDivider())

        """
            列表区
        """
        self.my_list = MYList()
        self.layout.add_widget(self.my_list)
