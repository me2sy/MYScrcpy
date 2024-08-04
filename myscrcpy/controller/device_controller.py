# -*- coding: utf-8 -*-
"""
    设备控制器
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-08-04 1.2.0 Me2sY
            1.升级 Scrcpy Server 2.6.1
            2.重构 DeviceFactory 支持TCPIP无线连接，支持历史连接记录，历史重连等
            3.新增 DeviceInfo，并通过 ADB getprop 获取设备信息，在建立Scrcpy连接前，阻止低版本设备连接造成的异常

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
__version__ = '1.2.0'

__all__ = [
    'DeviceInfo',
    'DeviceController', 'DeviceFactory'
]

import datetime
import threading
import time
from typing import NamedTuple, Dict, Tuple

from loguru import logger

from adbutils import adb, AdbError, AdbDevice, AdbConnection, Network

from myscrcpy.utils import Coordinate, Param, CfgHandler
from myscrcpy.controller import VideoSocketController, AudioSocketController, AudioSocketServer, ControlSocketController


class DeviceInfo(NamedTuple):
    """
        Device Info
    """

    serial_no: str
    brand: str = ''
    model: str = ''
    sdk: int = 34                       # Use High When not get
    release: int = 14                   # Use High When not get

    @property
    def is_scrcpy_supported(self) -> bool:
        return self.sdk > 21 and self.release > 5

    @property
    def is_audio_supported(self) -> bool:
        return self.release >= 12

    @property
    def is_camera_supported(self) -> bool:
        return self.release >= 12

    @property
    def is_uhid_supported(self) -> bool:
        return self.release >= 11


class DeviceController:
    """
        Scrcpy Device Controller
    """

    def __init__(
            self,
            adb_device: AdbDevice,
            auto_drop_disconnected: bool = False,
            *args, **kwargs
    ):
        """
            Create Device Controller But NOT CONNECT TO Scrcpy NOW
        """
        self.info: DeviceInfo = self.analysis_device_info(adb_device)
        self.serial = self.info.serial_no

        self.usb_dev = adb_device if adb_device.serial == self.info.serial_no else None
        self.net_dev = None if self.usb_dev else adb_device

        # Coordinate
        _size = adb_device.window_size()
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

        self.auto_drop_disconnected = auto_drop_disconnected

        msg = f"{adb_device} Found! Device Rotation:{self.rotation}"
        msg += f" Width:{self.coordinate.width} Height:{self.coordinate.height}"
        logger.success(msg)

    @property
    def adb_dev(self) -> AdbDevice:
        try:
            if self.usb_dev and self.usb_dev.window_size():
                return self.usb_dev

        except AdbError as e:
            logger.warning(f"{self.info} USB Connection Maybe LOST! Error => {e}")
            if self.auto_drop_disconnected:
                self.usb_dev = None
        try:
            if self.net_dev and self.net_dev.window_size():
                return self.net_dev

        except AdbError as e:
            logger.warning(f"{self.info} Net Connection Maybe LOST! Error => {e}")

        raise RuntimeError('Device not connected')

    @staticmethod
    def reconnected():
        """
            重连至ADB Device
        """
        DeviceFactory.load_devices(load_history=False, save_history=False)

    def set_tcpip(self, port: int, auto_reconnect: bool = True, timeout: int = 5):
        """
            设置TCPIP模式及端口号
        """
        wlan_ip = self.wlan_ip
        self.adb_dev.tcpip(port)
        if auto_reconnect:
            if wlan_ip is None:
                logger.error(f"WLAN IP is None, Maybe Device {self.info} Not Connect to WIFI.")

            else:
                logger.info(f"Auto-Reconnect: {adb.connect(f'{wlan_ip}:{port}', timeout=timeout)}")
        DeviceFactory.load_devices()

    @property
    def wlan_ip(self) -> str | None:
        try:
            return self.adb_dev.wlan_ip()
        except AdbError:
            return None

    @property
    def tcpip_port(self) -> int | None:
        p = self.adb_dev.getprop('service.adb.tcp.port')
        if p is None or p == '':
            return None
        else:
            return int(p)

    @staticmethod
    def analysis_device_info(dev: AdbDevice) -> DeviceInfo:
        """
            Get Device Info By getprop
        """

        try:
            serial_no = dev.getprop('ro.serialno')
        except KeyError:
            raise ValueError(f'Serial No Found In prop!')

        release = dev.getprop('ro.build.version.release')
        if release is None or release == '':
            release = 14
        elif '.' in release:
            release = int(release.split('.')[0])
        else:
            release = int(release)

        return DeviceInfo(
            serial_no=serial_no,
            brand=dev.getprop('ro.product.brand'),
            model=dev.getprop('ro.product.model'),
            sdk=int(dev.getprop('ro.build.version.sdk')),
            release=release,
        )

    def __repr__(self):
        return f"DeviceController > {self.info} | W:{self.coordinate.width:>4} H:{self.coordinate.height:>4} | vc: {self.is_scrcpy_running}"

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
            if self.vsc:
                self.vsc.close()
        except:
            ...

        try:
            if self.asc:
                self.asc.close()
        except:
            ...

        try:
            if self.csc:
                self.csc.close()
        except:
            ...

        try:
            DeviceFactory.DEVICE_CONTROLLERS.pop(self.serial)
        except KeyError:
            pass

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

    def connect(self, *args) -> Tuple[
        VideoSocketController | None,
        AudioSocketController | AudioSocketServer | None,
        ControlSocketController | None
    ]:
        """
            Create VSC/ASC/ASS/CSC
        """

        if not self.info.is_scrcpy_supported:
            logger.error(f"Sorry. This Device {self.info} is Too OLD To Use Scrcpy."
                         f'At Lease API 21 (Android 5.0) Required!')
            return None, None, None

        self.vsc, self.asc, self.csc = None, None, None

        if len(args) == 0:
            raise RuntimeError('Create at least one Controller!')
        elif len(args) > 3:
            raise RuntimeError('ONE Socket ONE Controller!')

        socket_num = 0

        for arg in args:
            if isinstance(arg, VideoSocketController):
                if not self.info.is_camera_supported and arg.camera:
                    logger.warning(f"Sorry. This Device {self.info} is Too OLD To Use Camera.")
                    logger.warning('At Lease Android 12 Required! CameraSocket Auto Disabled.')
                    continue

                if self.vsc:
                    raise ValueError('ONE VideoSocket ONLY!')

                self.vsc = arg
                socket_num += 1
                continue

            if isinstance(arg, AudioSocketController) or isinstance(arg, AudioSocketServer):
                if not self.info.is_audio_supported:
                    logger.warning(f"Sorry. This Device {self.info} is Too OLD To Use AudioSocket.")
                    logger.warning('At Lease Android 12 Required! AudioSocket Auto Disabled.')
                    continue

                if self.asc:
                    raise ValueError('ONE AudioSocket ONLY!')

                self.asc = arg
                socket_num += 1
                continue

            if isinstance(arg, ControlSocketController):
                if self.csc:
                    raise ValueError('ONE ControlSocket ONLY!')

                self.csc = arg
                socket_num += 1
                continue

        if self.csc and self.vsc and self.vsc.video_source == self.vsc.SOURCE_CAMERA:
            logger.warning(f"VideoSocket Set To Camera, Auto Disabled ControlSocket!")
            self.csc = None
            socket_num -= 1

        if socket_num <= 0:
            raise RuntimeError('Create at least one socket!')

        logger.info(f"Prepare to Create {socket_num} "
                    f"({' VS' if self.vsc else ''}{' AS' if self.asc else ''}{' CS' if self.csc else ''} ) sockets.")

        cmd = Param.SCRCPY_SERVER_START_CMD

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
        self.adb_dev.sync.push(Param.PATH_SCRCPY_SERVER_JAR, Param.PATH_SCRCPY_TEMP)

        logger.debug(f"Adb Run => {cmd}")

        self.stream = self.adb_dev.shell(cmd, stream=True)

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

        for conn in _conn_list:

            if self.vsc and not self.vsc.is_running:
                logger.info('Init Video Socket')
                self.vsc.setup_socket_connection(conn)
                continue

            if self.asc and not self.asc.is_running:
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

        dev_info = f"Device {self.info}"
        dev_info += ' | Connected to Scrcpy Server！\n'
        dev_info += '-' * 200
        logger.success(dev_info)
        return self.vsc, self.asc, self.csc

    def _thread_load_stream(self):
        msg = ''
        while self.is_scrcpy_running:
            w = self.stream.read_string(1)
            if w == '\n':
                logger.info(f"Scrcpy Server Return => {msg}")
                break
            else:
                msg += w


class DeviceFactory:
    """
        设备管理工厂
        通过使用 .device() 方法 获取 DeviceController 对象实例
    """

    DEVICE_CONTROLLERS = {}

    HISTORY_FILE_PATH = Param.PATH_TEMP / 'connected_history.json'

    def __init__(self):
        pass

    @classmethod
    def load_history(cls) -> dict:
        if not cls.HISTORY_FILE_PATH.exists():
            return {}
        return CfgHandler.load(cls.HISTORY_FILE_PATH)

    @classmethod
    def load_devices(cls, load_history: bool = True, save_history: bool = True, auto_remove: bool = False):
        """
            加载 ADB Device
        """

        logger.info('Load Devices')

        history = {} if not load_history else cls.load_history()

        if load_history:
            logger.info(f"History {len(history)} Records")

        loaded_net_dev = {
            serial_no: {
                **dc.info._asdict(),
                'addr': dc.net_dev.serial
            } for serial_no, dc in cls.DEVICE_CONTROLLERS.items() if dc.net_dev
        }

        history.update(loaded_net_dev)

        remove_serial_no = []

        for serial_no, dc_info in history.items():
            if dc_info['addr']:
                try:
                    logger.info(f"Connecting to {dc_info['addr']} => {adb.connect(addr=dc_info['addr'], timeout=1)}")
                except AdbError:
                    logger.warning(f"Connecting to {dc_info['addr']} failed")
                    if auto_remove:
                        remove_serial_no.append(serial_no)

        for serial_no in remove_serial_no:
            history.pop(serial_no)

        for adb_dev in adb.device_list():
            try:
                # 解析设备信息
                info = DeviceController.analysis_device_info(adb_dev)

                if info.serial_no in cls.DEVICE_CONTROLLERS:
                    _dc = cls.DEVICE_CONTROLLERS[info.serial_no]

                    if info.serial_no == adb_dev.serial:    # USB Device
                        _dc.usb_dev = adb_dev
                    else:                                   # WLAN ADB
                        _dc.net_dev = adb_dev
                else:
                    cls.DEVICE_CONTROLLERS[info.serial_no] = DeviceController(adb_dev)

            except AdbError as e:
                logger.error(e)

        if save_history:
            _loaded = {
                serial_no: {
                    **dc.info._asdict(),
                    'addr': dc.net_dev.serial if dc.net_dev else history.get(
                        serial_no, {'addr': ''}
                    ).get('addr', ''),
                    'last_connected_time': datetime.datetime.now().timestamp(),
                } for serial_no, dc in cls.DEVICE_CONTROLLERS.items()
            }
            history.update(_loaded)
            CfgHandler.save(cls.HISTORY_FILE_PATH, history)
            logger.success(f"{len(history)} Records Saved => {cls.HISTORY_FILE_PATH}")

        msg = f"Load Devices Finished! {len(cls.DEVICE_CONTROLLERS)} Devices Connected!\n"
        msg += '-' * 200

        logger.success(msg)

    @classmethod
    def connect(cls, addr: str, timeout: int = 1) -> DeviceController | None:
        try:
            logger.info(f"Connecting to {addr} {adb.connect(addr, timeout=timeout)}")
        except AdbError:
            logger.error(f'Failed to connect to {addr}')
            return None

        cls.load_devices()

        for _ in cls.DEVICE_CONTROLLERS.values():
            if _.net_dev and _.net_dev.serial == addr:
                return _

        return None

    @classmethod
    def device(cls, serial_no: str = None, addr: str = None) -> DeviceController | None:

        # Update Device Controllers
        cls.load_devices()

        if serial_no:
            if serial_no in cls.DEVICE_CONTROLLERS:
                return cls.DEVICE_CONTROLLERS[serial_no]
            else:
                logger.error(f'Serial >{serial_no}< Device Not Found!')
                return None

        if addr:
            return cls.connect(addr=addr)

        if len(cls.DEVICE_CONTROLLERS) == 0:
            logger.error('No Device Controllers Found!')
            return None
        else:
            return cls.DEVICE_CONTROLLERS[
                list(cls.DEVICE_CONTROLLERS.keys())[0]
            ]

    @classmethod
    def devices(cls) -> Dict[str, DeviceController]:
        """
            获取所有设备
        :return:
        """
        return cls.DEVICE_CONTROLLERS

    @classmethod
    def device_num(cls) -> int:
        """
            设备数量
        :return:
        """
        return len(cls.DEVICE_CONTROLLERS)

    @classmethod
    def close_device(cls, device_serial: str):
        """
            关闭设备连接
        :param device_serial:
        :return:
        """
        try:
            cls.DEVICE_CONTROLLERS[device_serial].close()
        except KeyError:
            raise RuntimeError(f"Device > {device_serial} not Created!")

    @classmethod
    def close_all_devices(cls):
        """
            关闭全部设备
        :return:
        """
        for dev in [*cls.DEVICE_CONTROLLERS.values()]:
            dev.close()
        time.sleep(1)
        logger.success('All Devices Closed!')

    @classmethod
    def disconnect(cls, device_serial: str) -> bool:
        """
            断开连接
        """
        if device_serial in cls.DEVICE_CONTROLLERS:
            dc = cls.DEVICE_CONTROLLERS[device_serial]
            if dc.net_dev:
                try:
                    logger.info(f"Disconnecting {device_serial} => {adb.disconnect(dc.net_dev.serial)}")
                except AdbError as e:
                    logger.error(e)
                    return False
                return True
        logger.warning(f"Disconnected {device_serial} Failed!")
        return False


if __name__ == '__main__':
    d = DeviceFactory.device()
    vsc, asc, csc = d.connect(
        VideoSocketController(max_size=1366),
        AudioSocketController(),
        ControlSocketController()
    )
    time.sleep(2)
    d.close()
