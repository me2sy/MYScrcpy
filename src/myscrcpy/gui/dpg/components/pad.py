# -*- coding: utf-8 -*-
"""
    面板组件
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-09-23 1.6.0 Me2sY  新增底部状态及日志栏

        2024-09-10 1.5.9 Me2sY  新增文件管理器

        2024-08-29 1.4.0 Me2sY
            1.适配新架构
            2.新增部分功能按键

        2024-08-15 1.3.0 Me2sY  发布初版

        2024-08-13 0.1.2 Me2sY
            1.整合ADB Key Event 功能至Switch Pad
            2.新增 Icon按钮

        2024-08-10 0.1.1 Me2sY  分离
"""

__author__ = 'Me2sY'
__version__ = '1.6.0'

__all__ = [
    'CPMPad',
    'CPMNumPad', 'CPMControlPad',
    'CPMSwitchPad', 'CPMFilePad',
    'CPMBottomPad'
]

import datetime
import pathlib
import stat
import threading
import time
from typing import Callable
import webbrowser
from dataclasses import dataclass, field

from loguru import logger
import dearpygui.dearpygui as dpg

from myscrcpy.utils import ADBKeyCode, Param
from myscrcpy.gui.dpg.components.component_cls import Component, TempModal
from myscrcpy.core import AdvDevice


class CPMPad(Component):
    """
        控制面板
    """

    DEFAULT_CONTAINER_ADD_METHOD = dpg.add_group

    def __init__(self, callback: Callable = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._callback = callback

    def callback(self, user_data):
        if self._callback:
            self._callback(user_data)

    def update(self, callback: Callable, *args, **kwargs):
        self._callback = callback
        return self


class CPMNumPad(CPMPad):
    """
        数字键盘
        使用 ADB Key event 实现
    """
    def setup_inner(self, *args, **kwargs):
        def show_input(value):
            if value == ADBKeyCode.KB_BACKSPACE:
                dpg.set_value(self.tag_ipt, dpg.get_value(self.tag_ipt)[:-1])
            elif value == ADBKeyCode.KB_ENTER:
                dpg.set_value(self.tag_ipt, '')
            else:
                dpg.set_value(self.tag_ipt, dpg.get_value(self.tag_ipt) + '*')

        btn_cfg = dict(width=25, height=25, callback=lambda s, a, u: self.callback(u) or show_input(u))
        self.tag_ipt = dpg.add_input_text(width=-1, enabled=False)
        for i in range(3):
            with dpg.group(horizontal=True):
                for j in range(1, 4):
                    bn = i * 3 + j
                    dpg.add_button(label=f"{bn}", user_data=ADBKeyCode[f"KB_{bn}"], **btn_cfg)

        with dpg.group(horizontal=True):
            dpg.add_button(label="|<-", user_data=ADBKeyCode.KB_BACKSPACE, **btn_cfg)
            dpg.add_button(label="0", user_data=ADBKeyCode.KB_0, **btn_cfg)
            dpg.add_button(label="OK", user_data=ADBKeyCode.KB_ENTER, **btn_cfg)

    def clear(self):
        dpg.set_value(self.tag_ipt, '')


class CPMControlPad(CPMPad):
    """
        控制面板
        # TODO 2024-08-15 Me2sY ADB Shell功能 调试功能等
    """

    def callback(self, user_data):
        code = dpg.get_value(self.tag_ipt)
        super().callback(code)
        if self._callback:
            dpg.set_value(self.tag_msg, f"{code} Send")

    def setup_inner(self, *args, **kwargs):
        self.tag_msg = dpg.add_text(f"Send KeyCode")
        self.tag_ipt = dpg.add_input_int(min_value=0, max_value=999, on_enter=True, width=-1)
        dpg.add_button(label='send', height=35, width=-1, callback=self.callback)


class CPMSwitchPad(CPMPad):
    """
        开关/ADB控制 面板
    """

    WIDTH = 38

    @classmethod
    def default_container(cls, parent=None):
        return cls.create_container(dpg.add_child_window, parent, border=False, width=cls.WIDTH, no_scrollbar=True)

    def switch_show(self, sender):
        """
            开关
        """
        self.status = not self.status
        self._switch_show_callback(self.status)
        dpg.configure_item(self.tag_ib_switch, texture_tag=self.icon_map[self.status])

    def setup_inner(self, icons, *args, **kwargs):

        self.status = False
        self.icon_map = {
            True: icons['lp_close'],
            False: icons['lp_open']
        }

        btn_icon_cfg = dict(height=30, width=30, callback=lambda s, a, u: self.callback(u))

        dpg.add_image_button(icons['power'], user_data=ADBKeyCode.POWER, **btn_icon_cfg)
        dpg.add_spacer(height=3)

        dpg.add_image_button(icons['switch'], user_data=ADBKeyCode.APP_SWITCH, **btn_icon_cfg)
        dpg.add_separator()
        dpg.add_image_button(icons['home'], user_data=ADBKeyCode.HOME, **btn_icon_cfg)
        dpg.add_separator()
        dpg.add_image_button(icons['back'], user_data=ADBKeyCode.BACK, **btn_icon_cfg)
        dpg.add_separator()
        dpg.add_image_button(icons['notification'], user_data=ADBKeyCode.NOTIFICATION, **btn_icon_cfg)
        dpg.add_image_button(icons['settings'], user_data=ADBKeyCode.SETTINGS, **btn_icon_cfg)
        dpg.add_spacer(height=3)
        self.tag_ib_switch = dpg.add_image_button(
            self.icon_map[self.status], height=30, width=30, callback=self.switch_show
        )
        dpg.add_spacer(height=3)

        with dpg.child_window(no_scrollbar=True, border=False, width=self.WIDTH):
            dpg.add_image_button(icons['play'], user_data=ADBKeyCode.KB_MEDIA_PLAY_PAUSE, **btn_icon_cfg)
            dpg.add_image_button(icons['p_next'], user_data=ADBKeyCode.KB_MEDIA_NEXT_TRACK, **btn_icon_cfg)
            dpg.add_image_button(icons['p_pre'], user_data=ADBKeyCode.KB_MEDIA_PREV_TRACK, **btn_icon_cfg)
            dpg.add_separator()
            dpg.add_image_button(icons['mic_off'], user_data=ADBKeyCode.MIC_MUTE, **btn_icon_cfg)
            dpg.add_image_button(icons['vol_off'], user_data=ADBKeyCode.KB_VOLUME_MUTE, **btn_icon_cfg)
            dpg.add_image_button(icons['vol_up'], user_data=ADBKeyCode.KB_VOLUME_UP, **btn_icon_cfg)
            dpg.add_image_button(icons['vol_down'], user_data=ADBKeyCode.KB_VOLUME_DOWN, **btn_icon_cfg)
            dpg.add_separator()
            dpg.add_image_button(icons['camera'], user_data=ADBKeyCode.CAMERA, **btn_icon_cfg)
            dpg.add_image_button(icons['zoom_in'], user_data=ADBKeyCode.ZOOM_IN, **btn_icon_cfg)
            dpg.add_image_button(icons['zoom_out'], user_data=ADBKeyCode.ZOOM_OUT, **btn_icon_cfg)
            dpg.add_separator()
            dpg.add_image_button(icons['brightness_up'], user_data=ADBKeyCode.BRIGHTNESS_UP, **btn_icon_cfg)
            dpg.add_image_button(icons['brightness_down'], user_data=ADBKeyCode.BRIGHTNESS_DOWN, **btn_icon_cfg)
            dpg.add_separator()
            dpg.add_image_button(icons['screenshot'], user_data=ADBKeyCode.KB_PRINTSCREEN, **btn_icon_cfg)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Screenshot')
            dpg.add_image_button(icons['voice'], user_data=ADBKeyCode.VOICE_ASSIST, **btn_icon_cfg)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Voice Assist')
            dpg.add_image_button(icons['explore'], user_data=ADBKeyCode.EXPLORER, **btn_icon_cfg)
            dpg.add_image_button(icons['calculate'], user_data=ADBKeyCode.CALCULATOR, **btn_icon_cfg)
            dpg.add_image_button(icons['calendar'], user_data=ADBKeyCode.CALENDAR, **btn_icon_cfg)
            dpg.add_image_button(icons['call'], user_data=ADBKeyCode.CALL, **btn_icon_cfg)
            dpg.add_image_button(icons['contacts'], user_data=ADBKeyCode.CONTACTS, **btn_icon_cfg)

    def update(self, callback: Callable, switch_show_callback: Callable, *args, **kwargs):
        self._callback = callback
        self._switch_show_callback = switch_show_callback
        self.status = kwargs.get('status', False)


class CPMFilePad(CPMPad):
    """
        文件管理面板
    """
    def setup_inner(self, *args, **kwargs):

        self.tag_filter = dpg.generate_uuid()
        self.tag_table = dpg.generate_uuid()

        # Download Open Delete
        with dpg.group(horizontal=True):
            # Open Download File
            dpg.add_button(
                label='F', callback=lambda: webbrowser.open(Param.PATH_DOWNLOAD / self.adv_device.serial_no)
            )
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Open Download File')

            # Upload File in PC clipboard to current path
            dpg.add_button(label='UP', callback=self.upload)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Upload Files in Clipboard')

            # Download Selected Files
            dpg.add_button(label='DLD', callback=self.download_selected)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Download Selected File')

            # Delete Selected Files
            dpg.add_button(label='DEL', callback=self.rm_selected)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Delete Selected File')

            dpg.add_spacer(width=2)

            self.tag_txt_info = dpg.add_text(default_value='0 Selected')
            with dpg.tooltip(dpg.last_item()):
                self.tag_txt_info_detail = dpg.add_text(default_value='No Item Selected')

        dpg.add_separator()

        # File Select and Filter
        with dpg.group(horizontal=True):

            dpg.add_button(label='A', callback=self.select_all)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Select All')

            dpg.add_button(label='C', callback=self.unselect_all)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Unselect All')

            self.tag_filter = dpg.add_input_text(
                label="Filter", user_data=self.tag_table, width=-40,
                callback=lambda s, a, u: dpg.set_value(self.tag_table, dpg.get_value(s))
            )

        # Path
        with dpg.group(horizontal=True):
            dpg.add_button(label='R', callback=self.draw_path)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text('Reload Path')

            dpg.add_button(
                label='..', user_data='..', width=40,
                callback=lambda s, a, u: self.open_dir(s, a, u) or
                                         dpg.set_value(self.tag_filter, '') or
                                         dpg.set_value(self.tag_table, '')
            )

            # Current Path
            self.tag_path_cur = dpg.add_text('')
            with dpg.tooltip(self.tag_path_cur):
                self.tag_path_full = dpg.add_text('')

        dpg.add_separator()

        with dpg.table(tag=self.tag_table, delay_search=True):
            dpg.add_table_column(label='cb', parent=self.tag_table, init_width_or_weight=0.1)
            dpg.add_table_column(label='path', parent=self.tag_table)



    def update(self, callback: Callable, adv_device: AdvDevice, *args, **kwargs):
        """
            初始化控件
        :param callback:
        :param adv_device:
        :param args:
        :param kwargs:
        :return:
        """
        self.adv_device = adv_device
        self.fm = self.adv_device.file_manager
        self.draw_path()

    def draw_path(self):
        """
            更新路径显示窗口
        :return:
        """
        self.all_cb = set()
        self.selected(None, None, None)

        # 显示当前路径
        path_cur = self.fm.path_cur.__str__()
        if len(path_cur) > 20:
            path_cur = '...' + path_cur[-20:]
        else:
            path_cur = path_cur

        dpg.set_value(self.tag_path_cur, path_cur)
        dpg.set_value(self.tag_path_full, self.fm.path_cur.__str__())

        # 加载路径文件列表
        fs = self.fm.ls()

        # 清空并绘制表格
        dpg.delete_item(self.tag_table, children_only=True, slot=1)

        for ind, _ in enumerate(fs):

            abs_path = self.fm.path_cur / _.path

            with dpg.table_row(filter_key=f"{_.path}", parent=self.tag_table) as tag_row:

                # column function
                tag_sel = dpg.add_selectable(
                    label=str(ind + 1), default_value=False, user_data=(abs_path, ind),
                    callback=lambda s, a, u: self.selected(s, a, u) or self.highlight(s, a, u)
                )
                with dpg.popup(tag_sel):
                    dpg.add_text(default_value=abs_path.__str__())
                    dpg.add_separator()

                    if stat.S_ISREG(_.mode) and _.size < Param.OPEN_MAX_SIZE:
                        dpg.add_selectable(
                            label='Open', user_data=abs_path,
                            callback=lambda s, a, u: self.open_file(u) or dpg.set_value(s, False)
                        )
                    dpg.add_selectable(
                        label='Download', user_data=abs_path,
                        callback=lambda s, a, u: self.download(u) or dpg.set_value(s, False)
                    )
                    dpg.add_selectable(
                        label='Delete', user_data=abs_path,
                        callback=lambda s, a, u: self.rm(u) or dpg.set_value(s, False)
                    )

                self.all_cb.add(tag_sel)
                self.highlight(tag_sel, False, (abs_path, ind))

                # column path
                if stat.S_ISDIR(_.mode) or stat.S_ISLNK(_.mode):
                    dpg.add_selectable(
                        label=f"> {_.path}", default_value=False, user_data=abs_path,
                        callback=lambda s, a, u: self.open_dir(s, a, u)
                    )
                else:
                    dpg.add_text(default_value=f"{_.path}")

                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text(f"{stat.filemode(_.mode)} | {_.mtime} | {_.size} | {_.path}")

    def upload(self):
        """
            上传文件至当前位置
            因为是异步上传，大文件时可能存在刷新延迟未显示情况
        :return:
        """
        self.fm.push_clipboard_to_device(self.fm.path_cur)
        self.draw_path()

    def download(self, file_path):
        """
            下载文件
        :param file_path:
        :return:
        """
        path_download = Param.PATH_DOWNLOAD / self.adv_device.serial_no
        path_download.mkdir(parents=True, exist_ok=True)

        file_stat = self.adv_device.adb_dev.sync.stat(file_path.__str__())
        if stat.S_ISDIR(file_stat.mode):
            path_base = path_download / file_path.name
            path_base.mkdir(parents=True, exist_ok=True)
            self.adv_device.adb_dev.sync.pull_dir(file_path.__str__(), path_base)
            logger.success(f"Dir {file_path} Download to {path_download}")
        elif stat.S_ISREG(file_stat.mode):
            self.adv_device.adb_dev.sync.pull(file_path.__str__(), path_download / file_path.name)
            logger.success(f"File {file_path} Download to {path_download}")

    def download_selected(self):
        """
            下载选中文件
        :return:
        """
        for _ in self.all_cb:
            if dpg.get_value(_):
                self.download(dpg.get_item_user_data(_)[0])
        self.draw_path()

    def rm_selected(self):
        """
            删除选中项
        :return:
        """
        selected = [dpg.get_item_user_data(_) for _ in self.all_cb if dpg.get_value(_)]
        if len(selected) == 0:
            return

        def _rm():
            for path, ind in selected:
                self.fm.rm(path)

            self.draw_path()

        TempModal.draw_confirm(f"Delete {len(selected)} selected items?", _rm)

    def rm(self, file_path):
        """
            删除单个文件
        :param file_path:
        :return:
        """
        def _rm():
            self.fm.rm(file_path)
            self.draw_path()

        TempModal.draw_confirm(f"Delete {file_path} ?", _rm)

    def highlight(self, sender, app_data, user_data):
        """
            高亮选中项
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        if app_data:
            dpg.highlight_table_cell(self.tag_table, user_data[1], 1, [100, 100, 100])
        else:
            dpg.unhighlight_table_cell(self.tag_table, user_data[1], 1)

    def selected(self, sender, app_data, user_data):
        """
            选中回调函数
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """

        selected_item = [_ for _ in self.all_cb if dpg.get_value(_)]
        values = [dpg.get_item_user_data(_) for _ in selected_item]

        dpg.set_value(self.tag_txt_info, f"{len(selected_item)} selected")
        if len(selected_item) > 0:
            msg = [f"{_[1]} | {_[0]}" for _ in values]
            dpg.set_value(self.tag_txt_info_detail, '\n'.join(msg))
        else:
            dpg.set_value(self.tag_txt_info_detail, 'No Item Selected.')

        for _ in self.all_cb:
            self.highlight(_, _ in selected_item, dpg.get_item_user_data(_))

    def select_all(self):
        """
            全选
        :return:
        """
        for _ in self.all_cb:
            dpg.set_value(_, True)

        self.selected(None, None, None)

    def unselect_all(self):
        """
            全否
        :return:
        """
        for _ in self.all_cb:
            dpg.set_value(_, False)

        self.selected(None, None, None)

    def open_dir(self, sender, app_data, user_data):
        """
            打开路径
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """

        self.fm.cd(user_data)
        self.draw_path()

    def open_file(self, file_path):
        """
            本地打开文件
            下载文件至临时目录，并打开
        :param file_path:
        :return:
        """
        path_temp = Param.PATH_TEMP / self.adv_device.serial_no
        path_temp.mkdir(parents=True, exist_ok=True)

        path_save = path_temp / file_path.name

        file_info = self.adv_device.adb_dev.sync.stat(file_path.__str__())

        self.adv_device.adb_dev.sync.pull(file_path.__str__(), path_save)
        threading.Thread(target=self._open, args=(path_save, file_info.size,)).start()

    def _open(self, path_save: pathlib.Path, file_size: int):
        """
            使用线程打开，避免大文件导致下载时间过长
        :param path_save:
        :param file_size:
        :return:
        """
        retry_n = file_size // (1024 * 1024) + 5
        while path_save.stat().st_size != file_size:
            time.sleep(1)
            logger.warning(f"File Still Downloading...")
            retry_n -= 1
            if retry_n == 0:
                logger.error(f"File Download Failed")
                return
        webbrowser.open(path_save.__str__())


@dataclass
class Message:
    """
        信息
    """

    payload: str
    dt: datetime.datetime = field(default_factory=datetime.datetime.now)
    msg_from: str = None
    msg_to: str = None
    print_console: bool = True


class CPMBottomPad(CPMPad):
    """
        底部栏
    """

    def show_message(self, msg: str | Message, with_datetime: bool = True, print_console: bool = True):
        """
            展示信息
        :param msg:
        :param with_datetime:
        :param print_console:
        :return:
        """
        msg = Message(msg) if type(msg) is str else msg
        show_msg = f"{datetime.datetime.now().strftime('%m-%d %H:%M:%S ') if with_datetime else ''}{msg.payload}"
        dpg.set_value(self.tag_msg, show_msg if len(show_msg) <= 50 else (show_msg[:50] + '...'))
        dpg.set_value(self.tag_msg_all, show_msg)
        self.logs.insert(0, msg)

        if msg.print_console and print_console:
            logger.info(f"Message: {msg}")
    def clear(self):
        """
            清空
        :return:
        """
        self.logs.clear()
        self.tag_msg = ''
        self.tag_msg_all = ''

    def draw_win_logs(self):
        """
            绘制日志窗口
        :return:
        """

        def clear_logs():
            """
                清空日志
            :return:
            """
            self.logs.clear()
            dpg.delete_item(tag_win)

        with dpg.window(width=400, label='Logs') as tag_win:
            with dpg.group(horizontal=True):
                dpg.add_input_text(
                    label='Filter', callback=lambda s, a: dpg.set_value(tag_filter, a), width=-35
                )

            dpg.add_separator()
            with dpg.child_window(height=300, autosize_x=True, horizontal_scrollbar=True) as tag_win_logs:
                with dpg.filter_set() as tag_filter:
                    for index, _ in enumerate(self.logs):
                        with dpg.group(horizontal=True, filter_key=f"{_.dt} {_.payload}") as tag_g:
                            dpg.add_selectable(
                                label=f"{str(index).rjust(4, '0')} {_.dt.strftime('%H:%M:%S')} > {_.payload}"
                            )
                        with dpg.tooltip(tag_g):
                            dpg.add_text(f"{str(index).rjust(4, '0')} | {_.dt} >> {_.payload}")

            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_button(label='Clear & Close', callback=clear_logs, width=-70, height=30)
                dpg.add_button(label='Close', callback=lambda: dpg.delete_item(tag_win), width=-1, height=30)

    def setup_inner(self, *args, **kwargs):

        self.logs = []

        with dpg.child_window(no_scrollbar=True, height=40):

            with dpg.group(horizontal=True):

                self.tag_show_logs = dpg.add_button(label='Logs', callback=self.draw_win_logs)

                self.tag_msg = dpg.add_text()

                with dpg.tooltip(dpg.last_item()):
                    self.tag_msg_all = dpg.add_text()
