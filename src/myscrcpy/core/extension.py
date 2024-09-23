# -*- coding: utf-8 -*-
"""
    插件及管理器
    ~~~~~~~~~~~~~~~~~~

    Log:
         2024-09-15 1.6.0 Me2sY  创建，插件核心类
"""

__author__ = 'Me2sY'
__version__ = '1.6.0'

__all__ = [
    'ExtInfo',
    'ExtLoader',
    'Extension',
    'RegisteredExtension', 'ExtensionManager'
]

import threading
from abc import abstractmethod, ABCMeta
from dataclasses import dataclass, field
from hashlib import md5
import importlib
import pathlib
import sys
import tomllib
import zipfile
from importlib.machinery import SourceFileLoader
from types import ModuleType
from typing import Tuple

from loguru import logger

from myscrcpy.core import AdvDevice, Session
from myscrcpy.utils import Param, KVManager, Coordinate


@dataclass
class ExtInfo:
    """
        插件信息
    """
    ext_module: str
    ext_md5: str
    ext_path: pathlib.Path

    ext_name: str = ''
    version: str = '0.0.0'
    author: str = ''
    email: str = ''
    web: str = ''
    contact: str = ''
    desc: str = ''

    settings: dict = field(default_factory=dict)

    raw: dict = field(default_factory=dict)


class ExtLoader:
    """
        模块加载器
        插件结构

        XXX.zip
        |- your_ext_module_file
        |-- __init__.py
        |-- extensions.toml
        |-- your_other_module_files
        |-- ...

        配置文件使用 toml格式，详见示例
    """

    CFG_FILE_NAME = 'extension.toml'

    @staticmethod
    def load_zip_info(ext_zip_path: str | pathlib.Path) -> ExtInfo:
        """
            从ZIP中加载插件信息
        :param ext_zip_path:
        :return:
        """

        # 加载 ZIP 文件
        zip_path = pathlib.Path(ext_zip_path)
        if not zip_path.exists() or not zip_path.is_file():
            msg = f"Extension ZIP Not Found in {ext_zip_path}"
            logger.error(msg)
            raise FileNotFoundError(msg)

        # 计算MD5
        ext_md5 = md5(zip_path.read_bytes()).hexdigest()

        # 加载 ZIP 文件
        zf = zipfile.ZipFile(ext_zip_path)

        cfg_path = None
        zf_files = zf.namelist()

        # 读取 extension.toml
        # 需放置在 module一级目录下
        for _ in zf_files:
            if _.endswith(f"/{ExtLoader.CFG_FILE_NAME}"):
                cfg_path = _

                if len(_.split('/')) != 2:
                    msg = f"File Struct is invalid. Use /your_extension/{ExtLoader.CFG_FILE_NAME}"
                    logger.error(msg)
                    raise TypeError(msg)

                ext_module = _.split('/')[0]
                break

        if cfg_path is None:
            msg = f"{ExtLoader.CFG_FILE_NAME} Not Found in {ext_zip_path}"
            logger.error(msg)
            raise FileNotFoundError(msg)

        # 加载 配置文件
        try:
            cfg = tomllib.load(zf.open(cfg_path))
        except tomllib.TOMLDecodeError as e:
            logger.error(f'Load Toml File Error -> {e}')
            raise e

        ext_info = ExtInfo(
            ext_module=ext_module, ext_md5=ext_md5, ext_path=ext_zip_path,
            **cfg.get('info', {}), settings=cfg.get('settings', {}), raw=cfg
        )

        # TODO MD5检查
        if not ExtLoader.check_md5(ext_info):
            msg = f"Check {ext_zip_path} MD5 Error!"
            logger.error(msg)
            raise PermissionError(msg)

        return ext_info

    @staticmethod
    def check_md5(ext_info: ExtInfo) -> bool:
        """
            联网检查 ZIP Module MD5
        :param ext_info: Ext Info
        :return:
        """
        # TODO 2024-09-15 Me2sY
        # 可联网核查 通过Ext_ZIP FILE NAME/Module/Version 判断MD5是否一致
        return True

    @staticmethod
    def load_zip_extension(ext_info: ExtInfo) -> Tuple[ModuleType, 'Extension']:
        """
            加载插件至当前环境
        :param ext_info:
        :return:
        """

        # 加载至当前环境
        # 隐形使用 zipimport 引入 module
        # 返回 __init__.py 中 __all__ 暴露的 第一个 Extension Class
        # 否则 Raise 异常

        sys.path.insert(0, ext_info.ext_path.__str__())
        _module = importlib.import_module(ext_info.ext_module)

        for _ in _module.__all__:
            if issubclass(_module.__getattribute__(_), Extension):
                return _module, _module.__getattribute__(_)

        raise ModuleNotFoundError(f"Extension Class Not Found in __init__.py / __all__")

    @staticmethod
    def load_local_info(local_path: str | pathlib.Path) -> ExtInfo:
        """
            加载本地原生插件
        :param local_path:
        :return:
        """
        local_path = pathlib.Path(local_path)

        cfg_path = local_path.joinpath(ExtLoader.CFG_FILE_NAME)

        if not cfg_path.exists():
            msg = f"{ExtLoader.CFG_FILE_NAME} Not Found in {local_path}"
            logger.error(msg)
            raise FileNotFoundError(msg)

        # 加载 toml
        try:
            cfg = tomllib.load(cfg_path.open('rb'))
        except tomllib.TOMLDecodeError as e:
            logger.error(f'Load Toml File Error -> {e}')
            raise e

        ext_path = local_path / '__init__.py'

        if not ext_path.exists():
            raise FileNotFoundError(f"__init__.py Not Found in {local_path}")

        # 返回 ExtInfo
        return ExtInfo(
            ext_module=local_path.name, ext_md5='0' * 32, ext_path=ext_path,
            **cfg.get('info', {}), settings=cfg.get('settings', {}), raw=cfg
        )

    @staticmethod
    def load_local_extension(ext_info: ExtInfo) -> Tuple[ModuleType, 'Extension']:
        """
            加载本地插件
        :param ext_info:
        :return:
        """

        # 加载 module
        _module = SourceFileLoader(ext_info.ext_module, ext_info.ext_path.__str__()).load_module()

        # 查找 Extension Class
        for _ in _module.__all__:
            if issubclass(_module.__getattribute__(_), Extension):
                return _module, _module.__getattribute__(_)

        raise ModuleNotFoundError(f"Extension Class Not Found in __init__.py / __all__")


class Extension(metaclass=ABCMeta):
    """
        插件抽象基类
        继承该基类，重新相关方法
    """

    def __init__(self, ext_info: ExtInfo):
        """
            插件初始化，传入插件信息
        :param ext_info:
        """
        self.ext_info = ext_info

        # 运行配置管理器
        self.kv = KVManager(f"ext_{ext_info.ext_module}")

    @abstractmethod
    def start(self):
        """
            启动，界面绘制等
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def device_connect(
            self, adv_device: AdvDevice, session: Session
    ):
        """
            设备连接后回调方法，传入 设备 及 session 实例
        :param adv_device:
        :param session:
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def device_disconnect(self):
        """
            设备断连后回调
        :return:
        """
        raise NotImplementedError

    def device_rotation(self, video_coord: Coordinate):
        """
            设备旋转
        :param video_coord:
        :return:
        """
        ...

    @abstractmethod
    def stop(self):
        """
            插件停止时回调
        :return:
        """
        raise NotImplementedError


@dataclass
class RegisteredExtension:
    """
        已注册插件信息
    """
    ext_info: ExtInfo
    ext_module: ModuleType
    ext_cls: Extension.__class__
    ext_obj: Extension | None = None
    is_activated: bool = False


class ExtensionManager:
    """
        插件管理器
    """

    def __init__(self):
        self.extensions = {}

    def __iter__(self):
        return iter(self.extensions.items())

    def load_extensions(self, load_local: bool = True, load_zip: bool = True):
        """
            加载 插件
        :return:
        """
        if load_local:
            for ext_local in Param.PATH_EXTENSIONS_LOCAL.iterdir():
                if not ext_local.is_dir():
                    continue

                if ext_local.is_dir():
                    if ext_local.name.startswith('_'):
                        continue

                    if ext_local.name.startswith('.'):
                        continue

                logger.info(f'Loading Local {ext_local}')
                try:
                    ext_info = ExtLoader.load_local_info(ext_local)

                    if ext_info.ext_module in self.extensions:
                        raise FileExistsError(f"Extension {ext_info.ext_module} already loaded")

                    ext_module, ext_cls = ExtLoader.load_local_extension(ext_info)

                    logger.debug(f"Load => {ext_module} {ext_cls} | {type(ext_cls)}")

                    self.extensions[ext_info.ext_module] = RegisteredExtension(
                        ext_info=ext_info, ext_module=ext_module, ext_cls=ext_cls
                    )

                    logger.success(f'{ext_info.ext_module} | {ext_cls} Loaded')
                except Exception as e:
                    logger.error(e)
                    continue

        if load_zip:
            for ext_zip in Param.PATH_EXTENSIONS.glob('*.zip'):
                logger.info(f'Loading ZIP {ext_zip}')
                try:
                    ext_info = ExtLoader.load_zip_info(ext_zip)

                    if ext_info.ext_module in self.extensions:
                        raise FileExistsError(f"Extension {ext_info.ext_module} already loaded")

                    ext_module, ext_cls = ExtLoader.load_zip_extension(ext_info)
                    self.extensions[
                        ext_info.ext_module
                    ] = RegisteredExtension(ext_info=ext_info, ext_module=ext_module, ext_cls=ext_cls)

                    logger.success(f'{ext_info.ext_module} | {ext_cls} Loaded')

                except Exception as e:
                    logger.error(e)
                    continue

    @staticmethod
    def register_extension(registered_ext: RegisteredExtension) -> Extension:
        """
            注册插件
        :param registered_ext:
        :return:
        """
        registered_ext.ext_obj = registered_ext.ext_cls(ext_info=registered_ext.ext_info)
        return registered_ext.ext_obj

    @staticmethod
    def unregister_extension(registered_ext: RegisteredExtension):
        """
            取消插件注册
        :param registered_ext:
        :return:
        """
        try:
            registered_ext.ext_obj.stop()
        except Exception as e:
            ...

        registered_ext.ext_obj = None

    def device_connected(self, adv_device: AdvDevice, session: Session):
        """
            设备连接
        :param adv_device:
        :param session:
        :return:
        """
        for _, registered_ext in self.extensions.items():
            if registered_ext.is_activated:
                threading.Thread(target=registered_ext.ext_obj.device_connect, args=(adv_device, session,)).start()

    def device_disconnect(self):
        """
            设备断联
        :return:
        """
        for _, registered_ext in self.extensions.items():
            if registered_ext.is_activated:
                threading.Thread(target=registered_ext.ext_obj.device_disconnect).start()

    def device_rotation(self, video_coord: Coordinate):
        """
            设备旋转
        :param video_coord:
        :return:
        """
        for _, registered_ext in self.extensions.items():
            if registered_ext.is_activated:
                threading.Thread(target=registered_ext.ext_obj.device_rotation, args=(video_coord,)).start()

    def stop(self):
        """
            停止
        :return:
        """
        for _, registered_ext in self.extensions.items():
            if registered_ext.is_activated:
                threading.Thread(target=registered_ext.ext_obj.stop).start()

        self.extensions.clear()
