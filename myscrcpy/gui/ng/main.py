# -*- coding: utf-8 -*-
"""
    NiceGui Better DEMO
    ~~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-22 0.1.0 Me2sY  创建
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = []

import base64
import string
from io import BytesIO
from functools import partial

from loguru import logger

from PIL import Image
from fastapi import Response
from nicegui import app, run, ui
from nicegui.events import KeyEventArguments


from myscrcpy.controller.device_controller import DeviceFactory, DeviceController
from myscrcpy.controller.video_socket_controller import VideoSocketController
from myscrcpy.controller.control_socket_controller import ControlSocketController, KeyboardWatcher
from myscrcpy.utils import Action, ADBKeyCode, Param
from myscrcpy.gui.ng.key_mapper import ng2uk


black_1px = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAA1JREFUGFdjYGBg+A8AAQQBAHAgZQsAAAAASUVORK5CYII='
placeholder = Response(content=base64.b64decode(black_1px.encode('ascii')), media_type='image/png')

DeviceFactory.load_devices()


class NGController:
    """
        NiceGui Controller
    """

    def __init__(self, device_serial: str):
        self.jpg_io = BytesIO()
        self.dc: DeviceController = DeviceFactory.device(device_serial)
        self.is_connected = self.connect()

        self.touch_id_left = 0x0413
        self.touch_id_right = self.touch_id_left + 10

        self.key_watcher = None

        self.mouse_pressed = {
            0: False,
            2: False
        }
        self.right_pos = (0, 0)

        if self.is_connected:
            NGFactory.register(self)

    def connect(self):
        """
            Defined Connections
        :return:
        """
        if self.dc:
            vsc, asc, csc = self.dc.connect(
                VideoSocketController(max_size=1200, fps=30),
                ControlSocketController()
            )
            if vsc or asc or csc:
                return True
        return False

    def f2jpg(self) -> Response:
        """
            Load np.ndarray and convert it to jpg
        :return:
        """
        if self.dc is None or self.dc.vsc is None or not self.dc.vsc.is_running:
            return placeholder

        self.jpg_io.seek(0)
        self.jpg_io.truncate()
        Image.fromarray(self.dc.vsc.get_frame()).save(self.jpg_io, 'JPEG')
        return Response(content=self.jpg_io.getvalue(), media_type="image/jpeg")


class NGFactory:
    """
        Defined a Factory Class for All NiceGui Controllers
    """

    ngc_dict = {}

    @classmethod
    def get_ngc(cls, device_serial: str) -> NGController:
        if device_serial in cls.ngc_dict and cls.ngc_dict[device_serial].is_connected:
            return cls.ngc_dict[device_serial]
        else:
            return NGController(device_serial)

    @classmethod
    def register(cls, ngc: NGController):
        cls.ngc_dict[ngc.dc.serial_no] = ngc

    @classmethod
    def get_device_video(cls, device_serial: str) -> Response:
        """
            Get Device Video and Convert it to jpg response
        :param device_serial:
        :return:
        """
        if device_serial in cls.ngc_dict:
            return cls.ngc_dict[device_serial].f2jpg()
        else:
            return placeholder


@app.get('/vsc/frame/{device_serial}')
async def get_vsc_frame(device_serial: str) -> Response:
    """
        Create A interface To Get Device Frame
        NOTICE: EVERY ONE CAN SEE THE VIDEO FROM THE DEVICE BY THIS URL!
        CONSIDER SET A PASSWORD IN ATTR OR AUTH NEXT STEP

    :param device_serial:
    :return:
    """
    return await run.io_bound(NGFactory.get_device_video, device_serial)


@ui.page('/device/{device_serial}')
def device_page(device_serial: str):
    """
        Device Page
    :param device_serial:
    :return:
    """

    ngc = NGFactory.get_ngc(device_serial)

    # Cancel Web Browser contextmenu
    ui.add_head_html("""
        <script>
            document.oncontextmenu = function() {return false;};
        </script>
    """)

    # ------------------------- Keyboard Part -------------------------

    def _send(modifiers, key_scan_codes):
        ngc.dc.csc.f_uhid_keyboard_input(
            modifiers=modifiers, key_scan_codes=key_scan_codes
        )

    ngc.key_watcher = KeyboardWatcher(
        uhid_keyboard_send_method=_send, active=ngc.dc.info.is_uhid_supported
    )

    if ngc.dc.info.is_uhid_supported:
        ngc.dc.csc.f_uhid_keyboard_create()

    def handle_key(e: KeyEventArguments):
        """
            handle key event
        :param e:
        :return:
        """
        if not keyboard_switch.value:

            if e.action.keydown:
                try:
                    if e.key.name in [str(_) for _ in range(10)]:
                        ngc.dc.adb_dev.keyevent(ADBKeyCode[f"N{e.key.name}"].value)

                    elif e.key.name in string.ascii_letters:
                        ngc.dc.adb_dev.send_keys(e.key.name)

                    elif e.key.name.upper().startswith('ARROW'):
                        ngc.dc.adb_dev.keyevent(ADBKeyCode[e.key.name.upper()[5:]])

                    else:
                        # Functions Keys
                        try:
                            ngc.dc.adb_dev.keyevent(ADBKeyCode[ng2uk(e.key.code).name])
                        except:
                            try:
                                ngc.dc.adb_dev.keyevent(ADBKeyCode[e.key.code.upper()])
                            except:
                                ngc.dc.adb_dev.send_keys(e.key.name)
                                logger.warning(f"key is {e.key.name}, Make Your OWN Keymapper~")

                except Exception as e:
                    logger.error(e)

        else:
            # Use UHID Input
            if e.action.repeat:
                return
            if e.action.keydown:
                ngc.key_watcher.key_pressed(ng2uk(e.key.code))
            elif e.action.keyup:
                ngc.key_watcher.key_release(ng2uk(e.key.code))

    keyboard = ui.keyboard(on_key=handle_key)

    # ------------------------- Mouse Part -------------------------

    def mouse_event(event):
        """
            Mouse Left And Right
        :param event:
        :return:
        """
        if event.type == 'mousedown':
            ngc.dc.csc.f_touch(
                Action.DOWN,
                x=event.image_x, y=event.image_y,
                **ngc.dc.vsc.coordinate.d,
                touch_id=ngc.touch_id_left if event.button == 0 else ngc.touch_id_right
            )
            ngc.mouse_pressed[event.button] = True

            if event.button == 2:
                ngc.right_pos = (event.image_x, event.image_y)

        elif event.type == 'mouseup':
            ngc.dc.csc.f_touch(
                Action.RELEASE,
                x=event.image_x if event.button == 0 else ngc.right_pos[0],
                y=event.image_y if event.button == 0 else ngc.right_pos[1],
                **ngc.dc.vsc.coordinate.d,
                touch_id=ngc.touch_id_left if event.button == 0 else ngc.touch_id_right
            )
            ngc.mouse_pressed[event.button] = True

        elif ngc.mouse_pressed[0] and event.type == 'mousemove':
            ngc.dc.csc.f_touch(
                Action.MOVE,
                x=event.image_x, y=event.image_y,
                **ngc.dc.vsc.coordinate.d,
                touch_id=ngc.touch_id_left
            )

    # ------------------------- UI Part -------------------------
    # This Part to Draw The Device Page
    # It may perform poorly on mobile devices.

    ui.label(f"{ngc.dc.info}")

    with ui.row():
        with ui.button_group():
            # Function Buttons
            ui.button(icon='apps', on_click=lambda: ngc.dc.adb_dev.keyevent(ADBKeyCode.APP_SWITCH))
            ui.button(icon='home', on_click=lambda: ngc.dc.adb_dev.keyevent(ADBKeyCode.HOME))
            ui.button(icon='arrow_back', on_click=lambda: ngc.dc.adb_dev.keyevent(ADBKeyCode.BACK))
            ui.button(
                icon='power_settings_new', on_click=lambda: ngc.dc.adb_dev.keyevent(ADBKeyCode.POWER), color='red'
            )

        def set_screen(e):
            """
                Switch Screen
            :param e:
            :return:
            """
            ngc.dc.set_screen(e.value)

        ui.switch('Screen', value=False, on_change=set_screen)

        keyboard = ui.checkbox('Keyboard', value=True).bind_value_to(keyboard, 'active')

        # ADB keyevent to input password in lock screen
        keyboard_switch = ui.switch('ADB/UHID', value=ngc.dc.info.is_uhid_supported)

    # Video Controller
    video_image = ui.interactive_image(
        source=f"/vsc/frame/{device_serial}", on_mouse=mouse_event, events=['mousedown', 'mouseup','mousemove']
    )
    # .style('height: 75vh') to show all

    # ------------------------- UHID Mouse Part -------------------------
    # For Mobile Use

    # For Unlock device
    with ui.button_group():

        ui.button(icon='backspace', on_click=lambda: ngc.dc.adb_dev.keyevent(ADBKeyCode.BACKSPACE), color='red')

        for _ in range(10):
            ui.button(text=f"{_}", on_click=partial(ngc.dc.adb_dev.keyevent, ADBKeyCode[f"N{_}"].value))

        ui.button(icon='keyboard_return', on_click=lambda: ngc.dc.adb_dev.keyevent(ADBKeyCode.ENTER), color='green')

    if ngc.dc.info.is_uhid_supported:

        ngc.dc.csc.f_uhid_mouse_create()

        def joy_move(e):
            lb = btn_left.value
            rb = btn_right.value

            ngc.dc.csc.f_uhid_mouse_input(
                x_rel=int(e.x * 30), y_rel=int(e.y * -30),
                left_button=lb, right_button=rb
            )

        with ui.row():
            ui.joystick(
                color='blue', size=50,
                on_move=joy_move
            )
            btn_left = ui.switch(text='LEFT')
            btn_right = ui.switch(text='RIGHT')

    # Refresh The Video
    ui.timer(interval=1 / 30, callback=video_image.force_reload)


@ui.page('/')
def main():
    """
        Just A Simple Page To Choose A Device.
    :return:
    """

    for dev in DeviceFactory.device_list():
        ui.button(
            text=f"{dev.serial_no} | {dev.info}",
            on_click=lambda: ui.navigate.to(f"/device/{dev.serial_no}", True)
        )

    ui.separator()
    ui.button(text='Refresh', on_click=lambda: DeviceFactory.load_devices())


ui.run(
    port=51000,
    title=f"{Param.PROJECT_NAME} {Param.AUTHOR} NiceGui Demo",
    reload=False
)
