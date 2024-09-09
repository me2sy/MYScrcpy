# -*- coding: utf-8 -*-
"""
    文件管理器
    ~~~~~~~~~~~~~~~~~~
    

    Log:
         1.0.0 Me2sY
            创建，Windows系统支持从电脑拷贝文件至 sdcard/MYScrcpy

"""

__author__ = 'Me2sY'
__version__ = '1.0.0'

__all__ = [
    'FileManager'
]

import datetime
from pathlib import PurePosixPath, Path
from typing import List

from adbutils import AdbDevice, FileInfo
from loguru import logger
from PIL import ImageGrab

from myscrcpy.utils.params import Param


class FileManager:
    """
        文件管理器
    """

    def __init__(self, adb_device: AdbDevice, default_push_path: PurePosixPath = PurePosixPath('MYScrcpy')):
        self.adb_device = adb_device

        self.path_base = PurePosixPath('/storage/emulated/0/')
        self.path_cur = self.path_base
        self.path_push = self.path_base / default_push_path

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

    def cd(self, path: str | PurePosixPath) -> PurePosixPath:
        """
            CD
        :param path:
        :return:
        """
        _path = self.path_cur / path
        if self.adb_device.sync.exists(_path.__str__()):
            self.path_cur = PurePosixPath(self.adb_device.shell(f"cd {_path} && pwd"))
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

    def push_clipboard_to_device(self):
        """
            将剪切板内容推送至设备
        :return:
        """
        im = ImageGrab.grabclipboard()

        if im is None:
            pass

        elif isinstance(im, list):
            for _ in im:
                p = Path(_)
                if p.is_dir():
                    self.adb_device.shell(['mkdir', (self.path_push / p.name).__str__()])
                    logger.info(f"mkdir {(self.path_push / p.name).__str__()}")
                    self.push_dir(p, self.path_push / p.name)

                elif p.is_file():
                    self.push(p)
        else:
            # 截图 放置到 DCIM文件夹
            try:
                fp = Param.PATH_TEMP / ('ps_' + datetime.datetime.now().strftime('%Y%m%d%H%M%S') + '.jpg')
                with fp.open('wb') as f:
                    im.save(f, 'JPEG')
                self.push(fp, self.path_base / 'DCIM')
                fp.unlink()
            except:
                pass
