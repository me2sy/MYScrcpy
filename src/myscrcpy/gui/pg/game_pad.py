# -*- coding: utf-8 -*-
"""
    GamePad Demo
    ~~~~~~~~~~~~~~~~~~
    示例
    使用 pygame 接收转发 gamepad(joystick) 控制信号

    Log:
        2024-10-27 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = []


from myscrcpy.core.control import ControlAdapter, Gamepad, ControlArgs
from myscrcpy.utils import UnifiedKeys

import pygame

from loguru import logger
from adbutils import adb

# 连接并创建 ControlAdapter
d = adb.device_list()[0]
ca = ControlAdapter.connect(d, ControlArgs(screen_status=ControlArgs.STATUS_ON))

# 初始化 pygame
pygame.init()
pygame.display.init()
pygame.display.set_caption('MYScrcpy - GamePad')
pygame.display.set_mode((320, 240))

# 初始化控制器
pygame.joystick.init()

clock = pygame.time.Clock()

# 定义按键映射
key_mapper = {
    0: UnifiedKeys.UK_GP_S,
    1: UnifiedKeys.UK_GP_E,
    2: UnifiedKeys.UK_GP_W,
    3: UnifiedKeys.UK_GP_N,
    4: UnifiedKeys.UK_GP_BACK,
    5: UnifiedKeys.UK_GP_GUIDE,
    6: UnifiedKeys.UK_GP_START,
    7: UnifiedKeys.UK_GP_LS,
    8: UnifiedKeys.UK_GP_RS,
    9: UnifiedKeys.UK_GP_L1,
    10: UnifiedKeys.UK_GP_R1,
    11: UnifiedKeys.UK_GP_DP_U,
    12: UnifiedKeys.UK_GP_DP_D,
    13: UnifiedKeys.UK_GP_DP_L,
    14: UnifiedKeys.UK_GP_DP_R,
}

gamepads = {}

running = True
while running:
    pygame.display.update()

    try:
        for event in pygame.event.get(
            [
                pygame.QUIT,
                pygame.JOYDEVICEADDED,
                pygame.JOYDEVICEREMOVED,
                pygame.JOYBUTTONDOWN,
                pygame.JOYBUTTONUP,
                pygame.JOYAXISMOTION
            ]
        ):

            if event.type == pygame.QUIT:
                running = False
                break

            # 手柄连接
            if event.type == pygame.JOYDEVICEADDED:
                joystick = pygame.joystick.Joystick(event.device_index)
                gamepads[joystick.get_instance_id()] = (joystick, Gamepad(ca.send_packet))
                logger.success(f"Gamepad {joystick.get_instance_id()} | {joystick.get_name()} Connected!")
                continue

            # 手柄移除
            if event.type == pygame.JOYDEVICEREMOVED:
                js, gp = gamepads.pop(event.instance_id)
                gp.uhid_destroy()
                logger.warning(f"Gamepad {event.instance_id} | {js.get_name()} Destroyed!")
                continue

            # 按钮事件
            if event.type in [pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP]:
                uk = key_mapper.get(event.button, None)

                if uk is None:
                    continue

                if event.type == pygame.JOYBUTTONDOWN:
                    gamepads[event.instance_id][1].key_pressed(uk)

                elif event.type == pygame.JOYBUTTONUP:
                    gamepads[event.instance_id][1].key_release(uk)

            # 轴事件
            if event.type == pygame.JOYAXISMOTION:
                gamepads[event.instance_id][1].axis_value_changed(event.axis, event.value)

        # 更新当前手柄状态
        for js, gp in gamepads.values():
            gp.update_status()

    except Exception as e:
        ...

    clock.tick(15)

pygame.quit()
