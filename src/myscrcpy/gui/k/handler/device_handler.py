# -*- coding: utf-8 -*-
"""
    device_handler
    ~~~~~~~~~~~~~~~~~~
    解决 AdvDevice 连接过慢问题

    Log:
        2025-05-08 3.2.0 Me2sY 创建，替换原 AdvDevice，解决连接过慢问题
"""

__author__ = 'Me2sY'
__version__ = '3.2.0'

__all__ = [
    'DeviceConnectMode', 'PackageInfo',
    'MYDeviceInfo', 'MYDevice'
]

from dataclasses import dataclass
from enum import IntEnum
import re
from typing import Self, ClassVar, Optional, Tuple

from adbutils import adb, AdbDevice, AppInfo
from adbutils.errors import AdbError
import uiautomator2
from uiautomator2 import Device as U2Device

from kivy.storage.dictstore import DictStore
from kivy.logger import Logger

from myscrcpy.utils import Param, Coordinate, ROTATION_VERTICAL, ROTATION_HORIZONTAL


class DeviceConnectMode(IntEnum):
    """
        设备连接模式，USB及WLAN两种
    """
    USB = 0
    WLAN = 1


@dataclass(frozen=True)
class PackageInfo:
    """
        Android Package Info
    """
    package_name: str
    activity: str


@dataclass(frozen=True)
class MYDeviceInfo:
    """
        设备基础信息
    """
    brand: str = ''
    model: str = ''
    sdk: int = 34                       # Use High When not get
    release: int = 14                   # Use High When not get
    arch: str = ''
    marketname: str = ''

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
        return self.release >= 9


class MYDevice:

    DeviceInfoStore: ClassVar[DictStore] = DictStore(Param.PATH_CONFIGS.joinpath('ky_devices.dsf'))

    @staticmethod
    def analysis_device(dev: AdbDevice, u2d: U2Device) -> MYDeviceInfo:
        """
            获取并分析设备信息
        :param dev: AdbDevice
        :param u2d: U2Device
        :return:
        """
        prop_d = {}

        for _ in dev.shell('getprop', timeout=1).split('\n'):
            _ = _.replace('\r', '')
            if _[0] != '[' or _[-1] != ']':
                continue
            try:
                k, v = _.split(': ')
            except Exception as e:
                continue

            cmd = "prop_d"
            for _ in k[1:-1].split('.'):
                cmd += f".setdefault('{_}', {{}})"

            cmd = cmd[:-3] + "'" + v[1:-1] + "')"

            try:
                exec(cmd)
            except:
                pass

        device_info_u2d = u2d.device_info
        info_u2d = u2d.info

        try:
            brand = prop_d['ro']['vendor']['brand']
        except:
            try:
                brand = device_info_u2d['brand']
            except:
                brand = ''

        try:
            model = prop_d['ro']['vendor']['model']
        except:
            try:
                model = device_info_u2d['model']
            except:
                model = ''

        try:
            sdk = int(prop_d['ro']['build']['version']['sdk'])
        except:
            sdk = info_u2d['sdkInt']

        try:
            release = prop_d['ro']['build']['version']['release']
        except Exception:
            release = None

        if release is None or release == '':
            try:
                release = device_info_u2d['version']
            except:
                release = 14
        elif '.' in release:
            release = int(release.split('.')[0])
        else:
            release = int(release)

        arch = device_info_u2d['arch']

        try:
            marketname = prop_d['ro']['product']['marketname']
        except:
            marketname = brand

        return MYDeviceInfo(**{
            'brand': brand,
            'model': model,
            'sdk': sdk,
            'release': release,
            'arch': arch,
            'marketname': marketname,
        })

    @classmethod
    def list_devices(cls) -> list[Self]:
        """
            列出设备
        :return:
        """
        return [cls(d) for d in adb.device_list()]

    def __repr__(self):
        _ = f'MYDevice > {self.connect_mode.name:<4} | {self.serial:<18}'
        _ += f' | {self.wlan_ip if self.wlan_ip else ""}:{self.port}'
        return _

    def __init__(self, device: AdbDevice | str, **kwargs):
        """
            android设备，获取真实Serial以确保唯一，缓存设备信息提供加载速度
        :param device:
        :param kwargs:
        """

        self.adb_dev: AdbDevice = device if isinstance(device, AdbDevice) else adb.device(device)

        # 获取真实设备serial
        self.serial: str = device.getprop('ro.boot.serialno')

        self.connect_mode: DeviceConnectMode = DeviceConnectMode.USB
        self.wlan_ip: str | None = None
        self._port: int | None = None

        # 判断连接方式，确定 ip 及 ADB 端口
        try:
            self.wlan_ip = self.adb_dev.wlan_ip()

            if self.adb_dev.serial.startswith(self.wlan_ip + ':'):
                self.connect_mode = DeviceConnectMode.WLAN
                self._port = int(self.adb_dev.serial.split(':')[1])

        except AdbError:
            ...

        self._device_info: MYDeviceInfo | None = None
        if self.DeviceInfoStore.exists(self.serial):
            self._device_info = self.DeviceInfoStore.get(self.serial)['device_info']

        self._u2d: U2Device | None = None

        # 设备初始坐标
        self.orig_coord: Coordinate | None = None

    @property
    def port(self) -> int | None:
        """
            获取端口
        :return:
        """
        if self.connect_mode == DeviceConnectMode.WLAN and self._port:
            return self._port

        try:
            p = self.adb_dev.getprop('service.adb.tcp.port')
        except Exception as e:
            p = ''
        if p is None or p == '':
            return None
        else:
            return int(p)

    @property
    def connect_serial(self) -> str:
        """
            连接使用的 serial 可能是WLAN_IP + Port
        :return:
        """
        return self.adb_dev.serial

    def init_u2d(self, *args) -> U2Device:
        """
            初始化u2d
        :return:
        """
        if self._u2d is None:
            self._u2d = U2Device(self.connect_serial)
        return self._u2d

    def wlan_ip(self) -> str:
        """
            Wlan IP
        :return:
        """
        if self.connect_mode == DeviceConnectMode.WLAN:
            return self.wlan_ip
        else:
            return self.adb_dev.wlan_ip()

    def load_info(self) -> MYDeviceInfo:
        """
            加载设备信息
        :return:
        """
        if self._device_info:
            ...
        else:
            if not self.DeviceInfoStore.exists(self.serial):
                Logger.info(f'New Device {self.serial} Found. Getting Device Info. Please Wait.')
                self._u2d = uiautomator2.connect(self.adb_dev.serial) if self._u2d is None else self._u2d
                self._device_info = self.analysis_device(self.adb_dev, self._u2d)
                self.DeviceInfoStore.put(self.serial, device_info=self.device_info)
            else:
                self._device_info = self.DeviceInfoStore.get(self.serial)['device_info']

        return self._device_info

    @property
    def device_info(self) -> MYDeviceInfo:
        """
            懒加载，避免uiautomator2卡连接
        :return:
        """
        if self._device_info:
            return self._device_info
        else:
            return self.load_info()

    def _window_size(self) -> Coordinate:
        """
            改写 adbutils.window_size 避免Log错误
        :return:
        """
        output = self.adb_dev.shell('wm size')
        o = re.search(r"Override size: (\d+)x(\d+)", output)
        if o:
            w, h = o.group(1), o.group(2)
            return Coordinate(int(w), int(h))
        m = re.search(r"Physical size: (\d+)x(\d+)", output)
        if m:
            w, h = m.group(1), m.group(2)
            return Coordinate(int(w), int(h))
        raise ValueError('wm size output unexpected')

    def window_size(self, landscape: Optional[bool] = None) -> Coordinate:
        """
            改写 adbutils.window_size 避免Log错误
        :param landscape:
        :return:
        """
        coord = self._window_size()
        if landscape is None:
            landscape = self.adb_dev.rotation() % 2 == 1
        return coord.rotate() if landscape else coord

    def coord(self, reload: bool = False) -> Coordinate:
        """
            或者竖直屏幕坐标
        :param reload:
        :return:
        """
        if not reload and self.orig_coord:
            return self.orig_coord

        if self._u2d:
            info = self._u2d.info
            w = info['displayWidth'] if info['displayRotation'] % 2 == 0 else info['displayHeight']
            h = info['displayWidth'] if info['displayRotation'] % 2 == 1 else info['displayHeight']
            self.orig_coord = Coordinate(w, h)
        else:
            try:
                self.orig_coord = self.window_size(False)
            except Exception as e:
                Logger.error(f'Failed to get orig coordinate by ADB. Use uiautomator2: {e}')
                self._u2d = uiautomator2.connect(self.adb_dev.serial)
                return self.coord(reload)
        return self.orig_coord

    def get_current_package_info(self, has_app_info: bool = True) -> Tuple[PackageInfo, Optional[AppInfo]] | None:
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

        if has_app_info:
            return pi, self.adb_dev.app_info(pi.package_name)
        else:
            return pi, None

    def get_rotation(self):
        """
            获取设备垂直或水平方向, 如果u2d已经初始化，则使用u2d.info 速度较快
        :return:
        """
        if self._u2d:
            info = self._u2d.info
            w = info['displayWidth'] if info['displayRotation'] % 2 == 0 else info['displayHeight']
            h = info['displayWidth'] if info['displayRotation'] % 2 == 1 else info['displayHeight']
            self.orig_coord = Coordinate(w, h)
            return ROTATION_HORIZONTAL if info['displayRotation'] % 2 == 1 else ROTATION_VERTICAL
        else:
            return ROTATION_HORIZONTAL if self.adb_dev.rotation() % 2 == 1 else ROTATION_VERTICAL

    def cur_coord(self) -> Coordinate:
        """
            返回当前状态设备坐标
        :return:
        """
        if self._u2d:
            r = self.get_rotation()
            return self.orig_coord if r % 2 == 0 else self.orig_coord.rotate()
        else:
            return self.window_size()

    def set_power(self, status: bool = True):
        """
            set device power
        :param status:
        :return:
        """
        if self.adb_dev.is_screen_on() ^ status:
            self.adb_dev.keyevent('POWER')

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

    def reboot(self):
        """
            重启设备
        :return:
        """
        if self.adb_dev:
            self.adb_dev.reboot()
