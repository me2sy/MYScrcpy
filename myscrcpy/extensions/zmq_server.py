# -*- coding: utf-8 -*-
"""
    ZMQ Services
    ~~~~~~~~~~~~~~~~~~
    ZMQ 相关服务

    Log:
        2024-08-04 1.1.4 Me2sY  抽离形成 extensions
"""

__author__ = 'Me2sY'
__version__ = '1.1.4'

__all__ = [
    'ZMQAudioServer', 'ZMQAudioSubscriber',
    'ZMQControlServer'
]


import zlib
import threading

from loguru import logger

try:
    import zmq
except ImportError:
    logger.warning('You need to install pyzmq before using ZMQ extension.')
    raise ImportError

from myscrcpy.controller import AudioSocketServer, RawAudioPlayer
from myscrcpy.controller import ControlSocketController

# ZMQ Audio Server


class ZMQAudioServer:
    """
        Audio Publish Server
    """

    def __init__(self, ass: AudioSocketServer, url: str = 'tcp://127.0.0.1:20520'):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(url)

        self.ass = ass

        logger.success(f"Audio ZMQ Publish Running At {url}")

    def _server_thread(self):
        while self.ass.is_running:
            self.socket.send(zlib.compress(self.ass.get_raw_frame()))
        self.socket.close()
        self.context.term()

    def start(self):
        threading.Thread(target=self._server_thread).start()


class ZMQAudioSubscriber:
    """
        Audio Subscriber
    """
    def __init__(
            self, url: str = 'tcp://127.0.0.1:20520',
            **kwargs
    ):
        self.url = url
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(url)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")

        self.player = RawAudioPlayer(**kwargs)

        self.is_playing = True

    def _play_thread(self):
        logger.success(f"ZMQAudioSubscriber Listening To {self.url}")
        while self.is_playing:
            self.player.process(zlib.decompress(self.socket.recv()))

        self.player.close()
        self.socket.close()
        self.context.term()

        logger.warning(f"{self.__class__.__name__} Closed.")

    def start(self):
        threading.Thread(target=self._play_thread).start()


# ZMQ Controller Server


class ZMQControlServer:
    """
        ZMQ Controller
        create a ZMQ pull/push socket
        send socket packet to ControlSocketController
    """

    STOP = b'Me2sYSayBye'

    def __init__(self, csc: ControlSocketController, url: str = 'tcp://127.0.0.1:55556'):
        self.csc = csc
        self.url = url
        self.is_running = False

    def _control_thread(self):
        logger.info(f"ZMQ Control Pull Running At {self.url}")

        context = zmq.Context()
        socket = context.socket(zmq.PULL)
        socket.bind(self.url)

        self.is_running = True

        while self.is_running and self.csc.is_running:
            _ = socket.recv()
            if _ == self.STOP:
                self.is_running = False
                break
            self.csc.send_packet(_)

        socket.close()
        context.term()
        logger.warning(f"ZMQ Control Pull Shutting Down")

    def start(self):
        threading.Thread(target=self._control_thread).start()

    @classmethod
    def stop(cls, url: str = 'tcp://127.0.0.1:55556'):
        cls.create_sender(url).send(cls.STOP)

    @classmethod
    def create_sender(cls, url: str = 'tcp://127.0.0.1:55556'):
        context = zmq.Context()
        sender = context.socket(zmq.PUSH)
        sender.connect(url)
        return sender
