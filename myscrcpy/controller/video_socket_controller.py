# -*- coding: utf-8 -*-
"""
    Video Socket Controller
    ~~~~~~~~~~~~~~~~~~
    视频控制器，支持h264 h265(hevc)

    Log:
        2024-08-19 1.1.5 Me2sY 修复部分缺陷，新增未启动判断

        2024-08-04 1.1.4 Me2sY
            1.支持 h265
            2.更换 pyav 至 av

        2024-08-02 1.1.3 Me2sY
            1.新增 VideoCamera 用于控制相机视频流
            2.新增 to_args 方法

        2024-07-31 1.1.1 Me2sY
            1.send_frame_meta=false 降低数据包解析延迟
            2.修复 MacOS下 share_memory文件名限制31长度下的缺陷，缩短shm文件名长度

        2024-07-30 1.1.0 Me2sY 抽离，形成发布初版
"""

__author__ = 'Me2sY'
__version__ = '1.1.5'

__all__ = [
    'VideoSocketController', 'VideoStream', 'VideoCamera'
]

import datetime
import time
import struct
from multiprocessing import shared_memory
from copy import copy
import threading
import random

from loguru import logger

import numpy as np
import av

from myscrcpy.utils import Coordinate, Param
from myscrcpy.controller.scrcpy_socket import ScrcpySocket


class VideoStream:
    """
        Shared Memory Frame
    """

    def __init__(self, shm: shared_memory.SharedMemory):
        self._shm = shm

        c = self.coordinate
        self._frame_v = np.ndarray(
            (c.max_size, c.min_size, 3), dtype=np.uint8, buffer=shm.buf[8:]
        )
        self._frame_h = np.ndarray(
            (c.min_size, c.max_size, 3), dtype=np.uint8, buffer=shm.buf[8:]
        )
        self.frame_id = -1

    @property
    def coordinate(self):
        self.frame_id, h, w = struct.unpack('>IHH', self._shm.buf[:8])
        return Coordinate(w, h)

    def get_frame(self) -> np.ndarray:
        c = self.coordinate
        if self.frame_id == 0:
            raise RuntimeError(f"VideoStream Closed!")
        if c.rotation == Param.ROTATION_VERTICAL:
            return self._frame_v
        else:
            return self._frame_h

    @classmethod
    def create_by_name(cls, shm_name: str) -> 'VideoStream':
        return cls(shared_memory.SharedMemory(shm_name))


class VideoCamera:
    """
        定义Camera对象，读取Camera视频流
    """
    def __init__(
            self,
            camera_id: int = 0,
            camera_ar: str = None,
            camera_size: str = None,
            camera_fps: int = 30,
            **kwargs
    ):
        self.camera_id = int(camera_id)
        self.camera_ar = str(camera_ar)
        self.camera_size = str(camera_size)
        self.camera_fps = int(camera_fps)

    def to_args(self) -> list:
        args = [f"camera_id={self.camera_id}"]

        if self.camera_size:
            args.append(f"camera_size={self.camera_size}")
        elif self.camera_ar:
            args.append(f"camera_ar={self.camera_ar}")

        if self.camera_fps > 0:
            args.append(f"camera_fps={self.camera_fps}")

        return args


class VideoSocketController(ScrcpySocket):
    """
        Scrcpy Server 2.6.1
        Video Socket
        支持 h264/h265(hevc)
    """

    SOURCE_DISPLAY = 'display'
    SOURCE_CAMERA = 'camera'

    CODEC_H264 = 'h264'
    CODEC_H265 = 'h265'

    CODEC_AV_MAP = {
        CODEC_H264: 'h264',
        CODEC_H265: 'hevc',     # FFmpeg h265 codec name is hevc
    }

    def __init__(
            self,
            max_size: int | None,
            fps: int = 60,
            buffer_size: int = 131072,
            video_codec: str = CODEC_H264,
            camera: VideoCamera | None = None,
            **kwargs
    ):
        super().__init__(**kwargs)

        # 连接属性
        self.max_size = max_size
        self.fps = fps
        self.buffer_size = buffer_size
        self.video_codec = video_codec

        if isinstance(camera, VideoCamera):
            self.video_source = self.SOURCE_CAMERA
            self.camera = camera
        else:
            self.video_source = self.SOURCE_DISPLAY
            self.camera = None

        # 创建解码器
        self.code_context = av.CodecContext.create(self.CODEC_AV_MAP.get(self.video_codec), 'r')

        # 视频相关
        self.video_shm = None
        self.frame_n = 0
        self.last_frame = None

    @property
    def coordinate(self) -> Coordinate:
        """
            Video Frame Coordinate
        """
        return Coordinate(width=self.last_frame.shape[1], height=self.last_frame.shape[0])

    def _main_thread(self):
        _video_codec = self._conn.recv(4).decode()

        if _video_codec is None or _video_codec == '':
            msg = '\n1.Check VideoSocket max_size\n'
            msg += '2.Check camera_ar\n'
            msg += '3.In Camera Mode, No ControlSocket SETUP Please\n'
            msg += '4.Use scrcpy --list-camera or --list-camera-sizes then choose a RIGHT ar or size or camera_id\n'
            msg += '5.Make Sure Your Android Device >= 12\n'
            msg += '6.Some Android Device NOT SUPPORTED Camera. Use Scrcpy to see the WRONG MSG.'
            self.is_running = False
            raise RuntimeError(msg)

        if _video_codec != self.video_codec:
            self.is_running = False
            raise RuntimeError(f"Video Codec >{_video_codec}< not supported!")

        (width, height,) = struct.unpack('>II', self._conn.recv(8))
        logger.success(f"Video Socket Connected! {_video_codec} | Width: {width}, Height: {height}")

        self._conn.setblocking(False)

        while self.is_running:
            try:
                packets = self.code_context.parse(self._conn.recv(self.buffer_size))
                for packet in packets:
                    for _frame in self.code_context.decode(packet):
                        self.last_frame = _frame.to_ndarray(format='rgb24')
                        self.frame_n += 1
            except Exception:
                continue
        self._conn.close()
        logger.warning(f"{self.__class__.__name__} Socket Closed.")

    def create_shared_frame(self, size: int):
        """
            创建SharedFrame
        """
        f_name = f"vf_{datetime.datetime.now().strftime('%m%d%H%M%S')}_{random.randrange(10000, 99999)}"
        try:
            self.video_shm = shared_memory.SharedMemory(name=f_name, create=True, size=size)
        except FileExistsError:
            logger.warning(f"{f_name} Shared Frame Already Exists")
            self.video_shm = shared_memory.SharedMemory(name=f_name)

        logger.success(f"Video Socket share_memory created! name: > {self.video_shm.name} <")

    def _share_thread(self):
        """
            共享画面线程
        """
        logger.info("Start Shared Thread")
        while self.frame_n == 0:
            time.sleep(0.001)

        self.create_shared_frame(self.last_frame.nbytes + 8)

        n = 0
        while self.is_running:
            if n != self.frame_n:
                self.video_shm.buf[:] = struct.pack(
                    '>IHH',
                    self.frame_n, self.last_frame.shape[0], self.last_frame.shape[1]
                ) + self.last_frame.tobytes()
                n = copy(self.frame_n)
            else:
                time.sleep(0.00001)
        self.video_shm.buf[:4] = struct.pack('>I', 0)
        _name = self.video_shm.name
        self.video_shm.close()
        self.video_shm.unlink()
        logger.warning(f"Video Shared Thread Closed!")

    def get_frame(self) -> np.ndarray:
        return self.last_frame

    def _start_thread(self):
        threading.Thread(target=self._main_thread).start()
        threading.Thread(target=self._share_thread).start()

    def start(self) -> bool:
        wait_n = 2 * 10
        if self.is_running:
            self._start_thread()
            while self.get_frame() is None:
                time.sleep(0.1)
                wait_n -= 1
                if wait_n == 0:
                    logger.warning(f"Video Socket Not Connected!")
                    self.is_running = False
                    return False
            return True
        else:
            logger.warning(f"Video Socket Connection Not Ready!")
            return False

    def close(self):
        self.is_running = False

    def to_args(self) -> list:
        args = [
            'video=true',
            f"max_size={self.max_size}",
            f"max_fps={self.fps}",
            f"video_codec={self.video_codec}",
            f"video_source={self.video_source}",
        ]
        if self.camera:
            args += self.camera.to_args()

        return args
