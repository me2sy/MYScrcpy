# -*- coding: utf-8 -*-
"""
    Control Adapter
    ~~~~~~~~~~~~~~~~~~

    Log:
        2025-04-23 3.2.0 Me2sY
            1.适配 Scrcpy 3.2 增加 vendorId ProductId
            2.优化关闭逻辑，避免卡线程
            3. 2025-05-06 增加 ignore_repeat 忽略重复输入，提高控制精确度

        2024-10-27 1.7.0 Me2sY  新增 Gamepad

        2024-09-08 1.5.7 Me2sY  适配 Scrcpy 屏幕坐标

        2024-09-06 1.5.5 Me2sY  增加 PC -> Device 剪贴板功能

        2024-08-29 1.4.0 Me2sY
            1.优化结构
            2.增加剪贴板功能

        2024-08-25 1.3.7 Me2sY
            新增部分方法，支持 ScalePointR 控制
"""

__author__ = 'Me2sY'
__version__ = '3.2.0'

__all__ = [
    'KeyboardWatcher', 'Gamepad',
    'ControlArgs', 'ControlAdapter'
]


from dataclasses import dataclass, field
from enum import IntEnum
import queue
import re
import struct
import threading
from typing import ClassVar, Callable

from adbutils import AdbDevice, AdbError
from loguru import logger
import pyperclip

from myscrcpy.core.args_cls import ScrcpyConnectArgs
from myscrcpy.core.adapter_cls import ScrcpyAdapter
from myscrcpy.core.connection import Connection
from myscrcpy.utils import Action, Coordinate, ScalePointR
from myscrcpy.utils import UnifiedKey, UnifiedKeys, KeyMapper
from myscrcpy.utils import (
    ROTATION_HORIZONTAL, ROTATION_VERTICAL,
    UHID_MOUSE_REPORT_DESC, UHID_KEYBOARD_REPORT_DESC, UHID_GAMEPAD_REPORT_DESC
)


class KeyboardWatcher:
    """
        KeyboardWatcher
        保存按键状态 转化为 hid keyboard事件
    """
    modifier_map = {
        UnifiedKeys.UK_KB_CONTROL: 0b1,
        UnifiedKeys.UK_KB_SHIFT: 0b10,
        UnifiedKeys.UK_KB_ALT: 0b100,

        UnifiedKeys.UK_KB_CONTROL_L: 0b1,
        UnifiedKeys.UK_KB_SHIFT_L: 0b10,
        UnifiedKeys.UK_KB_ALT_L: 0b100,

        UnifiedKeys.UK_KB_WIN_L: 0b1000,
        UnifiedKeys.UK_KB_CONTROL_R: 0b10000,
        UnifiedKeys.UK_KB_SHIFT_R: 0b100000,
        UnifiedKeys.UK_KB_ALT_R: 0b1000000,
        UnifiedKeys.UK_KB_WIN_R: 0b10000000,
    }

    def __init__(self, uhid_keyboard_send_method, active: bool = True):
        self.pressed = list()
        self.modifiers = 0
        self.uhid_keyboard_send_method = uhid_keyboard_send_method
        self.active = active

    def clear(self):
        """
            清空按键状态
        :return:
        """
        self.pressed = list()
        self.modifiers = 0

    def key_pressed(self, unified_key: UnifiedKey):
        """
            获取按键并存储状态
        :param unified_key:
        :return:
        """

        if unified_key in self.modifier_map:    # Mod Key Press
            b = self.modifier_map[unified_key]
            if self.modifiers & b == 0:
                self.modifiers |= b
            else:
                return

        else:
            scan_code = KeyMapper.uk2uhid(unified_key)
            if scan_code is None:
                return

            if scan_code in self.pressed:
                return

            if len(self.pressed) == 6:
                return

            self.pressed.append(scan_code)

        self.update()

    def key_release(self, unified_key: UnifiedKey):
        """
            按键释放
        :param unified_key:
        :return:
        """
        if unified_key in self.modifier_map:
            self.modifiers &= ~self.modifier_map[unified_key] & 0xff

        else:
            try:
                self.pressed.remove(KeyMapper.uk2uhid(unified_key))
            except ValueError:
                pass
            except KeyError:
                pass

        self.update()

    def update(self):
        """
            更新键盘状态
        :return:
        """

        if not self.active:
            return

        # 补全 6 位 按键码
        keys = [*self.pressed]
        for _ in range(6 - len(self.pressed)):
            keys.append(0)

        self.uhid_keyboard_send_method(
            modifiers=self.modifiers,
            key_scan_codes=keys
        )


class Gamepad:

    # A gamepad HID input report is 15 bytes long:
    #  - bytes 0-3:   left stick state
    #  - bytes 4-7:   right stick state
    #  - bytes 8-11:  L2/R2 triggers state
    #  - bytes 12-13: buttons state
    #  - bytes 14:    hat switch position (dpad)
    #
    #                  +---------------+
    #         byte 0:  |. . . . . . . .|
    #                  |               | left stick x (0-65535, little-endian)
    #         byte 1:  |. . . . . . . .|
    #                  +---------------+
    #         byte 2:  |. . . . . . . .|
    #                  |               | left stick y (0-65535, little-endian)
    #         byte 3:  |. . . . . . . .|
    #                  +---------------+
    #         byte 4:  |. . . . . . . .|
    #                  |               | right stick x (0-65535, little-endian)
    #         byte 5:  |. . . . . . . .|
    #                  +---------------+
    #         byte 6:  |. . . . . . . .|
    #                  |               | right stick y (0-65535, little-endian)
    #         byte 7:  |. . . . . . . .|
    #                  +---------------+
    #         byte 8:  |. . . . . . . .|
    #                  |               | L2 trigger (0-32767, little-endian)
    #         byte 9:  |0 . . . . . . .|
    #                  +---------------+
    #        byte 10:  |. . . . . . . .|
    #                  |               | R2 trigger (0-32767, little-endian)
    #        byte 11:  |0 . . . . . . .|
    #                  +---------------+
    #
    #                   ,--------------- SC_GAMEPAD_BUTTON_RIGHT_SHOULDER
    #                   | ,------------- SC_GAMEPAD_BUTTON_LEFT_SHOULDER
    #                   | |
    #                   | |   ,--------- SC_GAMEPAD_BUTTON_NORTH
    #                   | |   | ,------- SC_GAMEPAD_BUTTON_WEST
    #                   | |   | |
    #                   | |   | |   ,--- SC_GAMEPAD_BUTTON_EAST
    #                   | |   | |   | ,- SC_GAMEPAD_BUTTON_SOUTH
    #                   v v   v v   v v
    #                  +---------------+
    #        byte 12:  |. . 0 . . 0 . .|
    #                  |               | Buttons (16-bit little-endian)
    #        byte 13:  |0 . . . . . 0 0|
    #                  +---------------+
    #                     ^ ^ ^ ^ ^
    #                     | | | | |
    #                     | | | | |
    #                     | | | | `----- SC_GAMEPAD_BUTTON_BACK
    #                     | | | `------- SC_GAMEPAD_BUTTON_START
    #                     | | `--------- SC_GAMEPAD_BUTTON_GUIDE
    #                     | `----------- SC_GAMEPAD_BUTTON_LEFT_STICK
    #                     `------------- SC_GAMEPAD_BUTTON_RIGHT_STICK
    #
    #                  +---------------+
    #        byte 14:  |0 0 0 . . . . .| hat switch (dpad) position (0-8)
    #                  +---------------+
    #                     9 possible positions and their values:
    #                             8 1 2
    #                             7 0 3
    #                             6 5 4
    #                     (8 is top-left, 1 is top, 2 is top-right, etc.)

    @dataclass
    class Axis:
        """
            Axis 值转换器
        """
        max_value: int
        last_value: int | None = None
        jitter: int = 0

        def __post_init__(self):
            if self.max_value < 0:
                raise ValueError(f'Max Value must be positive')

            if self.last_value is None:
                self.last_value = int(self.max_value / 2)

        def __call__(self, *args, **kwargs) -> int:
            return self.last_value

        def s2v(self, scale: float) -> tuple[bool, int]:
            """
                将 -1 ~ 1 转为 正值
            :param scale:
            :return:
            """
            _ = max(
                0,
                min(
                    self.max_value,
                    round((scale + 1) / 2 * self.max_value)
                )
            )
            if abs(self.last_value - _) < self.jitter:
                return False, _
            else:
                self.last_value = _
                return True, _


    @dataclass
    class DPad:

        # 9 possible positions and their values:
        #   8 1 2
        #   7 0 3
        #   6 5 4
        # (8 is top-left, 1 is top, 2 is top-right, etc.)

        dpad_keys: ClassVar[tuple[UnifiedKey]] = (
            UnifiedKeys.UK_GP_DP_U, UnifiedKeys.UK_GP_DP_D, UnifiedKeys.UK_GP_DP_L, UnifiedKeys.UK_GP_DP_R,
            UnifiedKeys.UK_GP_DP_UL, UnifiedKeys.UK_GP_DP_UR, UnifiedKeys.UK_GP_DP_DL, UnifiedKeys.UK_GP_DP_DR
        )

        pressed: list[UnifiedKey] = field(default_factory=list)

        def key_pressed(self, unified_key: UnifiedKey):
            """
                Dpad key pressed
            :param unified_key:
            :return:
            """
            if unified_key not in self.pressed:
                self.pressed.append(unified_key)

        def key_release(self, unified_key: UnifiedKey):
            """
                Dpad key release
            :param unified_key:
            :return:
            """
            if unified_key in self.pressed:
                self.pressed.remove(unified_key)

        def __call__(self, *args, **kwargs) -> int:
            """
                Dpad Value
            :param args:
            :param kwargs:
            :return:
            """
            if len(self.pressed) == 1:
                return self.pressed[0].value

            elif len(self.pressed) == 2:
                if (UnifiedKeys.UK_GP_DP_U in self.pressed) and (UnifiedKeys.UK_GP_DP_L in self.pressed):
                    return UnifiedKeys.UK_GP_DP_UL.value

                if (UnifiedKeys.UK_GP_DP_U in self.pressed) and (UnifiedKeys.UK_GP_DP_R in self.pressed):
                    return UnifiedKeys.UK_GP_DP_UR.value

                if (UnifiedKeys.UK_GP_DP_D in self.pressed) and (UnifiedKeys.UK_GP_DP_L in self.pressed):
                    return UnifiedKeys.UK_GP_DP_DL.value

                if (UnifiedKeys.UK_GP_DP_D in self.pressed) and (UnifiedKeys.UK_GP_DP_R in self.pressed):
                    return UnifiedKeys.UK_GP_DP_DR.value

            else:
                return 0

    gamepad_inited = set()
    ID_START = 3
    MAX_COUNT = 8

    MAX_VALUE_STICK = 65535
    MAX_VALUE_TRIGGER = 32767

    @classmethod
    def init_id(cls) -> int:
        """
            创建唯一ID
            最多8个
        :return:
        """
        for _ in range(cls.ID_START, cls.ID_START + cls.MAX_COUNT):
            if _ not in cls.gamepad_inited:
                cls.gamepad_inited.add(_)
                return _
        raise RuntimeError(f"Only supports 8 gamepads")

    def __init__(
            self, send_method: Callable, name: str = 'MYGP',
            auto_create: bool = True
    ):
        self.gp_id = self.init_id()
        self.name = f"{name}_{self.gp_id}"

        self.send_method = send_method

        self.is_created = False

        self.pressed = list()

        self.left_stick_x = self.Axis(self.MAX_VALUE_STICK, jitter=1500)
        self.left_stick_y = self.Axis(self.MAX_VALUE_STICK, jitter=1500)

        self.right_stick_x = self.Axis(self.MAX_VALUE_STICK, jitter=1500)
        self.right_stick_y = self.Axis(self.MAX_VALUE_STICK, jitter=1500)

        self.left_trigger = self.Axis(self.MAX_VALUE_TRIGGER)
        self.right_trigger = self.Axis(self.MAX_VALUE_TRIGGER)

        self.last_packet = None

        self.dpad = self.DPad()

        self.axis_mapper = {
            0: self.left_stick_x,
            1: self.left_stick_y,
            2: self.right_stick_x,
            3: self.right_stick_y,
            4: self.left_trigger,
            5: self.right_trigger
        }

        auto_create and self.uhid_create() and self.update_status()

    def uhid_create(self):
        """
            Create uhid gamepad
        :return:
        """
        self.is_created = True
        self.send_method(
            struct.pack(
                '>BhhhB', *[
                    ControlAdapter.MessageType.UHID_CREATE.value,
                    self.gp_id,
                    0,
                    0,
                    len(self.name.encode())
                ]
            ) + self.name.encode(
            ) + struct.pack(
                '>H', len(UHID_GAMEPAD_REPORT_DESC)
            ) + UHID_GAMEPAD_REPORT_DESC
        )

    def uhid_destroy(self):
        """
            Destroy uhid gamepad
        :return:
        """
        if self.is_created:
            self.is_created = False
            self.send_method(
                ControlAdapter.packet__uhid_destroy(self.gp_id)
            )
            self.__class__.gamepad_inited.remove(self.gp_id)

    def key_pressed(self, unified_key: UnifiedKey, auto_update: bool = True):
        """
            按键按下
        :param unified_key:
        :param auto_update:
        :return:
        """
        if unified_key in self.dpad.dpad_keys:
            self.dpad.key_pressed(unified_key)
            auto_update and self.update_status()
            return

        elif unified_key not in self.pressed:
            self.pressed.append(unified_key)
            auto_update and self.update_status()
            return

    def key_release(self, unified_key: UnifiedKey, auto_update: bool = True):
        """
            按键释放
        :param unified_key:
        :param auto_update:
        :return:
        """
        if unified_key in self.dpad.dpad_keys:
            self.dpad.key_release(unified_key)
            auto_update and self.update_status()
            return

        elif unified_key in self.pressed:
            self.pressed.remove(unified_key)
            auto_update and self.update_status()
            return

    def axis_value_changed(self, axis_idx: int, value_scale: float):
        """
            stick value changed
            for pygame joystick
        :param axis_idx:
        :param value_scale:
        :return:
        """
        self.axis_mapper[axis_idx].s2v(value_scale)

    def update_status(self):
        """
            更新status
        :return:
        """

        # Buttons Status
        key_v = 0
        for uk in self.pressed:
            key_v |= uk.value

        # Create gamepad HID input report
        packet = struct.pack(
            '<HHHHHHHB', *[
                self.left_stick_x(),
                self.left_stick_y(),
                self.right_stick_x(),
                self.right_stick_y(),
                self.left_trigger(),
                self.right_trigger(),
                key_v,
                self.dpad()
            ]
        )

        # Send packet
        if packet != self.last_packet:
            self.last_packet = packet
            self.send_method(
                struct.pack(
                    '>BhH', *[
                        ControlAdapter.MessageType.UHID_INPUT.value,
                        self.gp_id,
                        15
                    ]
                ) + packet
            )


@dataclass
class ControlArgs(ScrcpyConnectArgs):
    """
        控制参数
    """

    STATUS_OFF: ClassVar[str] = 'off'
    STATUS_ON: ClassVar[str] = 'on'
    STATUS_KEEP: ClassVar[str] = 'keep'      # 保持当前状态

    screen_status: str = STATUS_KEEP    # 默认屏幕状态
    clipboard: bool = True              # 开启剪切板回写功能

    def to_args(self) -> list:
        return [
            f"control={'true' if self.is_activate else 'false'}"
        ]

    @classmethod
    def load(cls, **kwargs):
        return cls(
            is_activate=kwargs.get('is_activate', True),
            screen_status=kwargs.get('screen_status', cls.STATUS_KEEP),
            clipboard=kwargs.get('clipboard', True),
        )


class ControlAdapter(ScrcpyAdapter):
    """
        Control 采用全尺寸输入
        建议使用 ScalePointR 进行输入，无需判断旋转状态
    """

    CLOSE_PACKET = b'Me2sYSayBye'

    class MessageType(IntEnum):
        INJECT_TOUCH_EVENT = 2
        SET_CLIPBOARD = 9
        SET_SCREEN_POWER_MODE = 10
        UHID_CREATE = 12
        UHID_INPUT = 13
        UHID_DESTROY = 14

    @staticmethod
    def get_window_size(adb_device: AdbDevice) -> Coordinate:
        """
            Rewrite adbutils.adb.shell.window_size
            注意！旋转参数缺失
            去除Rotation，避免延迟
        :return:
        """
        output = adb_device.shell("wm size")
        o = re.search(r"Override size: (\d+)x(\d+)", output)
        if o:
            w, h = o.group(1), o.group(2)
            return Coordinate(int(w), int(h))
        m = re.search(r"Physical size: (\d+)x(\d+)", output)
        if m:
            w, h = m.group(1), m.group(2)
            return Coordinate(int(w), int(h))
        raise AdbError("wm size output unexpected", output)

    def __init__(self, connection: Connection):
        """
            创建 Control Socket
        :param connection:
        """
        super().__init__(connection)

        self.__packet_queue = queue.Queue()
        self.last_packet = None

        self.screen_status = connection.args.screen_status
        self.clipboard = connection.args.clipboard

        self.coord_hv = {}

    def start(self, adb_device: AdbDevice, *args, **kwargs) -> bool:
        """
            启动进程
        :param adb_device:
        :param args:
        :param kwargs:
        :return:
        """
        if self.is_running and self.is_ready:
            return True

        _coord = self.get_window_size(adb_device)

        # 2024-09-08 1.5.7 Me2sY  适配Scrcpy control
        _coord = _coord.fit_scrcpy_video()

        if _coord.rotation == ROTATION_VERTICAL:
            _coord_v = _coord
        else:
            _coord_v = Coordinate(_coord.height, _coord.width)

        self.coord_hv[ROTATION_VERTICAL] = _coord_v
        self.coord_hv[ROTATION_HORIZONTAL] = _coord_v.rotate()

        if self.screen_status == ControlArgs.STATUS_KEEP:
            self.screen_status = adb_device.is_screen_on()

        if self.conn.connect(adb_device):
            self.is_running = True
            threading.Thread(target=self.main_thread).start()
            threading.Thread(target=self.clipboard_thread).start()
            return True
        else:
            return False

    def stop(self):
        """
            停止进程
        :return:
        """
        self.is_running = False
        self.__packet_queue.put(self.CLOSE_PACKET)
        self.conn.disconnect()
        self.is_ready = False

    def main_thread(self):
        """
            主进程
        :return:
        """
        self.is_ready = True
        logger.success(f"Control Socket {self.conn.scid} Connected!")
        self.f_set_screen(
            True if self.screen_status == ControlArgs.STATUS_ON else False
        )
        while self.is_running:
            try:
                self.conn.send(self.__packet_queue.get())
            except OSError:
                continue
            except Exception as e:
                logger.info(f"Exception while sending control {e}")
                continue

        self.is_ready = False
        logger.warning(f"{self.__class__.__name__} Main Thread {self.conn.scid} Closed.")

    def clipboard_thread(self):
        """
            剪切板
            使用 pyperclip https://pypi.org/project/pyperclip/
            实现回写功能
        :return:
        """
        while self.is_running:
            try:
                _bs = self.conn.recv(262144)
                if _bs == b'':
                    # socket 断开
                    self.is_running = False
                else:
                    (_t, _size,) = struct.unpack('>Bi', _bs[:5])
                    if self.clipboard:
                        pyperclip.copy(_bs[5:5+_size].decode('utf-8'))
            except OSError:
                pass
            except Exception as e:
                logger.info(f"Exception while sending clipboard {e}")
                continue

    def set_clipboard_status(self, status: bool):
        """
            设置剪贴板开关
        :param status:
        :return:
        """
        self.clipboard = status

    @classmethod
    def connect(cls, adb_device: AdbDevice, control_args: ControlArgs, *args, **kwargs):
        """
            根据 ControlArgs 快速创建连接
        :param adb_device:
        :param control_args:
        :param args:
        :param kwargs:
        :return:
        """
        if not control_args.is_activate:
            return None

        _ = cls(Connection(control_args))
        if _.start(adb_device):
            return _
        else:
            logger.error('ControlAdapter Start Failed!')
            return None

    # ---------------------------- Functions ----------------------------

    def send_packet(self, packet: bytes, ignore_repeat: bool = False):
        """
            发送控制数据包
        :param packet:
        :param ignore_repeat: 忽略重复命令
        :return:
        """
        if packet != self.last_packet or ignore_repeat:
            self.__packet_queue.put(packet)
        self.last_packet = packet

    @classmethod
    def packet__screen(cls, status: bool) -> bytes:
        """
            控制设备屏幕
        :param status:
        :return:
        """
        return struct.pack(
            '>BB',
            *[
                cls.MessageType.SET_SCREEN_POWER_MODE.value,
                1 if status else 0
            ]
        )

    def f_set_screen(self, status: bool):
        """
            控制屏幕开关
        :param status:
        :return:
        """
        self.send_packet(self.packet__screen(status))
        self.screen_status = status

    @classmethod
    def packet__touch(
            cls,
            action: int,
            x: int, y: int,
            width: int, height: int,
            touch_id: int,
    ) -> bytes:
        """
            转换为 Scrcpy injectTouch 指令
            注意 width height 需要随着视频旋转进行变换
            同时 x y 值 计算相对于frame坐标系内值
            device 1920x1080
            frame  1600x900
            x 0 - 1600
            y 0 - 900
            发生旋转后
            frame 900x1600
            x 0 - 900
            y 0 - 1600

        :param action:
        :param x:       frame_x
        :param y:       frame_y
        :param width:   frame_width
        :param height:  frame_height
        :param touch_id:
        :return:
        """
        return struct.pack(
            '>BBQiiHHHII',
            *[
                cls.MessageType.INJECT_TOUCH_EVENT.value,           # 1 B  Event Type
                action,                                                 # 2 B  Action
                touch_id,                                               # 3 Q pointerId
                int(x), int(y),                                         # 4 ii position x, y
                width, height,                                          # 5 HH width height
                0 if action == Action.RELEASE.value else 0xffff,        # 6 H pressure
                1, 1                                                    # 7 II actionButton/buttons
            ]
        )

    def f_touch(
            self,
            action: int,
            x: int, y: int,
            width: int, height: int,
            touch_id: int,
            ignore_repeat: bool = False
    ):
        self.send_packet(
            self.packet__touch(
                action, x, y, width, height, touch_id
            ), ignore_repeat=ignore_repeat
        )

    def f_touch_spr(
            self,
            action: int,
            scale_point_r: ScalePointR,
            touch_id: int,
            ignore_repeat: bool = False
    ):
        """
            比例触摸，若方向不一致则无效
        :param action:
        :param scale_point_r:
        :param touch_id:
        :param ignore_repeat: 忽略重复按键
        :return:
        """
        _coord = self.coord_hv[scale_point_r.r]
        self.f_touch(
            action,
            **_coord.to_point(scale_point_r).d,
            **_coord.d,
            touch_id=touch_id, ignore_repeat=ignore_repeat
        )

    @classmethod
    def packet__text_paste(cls, text: str, paste: bool = True) -> bytes:
        text_bytes = text.encode('utf-8')
        return struct.pack(
            '>BQ?I',
            cls.MessageType.SET_CLIPBOARD.value,
            0,
            paste,
            len(text_bytes)
        ) + text_bytes

    def f_text_paste(self, text: str, paste: bool = True):
        self.send_packet(self.packet__text_paste(text, paste))

    def f_clipboard_pc2device(self, paste: bool = True) -> bool:
        """
            读取 PC 剪切板内容 粘贴至 设备
        :param paste:
        :return:
        """
        text = pyperclip.paste()
        if text is not None and len(text) > 0:
            self.f_text_paste(text, paste)
            return True
        else:
            return False

    @classmethod
    def packet__uhid_mouse_create(
            cls, mouse_name: str = 'MYScrcpy', mouse_id: int = 2, vendor_id: int = 0, product_id: int = 0,
    ):
        """
            Create Mouse UHID
        :param mouse_name:
        :param mouse_id:
        :param vendor_id:
        :param product_id:
        :return:
        """
        return struct.pack(
            '>BhhhB', *[
                cls.MessageType.UHID_CREATE.value,              # 1 type                        B
                mouse_id,                                           # 2 mouse_id                   h

                # 3.X 新增 VendorId ProductId
                vendor_id,                                          # 3 VendorId                    h
                product_id,                                         # 4 ProductId                   h

                len(mouse_name.encode()),                           # 5 len(bytes(mouse_name))       B
            ]
        ) + mouse_name.encode(                                      # 6 mouse_name
        ) + struct.pack(
            '>H', len(UHID_MOUSE_REPORT_DESC)               # 7 report_desc_len             H
        ) + UHID_MOUSE_REPORT_DESC                                  # 8 report desc

    def f_uhid_mouse_create(
            self, mouse_name: str = 'MYScrcpy', mouse_id: int = 2, vendor_id: int = 0, product_id: int = 0
    ):
        self.send_packet(self.packet__uhid_mouse_create(mouse_name, mouse_id, vendor_id, product_id))

    @classmethod
    def packet__uhid_mouse_input(
            cls,
            x_rel: int, y_rel: int,
            mouse_id: int = 2,
            left_button: bool = False,
            right_button: bool = False,
            middle_button: bool = False,
            wheel_motion: int = 0
    ):
        return struct.pack(
            '>BhHBbbb',
            *[
                cls.MessageType.UHID_INPUT.value,
                mouse_id,
                4,
                0b00000000 | (
                    0b100 if middle_button else 0
                ) | (
                    0b10 if right_button else 0
                ) | (
                    0b1 if left_button else 0
                ),
                x_rel,
                y_rel,
                wheel_motion
            ]
        )

    def f_uhid_mouse_input(
            self,
            x_rel: int, y_rel: int,
            mouse_id: int = 2,
            left_button: bool = False,
            right_button: bool = False,
            middle_button: bool = False,
            wheel_motion: int = 0,
            ignore_repeat: bool = True,
    ):
        self.send_packet(self.packet__uhid_mouse_input(
            x_rel, y_rel, mouse_id, left_button, right_button, middle_button, wheel_motion
        ), ignore_repeat=ignore_repeat)

    @classmethod
    def packet__uhid_keyboard_create(
            cls,
            keyboard_name: str = 'MYScrcpy', keyboard_id: int = 1, vendor_id: int = 0, product_id: int = 0,
    ):
        """
            Scrcpy 1.7 add uhid name
        :param keyboard_name:
        :param keyboard_id:
        :param vendor_id:
        :param product_id:
        :return:
        """
        return struct.pack(
            '>BhhhB', *[
                cls.MessageType.UHID_CREATE.value,               # 1 type                        B
                keyboard_id,                                        # 2 keyboard_id                 h

                # 3.X 新增 VendorId ProductId
                vendor_id,                                          # 3 VendorId                    h
                product_id,                                         # 4 ProductId                   h

                len(keyboard_name.encode()),                        # 5 len(bytes(keyboard_name))   B
            ]
        ) + keyboard_name.encode(                                   # 6 keyboard_name
        ) + struct.pack(
            '>H', len(UHID_KEYBOARD_REPORT_DESC)            # 7 report_desc_len             H
        ) + UHID_KEYBOARD_REPORT_DESC                               # 8 report desc

    def f_uhid_keyboard_create(
            self, keyboard_name: str = 'MYScrcpy', keyboard_id: int = 1, vendor_id: int = 0, product_id: int = 0
    ):
        self.send_packet(
            self.packet__uhid_keyboard_create(
                keyboard_name=keyboard_name, keyboard_id=keyboard_id, vendor_id=vendor_id, product_id=product_id
            )
        )

    @classmethod
    def packet__uhid_keyboard_input(
            cls,
            keyboard_id: int = 1,
            modifiers: int = 0,
            key_scan_codes: tuple = tuple()
    ):
        """
            详见 https://github.com/Genymobile/scrcpy/blob/master/app/src/hid/hid_keyboard.c
        :param keyboard_id:
        :param modifiers:
        :param key_scan_codes:
        :return:
        """
        return struct.pack(
            '>BhHBbBBBBBB',
            *[
                cls.MessageType.UHID_INPUT.value,   # 1 Type
                keyboard_id,                            # 2 id
                8,                                      # 3 size
                modifiers,                              # 4 modifiers bytes
                0,                                      # 5 reserved always 0  byte1
                *key_scan_codes                         # 6 - 11 key scancode  byte2-7
            ]
        )

    def f_uhid_keyboard_input(
            self,
            keyboard_id: int = 1,
            modifiers: int = 0,
            key_scan_codes: tuple = tuple()
    ):
        self.send_packet(self.packet__uhid_keyboard_input(
            keyboard_id, modifiers, key_scan_codes
        ))

    @classmethod
    def packet__uhid_destroy(cls, device_id: int):
        """
            Scrcpy 1.7 Destroy uhid device(keyboard/mouse/joystick)
        :param device_id:
        :return:
        """
        return struct.pack(
            '>BB',
            *[
                cls.MessageType.UHID_DESTROY.value,
                device_id
            ]
        )

    def f_uhid_destroy(self, device_id: int):
        """
            Destroy uhid device(keyboard/mouse/joystick)
        :param device_id:
        :return:
        """
        self.send_packet(self.packet__uhid_destroy(device_id))


if __name__ == '__main__':
    """
        DEMO Here
    """
    from adbutils import adb
    d = adb.device_list()[0]

    ca = ControlAdapter.connect(d, ControlArgs())
