# -*- coding: utf-8 -*-
"""
    设备控制器
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-07-28 1.0.1 Me2sY
            新增 ZMQController

        2024-07-28 1.0.0 Me2sY
            发布

        2024-07-23 0.2.0 Me2sY
            1.改用 Scrcpy-server-v2.5
            https://github.com/Genymobile/scrcpy/releases/tag/v2.5
            2.移除自动开锁功能，采用ADB keyevent方式自行输入，解决不同设备黑屏输入解锁码问题

        2024-07-11 0.1.3 Me2sY
            新增锁屏判断及自动开锁功能

        2024-06-04 0.1.2 Me2sY
            1.新增 DeviceFactory
            2.抽离 ScrcpySockets
            3.将 VS， CS 包含在 Device对象中，新增关闭功能

        2024-06-03 0.1.1 Me2sY
            新增 Size(Width, Height, Rotation)

        2024-06-01 0.1.0 Me2sY
            1. 去除与 Device 无关项， 简化结构
            2. 新增 ScrcpySocket 类 包装视频及控制流
            3. 设置为单例模式

"""

__author__ = 'Me2sY'
__version__ = '1.0.1'

__all__ = [
    'DeviceController', 'DeviceFactory', 'ZMQController'
]

import warnings
import threading
import time
from queue import Queue
from typing import Tuple, Dict

import zmq
from adbutils import adb, Network, AdbError, AdbConnection
from loguru import logger

from myscrcpy.utils import Param, Coordinate
from myscrcpy.socket_adapter import VideoSocket, ControlSocket


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
    'audio=false',
    'control=true',
    'send_frame_meta=false',
    'stay_awake=true',
    'video=true'
]


class ZMQController:

    STOP = b'Me2sYSayBye'

    def __init__(self, device: 'DeviceController',  url: str = 'tcp://127.0.0.1:55556'):
        self.device = device
        self.url = url
        self.is_running = True
        self.socket = None

        threading.Thread(target=self._control_thread).start()

    def _control_thread(self):
        logger.info(f"ZMQ Control Pull Running At {self.url}")
        context = zmq.Context()
        self.socket = context.socket(zmq.PULL)
        self.socket.bind(self.url)

        while self.is_running and self.device.cs.is_running:
            _ = self.socket.recv()
            if _ == self.STOP:
                self.is_running = False
                break
            self.device.cs.send_packet(_)

        logger.warning(f"ZMQ Control Pull Shutting Down")

    @classmethod
    def stop(cls, url: str = 'tcp://127.0.0.1:55556'):
        cls.create_sender(url).send(cls.STOP)

    @classmethod
    def create_sender(cls, url: str = 'tcp://127.0.0.1:55556'):
        context = zmq.Context()
        sender = context.socket(zmq.PUSH)
        sender.connect(url)
        return sender


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
        self.vs: VideoSocket
        self.cs: ControlSocket

        self.zmq_url = None
        self.zmq: ZMQController = None

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
        if not hasattr(self, 'cs') or self.cs is None:
            warnings.warn('ControlConnect Required!')
            return False

        self.cs.set_screen_on(status)

    def back(self):
        self.adb_dev.keyevent('BACK')

    def home(self):
        self.adb_dev.keyevent('HOME')

    def close(self):
        try:
            self.vs.close()
        except:
            pass

        try:
            self.cs.close()
        except:
            pass

        try:
            del self.device_factory.DEVICES[self.serial]
        except KeyError:
            pass

        try:
            if self.zmq is not None:
                self.zmq.stop(self.zmq_url)
        except:
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

    def connect_to_scrcpy(
            self,
            max_size: int = None,
            scale: float = 0.5,
            fps: int = 90,
            screen_on: bool = False,
            *args, **kwargs
    ) -> Tuple[VideoSocket, ControlSocket]:
        """
            Get Video and Controller socket provided by Scrcpy
        :return:
        """

        logger.info('Start Scrcpy Server')

        logger.info('Clean Sockets')
        try:
            self.vs.close()
        except:
            pass

        try:
            self.cs.close()
        except:
            pass

        if scale <= 0 or scale > 1:
            raise ValueError('Scale must be between 0 and 1')

        if max_size is None and scale is None:
            max_size = self.coordinate.max_size
            # raise ValueError('Max size or Scale must be provided')

        elif max_size is None:
            max_size = int(self.coordinate.max_size * scale)

        else:
            if max_size > self.coordinate.max_size:
                max_size = self.coordinate.max_size
                # raise RuntimeError(f"Max size is {self.coordinate.max_size}")

        self.adb_dev.sync.push(JAR_PATH, TEMP_JAR_PATH)
        cmd = CMD + [
                f'max_size={int(max_size)}',
                f'max_fps={int(fps)}'
        ]
        logger.debug(f"Adb Run => {cmd}")

        self.stream = self.adb_dev.shell(cmd, stream=True)
        stream_msg = self.stream.read(1)
        logger.success(f"Scrcpy Server Started! Stream Msg => {stream_msg}")

        # Get socket connections
        video_conn = None
        for _ in range(100):
            try:
                video_conn = self.adb_dev.create_connection(Network.LOCAL_ABSTRACT, "scrcpy")  # 有可能一次创建不成功
                logger.success(f'Video Socket   => {video_conn}')
                break
            except AdbError:
                time.sleep(0.1)

        if video_conn.recv(1) != b'\x00':
            logger.error('Dummy Data Error!')
            raise RuntimeError('Dummy Data Error!')

        control_conn = None
        for _ in range(100):
            try:
                control_conn = self.adb_dev.create_connection(Network.LOCAL_ABSTRACT, "scrcpy")  # 有可能一次创建不成功
                logger.success(f'Control Socket => {control_conn}')
                break
            except AdbError as e:
                logger.error(e)
                time.sleep(0.1)

        time.sleep(0.5)

        device_name = video_conn.recv(64).decode('utf-8').rstrip('\x00')
        logger.debug(f"Device Name    => {device_name}")
        self.device_name = device_name

        res = video_conn.recv(4)
        logger.debug(f"Video Type     => {res}")

        self.vs = VideoSocket(video_conn, self.serial)
        self.cs = ControlSocket(control_conn, screen_on=screen_on)

        while self.vs.last_frame is None:
            time.sleep(0.01)

        self.is_scrcpy_running = True

        return self.vs, self.cs

    def create_zmq_server(self, zmq_url: str = 'tcp://127.0.0.1:55556'):
        if self.is_scrcpy_running and self.cs.is_running:
            self.zmq_url = zmq_url
            self.zmq = ZMQController(self, zmq_url)
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
