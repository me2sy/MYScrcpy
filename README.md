# MYScrcpy

作为从 [Scrcpy](https://github.com/Genymobile/scrcpy/) 1.X时代就开始使用的老玩家，感叹于Scrcpy的发展及神奇的功能得同时，也一直想做点什么。 
碍于手头有其他项目（~~懒~~）一直迟迟没有动手。 
直到遇到了[Scrcpy Mask](https://github.com/AkiChase/scrcpy-mask) 这一优秀项目，感觉我也要做点什么了。

遂于24年6月1日开始，阅读Scrcpy源码，使用python语言，借由pyav、adbutils、numpy等优秀工具包，形成了MYScrcpy这一项目。

MYScrcpy 开发初期，是想解决在某些场景下，鼠标移动出域等问题。随着不断开发，也产生许多新想法。

目前采用的是 [DearPyGui](https://github.com/hoffstadt/DearPyGui) 作为GUI，感谢这一优秀的GUI框架，提供了很多好用易用的控件。

同时在某些控制代理场景，使用[pygame](https://www.pygame.org/)作为鼠标及键盘控制映射GUI。pygame提供了鼠标隐藏、按键事件监听等功能，
适用于第一人称相关应用的按键映射。

在视频流解析中，采用numpy.ndarray保存单帧视频

在5900x + gtx1080 + 三星Galaxy Tab S9 8gen2/小米11pro 888 1920x1080分辨率下， 可以达到6~20ms的延迟。

使用SharedMemory，将视频帧进行内存共享，实现[Nicegui](https://github.com/zauberzeug/nicegui)的网页绘制展现、 OpenCV图像处理等。

MYScrcpy是MY（Mxx & ysY）系列的开始，接下来，将继续开发完善这一项目及相关应用。方向涉及图形分析、AI接入（YOLO）、自动控制等。

目前项目为个人开发，时间、精力、水平有限，功能说明等文档方面会逐步完善。欢迎大家使用及指正。也可通过邮箱联系。如果后续有需要，也可以建群联系。

感谢我的挚爱在开发中给予的支持。 :heart_eyes:


## 特性

- [x] 有线连接安卓设备
- [x] 实现了视频流解析，生成numpy.ndarray，可自行使用opencv、image等进行图形处理
- [x] 实现了控制按键映射
- [x] 实现了UHID-Keyboard UHID-Mouse与鼠标点击混用，可以实现Android界面中鼠标与PC混用模式
- [X] 实现了SharedMemory，不同进程间共享视频画面


## 基本使用

1. 使用pip install dist/myscrcpy-1.0.0.tar.gz 或者 克隆本项目至本地
2. 结构如下：
   1. utils.py
   定义基本工具类及各类参数
   2. socket_adapter.py
   Video Socket 及 Control Socket
   3. device_controller.py
   Android Device控制类
   4. gui.dpg
   DearPyGui 界面实现，包括视频绘制，鼠标事件，UHID鼠标、键盘输入，映射编辑等。
   5. gui.pg
   pygame 界面实现，包括视频绘制、鼠标事件、键盘事件控制等。
3. 程序引用使用，便于自行开发
```python
    from myscrcpy.device_controller import DeviceFactory
    
    # 通过 DeviceFactory 连接 Android Device
    dev = DeviceFactory.device()
    
    # 连接 Scrcpy-Server 获取 Video Socket 及 Control Socket
    video_conn, ctrl_conn = dev.connect_to_scrcpy(1920, screen_on=True)
    
    # 获取视频帧 np.ndarray 颜色格式为 RGB
    # (height, width, 3) = frame.shape
    frame = video_conn.get_frame()
    
    # 发送控制指令
    ctrl_conn.send_packet(
        ctrl_conn.touch_packet(
            *args, **kwargs
        )
    )
```

4.直接使用

安装
```bash
pip install myscrcpy-1.0.0.tar.gz
```

运行DearPyGui GUI
```bash
python -m myscrcpy.run
```

运行pygame GUI （直接进入控制模式）
```bash
python -m myscrcpy.run -g
```
