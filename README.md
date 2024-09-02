# MYScrcpy V1.5.2

### [README in English](https://github.com/me2sy/MYScrcpy/blob/main/README_EN.md)

python语言实现的一个 [Scrcpy](https://github.com/Genymobile/scrcpy/) 客户端。包含完整的视频、音频、控制解析及展现，**开发友好，引入即用！**

采用 [DearPyGui](https://github.com/hoffstadt/DearPyGui) 作为主要GUI。支持窗口位置记忆、右键手势控制、断线重连、中文输入，锁屏密码解锁等功能。
同时在某些控制代理场景，使用[pygame](https://www.pygame.org/)作为鼠标及键盘控制映射GUI。pygame提供了鼠标隐藏、按键事件监听等功能，
适用于第一人称相关应用的按键映射。

在5900x + gtx1080 + 三星Galaxy Tab S9 8gen2/小米11pro 888 1920x1080分辨率下， Pygame控制模式可以达到13~30ms的延迟。

使用SQLite进行配置管理。

### :tv: 视频简介 [BiliBili](https://www.bilibili.com/video/BV1DxWKeXEyA/)

![dpg Screenshot](/src/myscrcpy/files/images/mys_1_3_4.jpg)
**1.4.2 手势控制功能**
![dpg_gesture](/src/myscrcpy/files/images/myscrcpy_1_4_2_g.jpg)

## 特性
- [x] **1.5.0 NEW** 现已上线**pypi** 使用 `pip install mysc` （GUI版本`pip install mysc[gui]`） 使用`mysc-gui` or `mysc-cli` (带console版本)命令打开GUI
- [x] **1.4.2 NEW** 使用[moosegesture](https://github.com/asweigart/moosegesture)实现右键手势控制功能，支持模拟第二个点、画线后退、调整音量、播放媒体等功能
- [x] **1.4.1 NEW** 改用SQLite进行配置管理
- [x] **1.4.0 NEW** 久等了！全新Core/Session/Connection/Utils架构
- [x] **1.4.0 NEW** 新增窗口位置记忆功能，记录旋转前位置
- [x] **1.4.0 NEW** 支持心跳检测，自动断线重连
- [x] **1.4.0 NEW** 现已支持设备->PC 剪贴板
- [x] **1.4.0 NEW** 优化按键映射方式，Linux适用
- [x] **1.4.0 NEW** 更多控制按钮
- [x] 1.3.6 新增网页端设备浏览页面DEMO(Nicegui),支持鼠标输入，UHID键盘输入、ADB输入及摇杆模拟鼠标输入
- [x] 1.3.3 新增选择音频输出设备功能，可配合VB-Cables模拟麦克风输入
- [x] 1.3.2 新增[pyvirtualcam](https://github.com/letmaik/pyvirtualcam?tab=readme-ov-file),支持OBS虚拟摄像头
- [x] 支持连接配置保存，窗口大小保存
- [x] 支持无线连接，历史连接记录及快速连接功能，告别繁琐命令行
- [x] 支持按比例调整窗口大小、任意拉伸等功能
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

### 1.1 直接安装使用
```bash
pip install mysc
# NOT myscrcpy... my-scrcpy already exists in pypi...

# 若使用界面 则：
pip install mysc[gui]

# 若使用web demo 则：
pip install mysc[web]

安装完成后，运行
mysc-cli
# Gui 及 日志 console

mysc-gui
# 只GUI 无Console
```

### 1.2  克隆本项目至本地或下载release package， 使用pip安装所需包
```bash
pip install mysc-X.X.X.tar.gz
pip install loguru adbutils pyperclip moosegesture av numpy pyaudio pyflac dearpygui pygame pyvirtualcam nicegui
```

### 2. 结构如下：
   1. **utils/**
   定义基本工具类及各类参数
   2. **gui/dpg**
   DearPyGui 界面实现，包括视频绘制，鼠标事件，UHID鼠标、键盘输入，映射编辑等。
   3. **gui/pg**
   pygame 界面实现，包括视频绘制、鼠标事件、键盘事件控制等。
   4. **gui/ng**
   Nicegui Web UI (DEMO)
   5. **core/***
   Session、Connection、视频流、音频流、控制流、设备控制器等核心包
   6. **homepath/.myscrcpy/tps/*.json**
   保存TouchProxy配置文件，.json格式。

### 3. 程序引用使用，便于自行开发

```python
# 1.4.X 新 Core/Session 架构，推荐使用

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

### 4.使用GUI

:exclamation: _Ubuntu等Linux下 使用pyaudio 需要先安装portaudio_
```bash
sudo apt install build-essential python3-dev ffmpeg libav-tools portaudio19-dev
```

#### 运行DearPyGui GUI
```bash
mysc-cli # With Log Console
mysc-gui # Only GUI

# or
python -m myscrcpy.run
```

#### 运行Nicegui DEMO
```bash
python -m myscrcpy.gui.ng.main
```


## 程序截图

### 主界面
![dpg Screenshot](/src/myscrcpy/files/images/myscrcpy_1_3_0_main.jpg)

### Nicegui Web 界面 **NEW 1.3.6**（DEMO）
![Nicegui Demo](/src/myscrcpy/files/images/Nicegui_DEMO.jpg)

### 按键映射编辑器
![Touch Proxy Editor](/src/myscrcpy/files/images/edit_touch_proxy.jpg)

### 7ms延迟
![7ms](/src/myscrcpy/files/images/7ms.jpg)

## 所思所想
作为从 Scrcpy 1.X时代就开始使用的老玩家，感叹于Scrcpy的发展及神奇的功能的同时，也一直想做点什么。不过碍于有其他项目（~~懒~~）一直迟迟没有动手。 
直到遇到了[Scrcpy Mask](https://github.com/AkiChase/scrcpy-mask) 这一优秀项目，感觉我也要做点什么了。

遂于24年6月1日开始，阅读Scrcpy源码，使用python语言，借由pyav、adbutils、numpy、pyflac等优秀工具包，形成了MYScrcpy这一项目。

开发初期，是想解决在某些场景下，鼠标操作映射相关问题。随着不断开发，也产生许多涉及图形分析、AI接入（YOLO）、自动控制等方向的新想法。

MYScrcpy是MY（Mxx & ysY）系列的开始，接下来，将继续开发完善这一项目及相关应用。

目前项目为个人开发，时间、精力、水平有限，功能说明等文档方面会逐步完善。欢迎大家使用及指正。也可通过邮箱联系。如果后续有需要，也可以建群联系。

欢迎访问我的 [Bilibili](https://space.bilibili.com/400525682)，之后会录制一些操作及讲解视频，希望大家喜欢。

最后十分感谢我的挚爱在开发中给予的支持。 :heart_eyes:

## 声明
本项目供日常学习（图形、声音、AI训练等）、Android测试、开发等使用。
**请一定注意：**

1.开启手机调试模式存在一定风险，可能会造成数据泄露等风险，使用前确保您了解并可以规避相关风险

**2.本项目不可用于违法犯罪等使用**

本人及本项目不对以上产生的相关后果负相关责任，请斟酌使用。