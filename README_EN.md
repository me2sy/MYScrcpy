# MYScrcpy V1.5.2

### [中文简介](https://github.com/me2sy/MYScrcpy/blob/main/README.md)

A [Scrcpy](https://github.com/Genymobile/scrcpy/) client implemented in **Python**. 

Includes comprehensive video, audio, and control flow parsing and presentation. **Developer-friendly, ready to use upon integration.**

Uses [DearPyGui](https://github.com/hoffstadt/DearPyGui) as the main GUI. Supports Window Position Record, Right-click gesture control, Chinese input, unlocking screen passwords, and other features.

In some control proxy scenarios, [pygame](https://www.pygame.org/) is used for mouse and keyboard control mapping GUI. 

Pygame provides features such as mouse hiding and key event listening, suitable for key mapping in **FPS**.

5900x + GTX1080 + Samsung Galaxy Tab S9 8gen2/Xiaomi 11pro 888 with 1920x1080 resolution, Pygame control mode can achieve **13~30ms** latency.

Managing Configuration with SQLite.

### :tv: Video Introduction: [BiliBili](https://www.bilibili.com/video/BV1DxWKeXEyA/)

![dpg Screenshot](/src/myscrcpy/files/images/mys_1_3_4.jpg)

**1.4.2 Right-Click Gesture Control Feature**
![dpg_gesture](/src/myscrcpy/files/images/myscrcpy_1_4_2_g.jpg)

## Features
- [x] **1.5.0 NEW** **pypi** support. Use `pip install mysc` or with gui: `pip install mysc[gui]`. then run `mysc-gui` or `mysc-cli` (with console)
- [x] **1.4.2 NEW** With [moosegesture](https://github.com/asweigart/moosegesture), Right-click gesture control functionality available, supporting features such as simulating a second touch point, line-based undo, volume adjustment, media playback, and more
- [x] **1.4.1 NEW** Managing Configuration with SQLite
- [x] **1.4.0 NEW** Introducing the brand-new Core/Session/Connection/Utils architecture
- [x] **1.4.0 NEW** Record the position of window before rotation
- [x] **1.4.0 NEW** Support for heartbeat detection with automatic reconnection upon disconnection
- [x] **1.4.0 NEW** Device-to-PC clipboard supported
- [x] **1.4.0 NEW** Optimize the key mapping strategy for Linux compatibility
- [x] **1.4.0 NEW** Provide more control buttons
- [x] 1.3.6 New Web Interface (DEMO) by Nicegui with video and UHID keyboard/mouse
- [x] 1.3.3 Support select audio output devices, With VB-Cables you can simulate microphone input
- [x] 1.3.2 Append [pyvirtualcam](https://github.com/letmaik/pyvirtualcam?tab=readme-ov-file),support OBS virtual camera.
- [x] Supports saving connection configurations and window size.
- [x] Supports wireless connection, connection history, and quick connect features, eliminating the need for complicated command-line input.
- [x] Supports proportional window resizing and freeform stretching.
- [x] Support for reconnecting after disconnection, connection history, and automatic reconnection attempts
- [x] Support for H265 Video Stream
- [x] Video stream parsing (H264) to generate numpy.ndarray for graphic processing with OpenCV, image, etc.
- [x] Audio stream parsing (FLAC) with [pyflac](https://github.com/sonos/pyFLAC) for decoding and [pyaudio](https://people.csail.mit.edu/hubert/pyaudio/) for playback
- [x] Control key mapping and mouse mapping
- [x] Mixed use of UHID-Mouse and mouse clicks, enabling mixed use of mouse on Android and PC interfaces
- [x] UHID-Keyboard for simulating an external keyboard, supporting direct Chinese input (tested with Sogou Input Method)
- [x] SharedMemory for low-latency video frame sharing between processes
- [x] ZMQ communication using ZMQ pull/push for controlling the phone
- [x] Mouse wheel zoom, scroll functions under DPG GUI
- [x] Unlock device screen using InputPad to input password
- [x] Automatic adjustment of device video stream rotation and unrestricted zooming under DPG GUI
- [x] Adjust mouse movement speed with Ctrl In Game Mode
- [x] TwinWindow approach to solve DPG widget overlap issues, implementing DPG control mapping editor (**TPEditor**)
- [x] Minimum latency of 7ms in pure Pygame control mode
- [x] Audio ZMQ Server to transmit audio streams over network sockets, enabling remote sound transmission, MIC monitoring, and more
- [x] Friendly to low Android version devices, automatically disabling Audio, Camera, UHID, etc., for better performance, recommended **Android 12** or above


## Basic Usage

### 1.Install
```bash
pip install mysc

# NOT myscrcpy... my-scrcpy already exists in pypi...

# Use Gui then:
pip install mysc[gui]

# use Web GUI then:
pip install mysc[web]


# After install, use 
mysc-cli
# For a console

mysc-gui
# GUI without log console

```

### 1.Install or clone the project
```bash
 pip install mysc-X.X.X.tar.gz
 
 pip install loguru adbutils pyperclip moosegesture av numpy pyaudio pyflac dearpygui pygame pyvirtualcam nicegui
```

### 2.Structure:
   1. **utils** Defines basic tool classes and various parameters
   2. **gui/dpg** DearPyGui interface implementation including video rendering, mouse events, UHID mouse and keyboard input, mapping editor, etc.
   3. **gui/pg** Pygame interface implementation including video rendering, mouse events, keyboard control, etc.
   4. **gui/ng** _(DEMO) Nicegui Web UI, uses SharedMemory to read video frames_
   5. **core/** Session, Connection, Video stream, audio stream, control stream, device controller, etc.
   6. **homepath/.myscrcpy/tps/*.json** Save TouchProxy configuration files in .json format


### 3.For developer

```python
# 1.4.X Recommend to use New Core/Session 

from adbutils import adb

from myscrcpy.core import *
from myscrcpy.utils import *

# Connect to Scrcpy
# Create a Session

adb_device = adb.device_list()[0]

session = Session(
   adb_device,
   video_args=VideoArgs(max_size=1200),
   audio_args=AudioArgs(),
   control_args=ControlArgs()
)


# Get RGB Frame np.ndarray
frame = session.va.get_frame()

# Get PIL.Image
image = session.va.get_image()

session.ca.f_set_screen(True)

session.ca.f_touch_spr(
   Action.DOWN,
   ScalePointR(.5, .5, 0),
   touch_id=0x0413
)

...
```

### 4.Using the GUI
:exclamation: _On Ubuntu and other Linux systems, installing portaudio first_
```bash
sudo apt install build-essential python3-dev ffmpeg libav-tools portaudio19-dev
```

#### Run DearPyGui GUI
```bash
mysc-cli # With Log Console
mysc-gui # Only GUI

# or
python -m myscrcpy.run
```

#### Run Nicegui GUI (WEB DEMO)
```bash
python -m myscrcpy.gui.ng.main
```


## Screenshots

### Main interface
![dpg Screenshot](/src/myscrcpy/files/images/myscrcpy_1_3_0_main.jpg)

### Nicegui Web Interface **NEW 1.3.6**（DEMO）
![Nicegui Demo](/src/myscrcpy/files/images/Nicegui_DEMO.jpg)

### Key mapping editor (TPEditor)
![Touch Proxy Editor](/src/myscrcpy/files/images/edit_touch_proxy.jpg)

### 7ms latency
![7ms](/src/myscrcpy/files/images/7ms.jpg)


## Thoughts
As a long-time user of Scrcpy since the 1.X era, I am amazed by its development and magical features. I've always wanted to do something, but due to other projects (laziness), I never got started.

Until I encountered the excellent project [Scrcpy Mask](https://github.com/AkiChase/scrcpy-mask), I felt it was time to do something.

On June 1, 2024, I started reading Scrcpy source code, using Python language and leveraging excellent tools like pyav, adbutils, numpy, pyflac, and more to create the MYScrcpy project.

Initially, the goal was to solve mouse operation mapping issues in certain scenarios. As development progressed, many new ideas involving graphic analysis, AI integration (YOLO), automatic control, etc., emerged.

**MYScrcpy** is the beginning of the MY (Mxx & ysY) series. Next, I will continue to develop and improve this project and related applications.

Currently, the project is developed personally, with limited time, energy, and skill. The documentation and feature descriptions will be gradually improved. Everyone is welcome to use and provide feedback. You can also contact me via email. If needed, a group can be created for contact.

Welcome to visit my [Bilibili](https://space.bilibili.com/400525682), where I will record some operational and explanatory videos. Hope you enjoy them.

Finally, I deeply appreciate the support from my beloved during the development. :heart_eyes:

## DECLARE
This project is intended for educational purposes (graphics, sound, AI training, etc.) , Android testing or just for fun.

**ATTENTION PLEASE:**

1. Enabling the mobile debugging mode carries certain risks, such as data leakage, and it is important to ensure that you understand and can mitigate these risks before using it.
2. **NEVER** use this project for illegal or criminal activities.

The author and this project are not responsible for any related consequences resulting from the above usage, and you should use it at your own discretion.