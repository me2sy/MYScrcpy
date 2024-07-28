# -*- coding: utf-8 -*-
"""
    Scrcpy 连接 适配器
    ~~~~~~~~~~~~~~~~~~


    Log:
        2024-07-28 1.0.0 Me2sY
            发布

        2024-07-27 0.3.0 Me2sY
            1.去除ZMQ
            2.使用 shared_memory 共享 frame
            3.创建VideoStream 解析共享frame

        2024-07-25 0.2.2 Me2sY
            1.新增 UHID Keyboard 输入
            2.新增 KeyboardWatcher

        2024-07-24 0.2.1 Me2sY
            新增 UHID Mouse 输入

        2024-07-23 0.2.0 Me2sY
            1.改用 scrcpy-server-2.5
            2.新增 paste 功能，支持中文输入

        2024-06-17 0.1.3 Me2sY
            新增 Screen 控制

        2024-06-10 0.1.2 Me2sY
            移除 Point
            改为 Coordinate
            迁移touch_cmd_bytes 至 ControlSocket

        2024-06-04 0.1.1 Me2sY
            1. 抽离形成新类 VideoSocket ControlSocket
            2. Point 用于 坐标转换
            3. 新增 VideoSocket ZMQ Publish
                    ControlSocket  ZMQ PULL PUSH
                    用于后期插件

        2024-06-01 0.1.0 Me2sY
            创建

"""

__author__ = 'Me2sY'
__version__ = '1.0.0'

__all__ = [
    'VideoSocket', 'ControlSocket', 'KeyboardWatcher', 'VideoStream'
]

import datetime
import socket
import struct
import time
from abc import abstractmethod, ABCMeta
import threading
from enum import IntEnum
from queue import Queue
from multiprocessing import shared_memory
from copy import copy

from loguru import logger

import numpy as np
from av.codec import CodecContext

from myscrcpy.utils import Coordinate, UnifiedKey, UnifiedKeyMapper, Param, Action


class ScrcpySocket(metaclass=ABCMeta):
    """
        Scrcpy Socket 基类
    """

    def __init__(self, conn: socket.socket):
        self._conn = conn
        self.is_running = True

    def __repr__(self):
        return f"{self.__class__.__name__} Socket: {self._conn}"

    @abstractmethod
    def close(self):
        """
            Stop Running and Close Socket
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def _main_thread(self):
        raise NotImplementedError

    def _start_thread(self):
        threading.Thread(target=self._main_thread).start()
        logger.success(f"{self.__class__.__name__} | Thread Started")


class VideoStream:
    """
        Shared Memory Frame
    """

    def __init__(self, shm: shared_memory.SharedMemory):
        self._shm = shm

        c = self.coordinate
        self._frame_v = np.ndarray(
            (c.max_size, c.min_size, 3), dtype=np.uint8, buffer=shm.buf[8:]
        )
        self._frame_h = np.ndarray(
            (c.min_size, c.max_size, 3), dtype=np.uint8, buffer=shm.buf[8:]
        )
        self.frame_id = -1

    @property
    def coordinate(self):
        self.frame_id, h, w = struct.unpack('>IHH', self._shm.buf[:8])
        return Coordinate(w, h)

    def get_frame(self) -> (Coordinate, np.ndarray):
        c = self.coordinate
        if self.frame_id == 0:
            raise RuntimeError(f"VideoStream Closed!")
        if c.rotation == Param.ROTATION_VERTICAL:
            return c, self._frame_v
        else:
            return c, self._frame_h

    @classmethod
    def create(cls, shm_name: str) -> 'VideoStream':
        return cls(shared_memory.SharedMemory(shm_name))


class VideoSocket(ScrcpySocket):
    """
        Scrcpy Video Socket
    """

    def __init__(
            self,
            conn: socket.socket,
            device_serial: str,
            buffer_size: int = 131072,
            video_codec: str = 'h264'
    ):

        super().__init__(conn)
        self.device_serial: str = device_serial
        self.buffer_size: int = buffer_size
        self.video_codec: str = video_codec

        self.code_context = CodecContext.create(self.video_codec, 'r')

        self.last_frame = None
        self.frame_n = 0
        self.shm = None

        self.is_running = True

        self._start_thread()

    def close(self):
        self.is_running = False
        logger.warning(f"{self.__class__.__name__} Socket Closed.")

    @property
    def coordinate(self) -> Coordinate:
        shape = self.last_frame.shape
        return Coordinate(width=shape[1], height=shape[0])

    def _main_thread(self):
        while self.is_running:
            try:
                packets = self.code_context.parse(self._conn.recv(self.buffer_size))
                for packet in packets:
                    for _frame in self.code_context.decode(packet):
                        self.last_frame = _frame.to_ndarray(format='rgb24')
                        self.frame_n += 1
            except Exception:
                continue
        self._conn.close()

    def create_shared_frame(self, size: int):
        f_name = f"{self.device_serial}_video_frame_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            self.shm = shared_memory.SharedMemory(name=f_name, create=True, size=size)
        except FileExistsError:
            logger.warning(f"{f_name} Shared Frame Already Exists")
            self.shm = shared_memory.SharedMemory(name=f_name)

        logger.success(f"share_memory created! name: > {self.shm.name} <")

    def _share_thread(self):
        logger.info("Start Shared Thread")
        while self.frame_n == 0:
            time.sleep(0.001)

        self.create_shared_frame(self.last_frame.nbytes + 8)

        n = 0
        while self.is_running:
            if n != self.frame_n:
                self.shm.buf[:] = struct.pack(
                    '>IHH',
                    self.frame_n, self.last_frame.shape[0], self.last_frame.shape[1]
                ) + self.last_frame.tobytes()
                n = copy(self.frame_n)
            else:
                time.sleep(0.00001)
        self.shm.buf[:4] = struct.pack('>I', 0)
        self.shm.close()
        self.shm.unlink()
        logger.warning(f"Shared Thread Closed!")

    def get_frame(self) -> np.ndarray:
        return self.last_frame

    def _start_thread(self):
        super()._start_thread()
        threading.Thread(target=self._share_thread).start()


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


class ControlSocket(ScrcpySocket):
    CLOSE_PACKET = b'Me2sYSayBye'

    class MessageType(IntEnum):
        INJECT_TOUCH_EVENT = 2
        SET_CLIPBOARD = 9
        SET_SCREEN_POWER_MODE = 10
        UHID_CREATE = 12
        UHID_INPUT = 13

    def __init__(
            self,
            conn: socket.socket,
            screen_on: bool = False,
    ):
        super().__init__(conn)

        self.__packet_queue = Queue()

        self.is_running = True
        self.last_packet = None

        self.set_screen_on(screen_on)

        self._start_thread()

    def close(self):
        self.is_running = False
        time.sleep(0.5)
        self.__packet_queue.put(self.CLOSE_PACKET)

    def _main_thread(self):
        while self.is_running:
            self._conn.send(self.__packet_queue.get())
        self._conn.close()
        logger.warning(f"{self.__class__.__name__} Socket Closed.")

    def send_packet(self, packet: bytes):
        if packet != self.last_packet:
            self.__packet_queue.put(packet)
            self.last_packet = packet

    def set_screen_on(self, status: bool):
        """
            控制屏幕开关
        :param status:
        :return:
        """
        self.send_packet(self.screen_ctrl_packet(status))

    @classmethod
    def touch_packet(
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
                cls.MessageType.INJECT_TOUCH_EVENT.value,  # 1 B  Event Type
                action,  # 2 B  Action
                touch_id,  # 3 Q pointerId
                int(x), int(y),  # 4 ii position x, y
                width, height,  # 5 HH width height
                0 if action == Action.RELEASE.value else 0xffff,  # 6 H pressure
                1, 1  # 7 II actionButton/buttons
            ]
        )

    @classmethod
    def screen_ctrl_packet(cls, status: bool) -> bytes:
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

    @classmethod
    def text_paste_packet(cls, text: str, paste: bool = True) -> bytes:
        text_bytes = text.encode('utf-8')
        return struct.pack(
            '>BQ?I',
            cls.MessageType.SET_CLIPBOARD.value,
            0,
            paste,
            len(text_bytes)
        ) + text_bytes

    # Scrcpy UHID Mouse & Keyboard

    @classmethod
    def uhid_mouse_create_packet(cls, mouse_id: int = 2):
        return struct.pack(
            '>BhH',
            *[
                cls.MessageType.UHID_CREATE.value,  # 1 type                B
                mouse_id,  # 2 mouse_id  Short     H
                len(UHID_MOUSE_REPORT_DESC),  # 3 byte_size           h
            ]
        ) + UHID_MOUSE_REPORT_DESC

    @classmethod
    def uhid_mouse_input_packet(
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

    @classmethod
    def uhid_keyboard_create_packet(cls, keyboard_id: int = 1):
        return struct.pack(
            '>BhH',
            *[
                cls.MessageType.UHID_CREATE.value,  # 1 type                B
                keyboard_id,  # 2 mouse_id  Short     H
                len(UHID_KEYBOARD_REPORT_DESC),  # 3 byte_size           h
            ]
        ) + UHID_KEYBOARD_REPORT_DESC

    @classmethod
    def uhid_keyboard_input_packet(
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
                cls.MessageType.UHID_INPUT.value,  # 1 Type
                keyboard_id,  # 2 id
                8,  # 3 size
                modifiers,  # 4 modifiers byte0
                0,  # 5 reserved always0 byte1
                *key_scan_codes  # 6 - 11 key scancode  byte2-7
            ]
        )
