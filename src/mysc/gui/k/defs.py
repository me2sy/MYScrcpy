# -*- coding: utf-8 -*-
"""
    defs
    ~~~~~~~~~~~~~~~~~~

    Log:
        2026-01-20 0.1.0 Me2sY 创建
        2026-04-27 0.2.0 Me2sY 完善 i18n 框架（运行时切换、系统语言检测、监听者模式）
"""

__author__ = 'Me2sY'
__version__ = '0.2.0'

__all__ = [
    'init_language',
    'I18N', 'EnumLanguage',
    'Colors', 'CombineColors'
]

import gettext
import json
import locale as _locale_module
import pathlib
from enum import Enum
from typing import Callable, Optional

from mysc.utils.params import Param


class EnumLanguage(str, Enum):
    """支持的界面语言。AUTO 会按系统 locale 自动选择。"""
    AUTO = 'auto'
    EN_US = 'en_US'
    ZH_CN = 'zh_CN'

    @property
    def display_name(self) -> str:
        return {
            'auto': 'Auto / 自动',
            'en_US': 'English',
            'zh_CN': '简体中文',
        }[self.value]


# 持久化主配置文件路径（与 MainConfig 约定保持一致：APPCFG_main.json）
_MAIN_CONFIG_PATH: pathlib.Path = Param.PATH_CONFIG.joinpath('APPCFG_main.json')


def _detect_system_language() -> str:
    """读取系统 locale，匹配到支持的语言；兜底 en_US。"""
    try:
        code = _locale_module.getdefaultlocale()[0] or ''
    except Exception:
        code = ''
    if code.lower().startswith('zh'):
        return EnumLanguage.ZH_CN.value
    return EnumLanguage.EN_US.value


def _read_persisted_language() -> Optional[str]:
    """从主配置文件直接读取 language 字段，避免与 app.MainConfig 形成循环依赖。"""
    if not _MAIN_CONFIG_PATH.exists():
        return None
    try:
        data = json.load(_MAIN_CONFIG_PATH.open('r', encoding='utf-8'))
        return data.get('language')
    except Exception:
        return None


class _I18NManager:
    """统一管理 gettext 翻译，支持运行时切换语言并通知监听者。"""

    def __init__(self):
        self._language: str = EnumLanguage.EN_US.value
        self._translator: gettext.NullTranslations = gettext.NullTranslations()
        self._listeners: list[Callable[[], None]] = []

    @property
    def current(self) -> str:
        return self._language

    def gettext(self, message: str) -> str:
        return self._translator.gettext(message)

    def set_language(self, language: str = EnumLanguage.AUTO.value) -> str:
        """切换语言，加载对应 .mo 并通知所有监听者。返回最终生效的语言代码。"""
        if not language or language == EnumLanguage.AUTO.value:
            language = _detect_system_language()

        try:
            translator = gettext.translation(
                domain=Param.PROJECT_NAME,
                localedir=Param.PATH_LOCALES,
                languages=[language],
                fallback=True,
            )
        except FileNotFoundError:
            translator = gettext.NullTranslations()

        translator.install()
        self._translator = translator
        self._language = language

        for cb in list(self._listeners):
            try:
                cb()
            except Exception:
                pass
        return language

    def add_listener(self, cb: Callable[[], None]) -> None:
        if cb not in self._listeners:
            self._listeners.append(cb)

    def remove_listener(self, cb: Callable[[], None]) -> None:
        if cb in self._listeners:
            self._listeners.remove(cb)


I18N = _I18NManager()

# 模块加载时立即根据持久化配置或系统语言初始化，
# 这样 GUI 模块的 class-body `_('...')` 调用也能命中正确翻译。
I18N.set_language(_read_persisted_language() or EnumLanguage.AUTO.value)


def init_language(language: Optional[str] = None) -> Callable[[str], str]:
    """
        历史接口：返回当前 _() 函数。
        若传入 language 则切换到该语言。
    """
    if language is not None:
        I18N.set_language(language)
    return I18N.gettext


_ = I18N.gettext


class Colors:
    """
        色彩定义
    """
    Black = 'black'
    White = 'white'
    Red = '#ff6b81'

    Green = '#7bed9f'
    GreenLight = '#8BBD8B'
    Blue = '#1e90ff'
    BlueLight = '#57B8FF'
    Grey = '#e2e2e2'
    GreyDust = '#D6D2D2'
    Yellow = '#f1c40f'
    Orange = '#ffa502'
    PaleOak = '#DBCFB0'
    SoftLinen = '#E0E2DB'

    Background = [1, 1, 1, 1]
    TouchPad = [.749, .749, .749, 1]


class CombineColors(Enum):
    """
        Button 配色
    """
    black = (Colors.Black, Colors.White)
    white = (Colors.White, Colors.Black)
    red = (Colors.Red, Colors.White)
    green = (Colors.Green, Colors.Black)
    blue = (Colors.Blue, Colors.Black)
    grey = (Colors.Grey, Colors.Black)
    yellow = (Colors.Yellow, Colors.Black)
    orange = (Colors.Orange, Colors.Black)
    grey_dust = (Colors.GreyDust, Colors.Black)
