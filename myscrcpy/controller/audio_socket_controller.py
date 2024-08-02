# -*- coding: utf-8 -*-
"""
    Audio Socket Controller
    ~~~~~~~~~~~~~~~~~~
    音频控制器，使用flac
    支持ZMQ分享

    Log:
        2024-08-02 1.1.3 Me2sY  新增 to_args 方法

        2024-08-01 1.1.2 Me2sY
            1.新增 FRAMES_PER_BUFFER 解决pyaudio Linux下声音播放异常问题
            2.新增 AudioPlayer 支持 Flac 及 通过ZMQ publish的 Raw 音乐流
            3.新增 ZMQAudioServer ZMQAudioSubscriber 支持通过ZMQ 分享 Raw 音频流

        2024-07-31 1.1.1 Me2sY  设置send_frame_meta = false 降低延迟

        2024-07-30 1.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '1.1.3'

__all__ = [
    'AudioSocketController', 'AudioSocketServer',
    'FlacAudioPlayer', 'RawAudioPlayer',
    'ZMQAudioServer', 'ZMQAudioSubscriber'
]

import queue
import threading
import zlib

import zmq
from loguru import logger

import pyaudio
import pyflac

from myscrcpy.controller.scrcpy_socket import ScrcpySocket


class AudioPlayer:
    """
        解析Audio Frame
        Scrcpy Server 2.5
    """

    RATE = 48000
    CHANNELS = 2
    FORMAT = pyaudio.paInt16
    FRAMES_PER_BUFFER = 4096

    def process(self, *args, **kwargs):
        ...

    def close(self):
        ...

    def __init__(
            self,
            audio_format: int = pyaudio.paInt16,
            *args, **kwargs
    ):
        self.audio_format = audio_format
        self.is_playing = False
        self.player = None


class FlacAudioPlayer(AudioPlayer):

    # For Scrcpy Server 2.5 Version
    # Rewrite Header Replace Scrcpy Flac METADATA
    # 详见 https://xiph.org/flac/format.html#metadata_block_streaminfo
    FLAC_METADATA = (
        b'fLaC'                             # stream Header
        b'\x80'                             # Flag + BLOCK_TYPE 0
        b'\x00\x00"'                        # Length
        b'\x04\x80'
        b'\x04\x80'
        b'\x00\x00\x00'
        b'\x00\x00\x00'
        b'\x0b\xb8\x04\xf0'                 # 48000Hz 2channel 16bps
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    )

    def decoder(self, audio_stream, sample_rate, num_channels, num_samples):
        """
            Decode Callback
        """
        self.player.write(audio_stream.tobytes())

    def __init__(self, *args, **kwargs):
        """
            if for Record
        """

        super().__init__(*args, **kwargs)

        self.player = pyaudio.PyAudio().open(
            rate=kwargs.get('rate', self.RATE),
            channels=kwargs.get('channels', self.CHANNELS),
            format=self.audio_format,
            frames_per_buffer=kwargs.get('frames_per_buffer', self.FRAMES_PER_BUFFER),
            output=True
        )

        self.stream_decoder = pyflac.StreamDecoder(self.decoder)

        # Pass FLAC Header
        # Then Process Pure Flac Frame
        self.stream_decoder.process(self.FLAC_METADATA)

    def process(self, audio_bytes: bytes):
        self.stream_decoder.process(audio_bytes)

    def close(self):
        self.stream_decoder.finish()
        self.player.close()
        self.is_playing = False
        logger.warning(f"Audio Stream Closed.")


class RawAudioPlayer(AudioPlayer):
    """
        Raw Audio Frame Player
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player = pyaudio.PyAudio().open(
            rate=kwargs.get('rate', self.RATE),
            channels=kwargs.get('channels', self.CHANNELS),
            format=kwargs.get('format', self.audio_format),
            frames_per_buffer=kwargs.get('frames_per_buffer', self.FRAMES_PER_BUFFER),
            output=True
        )
        self.is_playing = True

    def process(self, audio_bytes: bytes):
        self.player.write(audio_bytes)

    def close(self):
        self.player.close()
        self.is_playing = False
        logger.warning(f"Audio Stream Closed.")


class AudioSocketController(ScrcpySocket):
    """
        Scrcpy Server 2.5
        Audio Socket
        Use Flac Only
        Fast But Simple
    """

    SOURCE_OUTPUT = 'output'
    SOURCE_MIC = 'mic'

    AUDIO_CODEC = 'flac'

    RECEIVE_FRAMES_PER_BUFFER = 8192

    def __init__(
            self, audio_source: str = SOURCE_OUTPUT,
            **kwargs
    ):
        super().__init__(**kwargs)

        if audio_source not in [self.SOURCE_OUTPUT, self.SOURCE_MIC]:
            raise ValueError(f"Source {audio_source} not supported, only {[self.SOURCE_OUTPUT, self.SOURCE_MIC]}")
        self.audio_source = audio_source
        self.audio_player = FlacAudioPlayer()

    def close(self):
        self.is_running = False
        logger.warning(f"{self.__class__.__name__} Socket Closed.")

    def _main_thread(self):
        _audio_codec = self._conn.recv(4).decode()
        if _audio_codec != self.AUDIO_CODEC:
            raise RuntimeError(f"Audio Codec {_audio_codec} not supported!")
        logger.success(f"Audio Socket Connected! Codec: {_audio_codec}")

        # Drop Strange Flac MetaDataBlock
        self._conn.recv(34)

        while self.is_running:
            self.audio_player.process(self._conn.recv(self.RECEIVE_FRAMES_PER_BUFFER * 2))

        self.audio_player.close()
        self._conn.close()

    def start(self):
        threading.Thread(target=self._main_thread).start()

    def to_args(self) -> list:
        return [
            'audio=true',
            f"audio_codec={self.AUDIO_CODEC}",
            f"audio_source={self.audio_source}",
        ]


class AudioSocketServer(AudioSocketController):
    """
        Scrcpy Server 2.5
        Audio Socket Server
        For ZMQ Share Raw Video Frame
    """

    def decode(self, audio, sample_rate, num_channels, num_samples):
        _ = audio.tobytes()
        self.audio_raw_queue.put(_)

        if self.output:
            if not self.player:
                self.player = RawAudioPlayer(
                    rate=sample_rate, channels=num_channels, frames_per_buffer=num_samples
                )
            self.player.process(_)

    def __init__(
            self,
            output: bool = True,
            **kwargs
    ):

        super().__init__(**kwargs)

        self.flac_decode = pyflac.StreamDecoder(self.decode)
        self.flac_decode.process(FlacAudioPlayer.FLAC_METADATA)

        self.output = output
        self.player = None

        self.audio_raw_queue = queue.Queue()

        logger.warning(f"AudioSocketServer is Running! Make Sure Queue has a consumer")

    def close(self):
        self.is_running = False
        logger.warning(f"{self.__class__.__name__} Socket Closed.")

    def _main_thread(self):
        _audio_codec = self._conn.recv(4).decode()
        if _audio_codec != self.AUDIO_CODEC:
            raise RuntimeError(f"Audio Codec {_audio_codec} not supported!")
        logger.success(f"Audio Socket Connected! Codec: {_audio_codec}")

        # Drop Strange Flac MetaDataBlock
        self._conn.recv(34)

        while self.is_running:
            self.flac_decode.process(self._conn.recv(self.RECEIVE_FRAMES_PER_BUFFER))

        # Close
        if self.player:
            self.player.close()
        self.flac_decode.finish()
        self._conn.close()

    def start(self):
        threading.Thread(target=self._main_thread).start()

    def get_raw_frame(self) -> bytes:
        return self.audio_raw_queue.get()


class ZMQAudioServer:
    """
        Publish Server
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
