# -*- coding: utf-8 -*-
"""
    Audio
    ~~~~~~~~~~~~~~~~~~
    音频相关类

    Log:
        2024-08-28 1.4.0 Me2sY  创建，优化 Player/Adapter 结构

        2024-08-25 0.1.0 Me2sY
            1.从connect中分离，独占连接
            2.预初始化播放器，降低声音延迟
"""

__author__ = 'Me2sY'
__version__ = '1.4.0'

__all__ = [
    'AudioArgs', 'AudioAdapter'
]

import threading
import time
from dataclasses import dataclass
from typing import ClassVar, Callable, Mapping, List, Any

from adbutils import AdbDevice
from loguru import logger
import pyaudio
import pyflac

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
            rate: int = RATE, channels: int = CHANNELS,
            audio_format: int = FORMAT, frames_per_buffer: int = FRAMES_PER_BUFFER,
            output: bool = True,
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

        self.stream = self._player.open(
            rate=rate, channels=channels, format=audio_format,
            frames_per_buffer=frames_per_buffer, output=output,
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
        try:
            if self.stream is not None:
                self.stream.stop_stream()
                self.stream.close()
        except OSError:
            ...

        try:
            if self._player:
                self._player.terminate()
        except:
            ...

    def play(self, audio_bytes: bytes):
        """
            播放
        :param audio_bytes:
        :return:
        """
        if self.is_ready:
            self.stream.write(audio_bytes)


class RawDecoder:
    """
        Raw Audio Bytes Decoder
    """

    def __init__(
            self,
            setup_player_method: Callable,
            play_method: Callable[[bytes], None],
    ):
        self.setup_player_method = setup_player_method
        self.play_method = play_method

    def decoder(self, audio_bytes: bytes):
        """
            Decode Callback
        :param audio_bytes:
        :return:
        """
        try:
            self.play_method(audio_bytes)
        except Exception as e:
            logger.warning(f"Player Error: {e}, Try Reset Player")
            self.setup_player_method()

    def process(self, audio_bytes: bytes):
        """
            与Flac保持结构一致
        :param audio_bytes:
        :return:
        """
        self.decoder(audio_bytes)

    def stop(self):
        """
            与Flac保持结构一致
        :return:
        """
        ...


class FlacDecoder:

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
        try:
            self.play_method(audio_stream.tobytes())
        except Exception as e:
            logger.warning(f"Player Error: {e}, Try Reset Player")
            self.setup_player_method()

    def __init__(
            self,
            setup_player_method: Callable,
            play_method: Callable[[bytes], None],
    ):
        self.setup_player_method = setup_player_method
        self.play_method = play_method
        self.stream_decoder = pyflac.StreamDecoder(self.decoder)

    def __del__(self):
        self.stop()

    def process(self, audio_bytes: bytes):
        """
            处理原数据
        :param audio_bytes:
        :return:
        """
        self.stream_decoder.process(audio_bytes)

    def stop(self):
        """
            停止进程
        :return:
        """
        try:
            del self.stream_decoder
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

    CODEC_FLAC: ClassVar[str] = 'flac'
    CODEC_RAW: ClassVar[str] = 'raw'

    RECEIVE_FRAMES_PER_BUFFER: ClassVar[int] = 1024

    audio_source: str = SOURCE_OUTPUT
    audio_codec: str = CODEC_FLAC
    device_index: int | None = None

    def __post_init__(self):
        if self.audio_source not in [self.SOURCE_OUTPUT, self.SOURCE_MIC]:
            raise ValueError(f"Invalid Audio Source: {self.audio_source}")

        # if self.audio_codec not in [self.CODEC_FLAC, self.CODEC_RAW]:
        #     raise ValueError(f"Invalid Audio Codec: {self.audio_codec}")


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
            kwargs.get('audio_codec', cls.CODEC_FLAC),
            kwargs.get('device_index', None),
        )


class AudioAdapter(ScrcpyAdapter):
    """
        Audio 适配器
    """

    DECODER_MAP = {
        AudioArgs.CODEC_FLAC: FlacDecoder,
        AudioArgs.CODEC_RAW: RawDecoder,
    }

    def __init__(self, connection: Connection):
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
        self.decoder = self.DECODER_MAP.get(self.conn.args.audio_codec, lambda: ...)(
            self.player.setup_player, self.player.play
        )

        if self.conn.connect(adb_device, ['video=false', 'control=false']):
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
        _audio_codec = self.conn.recv(4).replace(b'\x00', b'').decode()
        if _audio_codec not in [
            AudioArgs.CODEC_FLAC, AudioArgs.CODEC_RAW
        ] or _audio_codec != self.conn.args.audio_codec:

            self.is_running = False
            logger.error(f"Invalid Audio Codec: {_audio_codec}")
            return False

        logger.success(f"Audio Socket {self.conn.scid} Connected! Codec: {_audio_codec}")
        self.is_ready = True

        # IF Flac, Drop Strange Flac MetaDataBlock
        if self.conn.args.audio_codec == AudioArgs.CODEC_FLAC:
            self.conn.recv(34)
            self.decoder.process(FlacDecoder.FLAC_METADATA)

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
    def current_output_device_info(self) -> int | None:
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


if __name__ == '__main__':
    """
        DEMO Here
    """
    from adbutils import adb
    d = adb.device_list()[0]

    aa1 = AudioAdapter.connect(d, AudioArgs(audio_codec=AudioArgs.CODEC_FLAC))
    aa2 = AudioAdapter.connect(d, AudioArgs(audio_codec=AudioArgs.CODEC_RAW, audio_source=AudioArgs.SOURCE_MIC))
    logger.info(f"{aa1.current_output_device_info}")

    time.sleep(10)

    aa1.stop()
    aa2.stop()
