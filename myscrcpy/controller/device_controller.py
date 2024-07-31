# -*- coding: utf-8 -*-
"""
    设备控制器
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-07-31 1.1.1 Me2sY
            1.send_frame_meta=false 降低数据包解析延迟
            2.修复 ControlSocketController 未启动线程缺陷

        2024-07-30 1.1.0 Me2sY
            1.抽离ZMQController
            2.新增AudioSocketController
            3.修改连接Scrcpy方式，支持V/A/C自选连接

        2024-07-28 1.0.1 Me2sY 新增 ZMQController

        2024-07-28 1.0.0 Me2sY 发布

        2024-07-23 0.2.0 Me2sY
            1.改用 Scrcpy-server-v2.5
            https://github.com/Genymobile/scrcpy/releases/tag/v2.5
            2.移除自动开锁功能，采用ADB keyevent方式自行输入，解决不同设备黑屏输入解锁码问题

        2024-07-11 0.1.3 Me2sY 新增锁屏判断及自动开锁功能

        2024-06-04 0.1.2 Me2sY
            1.新增 DeviceFactory
            2.抽离 ScrcpySockets
            3.将 VS， CS 包含在 Device对象中，新增关闭功能

        2024-06-03 0.1.1 Me2sY 新增 Size(Width, Height, Rotation)

        2024-06-01 0.1.0 Me2sY
            1. 去除与 Device 无关项， 简化结构
            2. 新增 ScrcpySocket 类 包装视频及控制流
            3. 设置为单例模式
"""

__author__ = 'Me2sY'
__version__ = '1.1.1'

__all__ = [
    'DeviceController', 'DeviceFactory'
]

import warnings
import threading
import time
from typing import Dict

from adbutils import adb, Network, AdbError, AdbConnection
from loguru import logger

from myscrcpy.utils import Param, Coordinate
from myscrcpy.controller.video_socket_controller import VideoSocketController
from myscrcpy.controller.audio_socket_controller import AudioSocketController
from myscrcpy.controller.control_socket_controller import ControlSocketController, ZMQController


JAR_PATH = Param.PATH_LIBS.joinpath('scrcpy-server-v2.5')

TEMP_JAR_PATH = '/data/local/tmp/scrcpy-server'

CMD = [
    f'CLASSPATH={TEMP_JAR_PATH}',
    'app_process',
    '/',
    'com.genymobile.scrcpy.Server',
    '2.5',
    'log_level=info',
    'tunnel_forward=true',
    'send_frame_meta=false',
    'stay_awake=true',
]


class DeviceController:
    """
        Scrcpy Device Controller
    """

    def __init__(
            self, device_factory: "DeviceFactory.__class__", device_serial: str = None,
            *args, **kwargs
    ):

        # 获取 Device 显示参数
        logger.info('Init Device Controller')
        self.device_factory = device_factory
        self.adb_dev = adb.device(serial=device_serial) if device_serial else adb.device_list()[0]
        self.serial = device_serial if device_serial else self.adb_dev.serial
        self.device_name = 'Android Device'

        # Coordinate
        _size = self.adb_dev.window_size()
        self.coordinate = Coordinate(width=_size.width, height=_size.height)

        # Get App Name
        self.is_getting_name = False
        self.get_app_name()

        # Scrcpy
        self.is_scrcpy_running = False
        self.stream: AdbConnection

        self.vsc: VideoSocketController
        self.asc: AudioSocketController
        self.csc: ControlSocketController

        msg = f"{self.adb_dev} Ready! Device Rotation:{self.rotation}"
        msg += f" Width:{self.coordinate.width} Height:{self.coordinate.height}"
        logger.success(msg)

    def __repr__(self):
        return f"DeviceController > {self.device_name} | {self.serial} | W:{self.coordinate.width:>4} H:{self.coordinate.height:>4} | vc: {self.is_scrcpy_running}"

    def lock(self):
        self.set_power(False)

    def is_locked(self):
        return self.adb_dev.shell('dumpsys deviceidle | grep "mScreenLocked="').strip().split('=')[1] == 'true'

    def set_power(self, status: bool = True):
        if self.adb_dev.is_screen_on() ^ status:
            self.adb_dev.keyevent('POWER')

    def set_screen(self, status: bool = True):
        if not hasattr(self, 'csc') or self.csc is None:
            warnings.warn('ControlConnect Required!')
            return False

        self.csc.f_set_screen(status)

    def back(self):
        self.adb_dev.keyevent('BACK')

    def home(self):
        self.adb_dev.keyevent('HOME')

    def close(self):
        try:
            self.vsc.close()
        except:
            pass

        try:
            self.asc.close()
        except:
            pass

        try:
            self.csc.close()
        except:
            pass

        try:
            del self.device_factory.DEVICES[self.serial]
        except KeyError:
            pass

        self.set_power(False)

    @property
    def current_app_name(self) -> str | None:
        """
            通过ADB获取当前APP name 可能会导致延迟，采用线程等待机制获取
        :return:
        """
        if self.is_getting_name:
            warnings.warn(f"App Name is Updating. Please Wait")
            while self.is_getting_name:
                time.sleep(0.1)
        return self._current_app_name

    def _get_app_name(self):
        self._current_app_name = self.adb_dev.app_current().package.split('.')[-1]
        self.is_getting_name = False

    def get_app_name(self):
        self.is_getting_name = True
        threading.Thread(target=self._get_app_name).start()

    @property
    def rotation(self) -> int:
        """
            获取当前设备方向
        :return:
        """
        return self.coordinate.rotation

    def update_rotation(self, rotation: int):
        """
            旋转 并 更新当前APP名称
        :param rotation:
        :return:
        """
        if rotation != self.coordinate.rotation:
            self.coordinate = Coordinate(self.coordinate.height, self.coordinate.width)
            self.get_app_name()

    def connect(
            self,
            vsc: VideoSocketController | None = None,
            asc: AudioSocketController | None = None,
            csc: ControlSocketController | None = None,
    ):

        is_init_video_socket = vsc is not None
        is_init_audio_socket = asc is not None
        is_init_control_socket = csc is not None

        socket_num = sum(
            [
                1 if is_init_video_socket else 0,
                1 if is_init_audio_socket else 0,
                1 if is_init_control_socket else 0,
            ]
        )

        if socket_num == 0:
            raise RuntimeError('Create at least one socket!')

        cmd = CMD

        if is_init_video_socket:
            cmd += [
                'video=true',
                f"max_size={vsc.max_size}",
                f"max_fps={vsc.fps}",
                f"video_codec={vsc.video_codec}",
                f"video_source={vsc.video_source}",
            ]
        else:
            cmd += [
                'video=false'
            ]

        if is_init_audio_socket:
            cmd += [
                'audio=true',
                f"audio_codec={asc.audio_codec}",
                f"audio_source={asc.audio_source}"
            ]
        else:
            cmd += [
                'audio=false'
            ]

        if is_init_control_socket:
            cmd += [
                'control=true'
            ]
        else:
            cmd += [
                'control=false'
            ]

        # Push Jar And Start Scrcpy Server
        self.adb_dev.sync.push(JAR_PATH, TEMP_JAR_PATH)

        logger.debug(f"Adb Run => {cmd}")

        self.stream = self.adb_dev.shell(cmd, stream=True)
        stream_msg = ''
        while True:
            c = self.stream.read_string(1)
            if c == '\n':
                break
            else:
                stream_msg += c
        logger.success(f"Scrcpy Server Started! Stream Msg => {stream_msg}")

        _conn_list = []
        _conn = None
        for _ in range(5000):
            try:
                _conn = self.adb_dev.create_connection(Network.LOCAL_ABSTRACT, "scrcpy")
                _conn_list.append(_conn)
                break
            except AdbError:
                time.sleep(0.001)

        if _conn is None:
            raise RuntimeError('Connect Scrcpy Server Error!')
        else:
            if _conn.recv(1) != b'\x00':
                logger.error('Dummy Data Error!')
                raise RuntimeError('Dummy Data Error!')

        if socket_num > 1:
            for _ in range(socket_num - 1):
                _conn_list.append(self.adb_dev.create_connection(Network.LOCAL_ABSTRACT, "scrcpy"))

        device_name = _conn.recv(64).decode('utf-8').rstrip('\x00')
        logger.debug(f"Device Name    => {device_name}")
        self.device_name = device_name

        for conn in _conn_list:
            if is_init_video_socket:
                logger.info('Init Video Socket')
                self.vsc: VideoSocketController = vsc.setup_socket_connection(conn)
                self.vsc.start()
                is_init_video_socket = False
                continue

            if is_init_audio_socket:
                logger.info('Init Audio Socket')
                self.asc: AudioSocketController = asc.setup_socket_connection(conn)
                is_init_audio_socket = False
                self.asc.start()
                continue

            if is_init_control_socket:
                logger.info('Init Control Socket')
                self.csc: ControlSocketController = csc.setup_socket_connection(conn)
                self.csc.start()
                break

        self.is_scrcpy_running = True

    def create_zmq_server(self, zmq_url: str = 'tcp://127.0.0.1:55556'):
        if self.is_scrcpy_running and self.csc.is_running:
            self.zmq_url = zmq_url
            self.zmq = ZMQController(self.csc, zmq_url)
        else:
            logger.warning('Scrcpy is not running')


class DeviceFactory:

    DEVICES = {}

    @classmethod
    def device(cls, device_serial: str = None, *args, **kwargs) -> DeviceController:
        """
            获取 Device
        :param device_serial:
        :param args:
        :param kwargs:
        :return:
        """
        if device_serial in cls.DEVICES:
            return cls.DEVICES[device_serial]
        else:
            dev = DeviceController(cls, device_serial, *args, **kwargs)
            cls.DEVICES[device_serial] = dev
            return dev

    @classmethod
    def init_all_devices(cls, *args, **kwargs) -> Dict[str, DeviceController]:
        """
            初始化所有 ADB 设备
        :param args:
        :param kwargs:
        :return:
        """
        for dev in adb.device_list():
            try:
                cls.device(dev.serial, *args, **kwargs)
            except Exception as e:
                logger.error(f"Init {dev.serial} Error => {e}")
        return cls.DEVICES

    @classmethod
    def devices(cls) -> Dict[str, DeviceController]:
        """
            获取所有设备
        :return:
        """
        return cls.DEVICES

    @classmethod
    def device_num(cls) -> int:
        """
            设备数量
        :return:
        """
        return len(cls.DEVICES)

    @classmethod
    def close_device(cls, device_serial: str):
        """
            关闭设备连接
        :param device_serial:
        :return:
        """
        try:
            cls.DEVICES[device_serial].close()
        except KeyError:
            raise RuntimeError(f"Device > {device_serial} not Created!")

    @classmethod
    def close_all_devices(cls):
        """
            关闭全部设备
        :return:
        """
        for dev in [*cls.DEVICES.values()]:
            dev.close()
        time.sleep(1)
        logger.success('All Devices Closed!')


if __name__ == '__main__':
    # Create DeviceController
    # dc = DeviceFactory.device()
    dc = DeviceController(DeviceFactory())

    # Connect to Scrcpy
    # Create a SocketController and pass to connect method
    # None means NOT connect
    dc.connect(
        vsc=VideoSocketController(1366),
        asc=AudioSocketController(),
        csc=ControlSocketController()
    )

