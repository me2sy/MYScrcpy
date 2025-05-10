# -*- coding: utf-8 -*-
"""
    Video
    ~~~~~~~~~~~~~~~~~~
    视频相关类

    Log:
        2025-04-23 3.2.0 Me2sY  优化关闭逻辑，避免卡线程

        2024-09-23 1.6.0 Me2sY  新增更新 Callback 方法

        2024-09-09 1.5.8 Me2sY  新增raw_stream

        2024-08-28 1.4.0 Me2sY  优化调整功能结构

        2024-08-25 0.1.0 Me2sY  创建，分离Scrcpy.connect，Video独自连接
"""

__author__ = 'Me2sY'
__version__ = '3.2.0'

__all__ = [
    'CameraArgs', 'VideoArgs',
    'VideoAdapter'
]

import socket
import struct
import threading
import time
from dataclasses import dataclass
from typing import ClassVar, Tuple, Callable

from PIL.Image import Image
from adbutils import AdbDevice
import av
import numpy as np
from loguru import logger

from myscrcpy.core.args_cls import ScrcpyConnectArgs
from myscrcpy.core.adapter_cls import ScrcpyAdapter
from myscrcpy.core.connection import Connection
from myscrcpy.utils import Coordinate


@dataclass
class CameraArgs(ScrcpyConnectArgs):
    """
        Video Camera Args
    """
    camera_id: int = 0
    camera_fps: int = 15
    camera_ar: str | None = None
    camera_size: str | None = None

    def __post_init__(self):
        if self.camera_id < 0:
            raise ValueError('Camera ID must be > 0')
        if self.camera_fps is None or self.camera_fps <= 0:
            raise ValueError('Camera FPS must be > 0')

    def to_args(self) -> list:
        args = []
        if self.camera_id:
            args.append(f"camera_id={self.camera_id}")
        if self.camera_ar:
            args.append(f"camera_ar={self.camera_ar}")
        if self.camera_size:
            args.append(f"camera_size={self.camera_size}")
        if self.camera_fps:
            args.append(f"camera_fps={self.camera_fps}")
        return args

    @classmethod
    def load(cls, **kwargs) -> 'CameraArgs':
        return cls(
            kwargs.get('video_source') == 'camera',
            kwargs.get('camera_id', 0),
            kwargs.get('camera_fps', 15),
            kwargs.get('camera_ar', None),
            kwargs.get('camera_size', None),
        )

    def dump(self) -> dict:
        d = {}
        if self.camera_id is not None and self.camera_id >= 0:
            d['camera_id'] = self.camera_id
        if self.camera_ar:
            d['camera_ar'] = self.camera_ar
        if self.camera_size:
            d['camera_size'] = self.camera_size
        if self.camera_fps:
            d['camera_fps'] = self.camera_fps
        return d


@dataclass
class VideoArgs(ScrcpyConnectArgs):
    """
        Video Connection Args
    """

    CODEC_H264: ClassVar[str] = "h264"
    CODEC_H265: ClassVar[str] = "h265"

    SOURCE_DISPLAY: ClassVar[str] = "display"
    SOURCE_CAMERA: ClassVar[str] = "camera"

    max_size: int = 0
    fps: int = 60
    buffer_size: int = 131072
    video_codec: str = CODEC_H264
    video_source: str = SOURCE_DISPLAY
    camera: CameraArgs | None = None

    def __post_init__(self):
        if self.fps < 1:
            raise ValueError("fps must be greater than 0")

        if self.video_codec not in [self.CODEC_H264, self.CODEC_H265]:
            raise ValueError("Video codec not supported")

        if self.video_source not in [self.SOURCE_DISPLAY, self.SOURCE_CAMERA]:
            raise ValueError("Video source not supported")

    def to_args(self) -> list:
        """
            创建视频连接参数
        :return:
        """
        args = [
            f"video={'true' if self.is_activate else 'false'}",
            f"max_size={self.max_size}",
            f"max_fps={self.fps}",
            f"video_codec={self.video_codec}",
            f"video_source={self.video_source}",
        ]
        if self.video_source == VideoArgs.SOURCE_CAMERA and self.camera:
            args += self.camera.to_args()

        return args

    @classmethod
    def load(cls, **kwargs) -> 'VideoArgs':
        return cls(
            is_activate=kwargs.get('is_activate', True),
            max_size=kwargs.get("max_size", 1200),
            fps=kwargs.get("fps", 60),
            buffer_size=kwargs.get("buffer_size", 131072),
            video_codec=kwargs.get("video_codec", "h264"),
            video_source=kwargs.get("video_source", "camera"),
            camera=CameraArgs.load(**kwargs) if kwargs.get("video_source") == 'camera' else None,
        )

    def dump(self) -> dict:
        d = {
            'is_activate': self.is_activate,
            'max_size': self.max_size,
            'fps': self.fps,
            'buffer_size': self.buffer_size,
            'video_codec': self.video_codec,
            'video_source': self.video_source
        }
        if self.camera:
            d.update(self.camera.dump())
        return d


class VideoAdapter(ScrcpyAdapter):
    """
        视频适配器
    """

    CODEC_AV_MAP = {
        VideoArgs.CODEC_H264: 'h264',
        VideoArgs.CODEC_H265: 'hevc',     # FFmpeg h265 codec name is hevc
    }

    def __init__(self, connection: Connection, frame_update_callback: Callable = None):
        """
            实现视频解码，转换为 np.ndarray/av.VideoFrame/PIL.Image

        :param connection:
        """
        super().__init__(connection)

        self.frame_n = 0
        self._last_frame = None

        self.frame_update_callback: Callable = frame_update_callback

    def start(self, adb_device: AdbDevice, *args, **kwargs) -> bool:
        """
            启动解析
        :param adb_device:
        :param args:
        :param kwargs:
        :return:
        """
        if self.is_running and self.is_ready:
            return True

        # Make Connection
        if self.conn.connect(adb_device):

            # 2024-09-09 1.5.8 Me2sY  分离
            self.is_running, video_c = self.decode_header(self.conn.socket)
            if not self.is_running:
                return False

            threading.Thread(target=self.main_thread).start()
            retry = 0
            while not self.is_ready:
                if retry > 200:
                    logger.error(f"Video Got No Frame!")
                    break
                else:
                    retry = retry + 1
                    time.sleep(0.01)

                self.is_ready = not self.get_video_frame() is None

            else:
                logger.success(f"Video Socket {self.conn.scid} Connected! Codec: {video_c}")
                return True

        return False

    def stop(self):
        """
            停止进程
        :return:
        """
        self.is_running = False
        self.is_ready = False
        self._last_frame = None
        self.frame_n = 0
        self.conn.disconnect()

    @staticmethod
    def decode_header(socket_conn: socket.socket) -> Tuple[bool, Tuple[str, Coordinate] | None]:
        """
            解析 Scrcpy Stream
        :return:
        """

        _video_codec = socket_conn.recv(4).decode()

        if _video_codec is None or _video_codec == '':
            msg = '\n1.Check VideoSocket max_size\n'
            msg += '2.Check camera_ar\n'
            msg += '3.In Camera Mode, No ControlSocket SETUP Please\n'
            msg += '4.Use scrcpy --list-camera or --list-camera-sizes then choose a RIGHT ar or size or camera_id\n'
            msg += '5.Make Sure Your Android Device >= 12\n'
            msg += '6.Some Android Device NOT SUPPORTED Camera. Use Scrcpy to see the WRONG MSG.'
            logger.warning(msg)
            return False, None

        (width, height,) = struct.unpack('>II', socket_conn.recv(8))
        return True, (_video_codec, Coordinate(width, height))

    def main_thread(self):
        """
            解析主进程，读取Scrcpy视频流
        :return:
        """

        code_context = av.CodecContext.create(self.CODEC_AV_MAP.get(self.conn.args.video_codec), 'r')

        while self.is_running:
            try:
                packets = code_context.parse(self.conn.recv(self.conn.args.buffer_size))
                for packet in packets:
                    for _frame in code_context.decode(packet):
                        self._last_frame = _frame
                        self.frame_n += 1
                        if self.frame_update_callback:
                            threading.Thread(
                                target=self.frame_update_callback, args=[self._last_frame, self.frame_n]
                            ).start()

            except OSError as e:
                ...
            except Exception as e:
                logger.info(f"Exception while reading frame {self.frame_n} | {e}")
                continue

        self.is_ready = False

        logger.warning(f"{self.__class__.__name__} Main Thread {self.conn.scid} Closed.")

    def get_frame(self, _format: str = 'rgb24') -> np.ndarray | None:
        """
            获取frame
        :return:
        """
        if self.is_ready:
            return self._last_frame.to_ndarray(format=_format)
        else:
            return None

    def get_image(self) -> Image | None:
        """
            获取 Image
        :return:
        """
        if self.is_ready:
            return self._last_frame.to_image()
        else:
            return None

    def get_video_frame(self) -> av.VideoFrame | None:
        """
            获取 av.VideoFrame
        :return:
        """
        return self._last_frame

    @property
    def coordinate(self) -> Coordinate:
        """
            Video Frame Coordinate
        :return:
        """
        return Coordinate(self._last_frame.width, self._last_frame.height)

    @classmethod
    def connect(
            cls, adb_device: AdbDevice, video_args: VideoArgs, frame_update_callback: Callable = None, **kwargs
    ):
        """
            根据 VideoArgs 快速创建连接
        :param adb_device:
        :param video_args:
        :param frame_update_callback:
        :param kwargs:
        :return:
        """
        if not video_args.is_activate:
            return None

        _ = cls(Connection(video_args), frame_update_callback)
        if _.start(adb_device):
            return _
        else:
            logger.error('VideoAdapter Start Failed!')
            return None

    @classmethod
    def raw_stream(cls, adb_device: AdbDevice, video_args: VideoArgs, **kwargs) -> Connection | None:
        """
            返回原生stream
        :param adb_device:
        :param video_args:
        :param kwargs:
        :return:
        """
        conn = Connection(video_args, **kwargs)
        _f = conn.connect(adb_device, **kwargs)
        if _f:
            _f, args = cls.decode_header(conn.socket)
            if _f:
                logger.success(f"Raw Video Stream Ready! Codec: {args[0]} | {args[1]}")
                return conn

        logger.error('Raw Video Stream Start Failed!')
        return None


if __name__ == '__main__':
    """
        DEMO Here
    """
    from adbutils import adb
    dev = adb.device_list()[0]

    va = VideoAdapter.connect(dev, VideoArgs(1920))

    # av.VideoFrame
    va.get_video_frame()

    # np.ndarray
    va.get_frame()

    va.stop()

    va.start(dev)
    va.start(dev)

    print(va.get_frame())

    va.stop()
