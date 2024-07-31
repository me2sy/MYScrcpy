# -*- coding: utf-8 -*-
"""
    Nicegui Web Gui DEMO
    ~~~~~~~~~~~~~~~~~~
    用于演示SharedMemory WebGUI 等相关功能

    Log:
        2024-07-31 0.1.1 Me2sY  适配新Controller

        2024-07-28 0.1.0 Me2sY
            创建，使用Nicegui框架，建立WebGui
            处于Demo阶段

"""

__author__ = 'Me2sY'
__version__ = '0.1.1'

__all__ = []

import base64

import numpy as np
import cv2

from fastapi import Response
from nicegui import app, run, ui

from myscrcpy.utils import Action
from myscrcpy.controller import ControlSocketController as CSC
from myscrcpy.controller import ZMQController, VideoStream


class NGController:

    def __init__(self):
        self.tid = 0x1102
        self.pressed = False
        self.is_ready = False

        self.zmq_sender = None
        self.vs = None
        self.coord = None


ngc = NGController()
black_1px = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAA1JREFUGFdjYGBg+A8AAQQBAHAgZQsAAAAASUVORK5CYII='
placeholder = Response(content=base64.b64decode(black_1px.encode('ascii')), media_type='image/png')


def convert(frame: np.ndarray) -> bytes:
    _, b_image = cv2.imencode('.jpg', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    return b_image.tobytes()


@app.get('/video/frame')
async def grab_video_frame() -> Response:
    global ngc
    if ngc.is_ready:
        coord, frame = ngc.vs.get_frame()
        ngc.coord = coord
        jpeg = await run.cpu_bound(convert, frame)
        return Response(content=jpeg, media_type="image/jpeg")
    else:
        return placeholder


@ui.page('/mobile')
def mobile_page():

    global ngc

    def mouse_event(event):

        if event.type == 'mousedown':
            ngc.zmq_sender.send(
                CSC.packet__touch(
                    Action.DOWN.value,
                    x=event.image_x, y=event.image_y,
                    **ngc.coord.d,
                    touch_id=ngc.tid
                )
            )
            ngc.pressed = True
        elif event.type == 'mouseup':
            ngc.zmq_sender.send(
                CSC.packet__touch(
                    Action.RELEASE.value,
                    x=event.image_x, y=event.image_y,
                    **ngc.coord.d,
                    touch_id=ngc.tid
                )
            )
            ngc.pressed = False
        elif ngc.pressed and event.type == 'mousemove':
            ngc.zmq_sender.send(
                CSC.packet__touch(
                    Action.MOVE.value,
                    x=event.image_x, y=event.image_y,
                    **ngc.coord.d,
                    touch_id=ngc.tid
                )
            )

    def connect():
        global ngc
        ngc.zmq_sender = ZMQController.create_sender(zmq_url.value)
        ngc.vs = VideoStream.create_by_name(shm_name.value)
        ngc.is_ready = True

        video_image = ui.interactive_image(
            source='/video/frame',
            on_mouse=mouse_event,
            events=[
                'mousedown',
                'mouseup',
                'mousemove',
            ]
        ).classes('w-full h-full')

        ui.timer(interval=0.033, callback=video_image.force_reload)

    with ui.row():
        shm_name = ui.input(label='shm_name')
        zmq_url = ui.input(label='zmq', value='tcp://127.0.0.1:55556')
        ui.button('Connect', on_click=connect)


ui.run(port=51000, title='MYScrcpy Nicegui Demo - Me2sY')
