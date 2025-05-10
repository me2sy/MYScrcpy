# -*- coding: utf-8 -*-
"""
    设备控制器
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-10-13 1.6.6 Me2sY
            1. 修复prop解析错误问题
            2. 降低 UHID 输入版本功能需求至 9

        2024-10-09 1.6.5 Me2sY  适配 MuMu模拟器

        2024.09.18 1.6.0 Me2sY  适配 插件 体系

        2024-09-13 1.5.11 Me2sY 新引入 uiautomator2，在dump/info/screenshot方面使用jsonrpc,速度很快

        2024-09-10 1.5.9 Me2sY  新增文件管理器，支持拷贝、上传、删除等功能

        2024-08-31 1.4.1 Me2sY  改用新KVManager

        2024-08-29 1.4.0 Me2sY  重构，适配 Session 体系

        2024-08-25 0.1.0 Me2sY  重构，拆分VAC至单个连接
"""

__author__ = 'Me2sY'
__version__ = '1.6.6'

__all__ = [
    'DeviceInfo', 'PackageInfo',
    'AdvDevice', 'DeviceFactory'
]

import datetime
import stat
import threading
import time
from pathlib import PurePosixPath, Path
from typing import NamedTuple, Tuple, List, Dict

from adbutils import AdbDevice, AdbError, AppInfo, adb, FileInfo
from loguru import logger

from myscrcpy.utils import KVManager, kv_global, Coordinate, ROTATION_HORIZONTAL, ROTATION_VERTICAL, Param
import uiautomator2


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
        return self.release >= 9


class PackageInfo(NamedTuple):
    """
        Android Package Info
    """
    package_name: str
    activity: str


class FileManager:
    """
        文件管理器
    """

    def __init__(self, adb_device: AdbDevice):
        self.adb_device = adb_device

        self.path_base = Param.PATH_DEV_BASE
        self.path_cur = self.path_base
        self.path_push = Param.PATH_DEV_PUSH

        if not self.adb_device.sync.exists(self.path_push.__str__()):
            self.adb_device.shell(['mkdir', self.path_push.__str__()])

    def __repr__(self):
        return self.path_cur.__str__()

    def ls(self, path: str = None) -> List[FileInfo]:
        """
            ls
        :param path:
        :return:
        """
        _path = PurePosixPath(path) if path else self.path_cur
        return self.adb_device.sync.list(_path.__str__())

    def rm(self, abs_path: PurePosixPath | str):
        """
            Remove Path
        :param abs_path:
        :return:
        """

        file_info = self.adb_device.sync.stat(abs_path.__str__())
        if file_info.mode == 0 and file_info.size == 0 and file_info.mtime is None:
            logger.warning(f"{abs_path} Not Exists")
            return

        if stat.S_ISDIR(file_info.mode):
            sr = self.adb_device.shell2(f"rm -rf {abs_path}")
            if sr.returncode != 0:
                logger.warning(f"rm {abs_path} Error => {sr.output}")
            else:
                logger.error(f"{abs_path} Removed!")

        elif stat.S_ISREG(file_info.mode) or stat.S_ISLNK(file_info.mode):
            sr = self.adb_device.shell2(f"rm {abs_path}")
            if sr.returncode != 0:
                logger.warning(f"rm {abs_path} Error => {sr.output}")
            else:
                logger.error(f"{abs_path} Removed!")

    def cd(self, path: str | PurePosixPath) -> PurePosixPath:
        """
            CD
        :param path:
        :return:
        """
        _path = self.path_cur / path
        if self.adb_device.sync.exists(_path.__str__()):

            sr = self.adb_device.shell2(f"cd {_path} && pwd")
            if sr.returncode == 0:
                self.path_cur = PurePosixPath(sr.output.replace('\n', ''))
            else:
                logger.warning(f"{_path} => {sr.output}")
        else:
            logger.warning(f"{_path} does not exist")
        return self.path_cur

    def pwd(self) -> PurePosixPath:
        """
            file manager pwd
        :return:
        """
        return self.path_cur

    def push(
            self, src: Path, dest: PurePosixPath = None,
            mode: int = 0o755, check: bool = False,
            to_default_path: bool = True
    ):
        """
            上传文件
        :param src:
        :param dest:
        :param mode:
        :param check:
        :param to_default_path:
        :return:
        """
        if not src.is_file():
            logger.warning(f"{src} is not a file")

        if dest is None:
            if to_default_path:
                dest = self.path_push
            else:
                dest = self.path_cur

        self.adb_device.sync.push(src, dest.__str__(), mode=mode, check=check)
        logger.info(f"pushed {src} to {dest}")

    def push_dir(self, src: Path, dest: PurePosixPath = None, to_default_path: bool = True, **kwargs):
        """
            上传路径
        :param src:
        :param dest:
        :param to_default_path:
        :param kwargs:
        :return:
        """

        dest = dest or (self.path_push if to_default_path else self.path_cur)

        for _ in src.iterdir():

            if _.is_dir():
                self.adb_device.shell(['mkdir', (dest / _.name).__str__()])
                logger.info(f"mkdir {dest / _.name}")
                self.push_dir(_, dest / _.name, **kwargs)

            elif _.is_file():
                self.push(_, dest, **kwargs)

    def pull(self, *args, **kwargs):
        return self.adb_device.sync.pull(*args, **kwargs)

    def pull_file(self, file_name: str, dest: Path):
        """
            拉取当前目录下文件
        :param file_name:
        :param dest:
        :return:
        """
        return self.adb_device.sync.pull((self.path_cur / file_name).__str__(), dest / file_name)

    def pull_dir(self, *args, **kwargs):
        return self.adb_device.sync.pull_dir(*args, **kwargs)

    def push_clipboard_to_device(self, path: PurePosixPath = None):
        """
            将剪切板内容推送至设备
        :return:
        """
        try:
            from PIL import ImageGrab
        except ImportError:
            logger.error(f"PIL Not Install.")
            return False

        im = ImageGrab.grabclipboard()

        if im is None:
            pass

        elif isinstance(im, list):

            path_push = self.path_push if path is None else path

            for _ in im:
                p = Path(_)
                if p.is_dir():
                    self.adb_device.shell(['mkdir', (path_push / p.name).__str__()])
                    logger.info(f"mkdir {(path_push / p.name).__str__()}")
                    self.push_dir(p, path_push / p.name)

                elif p.is_file():
                    self.push(p, path)
        else:
            # 截图 放置到 DCIM文件夹
            try:
                fp = Param.PATH_TEMP / ('ps_' + datetime.datetime.now().strftime('%Y%m%d%H%M%S') + '.jpg')
                with fp.open('wb') as f:
                    im.save(f, 'JPEG')
                self.push(fp, Param.PATH_DEV_SCREENSHOT if path is None else path)
                fp.unlink()
            except:
                pass


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

        u2d = uiautomator2.connect(dev.serial)

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

        try:
            serial_no = prop_d['ro']['serialno']
        except:
            serial_no = dev.serial

        try:
            brand = prop_d['ro']['product']['brand']
        except:
            brand = ''

        try:
            model = prop_d['ro']['product']['model']
        except:
            model = u2d.info['productName']

        try:
            sdk = int(prop_d['ro']['build']['version']['sdk'])
        except:
            sdk = u2d.info['sdkInt']

        try:
            release = prop_d['ro']['build']['version']['release']
        except Exception:
            release = None

        if release is None or release == '':
            try:
                release = u2d.device_info['version']
            except:
                release = 14
        elif '.' in release:
            release = int(release.split('.')[0])
        else:
            release = int(release)

        return DeviceInfo(serial_no=serial_no, brand=brand, model=model, sdk=sdk, release=release), prop_d

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

        self.kvm = KVManager(f"dev_{self.serial_no.replace('.', '_').replace(':', '__')}")

        self.usb_dev = adb_device if adb_device.serial == self.info.serial_no else None
        self.net_dev = None if self.usb_dev else adb_device
        self.adb_dev_ready = None

        self.scrcpy_cfg = None
        self.sessions = set()

        # 2024-09-10 1.5.9 Me2sY 新增文件管理器
        self.file_manager = FileManager(adb_device)

        # 2024-09-13 1.5.11 Me2sY 引入 uiautomator2
        self.u2d = uiautomator2.connect(self.adb_dev.serial)

        # u2使用jsonrpc获取设备信息延迟低，极少出现卡加载情况
        info = self.u2d.info
        if info['displayRotation'] % 2 == 0:
            self.coord_device_v = Coordinate(width=info['displayWidth'], height=info['displayHeight'])
        else:
            self.coord_device_v = Coordinate(width=info['displayHeight'], height=info['displayWidth'])

        self.coord_device_h = self.coord_device_v.rotate()

    def coord_device(self, rotation: int) -> Coordinate:
        """
            获取设备实际尺寸
        :param rotation:
        :return:
        """
        if rotation % 2 == 0:
            return self.coord_device_v
        else:
            return self.coord_device_h

    @property
    def coordinate(self) -> Coordinate:
        """
            直接获取
            在当前device rotation 已知情况下，建议使用 coord_device(rotation) 获取
        :return:
        """
        return self.coord_device(self.u2d.info['displayRotation'] % 2)

    def __repr__(self):
        return f"AdvDevice > {self.info}"

    def stop(self):
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

            2024-09-18 1.6.0 Me2sY  改用 uiautomator2.info
        :return:
        """
        info = self.u2d.info
        return Coordinate(info['displayWidth'], info['displayHeight'])

    def get_rotation(self) -> int:
        """
            获取当前设备方向
        :return:
        """
        return ROTATION_HORIZONTAL if self.u2d.info['displayRotation'] % 2 == 1 else ROTATION_VERTICAL


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
        logger.warning('All Device Closed!')

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
