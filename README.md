# MYScrcpy V1.5.5

---

### [README in English](https://github.com/me2sy/MYScrcpy/blob/main/README_EN.md)

### python语言实现的一个 [**Scrcpy**](https://github.com/Genymobile/scrcpy/) 客户端。包含完整的视频、音频、控制解析及展现，**开发友好，引入即用！**

采用 [**DearPyGui**](https://github.com/hoffstadt/DearPyGui) 作为主要GUI。 支持窗口位置记忆、右键手势控制、断线重连、中文输入，锁屏密码解锁等功能。

高速模式使用[**pygame**](https://www.pygame.org/)作为鼠标及键盘控制映射GUI。提供鼠标隐藏、按键事件监听等功能， 适用于第一人称相关应用的按键映射。

### :tv: 视频简介 [BiliBili](https://www.bilibili.com/video/BV1DxWKeXEyA/)

![dpg Screenshot](/files/images/mys_1_3_4.jpg)

## 功能特性

---

### 开发
- 开箱即用 `pip install mysc[full]`
- 使用Session/Connection/Adapter/Args架构，一行代码获取图像
  - `Session(adb_device, video_args=VideoArgs(1200)).va.get_image()`
- 按需最小化引用。Core可在**Termux**上安装部署服务，支持局域网WEB浏览，[**安装部署教程**](/files/doc/MYScrcpy%20with%20Termux.md)

### GUI
- 支持有线、无线连接设备
- 支持设置无线端口，设置后自动重连功能
- 支持加载历史连接记录功能，自动记忆历史连接记录，快速连接
- 可根据设备配置相应连接模式，保存连接参数
  - 例如若使用手机摄像头模式，则video/audio配置，control关闭，并保存为Camera配置组合
  - 使用投屏，则全部配置，并保存为投屏配置组合
- 根据设备及当前连接参数，自动记忆窗口大小，同时记忆窗口旋转前位置。在横竖屏切换时，无需频繁调整窗口位置
- 支持Windows/Linux (暂无macOS设备，后期进行测试)
- 支持心跳检测，自动重连

### 视频
- 支持h264/h265视频流解析
- 根据设备情况，支持投屏及摄像头同时投屏
- 支持按比例调整窗口大小
  - 按原视频比例，等比伸缩
  - 拉动窗口，进行自由伸缩
  - 根据高度/宽度，自动调整窗口至视频比例
- 支持虚拟摄像头
  - 随时开启，随时关闭，随时切换设备
  - 支持OBS虚拟摄像头/Unity Capture(windows)/v4l2loopback

### 音频
- 支持**opus (1.5.3 NEW)**/flac/raw
- 支持切换声音输出设备，可配合VB-Cables模拟麦克风输入

### 控制
- 按键映射创建工具（TPEditor）,支持键盘，鼠标等多种控制映射方式，Windows/Linux 适用
- 支持UHID鼠标，可以实现Android界面中鼠标与PC混用
- 支持UHID-Keyboard，模拟外接键盘，直接输入中文（百度、搜狗输入法测试通过）
- 支持设备锁屏及黑屏下，通过InputPad输入密码解锁功能
- 支持鼠标滚轮滑动，缩放等功能
- 支持右键手势判断，快速回退、截屏、控制音乐播放
  - 支持创建第二个虚拟点，配合左键模拟两指操作
- 支持剪贴板
- 特殊场景下，支持ctrl调节鼠标移动速度功能
- 侧边栏多种功能键

## 基本使用

---

### 1.1 pypi直接安装使用（推荐）
```bash
# 完整安装
pip install mysc[full]
# NOT myscrcpy... my-scrcpy already exists in pypi...


# 仅核心
pip install mysc

# 支持flac
pip install mysc[flac]

# 支持opus
pip install mysc[opus]

# 若使用界面 则：
pip install mysc[gui]

# 若使用web demo 则：
pip install mysc[web]

# 可按需组合，例如
pip install mysc[gui, opus, web]

#安装完成后
# Gui 及 日志 console
mysc-cli

# 无Console
mysc-gui
```

### 1.2  克隆本项目至本地或下载release package， 使用pip安装所需包
```bash
pip install mysc-X.X.X.tar.gz
pip install loguru adbutils numpy av pyaudio

# GUI
pip install pyperclip moosegesture dearpygui pygame pyvirtualcam 

# Web GUI
pip install nicegui

# 使用flac
pip install pyflac

# 使用opus
pip install pyogg opuslib
```

### 2. 项目结构：
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
   6. **~/.myscrcpy/***
   本地化配置文件，包括运行类文件*.db 按键映射文件 tps/*.json

### 3. 程序引用使用，便于自行开发

```python
# 1.4.X 新 Core/Session 架构，推荐使用

from adbutils import adb

from myscrcpy.core import *
from myscrcpy.utils import *

# Connect to Scrcpy
# Create a Session

adb_device = adb.device_list()[0]
# 或者使用 myscrcpy提供的高级设备管理工厂创建
# DeviceFactory.load_devices()
# adv_device = DeviceFactory.device_list()[0]
# adb_device = adb_device.adb_dev

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

---

### 主界面
![dpg Screenshot](/files/images/myscrcpy_1_3_0_main.jpg)

### 右键手势功能
![right](/files/images/myscrcpy_1_4_2_g.jpg)

### Nicegui Web 界面 **NEW 1.3.6**（DEMO）
![Nicegui Demo](/files/images/Nicegui_DEMO.jpg)

### 按键映射编辑器
![Touch Proxy Editor](/files/images/edit_touch_proxy.jpg)


## 所思所想

---

作为从 Scrcpy 1.X时代就开始使用的老玩家，感叹于Scrcpy的发展及神奇的功能的同时，也一直想做点什么。不过碍于有其他项目（~~懒~~）一直迟迟没有动手。 
直到遇到了[Scrcpy Mask](https://github.com/AkiChase/scrcpy-mask) 这一优秀项目，感觉我也要做点什么了。

遂于24年6月1日开始，阅读Scrcpy源码，使用python语言，借由pyav、adbutils、numpy、pyflac等优秀工具包，形成了MYScrcpy这一项目。

开发初期，是想解决在某些场景下，鼠标操作映射相关问题。随着不断开发，也产生许多涉及图形分析、AI接入（YOLO）、自动控制等方向的新想法。

MYScrcpy是MY（Mxx & ysY）系列的开始，接下来，将继续开发完善这一项目及相关应用。

目前项目为个人开发，时间、精力、水平有限，功能说明等文档方面会逐步完善。欢迎大家使用及指正。也可通过邮箱联系。如果后续有需要，也可以建群联系。

欢迎访问我的 [Bilibili](https://space.bilibili.com/400525682)，之后会录制一些操作及讲解视频，希望大家喜欢。

最后十分感谢我的挚爱在开发中给予的支持。 :heart_eyes:


## 鸣谢

---

感谢 [**Scrcpy**](https://github.com/Genymobile/scrcpy/) 项目及作者 [**rom1v**](https://github.com/rom1v)，在这一优秀项目基础上，才有了本项目。

感谢使用到的各个包项目及作者们。有你们的付出，才有了如此好的软件开发环境。

同时感谢各位使用者们，谢谢你们的支持与帮助，也希望MYScrcpy成为你们得心应手的好工具，好帮手。

## 声明

---

本项目供日常学习（图形、声音、AI训练等）、Android测试、开发等使用。
**请一定注意：**

1.开启手机调试模式存在一定风险，可能会造成数据泄露等风险，使用前确保您了解并可以规避相关风险

**2.本项目不可用于违法犯罪等使用**

本人及本项目不对以上产生的相关后果负相关责任，请斟酌使用。

## 更新日志

---
- **1.5.5 NEW** 优化Nicegui界面，方便termux使用
- **1.5.4 NEW** 降低CPU占用
- **1.5.3 NEW** 更新 Readme 文件
- **1.5.3 NEW** 支持Opus音频解析
- **1.5.0 NEW** 现已上线**pypi**
- 1.4.2 使用[moosegesture](https://github.com/asweigart/moosegesture)实现右键手势控制功能，支持模拟第二个点、画线后退、调整音量、播放媒体等功能
- 1.4.1 改用SQLite进行配置管理
- 1.4.0 久等了！全新Core/Session/Connection/Utils架构
- 1.4.0 新增窗口位置记忆功能，记录旋转前位置
- 1.4.0 支持心跳检测，自动断线重连
- 1.4.0 现已支持设备->PC 剪贴板
- 1.4.0 优化按键映射方式，Linux适用
- 1.4.0 更多控制按钮
- 1.3.6 新增网页端设备浏览页面DEMO(Nicegui),支持鼠标输入，UHID键盘输入、ADB输入及摇杆模拟鼠标输入
- 1.3.3 新增选择音频输出设备功能，可配合VB-Cables模拟麦克风输入
- 1.3.2 新增[pyvirtualcam](https://github.com/letmaik/pyvirtualcam?tab=readme-ov-file),支持OBS虚拟摄像头
- 支持连接配置保存，窗口大小保存
- 支持无线连接，历史连接记录及快速连接功能，告别繁琐命令行
- 支持按比例调整窗口大小、任意拉伸等功能
- 支持有线、无线连接安卓设备
- 支持断线重连，连接历史记录并自动尝试连接功能
- 支持 H265连接
- 实现了视频流解析（H264），生成numpy.ndarray，可自行使用opencv、image等进行图形处理
- 实现了音频流解析（FLAC）, 使用 [pyflac](https://github.com/sonos/pyFLAC) 解码，[pyaudio](https://people.csail.mit.edu/hubert/pyaudio/) 播放
- 实现了控制按键映射，鼠标映射
- 实现了UHID-Mouse与鼠标点击混用，可以实现Android界面中鼠标与PC混用模式
- 实现了UHID-Keyboard，支持模拟外接键盘，直接输入中文（搜狗输入法测试通过）
- 实现了SharedMemory，不同进程间通过内存低延迟共享视频画面
- 实现了ZMQ通讯，使用ZMQ pull/push 对手机进行控制
- 实现了DPG GUI下，鼠标滚轮缩放、滑动等功能
- 实现了设备锁屏下，通过InputPad输入密码解锁功能
- DPG GUI下设备翻转图像自动调整，无限制拉伸缩放等功能
- 实现了Ctrl调节鼠标移动速度功能
- 采用TwinWindow思路，解决DPG控件无法重叠问题，实现DPG控制映射编辑器（TPEditor）
- 纯Pygame控制模式下，最低延迟在6ms
- 实现Audio ZMQ Server, 以ZMQ发布模式，通过网络Socket传输音频流，可以实现远程声音传输、MIC监听等更多可能
- 低Android版本设备友好，自动判断版本并禁用Audio、Camera、UHID等功能。为实现更好效果，建议使用Android 12版本以上设备


## 开发计划

---

- 接入[uiautomator2](https://github.com/openatx/uiautomator2)
- APK管理器
- 使用范例及教程
- twisted / fastapi 接口
- YOLO 及 快速拉框导出等训练工具
- 视频、音频录制