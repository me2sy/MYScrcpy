# -*- coding: utf-8 -*-
"""
    An Unlocker for Ubuntu 24.04 with X11
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Use xset to get pc status
    use xdotool to input password and switch desktop

    Log:
        2024-10-21 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = ['Unlocker']

import subprocess
import time
import tomllib

from loguru import logger

from myscrcpy.core.device import AdvDevice
from myscrcpy.utils import Param, ADBKeyCode


class Unlocker:

    def __init__(self, ):

        self.is_watching = False

        _cfg_path = Param.PATH_CONFIGS / 'unlocker.toml'
        if not _cfg_path.exists():
            logger.warning(f"{_cfg_path} Config Not Exists! Created One")
            logger.warning(f"Fill serial and psw to Start!")

            import shutil
            shutil.copyfile(Param.PATH_STATICS / 'unlocker.toml', _cfg_path)
            raise FileNotFoundError

        else:
            self.cfg = tomllib.load(_cfg_path.open('rb'))
            self.adv_device = AdvDevice.from_adb_direct(self.cfg['serial'])

    def prepare2unlock(self):
        """
            1. Get Lock Signal
            2. Close Device
            3. Wait Device Unlock
            4. Input Password and Unlock pc
        :return:
        """
        if self.is_watching:
            logger.warning(f"Unlocker is Watching!")
            return
        else:
            self.is_watching = True

        # Lock Phone When System Locked
        if not self.adv_device.is_locked():
            self.adv_device.adb_dev.keyevent(ADBKeyCode.SLEEP)

        logger.warning(f"System Locked!")

        time.sleep(2)

        while self.is_watching:
            time.sleep(self.cfg['loop_sec'])
            if not self.adv_device.is_locked():
                self.xdotool_unlock(self.cfg['psw'])
                if self.cfg['desktop_index'] >= 0:
                    self.xdotool_to_desktop(int(self.cfg['desktop_index']))

                if self.cfg['power_off_after_unlock']:
                    self.adv_device.adb_dev.keyevent(ADBKeyCode.SLEEP)

                self.is_watching = False

        logger.success(f"System UNLocked!")

    @staticmethod
    def xdotool_unlock(psw: str):
        """
            Use xdotool to unlock pc
        :return:
        """
        subprocess.call(['xdotool', 'type', psw])
        time.sleep(0.5)
        subprocess.call(['xdotool', 'key', 'Return'])

    @staticmethod
    def xdotool_to_desktop(desktop_index: int):
        """
            Use xdotool to set desktop
        :return:
        """
        subprocess.call(['xdotool', 'set_desktop', str(desktop_index)])

    @staticmethod
    def is_pc_locked() -> bool:
        """
            Use xset Monitor get pc lock or unlock
        :return:
        """
        output = subprocess.run("xset q | grep 'Monitor is'", shell=True, capture_output=True, text=True)
        return output.stdout.replace('\n', '').split(' ')[-1] == 'Off'

    def run(self):
        """
            Start Monitor
        :return:
        """

        logger.success(f"Unlocker started. Device => {self.cfg['serial']}")

        while True:
            if self.is_pc_locked():
                self.prepare2unlock()
            else:
                time.sleep(1)


def run():
    Unlocker().run()
