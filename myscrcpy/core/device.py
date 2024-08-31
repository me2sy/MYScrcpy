# -*- coding: utf-8 -*-
"""
    设备控制器
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-31 1.4.1 Me2sY  改用新KVManager

        2024-08-29 1.4.0 Me2sY  重构，适配 Session 体系

        2024-08-25 0.1.0 Me2sY  重构，拆分VAC至单个连接
"""

__author__ = 'Me2sY'
__version__ = '1.4.1'

__all__ = [
    'DeviceInfo', 'PackageInfo',
    'AdvDevice', 'DeviceFactory'
]

import datetime
import re
import threading
import time
from typing import NamedTuple, Tuple, List, Dict

from adbutils import AdbDevice, AdbError, AppInfo, adb
from loguru import logger

from myscrcpy.utils import KVManager, kv_global, Coordinate, ROTATION_HORIZONTAL, ROTATION_VERTICAL


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


class PackageInfo(NamedTuple):
    """
        Android Package Info
    """
    package_name: str
    activity: str


class AdvDevice:
    """
        设备适配器
    """

    @classmethod
    def from_adb_direct(cls, device_serial: str | None = None) -> 'AdvDevice':
        """
            针对某些性能场景，进行直接连接
        """
        if device_serial is None:
            _ = cls(adb.device_list()[0])
        else:
            _ = cls(adb.device(device_serial))

        DeviceFactory.DEVICE_CONTROLLERS[_.info.serial_no] = _
        return _

    @staticmethod
    def analysis_device(dev: AdbDevice) -> Tuple[DeviceInfo, dict]:
        """
            通过getprop 快速读取并解析设备信息
        """

        prop_d = {}

        for _ in dev.shell('getprop', timeout=1).split('\n'):
            _ = _.replace('\r', '')
            if _[0] != '[' or _[-1] != ']':
                continue
            k, v = _.split(': ')

            cmd = "prop_d"
            for _ in k[1:-1].split('.'):
                cmd += f".setdefault('{_}', {{}})"

            cmd = cmd[:-3] + "'" + v[1:-1] + "')"

            try:
                exec(cmd)
            except:
                pass

        release = prop_d['ro']['build']['version']['release']

        if release is None or release == '':
            release = 14
        elif '.' in release:
            release = int(release.split('.')[0])
        else:
            release = int(release)

        return DeviceInfo(
            serial_no=prop_d['ro']['serialno'],
            brand=prop_d['ro']['product']['brand'],
            model=prop_d['ro']['product']['model'],
            sdk=int(prop_d['ro']['build']['version']['sdk']),
            release=release
        ), prop_d

    def __init__(
            self, adb_device: AdbDevice,
            device_info: DeviceInfo = None,
            prop_d: dict = None,
            *args, **kwargs
    ):
        """
            Device Controller
        :param adb_device:
        :param device_info:
        :param prop_d:
        :param args:
        :param kwargs:
        """
        self.info, self.prop_d = self.analysis_device(adb_device) if device_info is None else (device_info, prop_d)
        self.serial_no = self.info.serial_no

        self.kvm = KVManager(f"dev_{self.serial_no}")

        self.usb_dev = adb_device if adb_device.serial == self.info.serial_no else None
        self.net_dev = None if self.usb_dev else adb_device
        self.adb_dev_ready = None

        self.scrcpy_cfg = None
        self.sessions = set()

    def __repr__(self):
        return f"AdvDevice > {self.info}"

    def stop(self):
        for sess in self.sessions:
            try:
                sess.stop()
            except:
                ...

    @property
    def adb_dev(self) -> AdbDevice:
        """
            获取 ADB Dev
        """
        if self.adb_dev_ready:
            return self.adb_dev_ready

        try:
            if self.usb_dev and self.usb_dev.shell('echo 1', timeout=0.1):
                self.adb_dev_ready = self.usb_dev
                return self.usb_dev

        except AdbError as e:
            logger.warning(f"{self.info} USB Connection Maybe LOST! Error => {e}")
            self.usb_dev = None

        try:
            if self.net_dev and self.net_dev.shell('echo 1', timeout=0.1):
                self.adb_dev_ready = self.net_dev
                return self.net_dev

        except AdbError as e:
            logger.warning(f"{self.info} Net Connection Maybe LOST! Error => {e}")

        self.adb_dev_ready = None

        raise RuntimeError(f'{self.usb_dev} {self.net_dev} Device not connected')

    @staticmethod
    def reconnected():
        """
            重连至ADB Device
        """
        DeviceFactory.load_devices(load_history=False, save_history=False)

    @property
    def wlan_ip(self) -> str | None:
        """
            获取 Wlan IP
        :return:
        """
        try:
            return self.adb_dev.wlan_ip()
        except AdbError:
            return None
        except RuntimeError:
            return None

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

        time.sleep(2)

        DeviceFactory.load_devices()

    @property
    def tcpip_port(self) -> int:
        """
            获取设备 TCPIP 端口
        :return:
        """
        # 2024-08-18 Me2sY 修复连接失败导致错误
        try:
            p = self.adb_dev.getprop('service.adb.tcp.port')
        except Exception as e:
            p = ''
        if p is None or p == '':
            return -1
        else:
            return int(p)

    def lock(self):
        """
            Lock Device
        :return:
        """
        self.set_power(False)

    def is_locked(self):
        """
            is device locked
        :return:
        """
        return self.adb_dev.shell('dumpsys deviceidle | grep "mScreenLocked="').strip().split('=')[1] == 'true'

    def set_power(self, status: bool = True):
        """
            set device power
        :param status:
        :return:
        """
        if self.adb_dev.is_screen_on() ^ status:
            self.adb_dev.keyevent('POWER')

    def reboot(self):
        """
            重启设备
        :return:
        """
        if self.adb_dev:
            self.adb_dev.reboot()

    def get_current_package_info(self) -> Tuple[PackageInfo, AppInfo] | None:
        """
            通过ADB获取当前APP name 无法获取时采用原生方法，相对速度较慢
        :return:
        """
        msg = self.adb_dev.shell("dumpsys window displays | grep -E 'mCurrentFocus'")
        try:
            pi = PackageInfo(msg.split('/')[0].split('{')[1].split(' ')[-1], msg.split('/')[1][:-1])
        except:
            app_info = self.adb_dev.app_current()
            pi = PackageInfo(package_name=app_info.package, activity=app_info.activity)
        return pi, self.adb_dev.app_info(pi.package_name)

    def get_window_size(self) -> Coordinate:
        """
            Rewrite adb.shell.window_size
            去除Rotation，降低延迟
        :return:
        """
        output = self.adb_dev.shell("wm size")
        o = re.search(r"Override size: (\d+)x(\d+)", output)
        if o:
            w, h = o.group(1), o.group(2)
            return Coordinate(int(w), int(h))
        m = re.search(r"Physical size: (\d+)x(\d+)", output)
        if m:
            w, h = m.group(1), m.group(2)
            return Coordinate(int(w), int(h))
        raise AdbError("wm size output unexpected", output)

    def get_rotation(self) -> int:
        """
            获取当前设备方向
        :return:
        """
        return ROTATION_HORIZONTAL if self.adb_dev.rotation() % 2 == 1 else ROTATION_VERTICAL


class DeviceFactory:
    """
        设备管理工厂
        通过使用 .device() 方法 获取 DeviceController 对象实例
    """

    DEVICE_CONTROLLERS = {}

    @classmethod
    def load_history(cls) -> dict:
        """
            加载历史连接记录
        """
        return kv_global.get('load_history', {})


    @staticmethod
    def _connect_device(addr: str, timeout: int):
        try:
            adb.connect(addr, timeout=timeout)
        except AdbError as e:
            logger.warning(f"Connecting to {addr} failed! => {e}")

    @classmethod
    def load_devices(cls, load_history: bool = True, save_history: bool = True):
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

        # 遍历历史记录，尝试连接无线设备
        # 2024-08-19 Me2sY  去除无用逻辑，添加ADB重连失败告警
        for serial_no, dc_info in history.items():
            if dc_info['addr']:
                threading.Thread(target=cls._connect_device, args=(dc_info['addr'], 1)).start()

        for adb_dev in adb.device_list():
            try:
                # 解析设备信息
                info, prop_d = AdvDevice.analysis_device(adb_dev)

                if info.serial_no in cls.DEVICE_CONTROLLERS:
                    _dc = cls.DEVICE_CONTROLLERS[info.serial_no]

                    if info.serial_no == adb_dev.serial:    # USB Device
                        _dc.usb_dev = adb_dev
                    else:                                   # WLAN ADB
                        _dc.net_dev = adb_dev
                else:
                    cls.DEVICE_CONTROLLERS[info.serial_no] = AdvDevice(adb_dev, device_info=info, prop_d=prop_d)
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

            kv_global.set('load_history', history)

            logger.success(f"{len(history)} Records Saved")

        msg = f"Load Devices Finished! {len(cls.DEVICE_CONTROLLERS)} Devices Connected!\n"
        msg += '-' * 200

        logger.success(msg)

    @classmethod
    def connect(cls, addr: str, timeout: int = 1) -> AdvDevice | None:
        """
            连接无线设备
        """
        try:
            logger.info(f"Connecting to {addr} {adb.connect(addr, timeout=timeout)}")
        except AdbError as e:
            logger.error(f'Failed to connect to {addr} => {e}')
            return None

        cls.load_devices()

        for _ in cls.DEVICE_CONTROLLERS.values():
            if _.net_dev and _.net_dev.serial == addr:
                return _

        return None

    @classmethod
    def device(cls, serial_no: str = None, addr: str = None) -> AdvDevice | None:
        """
            获取 DeviceController
        :param serial_no:
        :param addr:
        :return:
        """

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
    def devices(cls) -> Dict[str, AdvDevice]:
        """
            获取所有设备
        :return:
        """
        return cls.DEVICE_CONTROLLERS

    @classmethod
    def device_list(cls) -> List[AdvDevice]:
        """
            获取设备列
        """
        return list(cls.DEVICE_CONTROLLERS.values())

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
            cls.DEVICE_CONTROLLERS[device_serial].stop()
        except KeyError:
            raise RuntimeError(f"Device > {device_serial} not Created!")

    @classmethod
    def close_all_devices(cls):
        """
            关闭全部设备
        :return:
        """
        for dev in [*cls.DEVICE_CONTROLLERS.values()]:
            dev.stop()
        time.sleep(0.5)
        logger.success('All Device Closed!')

    @classmethod
    def disconnect(cls, device_serial: str) -> bool:
        """
            断开ADB WIFI 连接
        :param device_serial:
        :return:
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
