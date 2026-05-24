# -*- coding: utf-8 -*-
"""
    connect_kwargs
    ~~~~~~~~~~~~~~~~~~
    
    Log:
        2026-01-26 0.1.0 Me2sY 创建
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = [
    'JSMode',
    'ScreenListModes'
]

import pathlib
from dataclasses import dataclass, field
from typing import Callable, Optional

from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton, MDFabButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog, MDDialogHeadlineText, MDDialogContentContainer, MDDialogButtonContainer
from kivymd.uix.divider import MDDivider
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
from kivymd.uix.widget import MDWidget

from mysc.core.audio import AudioKwargs
from mysc.core.control import ControlKwargs
from mysc.core.device import MYDevice
from mysc.core.video import VideoKwargs
from mysc.gui.k.components.base.my_list import ListItemBase, ListItemDivider, ListItemConfig
from mysc.gui.k.components.base.my_screen import MYScreenList
from mysc.gui.k.components.base.my_snack_bar import MYSnackBarWarning, MYSnackBarInfo, MYSnackBarError, \
    MYSnackBarSuccess
from mysc.gui.k.defs import init_language, Colors
from mysc.utils.storage import JSONStorage

_ = init_language()


# 字段名 → 用于 gettext 的英文 msgid。msgid 即英文显示文案；
# 通过 _() 走 i18n 表得到目标语言文案。
KWARGS_LABEL_KEYS = {
    # Video
    'video': 'Enable Video',
    'video_codec': 'Video Codec',
    'video_buffer': 'Video Buffer (ms)',
    'video_encoder': 'Video Encoder',
    'max_fps': 'Max FPS',
    'max_size': 'Max Size',
    'video_bit_rate': 'Video Bit Rate',
    'crop': 'Crop',
    'video_source': 'Video Source',
    # Camera
    'camera_ar': 'Camera AR',
    'camera_facing': 'Camera Facing',
    'camera_fps': 'Camera FPS',
    'camera_high_speed': 'Camera High Speed',
    'camera_id': 'Camera ID',
    'camera_size': 'Camera Size',
    # Audio
    'audio': 'Enable Audio',
    'audio_source': 'Audio Source',
    'audio_codec': 'Audio Codec',
    'audio_bit_rate': 'Audio Bit Rate',
    'audio_buffer': 'Audio Buffer (ms)',
    'audio_output_buffer': 'Audio Output Buffer (ms)',
    # Control
    'control': 'Enable Control',
    'show_touches': 'Show Touches',
    '_clipboard': 'Clipboard Sync',
    '_screen_status': 'Screen Status',
}


def _kwargs_label(key: str) -> str:
    return _(KWARGS_LABEL_KEYS.get(key, key))


@dataclass
class JSMode(JSONStorage):
    """
        配置文件存储
    """
    Prefix = 'MODE_'

    is_default: bool = False
    storage_kwargs: dict = field(default_factory=dict)


class MYDialogName(MDDialog):
    """
        命名界面
    """
    def __init__(
            self,
            cb_confirm: Callable[[str], None],
            old_name: Optional[str] = None,
            *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cb_confirm = cb_confirm

        # 创建或修改
        if old_name is None:
            self.add_widget(MDDialogHeadlineText(text=_('Create Scrcpy Config')))
        else:
            self.add_widget(MDDialogHeadlineText(text=_('Changed Config Name')))

        self.widget_name = MDTextField(
            MDTextFieldHintText(text=_('File Name')),
            text='' if old_name is None else old_name,
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            multiline=False, mode='filled'
        )

        self.add_widget(MDDialogContentContainer(
            MDDivider(),
            self.widget_name,
            orientation='vertical'
        ))
        self.widget_btn_create = MDButton(
            MDButtonText(text=_('Confirm')),
            on_release = self._confirm, style='text'
        )
        self.add_widget(MDDialogButtonContainer(
            MDWidget(),
            MDButton(
                MDButtonText(text=_('Close')),
                on_release=self.dismiss, style='text'
            ),
            self.widget_btn_create
        ))

    def _confirm(self, *args):
        """
            确认回调
        :param args:
        :return:
        """
        self.dismiss()
        if self.widget_name.text != '':
            self.cb_confirm(self.widget_name.text)


class ScreenListModeEdit(MYScreenList):

    def __init__(self, mode: JSMode, **kwargs):

        self.mode = mode

        super().__init__(title=self.mode.save_key, **kwargs)

        self.kwargs_video = VideoKwargs.load(**self.mode.storage_kwargs)
        self.kwargs_audio = AudioKwargs.load(**self.mode.storage_kwargs)
        self.kwargs_control = ControlKwargs.load(**self.mode.storage_kwargs)

        # Video
        self.my_list.add_list_item(ListItemDivider(MDLabel(
            text=_('Video'), role='small', font_style='Headline', adaptive_height=True
        )))
        for item in self.kwargs_video.to_items():
            self.my_list.add_list_item(ListItemConfig(*item, label=_kwargs_label(item[0])))
        self.my_list.add_list_item(ListItemDivider())

        # Audio
        self.my_list.add_list_item(ListItemDivider(MDLabel(text=_('Audio'), role='small', font_style='Headline')))
        for item in self.kwargs_audio.to_items():
            self.my_list.add_list_item(ListItemConfig(*item, label=_kwargs_label(item[0])))
        self.my_list.add_list_item(ListItemDivider())

        # Control
        self.my_list.add_list_item(ListItemDivider(MDLabel(text=_('Control'), role='small', font_style='Headline')))
        for item in self.kwargs_control.to_items():
            self.my_list.add_list_item(ListItemConfig(*item, label=_kwargs_label(item[0])))

    def on_enter(self, *args):
        self.nav.clear_buttons()

        self.add_close_button()
        self.nav.add_main_button('content-save-outline', self.cb__save)

    def cb__save(self, *args):
        """
            保存配置文件
        :param args:
        :return:
        """
        self.mode.storage_kwargs.update(self.my_list.to_dict())
        self.mode.dump()
        MYSnackBarSuccess(_('Saved!'))


class ListItemKwargs(ListItemBase):
    def __init__(self, mode: JSMode, screen_list_modes: 'ScreenListModes', *args, **kwargs):
        """
            配置列表项
        :param js_kwargs:
        :param args:
        :param kwargs:
        """
        super().__init__(*args, **kwargs)

        self.mode = mode
        self.screen_list_modes: ScreenListModes = screen_list_modes

        self.card = MDCard(
            style='filled', adaptive_height=True, padding=dp(8), spacing=dp(10),
            theme_bg_color="Custom"
        )
        self.add_widget(self.card)
        self.widget_name = MDLabel(
            text=f"{self.mode.save_key}",
            font_style='Title'
        )
        self.card.add_widget(
            MDBoxLayout(
                MDIconButton(icon='rename', on_release=self.rename, pos_hint={'center_x': 0.5, 'center_y': 0.5}),
                self.widget_name,
                size_hint_y=None, height=dp(80), orientation='horizontal'
            )
        )

        self.card.add_widget(MDDivider(orientation='vertical'))

        self.card.add_widget(
            MDGridLayout(
                MDIconButton(
                    icon='star', on_release=lambda *_args: self.screen_list_modes.set_default(self.mode)
                ),
                MDIconButton(icon='file-cog', on_release=self.edit),
                MDIconButton(icon='delete', on_release=self.delete),
                MDIconButton(icon='content-copy', on_release=self.copy),
                cols=2,
                size_hint_x=None, width=dp(80),
                pos_hint={'center_x': 0.5, 'center_y': 0.5}
            )
        )

        self.card.add_widget(
            MDFabButton(icon='connection',pos_hint={'center_x': 0.5, 'center_y': 0.5},
                        on_release=lambda *_args: self.screen_list_modes.cb__connect(self.mode))
        )

        self.update_default()

    def delete(self, *args):
        """
            删除配置文件
        :return:
        """
        self.mode.delete()

        MYSnackBarWarning(_('Delete!'))

        self.screen_list_modes.remove_mode(self)

        # 若为默认配置，则重新设置默认配置
        if self.mode.is_default:
            self.screen_list_modes.set_default()

    def edit(self, *args):
        """
            编辑配置文件
        :param args:
        :return:
        """
        self.screen_list_modes.cb__edit(self)

    def rename(self, *args):

        def _rename(new_name: str):
            """
                重命名
            :param new_name:
            :return:
            """
            dialog.dismiss()

            try:
                self.mode.rename(new_name)
            except FileExistsError:
                MYSnackBarError(_('File Exists!'))
                return

            self.widget_name.text = new_name
            MYSnackBarSuccess()

        dialog = MYDialogName(_rename, self.mode.save_key)
        dialog.open()

    def update_default(self):
        """
            更新默认状态
        :return:
        """
        self.card.md_bg_color = Colors.Orange if self.mode.is_default else Colors.Grey

        # Fix Bug
        # 鼠标移出后颜色恢复
        self.card._bg_color = self.card.md_bg_color

    def copy(self, *args):
        """
            复制配置文件
        :param args:
        :return:
        """
        # 判断文件是否存在
        for i in range(99999):
            # new_save_path = self.mode._save_path.parent.joinpath(f"{JSKwargs.STORAGE_PREFIX}{self.mode.file_name}_{i}.json")

            new_file_name = f"{self.mode.save_key}_{i}"

            new_path = self.mode.file_path.parent.joinpath(
                JSMode.Prefix + new_file_name + f".json"
            )
            if not new_path.exists():
                break

        # 复制新文件
        _mode = self.screen_list_modes.mode_cls(
            save_key=new_file_name, is_default=False, storage_kwargs=self.mode.storage_kwargs
        ).dump()

        self.screen_list_modes.my_list.add_list_item(ListItemKwargs(_mode, self.screen_list_modes))

        MYSnackBarInfo(_('Copied!'))


class ScreenListModes(MYScreenList):
    """
        设备配置界面
    """

    TITLE = _('Modes')

    def __init__(self, my_device: MYDevice, **kwargs):
        super().__init__(**kwargs)

        self.my_device = my_device

        self.mode_cls = JSMode.get_cls(StoragePath=pathlib.Path(f"{self.my_device.serial_no}"))

    def draw(self):
        """
            刷新并绘制列表
        :return:
        """
        self.my_list.clear()
        for mode in self.get_device_modes():
            self.my_list.add_list_item(ListItemKwargs(mode, self))

    def on_enter(self):
        """
            进入设备配置界面
        """
        self.main.on_main(_('Modes') + f" - {self.my_device.serial_no}")

        self.nav.clear_buttons()

        self.add_close_button()
        self.nav.add_main_button('plus', self.cb__create)

        self.draw()

    @staticmethod
    def get_device_default_mode(serial_no: str) -> JSMode:
        """
            获取设备默认配置
        :param serial_no:
        :return:
        """
        _cls = JSMode.get_cls(StoragePath=pathlib.Path(f"{serial_no}"))
        for jsm in _cls.obj_glob():
            if jsm.is_default: return jsm

        jsm = _cls('Default', is_default=True)
        jsm.dump()
        return jsm

    def get_device_modes(self) -> list[JSMode]:
        """
            获取设备配置列表
        :return:
        """
        mode_list = []
        default_mode = None
        for mode in self.mode_cls.obj_glob():
            if mode.is_default: default_mode = mode
            else: mode_list.append(mode)

        mode_list = sorted(mode_list, key=lambda _mode: _mode.file_name)

        if default_mode is None: return [] + mode_list
        else: return [default_mode] + mode_list

    def cb__create(self, caller):
        """
            创建
        :param caller:
        :return: 
        """
        
        def create_callback(file_name: str):
            """
                创建新的配置界面
            :param file_name:
            :return:
            """
            if file_name in [_mode.save_key for _mode in self.get_device_modes()]:
                MYSnackBarError(_('File Exists!'))
            else:
                _mode = self.mode_cls(save_key=file_name)
                sl_me = ScreenListModeEdit(_mode, nav=self.nav, main=self.main)
                self.manager.add_widget(sl_me)
                self.manager.current = sl_me.name

        MYDialogName(create_callback).open()

    def cb__edit(self, caller: ListItemKwargs):
        """
            编辑模式
        :param caller:
        :return:
        """
        sl_me = ScreenListModeEdit(caller.mode, nav=self.nav, main=self.main)
        self.manager.add_widget(sl_me)
        self.manager.current = sl_me.name

    def remove_mode(self, caller: ListItemKwargs):
        """
            移除模式
        :param caller:
        :return:
        """
        self.my_list.remove_list_item(caller)

    def set_default(self, default_mode: Optional[JSMode] = None):
        """
            设置默认配置
        :param default_mode:
        :return:
        """
        # 若未定义默认同时不为空，则设置第一个为默认值
        if default_mode is None and len(self.my_list.items) > 0:
            default_mode = self.my_list.items[0].mode

        for item in self.my_list.items:
            if item.mode.file_name == default_mode.file_name:
                item.mode.is_default = True
            else:
                item.mode.is_default = False

            item.mode.dump()
            item.update_default()

    def cb__close(self, caller):
        """
            关闭回调，指定跳转页面
        :param caller:
        :return:
        """
        self.manager.switch_to(self.main.screen_devices)

    def cb__connect(self, mode: JSMode):
        """
            发起连接
        :param mode:
        :return:
        """
        self.main.screen_connections.create_vac(self.my_device, mode)