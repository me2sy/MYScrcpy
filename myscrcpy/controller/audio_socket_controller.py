# -*- coding: utf-8 -*-
"""
    Audio Socket Controller
    ~~~~~~~~~~~~~~~~~~
    音频控制器，使用flac

    Log:
        2024-08-19 1.1.6 Me2sY
            1.临时废弃 AudioSocketServer
            2.新增 Output Device，支持选择声音输出设备功能，方便使用VB-Audio 虚拟麦克风输入

        2024-08-15 1.1.5 Me2sY  新增静音方法

        2024-08-04 1.1.4 Me2sY  抽离ZMQ相关, 形成Core结构

        2024-08-02 1.1.3 Me2sY  新增 to_args 方法

        2024-08-01 1.1.2 Me2sY
            1.新增 FRAMES_PER_BUFFER 解决pyaudio Linux下声音播放异常问题
            2.新增 AudioPlayer 支持 Flac 及 通过ZMQ publish的 Raw 音乐流
            3.新增 ZMQAudioServer ZMQAudioSubscriber 支持通过ZMQ 分享 Raw 音频流

        2024-07-31 1.1.1 Me2sY  设置send_frame_meta = false 降低延迟

        2024-07-30 1.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '1.1.6'

__all__ = [
    'AudioSocketController', 'AudioSocketServer',
    'FlacAudioPlayer', 'RawAudioPlayer'
]

import threading
from typing import List, Set, Any, Dict, Mapping

from loguru import logger

import pyaudio
import pyflac

from myscrcpy.controller.scrcpy_socket import ScrcpySocket


class AudioPlayer:
    """
        解析Audio Frame
        Scrcpy Server 2.6.1
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
        self.output_device_index = pyaudio.PyAudio().get_default_output_device_info()['index']
        self.mute = False

    def set_mute(self, mute: bool):
        self.mute = mute

    def switch_mute(self):
        self.mute = not self.mute

    @staticmethod
    def output_devices() -> Dict[int, str]:
        """
            获取播放设备列表
        :return:
        """
        devices = {}
        p = pyaudio.PyAudio()
        for index in range(p.get_device_count()):
            dev = p.get_device_info_by_index(index)
            if dev['maxOutputChannels'] > 0 and dev['hostApi'] == 0:
                devices[dev['index']] = dev['name']
        return devices

    @staticmethod
    def default_output_device_index() -> int:
        return pyaudio.PyAudio().get_default_output_device_info()['index']

    def setup_player(
            self,
            rate: int = RATE, channels: int = CHANNELS,
            audio_format: int = FORMAT, frames_per_buffer: int = FRAMES_PER_BUFFER,
            output: bool = True, output_device_index: int = -1, *args, **kwargs
    ):
        """
            设置播放器
        :param rate:
        :param channels:
        :param audio_format:
        :param frames_per_buffer:
        :param output:
        :param output_device_index:
        :param args:
        :param kwargs:
        :return:
        """

        output_device_index = output_device_index if output_device_index >= 0 else self.default_output_device_index()

        self.output_device_index = output_device_index

        self.player = pyaudio.PyAudio().open(
            rate=rate, channels=channels, format=audio_format,
            frames_per_buffer=frames_per_buffer, output=output,
            output_device_index=output_device_index
        )

    @property
    def output_device(self) -> Mapping:
        """
            获取当前外放设备信息
        :return:
        """
        return pyaudio.PyAudio().get_device_info_by_index(self.output_device_index)


class FlacAudioPlayer(AudioPlayer):

    # For Scrcpy Server 2.6.1 Version
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
        if self.mute:
            return
        try:
            self.player.write(audio_stream.tobytes())
        except Exception as e:
            logger.warning(f"Player Error: {e}, Try Reset Player")
            self.setup_player()

    def __init__(self, *args, **kwargs):
        """
            Flac Audio Player
        """

        super().__init__(*args, **kwargs)

        self.setup_player(**kwargs)

        self.stream_decoder = pyflac.StreamDecoder(self.decoder)

        # Pass FLAC Header
        # Then Process Pure Flac Frame
        self.stream_decoder.process(self.FLAC_METADATA)

    def process(self, audio_bytes: bytes):
        """
            处理回测Audio数据
        :param audio_bytes:
        :return:
        """
        self.stream_decoder.process(audio_bytes)

    def close(self):
        try:
            self.stream_decoder.finish()
        except pyflac.decoder.DecoderProcessException as e:
            pass
        self.player.close()
        self.is_playing = False
        logger.warning(f"Audio Stream Closed.")


class RawAudioPlayer(AudioPlayer):
    """
        Raw Audio Frame Player
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_player(**kwargs)
        self.is_playing = True

    def process(self, audio_bytes: bytes):
        if self.mute:
            return
        self.player.write(audio_bytes)

    def close(self):
        self.player.close()
        self.is_playing = False
        logger.warning(f"Audio Stream Closed.")


class AudioSocketController(ScrcpySocket):
    """
        Scrcpy Server 2.6.1
        Audio Socket
        2024-08-19 1.1.6 Me2sY
            Support Raw and Flac
    """

    SOURCE_OUTPUT = 'output'
    SOURCE_MIC = 'mic'

    AUDIO_CODEC_FLAC = 'flac'
    AUDIO_CODEC_RAW = 'raw'

    RECEIVE_FRAMES_PER_BUFFER = 4096

    def __init__(
            self,
            audio_source: str = SOURCE_OUTPUT,
            audio_codec: str = AUDIO_CODEC_FLAC,
            output_device_index: int = -1,
            **kwargs
    ):
        super().__init__(**kwargs)

        if audio_source not in [self.SOURCE_OUTPUT, self.SOURCE_MIC]:
            raise ValueError(f"Source {audio_source} not supported, only {[self.SOURCE_OUTPUT, self.SOURCE_MIC]}")
        self.audio_source = audio_source
        self.audio_codec = audio_codec
        self.audio_player = {
            self.AUDIO_CODEC_FLAC: FlacAudioPlayer,
            self.AUDIO_CODEC_RAW: RawAudioPlayer
        }.get(self.audio_codec)(output_device_index=output_device_index)

    def set_mute(self, mute: bool):
        self.audio_player.set_mute(mute)

    def switch_mute(self):
        self.audio_player.switch_mute()

    def close(self):
        self.is_running = False

    def _main_thread(self):
        _audio_codec = self._conn.recv(4).replace(b'\x00', b'').decode()
        if _audio_codec not in [self.AUDIO_CODEC_FLAC, self.AUDIO_CODEC_RAW] or _audio_codec != self.audio_codec:
            raise RuntimeError(f"Invalid Audio Codec: {_audio_codec}")

        logger.success(f"Audio Socket Connected! Codec: {_audio_codec}")

        # IF Flac, Drop Strange Flac MetaDataBlock
        if self.audio_codec == self.AUDIO_CODEC_FLAC:
            self._conn.recv(34)

        while self.is_running:
            self.audio_player.process(self._conn.recv(self.RECEIVE_FRAMES_PER_BUFFER * 2))

        self.audio_player.close()
        self._conn.close()
        logger.warning(f"{self.__class__.__name__} Socket Closed.")

    def start(self) -> bool:
        threading.Thread(target=self._main_thread).start()
        return True

    def to_args(self) -> list:
        return [
            'audio=true',
            f"audio_codec={self.audio_codec}",
            f"audio_source={self.audio_source}",
        ]

    def select_player(self, output_device_index: int = -1, **kwargs):
        """
            设置播放设备
        :param output_device_index: 外放设备Index
        :param kwargs:
        :return:
        """
        self.audio_player.setup_player(output_device_index=output_device_index, **kwargs)

    @staticmethod
    def output_devices() -> Dict[int, str]:
        """
            获取外放设备列表
        :return: 外放设备列表
        """
        return AudioPlayer.output_devices()

    @staticmethod
    def default_output_device_index() -> int:
        return AudioPlayer.default_output_device_index()


class AudioSocketServer(AudioSocketController):
    """
        Scrcpy Server 2.6.1
        Audio Socket Server
        For ZMQ Share Raw Video Frame
        # TODO 2024-08-19 Me2sY 改造
    """
    # raise NotImplementedError
    ...
