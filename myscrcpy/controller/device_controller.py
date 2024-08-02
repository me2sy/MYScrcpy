# -*- coding: utf-8 -*-
"""
    设备控制器
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-08-02 1.1.3 Me2sY
            1.优化 connect 方法
            2.解决 VideoSource = camera时 与 ControlSocket冲突问题
            3.新增 获取设备信息方法 获取厂商及Android Version，判断是否支持某些功能（Audio、Camera）
            4.新增 Server回传信息显示功能，控制台显示从Stream中获得的Server回传信息

        2024-08-01 1.1.2 Me2sY
            1.优化connect方法，采用args传参方式
            2.去除 create zmq方法，形成ZMQController

        2024-07-31 1.1.1 Me2sY
            1.send_frame_meta=false 降低数据包解析延迟
            2.修复 ControlSocketController 未启动线程缺陷

        2024-07-30 1.1.0 Me2sY
            1.抽离ZMQController
            2.新增 AudioSocketController
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
__version__ = '1.1.3'

__all__ = [
    'DeviceController', 'DeviceFactory'
]

import threading
import time
from typing import Dict
import re

from adbutils import adb, Network, AdbError, AdbConnection
from loguru import logger

from myscrcpy.utils import Param, Coordinate
from myscrcpy.controller.video_socket_controller import VideoSocketController
from myscrcpy.controller.audio_socket_controller import AudioSocketController, AudioSocketServer
from myscrcpy.controller.control_socket_controller import ControlSocketController


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
        self.device_prod = ''
        self.device_sys_version = 14

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
        self.asc: AudioSocketController | AudioSocketServer
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
            logger.warning('Set Screen Method Need ControlSocket Connect!')
            return False

        self.csc.f_set_screen(status)

    def back(self):
        self.adb_dev.keyevent('BACK')

    def home(self):
        self.adb_dev.keyevent('HOME')

    def close(self):

        self.is_scrcpy_running = False

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
            logger.warning(f"App Name is Updating. Please Wait")
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

    def connect(self, *args):
        """
            Create VSC/ASC/ASS/CSC
        """

        self.vsc, self.asc, self.csc = None, None, None

        if len(args) == 0:
            raise RuntimeError('Create at least one Controller!')
        elif len(args) > 3:
            raise RuntimeError('ONE Socket ONE Controller!')

        socket_num = 0

        for arg in args:
            if isinstance(arg, VideoSocketController):
                if self.vsc:
                    raise ValueError('VideoSocket Already Occupied')
                self.vsc = arg
                socket_num += 1
                continue

            if isinstance(arg, AudioSocketController) or isinstance(arg, AudioSocketServer):
                if self.asc:
                    raise ValueError('AudioSocket Already Occupied')
                self.asc = arg
                socket_num += 1
                continue

            if isinstance(arg, ControlSocketController):
                if self.csc:
                    raise ValueError('ControlSocket Already Occupied')
                self.csc = arg
                socket_num += 1
                continue

        if self.csc and self.vsc and self.vsc.video_source == self.vsc.SOURCE_CAMERA:
            logger.warning(f"VideoSocket Set To Camera, Auto Disabled ControlSocket!")
            self.csc = None
            socket_num -= 1

        if socket_num <= 0:
            raise RuntimeError('Create at least one socket!')

        logger.info(f"Prepare to Create {socket_num} ({' VS' if self.vsc else ''}{' AS' if self.asc else ''}{' CS' if self.csc else ''} ) sockets.")

        cmd = CMD

        if self.vsc:
            cmd += self.vsc.to_args()
        else:
            cmd += ['video=false']

        if self.asc:
            cmd += self.asc.to_args()
        else:
            cmd += ['audio=false']

        if self.csc:
            cmd += self.csc.to_args()
        else:
            cmd += ['control=false']

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

        try:
            dev_info = stream_msg.split('INFO: ')[1]

            self.device_prod = re.findall('\[(.*?)\]', dev_info)[0]
            ver = re.findall('\((.*?)\)', dev_info)[0].split(' ')[1]
            if '.' in ver:
                self.device_sys_version = int(ver.split('.')[0])
            else:
                self.device_sys_version = int(ver)

        except:
            logger.warning(f"Analysis Device Info Failed => {stream_msg}")

        if self.device_sys_version < 12 and self.vsc and self.vsc.camera:
            raise RuntimeError('Android Version is less than 12. VideoSocket Camera Not Support!')

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
            raise RuntimeError('Failed to Create Socket')
        else:
            if _conn.recv(1) != b'\x00':
                raise RuntimeError('Dummy Data Error!')

        if socket_num > 1:
            for _ in range(socket_num - 1):
                _conn_list.append(self.adb_dev.create_connection(Network.LOCAL_ABSTRACT, "scrcpy"))

        device_name = _conn.recv(64).decode('utf-8').rstrip('\x00')
        self.device_name = device_name

        for conn in _conn_list:

            if self.vsc and not self.vsc.is_running:
                logger.info('Init Video Socket')
                self.vsc.setup_socket_connection(conn)
                continue

            if self.asc and not self.asc.is_running:
                if self.device_sys_version < 12:
                    logger.warning('Android Version is less than 12. AudioSocket Not Support! Auto Disabled.')
                    self.asc = None
                    continue

                logger.info('Init Audio Socket')
                self.asc.setup_socket_connection(conn)
                continue

            if self.csc and not self.csc.is_running:
                logger.info('Init Control Socket')
                self.csc.setup_socket_connection(conn)
                continue

        for _ in [self.asc, self.vsc, self.csc]:
            if _:
                _.start()

        self.is_scrcpy_running = True
        threading.Thread(target=self._thread_load_stream).start()

        dev_info = f"Device Info: {self.serial} | {self.device_prod} | {self.device_name} | "
        dev_info += f"Android Version: {self.device_sys_version}"
        dev_info += ' | Connected to Scrcpy Server\n'
        dev_info += '-' * 200
        logger.success(dev_info)

    def _thread_load_stream(self):
        msg = ''
        while self.is_scrcpy_running:
            w = self.stream.read_string(1)
            if w == '\n':
                logger.info(f"Server => {msg}")
                break
            else:
                msg += w


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
    from myscrcpy.controller.audio_socket_controller import AudioSocketServer

    # Create DeviceController
    # dc = DeviceFactory.device()
    dc = DeviceController(DeviceFactory())

    # Connect to Scrcpy
    # Instantiate SocketController and pass to connect method
    dc.connect(
        VideoSocketController(max_size=1366),
        AudioSocketController(),
        # AudioSocketServer(True),
        ControlSocketController()
    )

    # ZMQ Audio Server
    # from myscrcpy.controller.audio_socket_controller import ZMQAudioServer, ZMQAudioSubscriber
    # zas = ZMQAudioServer(dc.asc)
    # zas.start()

    # ZMQ Audio Subscriber
    # sub = ZMQAudioSubscriber()
    # sub.start()
