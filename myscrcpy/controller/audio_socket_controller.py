# -*- coding: utf-8 -*-
"""
    Audio Socket Controller
    ~~~~~~~~~~~~~~~~~~
    音频控制器，使用flac

    Log:
        2024-07-30 1.1.0 Me2sY
            创建

"""

__author__ = 'Me2sY'
__version__ = '1.1.0'

__all__ = [
    'AudioSocketController'
]

import threading

from loguru import logger

import pyaudio
import pyflac

from myscrcpy.controller.scrcpy_socket import ScrcpySocket


class AudioSocketController(ScrcpySocket):
    """
        Scrcpy Server 2.5
        Audio Socket
        Use Flac Only
    """

    SOURCE_OUTPUT = 'output'
    SOURCE_MIC = 'mic'

    # Wrong Steaminfo but can RUN.
    # Replace Scrcpy Flac METADATA
    FLAC_METADATA_STEAMINFO = b'\x00\x00\x00"\x04\x80\x04\x80\x00\x00\x00\x00\x00\x00\n\xc4B\xf0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    FLAC_METADATA_COMMENT = b'\x84\x00\x00\x00'
    FLAC_METADATA = b'fLaC' + FLAC_METADATA_STEAMINFO + FLAC_METADATA_COMMENT

    RATE = 48000
    CHANNELS = 2
    FORMAT = pyaudio.paInt16

    def __init__(
            self,
            audio_source: str = 'output',
            audio_output: bool = True,
            **kwargs
    ):
        super().__init__(**kwargs)

        self.audio_codec = 'flac'

        if audio_source not in [self.SOURCE_OUTPUT, self.SOURCE_MIC]:
            raise ValueError(f"Source {audio_source} not supported, only {[self.SOURCE_OUTPUT, self.SOURCE_MIC]}")
        self.audio_source = audio_source

        self.audio_output = audio_output

        self.player = pyaudio.PyAudio().open(
            rate=self.RATE, channels=self.CHANNELS, format=pyaudio.paInt16,
            output=self.audio_output
        )
        self.flac_steam_decoder = pyflac.StreamDecoder(self.decode_callback)

    def close(self):
        self.is_running = False
        logger.warning(f"{self.__class__.__name__} Socket Closed.")

    def decode_callback(self, audio, sample_rate, num_channels, num_samples):
        self.player.write(audio.tobytes())

    def _main_thread(self):
        _audio_codec = self._conn.recv(4).decode()
        if _audio_codec != self.audio_codec:
            raise RuntimeError(f"Audio Codec {_audio_codec} not supported!")
        logger.success(f"Audio Socket Connected! Codec: {_audio_codec}")

        # Drop Strange Flac MetaDataBlock
        self.decode_packet()

        self.flac_steam_decoder.process(self.FLAC_METADATA)

        while self.is_running:
            self.flac_steam_decoder.process(self.decode_packet())

        self.flac_steam_decoder.finish()
        self.player.close()
        self._conn.close()

    def start(self):
        threading.Thread(target=self._main_thread).start()
