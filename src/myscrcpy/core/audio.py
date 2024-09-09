# -*- coding: utf-8 -*-
"""
    Audio
    ~~~~~~~~~~~~~~~~~~
    音频相关类

    Log:
        2024-09-09 1.5.8 Me2sY  新增raw_stream

        2024-09-05 1.5.4 Me2sY 优化pyaudio引入，适配termux

        2024-09-04 1.5.3 Me2sY
            1.新增 Opus解析
            2.重构类结构

        2024-08-31 1.4.1 Me2sY  修复Linux下缺陷

        2024-08-28 1.4.0 Me2sY  创建，优化 Player/Adapter 结构

        2024-08-25 0.1.0 Me2sY
            1.从connect中分离，独占连接
            2.预初始化播放器，降低声音延迟
"""

__author__ = 'Me2sY'
__version__ = '1.5.8'

__all__ = [
    'AudioArgs', 'AudioAdapter'
]

import abc
import pkgutil
from dataclasses import dataclass
import socket
import struct
import threading
import time
from typing import ClassVar, Callable, Mapping, List, Any

from adbutils import AdbDevice
from loguru import logger

try:
    import pyaudio
except ImportError as e:
    logger.warning(f"Import pyaudio failed: {e}")

try:
    import pyflac
except:
    ...

# pyogg.opus 提供opus解析库
# pyogg导入后会污染环境，导致pyflac无法引入！
# 需先引入FLAC
# opuslib 提供解析方法
try:
    from pyogg import opus
    import opuslib
except:
    ...

from myscrcpy.core.args_cls import ScrcpyConnectArgs
from myscrcpy.core.adapter_cls import ScrcpyAdapter
from myscrcpy.core.connection import Connection


class Player:
    """
        Audio Player
        Use pyaudio
    """

    RATE = 48000
    CHANNELS = 2
    FORMAT = pyaudio.paInt16
    FRAMES_PER_BUFFER = 512

    def __init__(self):

        self._player = None
        self.stream = None

        # Default Device
        self.device_index = None
        self.is_ready = False

        self.rate = self.RATE
        self.channels = self.CHANNELS
        self.format = self.FORMAT
        self.frames_per_buffer = self.FRAMES_PER_BUFFER
        self.output = True

    def __del__(self):
        self.stop()

    def start(self, **kwargs):
        """
            启动播放器
        :param kwargs:
        :return:
        """
        self.stop()
        self.setup_player(**kwargs)

    def setup_player(
            self,
            rate: int = None, channels: int = None,
            audio_format: int = None, frames_per_buffer: int = None,
            output: bool = None,
            device_index: int | None = None,
            **kwargs
    ):
        """
            设置播放器
        :param rate:
        :param channels:
        :param audio_format:
        :param frames_per_buffer:
        :param output:
        :param device_index:
        :param kwargs:
        :return:
        """

        try:
            self.stop()
        except OSError:
            ...
        except Exception as e:
            logger.exception(e)

        self._player = pyaudio.PyAudio()

        self.rate = rate if rate else self.rate
        self.channels = channels if channels else self.channels
        self.format = audio_format if audio_format else self.format
        self.frames_per_buffer = frames_per_buffer if frames_per_buffer else self.frames_per_buffer
        self.output = output if output is not None else self.output

        self.stream = self._player.open(
            rate=self.rate, channels=self.channels, format=self.format,
            frames_per_buffer=self.frames_per_buffer, output=self.output,
            output_device_index=device_index
        )
        self.device_index = device_index
        self.is_ready = True

    def stop(self):
        """
            停止播放进程
        :return:
        """
        self.is_ready = False

    def play(self, raw_pcm_bytes: bytes):
        """
            播放
        :param raw_pcm_bytes:
        :return:
        """
        if self.is_ready:
            self.stream.write(raw_pcm_bytes)


class AudioDecoder(metaclass=abc.ABCMeta):
    """
        解析器基类
    """

    def __init__(
            self,
            setup_player_method: Callable,
            play_method: Callable[[bytes], None],
            sample_rate: int = Player.RATE,
            channels: int = Player.CHANNELS,
            *args, **kwargs
    ):
        self.setup_player_method = setup_player_method
        self.play_method = play_method
        self.sample_rate = sample_rate
        self.channels = channels
        self.decoder = None

    def __del__(self):
        self.stop()

    def parse_audio_args(self, audio_conn: socket.socket) -> bool:
        """
            如有需要，解析音频参数
        :param audio_conn: Scrcpy Audio Socket Connection
        :return: is Parse succeeded
        """
        return True

    def call_player_to_play(self, pcm_bytes: bytes, *args, **kwargs):
        """
            Decode Callback
        :param pcm_bytes:
        :return:
        """
        try:
            self.play_method(pcm_bytes)
        except Exception as e:
            logger.warning(f"Player Error: {e}, Try Reset Player")
            self.setup_player_method(rate=self.sample_rate, channels=self.channels)

    @abc.abstractmethod
    def process(self, stream_bytes: bytes):
        """
            数据处理
        :param stream_bytes:
        :return:
        """
        raise NotImplementedError

    def stop(self):
        """
            停止进程
        :return:
        """
        ...


class RawAudioDecoder(AudioDecoder):
    """
        Raw Audio Bytes Decoder
    """

    def process(self, stream_bytes: bytes):
        """
            Raw Input
        :param stream_bytes: Raw PCM Input
        :return:
        """
        self.call_player_to_play(stream_bytes)


class OpusDecoder(AudioDecoder):
    """
        Opus Audio Stream Decoder
        use opuslib
        https://github.com/orion-labs/opuslib
    """

    def __init__(
            self,
            setup_player_method: Callable, play_method: Callable[[bytes], None],
            frame_ms: int = 50,
            *args, **kwargs
    ):
        super().__init__(setup_player_method, play_method, *args, **kwargs)
        self.frame_ms = frame_ms
        self.frame_size = int(frame_ms / 1000 * Player.RATE)

    def parse_audio_args(self, audio_conn: socket.socket) -> bool:
        """
            Decode Opus Header
            See https://wiki.xiph.org/OggOpus#ID_Header
        :param audio_conn:
        :return:
        """
        # Opus With OpusHead
        header = audio_conn.recv(8)

        # OpusHead is the Magic signature
        if header != b'OpusHead':
            logger.error(f"Not Opus Stream! {header} Received!")
            return False

        # parse Header
        # Version/Channel 2 bytes
        (version, channel,) = struct.unpack('>BB', audio_conn.recv(2))

        # Pre-skip 2 | Rate 4 | output_gain 2 | little endian
        (pre_skip, rate, output_gain,) = struct.unpack('<HIH', audio_conn.recv(8))

        # Channel mapping family 1
        (cmf, ) = struct.unpack('>B', audio_conn.recv(1))

        # set args
        self.sample_rate = rate
        self.channels = channel

        # Decode Need a Frame Size
        self.frame_size = int(self.frame_ms / 1000 * self.sample_rate)

        self.decoder = opuslib.Decoder(fs=self.sample_rate, channels=self.channels)

        logger.success(
            f"Opus Decoder Ready with SampleRate: {rate} | Channel: {channel} | FrameSize: {self.frame_size}"
        )
        return True

    def process(self, stream_bytes: bytes):
        """
            Call opuslib.Decoder().decode to decode opus stream to raw pcm bytes
        :param stream_bytes: Opus Stream bytes
        :return:
        """
        self.call_player_to_play(self.decoder.decode(stream_bytes, self.frame_size))


class FlacDecoder(AudioDecoder):

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

    def call_player_to_play(self, audio_stream, sample_rate, num_channels, num_samples):
        """
            Flac Decoder Callback
            audio_stream is numpy.ndarray, need to call tobytes()
        :param audio_stream:
        :param sample_rate:
        :param num_channels:
        :param num_samples:
        :return:
        """

        try:
            self.play_method(audio_stream.tobytes())
        except Exception as e:
            logger.warning(f"Player Error: {e}, Try Reset Player")
            self.sample_rate = sample_rate
            self.channels = num_channels
            self.setup_player_method(rate=sample_rate, channels=num_channels)

    def parse_audio_args(self, audio_conn: socket.socket) -> bool:
        """
            The flac meta_data_block kind of strange in scrcpy flac stream
            So create a normal one to init decoder
        :param audio_conn:
        :return:
        """

        # Drop Strange Flac MetaDataBlock
        audio_conn.recv(34)

        # Init decoder and process
        self.decoder = pyflac.StreamDecoder(self.call_player_to_play)
        self.decoder.process(self.FLAC_METADATA)
        return True

    def process(self, audio_stream):
        """
            call pyflac decoder to decode audio stream
        :param audio_stream:
        :return:
        """
        self.decoder.process(audio_stream)

    def stop(self):
        """
            停止进程
        :return:
        """
        try:
            del self.decoder
        except pyflac.decoder.DecoderProcessException:
            ...
        except Exception as e:
            ...


@dataclass
class AudioArgs(ScrcpyConnectArgs):
    """
        Audio Connection Args
    """

    SOURCE_OUTPUT: ClassVar[str] = 'output'
    SOURCE_MIC: ClassVar[str] = 'mic'

    CODEC_OPUS: ClassVar[str] = 'opus'
    CODEC_FLAC: ClassVar[str] = 'flac'
    CODEC_RAW: ClassVar[str] = 'raw'

    RECEIVE_FRAMES_PER_BUFFER: ClassVar[int] = 1024

    audio_source: str = SOURCE_OUTPUT
    audio_codec: str = CODEC_RAW
    device_index: int | None = None

    def __post_init__(self):
        if self.audio_source not in [self.SOURCE_OUTPUT, self.SOURCE_MIC]:
            raise ValueError(f"Invalid Audio Source: {self.audio_source}")

        if self.audio_codec not in [self.CODEC_OPUS, self.CODEC_FLAC, self.CODEC_RAW]:
            raise ValueError(f"Invalid Audio Codec: {self.audio_codec}")

        # 2024-09-04 1.5.3 Me2sY  新增引用判断
        if self.audio_codec == self.CODEC_OPUS:
            if pkgutil.find_loader('pyogg') is None or pkgutil.find_loader('opuslib') is None:
                raise ModuleNotFoundError('Opus decoder is NOT INSTALLED. Try pip install mysc[opus]')

        if self.audio_codec == self.CODEC_FLAC:
            if pkgutil.find_loader('pyflac') is None:
                raise ModuleNotFoundError('Flac decoder is NOT INSTALLED. Try pip install mysc[flac]')

    def to_args(self) -> list:
        """
            创建音频连接参数
        :return:
        """
        return [
            'audio=true',
            f"audio_codec={self.audio_codec}",
            f"audio_source={self.audio_source}"
        ]

    @classmethod
    def load(cls, **kwargs) -> 'AudioArgs':

        if kwargs.get('device_name'):
            kwargs['device_index'] = AudioAdapter.get_device_index_by_name(kwargs.get('device_name'))

        return cls(
            kwargs.get('audio_source', cls.SOURCE_OUTPUT),
            kwargs.get('audio_codec', cls.CODEC_RAW),
            kwargs.get('device_index', None),
        )


class AudioAdapter(ScrcpyAdapter):
    """
        Audio 适配器
    """

    DECODER_MAPPER = {
        AudioArgs.CODEC_RAW: RawAudioDecoder
    }

    if pkgutil.find_loader('pyogg') and pkgutil.find_loader('opuslib'):
        DECODER_MAPPER[AudioArgs.CODEC_OPUS] = OpusDecoder

    if pkgutil.find_loader('pyflac'):
        DECODER_MAPPER[AudioArgs.CODEC_FLAC] = FlacDecoder

    def __init__(self, connection: Connection):
        """
            Audio 适配器
        :param connection: 音频连接
        """
        super().__init__(connection)
        self.player = Player()
        self.decoder = None
        self.mute = False

    def start(self, adb_device: AdbDevice,  *args, **kwargs) -> bool:
        """
            启动连接
        :param adb_device:
        :param args:
        :param kwargs:
        :return:
        """

        if self.is_running:
            return True

        # 初始化播放器，降低播放延迟
        self.player.start()

        # 初始化解码器
        self.decoder = self.DECODER_MAPPER.get(self.conn.args.audio_codec, lambda *args, **kwargs: ...)(
            self.player.setup_player, self.player.play, *args, **kwargs
        )

        if self.conn.connect(adb_device):
            self.is_running = True
        else:
            return False

        threading.Thread(target=self.main_thread).start()

        return True

    def main_thread(self):
        """
            主进程
        :return:
        """

        # Connect Detect
        _audio_codec = self.conn.recv(4).replace(b'\x00', b'').decode()
        if _audio_codec.lower() not in [
            AudioArgs.CODEC_OPUS, AudioArgs.CODEC_FLAC, AudioArgs.CODEC_RAW
        ] or _audio_codec != self.conn.args.audio_codec:
            self.is_running = False
            logger.error(f"Invalid Audio Codec: {_audio_codec}")
            return False

        logger.success(f"Audio Socket {self.conn.scid} Connected! Codec: {_audio_codec}")
        self.is_ready = True

        self.decoder.parse_audio_args(self.conn)

        while self.is_running:
            try:
                _ = self.conn.recv(AudioArgs.RECEIVE_FRAMES_PER_BUFFER * 2)
                not self.mute and self.decoder.process(_)
            except:
                ...

        logger.warning(f"{self.__class__.__name__} Main Thread {self.conn.scid} Closed.")

    def stop(self):
        """
            结束进程
        :return:
        """
        self.is_running = False
        self.is_ready = False
        self.decoder.stop()
        self.player.stop()
        self.conn.disconnect()

    def set_mute(self, mute: bool):
        """
            设置静音
        :param mute:
        :return:
        """
        self.mute = mute

    def switch_mute(self):
        """
            切换静音
        :return:
        """
        self.mute = not self.mute

    def select_device(self, device_index: int | None, **kwargs):
        """
            设置播放设备
        :param device_index:
        :return:
        """
        # 保存解析状态并暂停解析
        _mute = self.mute
        self.set_mute(True)

        # 切换播放源
        self.player.setup_player(device_index=device_index, **kwargs)

        # 恢复暂停状态
        self.set_mute(_mute)

    @property
    def current_output_device_info(self) -> Mapping | None:
        """
            获取当前外放设备信息
        :return:
        """
        if not self.is_ready:
            return None

        if self.player.device_index is None:
            _p = pyaudio.PyAudio()
            self.player.device_index = _p.get_default_output_device_info()['index']
            _p.terminate()

        return AudioAdapter.get_output_device_info_by_index(self.player.device_index)

    @staticmethod
    def get_output_devices() -> List[Mapping]:
        """
            获取播放设备信息列表
        :return:
        """
        _p = pyaudio.PyAudio()
        _devices = []
        for index in range(_p.get_device_count()):
            info = _p.get_device_info_by_index(index)
            if info['maxOutputChannels'] > 0 and info['hostApi'] == 0:
                _devices.append(info)
        _p.terminate()
        return _devices

    @staticmethod
    def get_device_index_by_name(device_name: str) -> int | None:
        """
            通过设备名获取设备Index
        :param device_name:
        :return:
        """
        _devices = AudioAdapter.get_output_devices()
        for _ in _devices:
            if _['name'] == device_name:
                return _['index']
        return None

    @staticmethod
    def get_output_device_info_by_index(index: int) -> Mapping[str, Any] | None:
        """
            获取设备信息
        :param index:
        :return:
        """
        devices = AudioAdapter.get_output_devices()
        for device in devices:
            if device['index'] == index:
                return device
        return None

    @classmethod
    def connect(cls, adb_device: AdbDevice, audio_args: AudioArgs, **kwargs) -> 'AudioAdapter':
        """
            根据 AudioArgs 快速创建连接
        :param adb_device:
        :param audio_args:
        :param kwargs:
        :return:
        """
        _ = cls(Connection(audio_args))
        if _.start(adb_device, **kwargs):
            return _
        else:
            logger.error('AudioAdapter Start Failed!')
            return None

    @classmethod
    def raw_stream(cls, adb_device: AdbDevice, audio_args: AudioArgs, **kwargs) -> Connection | None:
        """
            原生stream
        :param adb_device:
        :param audio_args:
        :param kwargs:
        :return:
        """
        conn = Connection(audio_args, **kwargs)
        _f = conn.connect(adb_device, **kwargs)
        if _f:
            logger.success(f"Raw Audio Stream Ready!")
            return conn

        logger.error(f"Raw Audio Stream Start Failed!")
        return None


if __name__ == '__main__':
    """
        DEMO Here
    """
    from adbutils import adb
    d = adb.device_list()[0]

    aa1 = AudioAdapter.connect(d, AudioArgs(audio_codec=AudioArgs.CODEC_FLAC, audio_source=AudioArgs.SOURCE_MIC))

    time.sleep(5)

    aa1.stop()
