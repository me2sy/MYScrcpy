# -*- coding: utf-8 -*-
"""
    Control Socket Controller
    ~~~~~~~~~~~~~~~~~~
    控制器

    Log:
        2024-08-02 1.1.3 Me2sY
            1.新增 to_args 方法
            2.修改 ZMQControlServer 部分方法

        2024-08-01 1.1.2 Me2sY  更新类名称

        2024-07-30 1.1.0 Me2sY
            1.抽离形成单独部分
            2.修改部分功能结构
"""

__author__ = 'Me2sY'
__version__ = '1.1.3'

__all__ = [
    'KeyboardWatcher', 'ControlSocketController',
    'ZMQControlServer'
]

import struct
from enum import IntEnum
import queue
import time
import threading

from loguru import logger
import zmq

from myscrcpy.utils import UnifiedKey, UnifiedKeyMapper, Action
from myscrcpy.controller.scrcpy_socket import ScrcpySocket


UHID_MOUSE_REPORT_DESC = bytearray([
    0x05, 0x01,  # Usage Page (Generic Desktop)
    0x09, 0x02,  # Usage (Mouse)
    0xA1, 0x01,  # Collection (Application)
    0x09, 0x01,  # Usage (Pointer)
    0xA1, 0x00,  # Collection (Physical)
    0x05, 0x09,  # Usage Page (Buttons)
    0x19, 0x01,  # Usage Minimum (1)
    0x29, 0x05,  # Usage Maximum (5)
    0x15, 0x00,  # Logical Minimum (0)
    0x25, 0x01,  # Logical Maximum (1)
    0x95, 0x05,  # Report Count (5)
    0x75, 0x01,  # Report Size (1)
    0x81, 0x02,  # Input (Data, Variable, Absolute): 5 buttons bits
    0x95, 0x01,  # Report Count (1)
    0x75, 0x03,  # Report Size (3)
    0x81, 0x01,  # Input (Constant): 3 bits padding
    0x05, 0x01,  # Usage Page (Generic Desktop)
    0x09, 0x30,  # Usage (X)
    0x09, 0x31,  # Usage (Y)
    0x09, 0x38,  # Usage (Wheel)
    0x15, 0x81,  # Local Minimum (-127)
    0x25, 0x7F,  # Local Maximum (127)
    0x75, 0x08,  # Report Size (8)
    0x95, 0x03,  # Report Count (3)
    0x81, 0x06,  # Input (Data, Variable, Relative): 3 position bytes (X, Y, Wheel)
    0xC0,  # End Collection
    0xC0,  # End Collection
])

UHID_KEYBOARD_REPORT_DESC = bytearray([
    0x05, 0x01,  # Usage Page (Generic Desktop)
    0x09, 0x06,  # Usage (Keyboard)
    0xA1, 0x01,  # Collection (Application)
    0x05, 0x07,  # Usage Page (Key Codes)
    0x19, 0xE0,  # Usage Minimum (224)
    0x29, 0xE7,  # Usage Maximum (231)
    0x15, 0x00,  # Logical Minimum (0)
    0x25, 0x01,  # Logical Maximum (1)
    0x75, 0x01,  # Report Size (1)
    0x95, 0x08,  # Report Count (8)
    0x81, 0x02,  # Input (Data, Variable, Absolute): Modifier byte
    0x75, 0x08,  # Report Size (8)
    0x95, 0x01,  # Report Count (1)
    0x81, 0x01,  # Input (Constant): Reserved byte
    0x05, 0x08,  # Usage Page (LEDs)
    0x19, 0x01,  # Usage Minimum (1)
    0x29, 0x05,  # Usage Maximum (5)
    0x75, 0x01,  # Report Size (1)
    0x95, 0x05,  # Report Count (5)
    0x91, 0x02,  # Output (Data, Variable, Absolute): LED report
    0x75, 0x03,  # Report Size (3)
    0x95, 0x01,  # Report Count (1)
    0x91, 0x01,  # Output (Constant): LED report padding
    0x05, 0x07,  # Usage Page (Key Codes)
    0x19, 0x00,  # Usage Minimum (0)
    0x29, 0x65,  # Usage Maximum (101)
    0x15, 0x00,  # Logical Minimum (0)
    0x25, 0x65,  # Logical Maximum(101)
    0x75, 0x08,  # Report Size (8)
    0x95, 0x06,  # Report Count (6)
    0x81, 0x00,  # Input (Data, Array): Keys
    0xC0  # End Collection
])


class KeyboardWatcher:
    """
        KeyboardWatcher
        保存按键状态 转化为 hid keyboard事件
    """
    modifier_map = {
        UnifiedKey.L_CTRL: 0b1,
        UnifiedKey.L_SHIFT: 0b10,
        UnifiedKey.L_ALT: 0b100,
        UnifiedKey.L_WIN: 0b1000,
        UnifiedKey.R_CTRL: 0b10000,
        UnifiedKey.R_SHIFT: 0b100000,
        UnifiedKey.R_ALT: 0b1000000,
        UnifiedKey.R_WIN: 0b10000000,
    }

    def __init__(self, uhid_keyboard_send_method):
        self.pressed = list()
        self.modifiers = 0
        self.uhid_keyboard_send_method = uhid_keyboard_send_method

    def key_pressed(self, unified_key: UnifiedKey):
        """
            获取按键并存储状态
        :param unified_key:
        :return:
        """
        if unified_key in self.modifier_map:
            b = self.modifier_map[unified_key]
            if self.modifiers & b == 0:
                self.modifiers |= b
            else:
                return

        else:
            scan_code = UnifiedKeyMapper.uk2uhidkey(unified_key)

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
                self.pressed.remove(UnifiedKeyMapper.uk2uhidkey(unified_key))
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

        # 补全 6 位 按键码
        keys = [*self.pressed]
        for _ in range(6 - len(self.pressed)):
            keys.append(0)

        self.uhid_keyboard_send_method(
            modifiers=self.modifiers,
            key_scan_codes=keys
        )


class ControlSocketController(ScrcpySocket):
    """
        Scrcpy Server 2.5
        Control Socket
    """

    CLOSE_PACKET = b'Me2sYSayBye'

    class MessageType(IntEnum):
        INJECT_TOUCH_EVENT = 2
        SET_CLIPBOARD = 9
        SET_SCREEN_POWER_MODE = 10
        UHID_CREATE = 12
        UHID_INPUT = 13

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__packet_queue = queue.Queue()
        self.last_packet = None

    def close(self):
        self.is_running = False
        time.sleep(0.5)
        self.__packet_queue.put(self.CLOSE_PACKET)
        logger.warning(f"{self.__class__.__name__} Socket Closed.")

    def to_args(self) -> list:
        return ['control=true']

    def start(self):
        threading.Thread(target=self._main_thread).start()

    def _main_thread(self):
        logger.success(f"Control Socket Connected!")
        while self.is_running:
            self._conn.send(self.__packet_queue.get())
        self._conn.close()
        logger.warning(f"{self.__class__.__name__} Socket Closed.")

    def send_packet(self, packet: bytes):
        if packet != self.last_packet:
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
        :param pressure:
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
    ):
        self.send_packet(
            self.packet__touch(
                action, x, y, width, height, touch_id
            )
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

    @classmethod
    def packet__uhid_mouse_create(cls, mouse_id: int = 2):
        return struct.pack(
            '>BhH',
            *[
                cls.MessageType.UHID_CREATE.value,  # 1 type                B
                mouse_id,                               # 2 mouse_id  Short     H
                len(UHID_MOUSE_REPORT_DESC),            # 3 byte_size           h
            ]
        ) + UHID_MOUSE_REPORT_DESC

    def f_uhid_mouse_create(self, mouse_id: int = 2):
        self.send_packet(self.packet__uhid_mouse_create(mouse_id))

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
            wheel_motion: int = 0
    ):
        self.send_packet(self.packet__uhid_mouse_input(
            x_rel, y_rel, mouse_id, left_button, right_button, middle_button, wheel_motion
        ))

    @classmethod
    def packet__uhid_keyboard_create(cls, keyboard_id: int = 1):
        return struct.pack(
            '>BhH',
            *[
                cls.MessageType.UHID_CREATE.value,      # 1 type                B
                keyboard_id,                                # 2 mouse_id  Short     H
                len(UHID_KEYBOARD_REPORT_DESC),             # 3 byte_size           h
            ]
        ) + UHID_KEYBOARD_REPORT_DESC

    def f_uhid_keyboard_create(self, keyboard_id: int = 1):
        self.send_packet(self.packet__uhid_keyboard_create(keyboard_id))

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
                modifiers,                              # 4 modifiers byte0
                0,                                      # 5 reserved always0 byte1
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


class ZMQControlServer:
    """
        ZMQ Controller
        create a ZMQ pull/push socket
        send socket packet to ControlSocketController
    """

    STOP = b'Me2sYSayBye'

    def __init__(self, csc: ControlSocketController, url: str = 'tcp://127.0.0.1:55556'):
        self.csc = csc
        self.url = url
        self.is_running = False

    def _control_thread(self):
        logger.info(f"ZMQ Control Pull Running At {self.url}")

        context = zmq.Context()
        socket = context.socket(zmq.PULL)
        socket.bind(self.url)

        self.is_running = True

        while self.is_running and self.csc.is_running:
            _ = socket.recv()
            if _ == self.STOP:
                self.is_running = False
                break
            self.csc.send_packet(_)

        socket.close()
        context.term()
        logger.warning(f"ZMQ Control Pull Shutting Down")

    def start(self):
        threading.Thread(target=self._control_thread).start()

    @classmethod
    def stop(cls, url: str = 'tcp://127.0.0.1:55556'):
        cls.create_sender(url).send(cls.STOP)

    @classmethod
    def create_sender(cls, url: str = 'tcp://127.0.0.1:55556'):
        context = zmq.Context()
        sender = context.socket(zmq.PUSH)
        sender.connect(url)
        return sender
