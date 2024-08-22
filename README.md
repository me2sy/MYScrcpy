# MYScrcpy V1.3.6

### [README in English](README_EN.md)

python语言实现的一个 [Scrcpy](https://github.com/Genymobile/scrcpy/) 客户端。包含完整的视频、音频、控制解析及展现，**开发友好，引入即用！**

采用 [DearPyGui](https://github.com/hoffstadt/DearPyGui) 作为主要GUI。支持中文输入，锁屏密码解锁等功能。
同时在某些控制代理场景，使用[pygame](https://www.pygame.org/)作为鼠标及键盘控制映射GUI。pygame提供了鼠标隐藏、按键事件监听等功能，
适用于第一人称相关应用的按键映射。

在5900x + gtx1080 + 三星Galaxy Tab S9 8gen2/小米11pro 888 1920x1080分辨率下， Pygame控制模式可以达到13~30ms的延迟。

使用SharedMemory，将视频帧通过内存共享，可以实现 [Nicegui](https://github.com/zauberzeug/nicegui) 的网页绘制展现、
[OpenCV](https://opencv.org/) 图像处理等。

使用[TinyDB](https://github.com/msiemens/tinydb)进行配置管理。

![dpg Screenshot](myscrcpy/files/images/mys_1_3_4.jpg)

## 特性
- [x] **1.3.6 NEW** 新增网页端设备浏览页面DEMO(Nicegui),支持鼠标输入，UHID键盘输入、ADB输入及摇杆模拟鼠标输入
- [x] **1.3.3 NEW** 新增选择音频输出设备功能，可配合VB-Cables模拟麦克风输入
- [x] **1.3.2 NEW** 新增视频简介：[BiliBili](https://www.bilibili.com/video/BV1DxWKeXEyA/)
- [x] **1.3.2 NEW** 新增[pyvirtualcam](https://github.com/letmaik/pyvirtualcam?tab=readme-ov-file),支持OBS虚拟摄像头
- [x] 支持连接配置保存，窗口大小保存
- [x] 支持无线连接，历史连接记录及快速连接功能，告别繁琐命令行
- [x] 支持按比例调整窗口大小、任意拉伸等功能
- [x] 使用TinyDB，动态保存配置
- [x] 支持有线、无线连接安卓设备
- [x] 支持断线重连，连接历史记录并自动尝试连接功能
- [x] 支持 H265连接
- [x] 实现了视频流解析（H264），生成numpy.ndarray，可自行使用opencv、image等进行图形处理
- [x] 实现了音频流解析（FLAC）, 使用 [pyflac](https://github.com/sonos/pyFLAC) 解码，[pyaudio](https://people.csail.mit.edu/hubert/pyaudio/) 播放
- [x] 实现了控制按键映射，鼠标映射
- [x] 实现了UHID-Mouse与鼠标点击混用，可以实现Android界面中鼠标与PC混用模式
- [x] 实现了UHID-Keyboard，支持模拟外接键盘，直接输入中文（搜狗输入法测试通过）
- [x] 实现了SharedMemory，不同进程间通过内存低延迟共享视频画面
- [x] 实现了ZMQ通讯，使用ZMQ pull/push 对手机进行控制
- [x] 实现了DPG GUI下，鼠标滚轮缩放、滑动等功能
- [x] 实现了设备锁屏下，通过InputPad输入密码解锁功能
- [x] DPG GUI下设备翻转图像自动调整，无限制拉伸缩放等功能
- [x] 实现了Ctrl调节鼠标移动速度功能
- [x] 采用TwinWindow思路，解决DPG控件无法重叠问题，实现DPG控制映射编辑器（TPEditor）
- [x] 纯Pygame控制模式下，最低延迟在6ms
- [x] 实现Audio ZMQ Server, 以ZMQ发布模式，通过网络Socket传输音频流，可以实现远程声音传输、MIC监听等更多可能
- [x] 低Android版本设备友好，自动判断版本并禁用Audio、Camera、UHID等功能。为实现更好效果，建议使用Android 12版本以上设备

## 基本使用

### 1.  克隆本项目至本地 或安装
```bash
pip install myscrcpy-X.X.X.tar.gz
```

### 2. 结构如下：
   1. **utils.py**
   定义基本工具类及各类参数
   2. **gui/dpg**
   ~~DearPyGui 界面实现，包括视频绘制，鼠标事件，UHID鼠标、键盘输入，映射编辑等。~~
   3. **gui/pg**
   pygame 界面实现，包括视频绘制、鼠标事件、键盘事件控制等。
   4. **gui/ng**
   Nicegui Web UI, 使用 SharedMemory 读取视频Frame
   4. **controller/***
   视频流、音频流、控制流、设备控制器等
   5. **homepath/.myscrcpy/tps/*.json**
   保存TouchProxy配置文件，.json格式。
   6. **gui/dpg_adv/**
   新一代GUI

### 3. 程序引用使用，便于自行开发

```python
from myscrcpy.controller import *

device = DeviceFactory.device()


# Connect to Scrcpy
# Create a SocketController and pass to connect method
device.connect(
   VideoSocketController(max_size=1366),
   # Use Camera:
   # VideoSocketController(max_size=1366, camera=VideoCamera(camera_size='1280x720', camera_fps=120)),
   
   AudioSocketController(audio_source=AudioSocketController.SOURCE_OUTPUT),
   # AudioSocketServer
   # AudioSocketServer(output=False),
    
   # ControlSocket CAN NOT Create When VideoSocket Source is Camera
   ControlSocketController()
)

# 从 extensions 引入功能插件

from myscrcpy.extensions.zmq_server import *
# create ZMQ Control Server
ZMQControlServer(device.csc).start()
sender = ZMQControlServer.create_sender()
sender.send(ControlSocketController.packet__screen(True))

# Get RGB Frame np.ndarray
frame = device.vsc.get_frame()
device.csc.f_set_screen(False)

# ZMQ Audio Server
# from myscrcpy.controller.audio_socket_controller import ZMQAudioServer, ZMQAudioSubscriber
# zas = ZMQAudioServer(device.asc)
# zas.start()

# ZMQ Audio Subscriber
# sub = ZMQAudioSubscriber()
# sub.start()
...
```

### 4.使用GUI

:exclamation: _Ubuntu等Linux下 使用pyaudio 需要先安装portaudio_
```bash
sudo apt install portaudio19-dev
```

#### 运行DearPyGui GUI
```bash
python -m myscrcpy.run
```

#### 运行pygame GUI （高速控制模式）

:exclamation: _使用该模式, 需要提前在DPG Gui下配置好相应按键映射_

:exclamation: _为追求性能，该模式剔除旋转等功能，设备发生旋转时，会导致运行终止。_
```bash
python -m myscrcpy.run -g
```

#### 运行Nicegui DEMO
```bash
python -m myscrcpy.gui.ng.main
```


## 程序截图

### 主界面
:boom: **NEW 1.3.0** :boom:
![dpg Screenshot](myscrcpy/files/images/myscrcpy_1_3_0_main.jpg)

### Nicegui Web 界面 **NEW 1.3.6**（DEMO）
![Nicegui Demo](myscrcpy/files/images/Nicegui_DEMO.jpg)

### 按键映射编辑器
![Touch Proxy Editor](myscrcpy/files/images/edit_touch_proxy.jpg)

### 7ms延迟
![7ms](myscrcpy/files/images/7ms.jpg)

## 所思所想
作为从 Scrcpy 1.X时代就开始使用的老玩家，感叹于Scrcpy的发展及神奇的功能的同时，也一直想做点什么。不过碍于有其他项目（~~懒~~）一直迟迟没有动手。 
直到遇到了[Scrcpy Mask](https://github.com/AkiChase/scrcpy-mask) 这一优秀项目，感觉我也要做点什么了。

遂于24年6月1日开始，阅读Scrcpy源码，使用python语言，借由pyav、adbutils、numpy、pyflac等优秀工具包，形成了MYScrcpy这一项目。

开发初期，是想解决在某些场景下，鼠标操作映射相关问题。随着不断开发，也产生许多涉及图形分析、AI接入（YOLO）、自动控制等方向的新想法。

MYScrcpy是MY（Mxx & ysY）系列的开始，接下来，将继续开发完善这一项目及相关应用。

目前项目为个人开发，时间、精力、水平有限，功能说明等文档方面会逐步完善。欢迎大家使用及指正。也可通过邮箱联系。如果后续有需要，也可以建群联系。

欢迎访问我的 [Bilibili](https://space.bilibili.com/400525682)，之后会录制一些操作及讲解视频，希望大家喜欢。

最后十分感谢我的挚爱在开发中给予的支持。 :heart_eyes:
