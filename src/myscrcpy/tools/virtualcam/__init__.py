# -*- coding: utf-8 -*-
"""
    Virtual Camera
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-09-08 1.0.0 Me2sY 创建
"""

__author__ = 'Me2sY'
__version__ = '1.0.0'

__all__ = ['VirtualCam']

import threading
import time

import click
import numpy as np
from loguru import logger

try:
    import pyvirtualcam as pvc

except ImportError:
    raise ImportError('pyvirtualcam is not installed')

from myscrcpy.core import Session, VideoArgs, CameraArgs
from myscrcpy.utils import Coordinate


class VirtualCam:
    """
        虚拟摄像头
        使用 pyvirtualcam
    """

    # OBS Virtual Camera
    # Win / macOS
    BACKEND_OBS = 'obs'

    # UnityCapture
    # Win
    # https://github.com/schellingb/UnityCapture
    BACKEND_UNITY_CAPTURE = 'unitycapture'

    # Linux
    BACKEND_V4L2LOOPBACK = 'v4l2loopback'

    # Auto
    BACKEND_AUTO = None

    def __init__(self, session: Session):
        self.session: Session = session

        self.is_running = False
        self.is_paused = False

    def __del__(self):
        self.is_running = False

    def run(self, backend: str = BACKEND_AUTO):
        """
            运行
        :param backend:
        :return:
        """
        if not (self.session and self.session.is_video_ready):
            logger.warning('Video Not Ready')
            return False

        _c = self.session.va.coordinate

        cam = pvc.Camera(**_c.d, fps=self.session.va.conn.args.fps, backend=backend)

        self.is_running = True

        logger.success(f"Virtual Camera Running | VideoArgs: {_c}")

        while self.session.va.is_running and self.is_running:
            if not self.is_paused:
                try:
                    cam.send(self.session.va.get_video_frame().to_ndarray(format='rgb24'))
                except ValueError as e:
                    vf = self.session.va.get_video_frame()
                    _nc = Coordinate(vf.width, vf.height)
                    if vf.width != _c.width or vf.height != _c.height:
                        logger.warning(f"Device Rotation {_c} => {_nc}")
                        cam.close()
                        time.sleep(0.5)
                        _c = _nc
                        cam = pvc.Camera(**_c.d, fps=self.session.va.conn.args.fps, backend=backend)
                        continue
                    else:
                        self.is_running = False
                        logger.warning(f"Virtual Camera Error: {e}")
                        break

                except Exception as e:
                    self.is_running = False
                    logger.warning(f"Virtual Camera Error: {e}")
                    break

            cam.sleep_until_next_frame()

        cam.send(
            np.full((_c.height, _c.width, 3), 0, dtype=np.uint8)
        )
        self.is_running = False
        logger.warning('Virtual Camera Stopped')

    def switch_pause(self):
        """
            暂停
        :return:
        """
        self.is_paused = not self.is_paused
        logger.info(f"Virtual Camera {'Paused' if self.is_paused else 'Playing'}")

    def start(self, backend: str = BACKEND_AUTO) -> 'VirtualCam':
        """
            线程启动，非阻塞
        :param backend:
        :return:
        """
        threading.Thread(target=self.run, args=(backend, )).start()
        return self

    def stop(self):
        """
            停止
        :return:
        """
        self.is_running = False


@click.command()
@click.option('--device_serial', default=None, help='Device Serial Number')
@click.option('--max-size', type=click.IntRange(min=0), default=0, help='Video Max Size. 0 is use device size')
@click.option('--fps', type=click.IntRange(min=1, max=120), default=30, help='fps')
@click.option(
    '--source', type=click.Choice([
        VideoArgs.SOURCE_DISPLAY, VideoArgs.SOURCE_CAMERA
    ]), default=VideoArgs.SOURCE_DISPLAY,
    help=f"Choose a video source"
)
@click.option(
    '--camera-id', default=0, help='If Camera, then pass a Camera ID'
)
@click.option(
    '--backend', type=click.Choice([
        VirtualCam.BACKEND_OBS, VirtualCam.BACKEND_UNITY_CAPTURE, VirtualCam.BACKEND_V4L2LOOPBACK
    ]), default=None,
    help=f"Backend to use"
)
@click.option(
    '--config', type=click.Path(exists=True, dir_okay=False, writable=True, resolve_path=True),
    default=None, help='Load Configuration File. Define a json file First!'
)
def cli(device_serial: str, max_size: int, fps: int, source: str, camera_id: int, backend: str, config: str = None):
    """
        Start a sess and run
    :param max_size:
    :param fps:
    :param backend:
    :param device_serial:
    :return:
    """

    from adbutils import adb

    if device_serial is None and len(adb.device_list()) > 1:
        logger.warning(f"More Than One Device! Pass a device_serial to connect one")
        for _ in adb.device_list():
            logger.info(f"--device_serial {_.serial}")
        return

    if config:
        # Load Config
        import pathlib
        import json
        va = VideoArgs.load(**json.load(pathlib.Path(config).open('r')))
    else:
        va = VideoArgs(max_size=max_size, fps=fps, video_source=source, camera=CameraArgs(camera_id))

    sess = Session(adb_device=adb.device(serial=device_serial), video_args=va)

    vc = VirtualCam(sess).start(backend=backend)

    try:
        while sess.is_running and vc.is_running:
            time.sleep(0.0001)
    except KeyboardInterrupt:
        ...

    vc.stop()
    sess.disconnect()
