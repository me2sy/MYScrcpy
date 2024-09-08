# MYScrcpy with Termux V1.5.6

教程：在Termux中安装MYScrcpy，提供Web访问界面


### 1. 安装 [**termux**](https://github.com/termux/termux-app)

### 2. 安装 python 环境
```bash
# 换源
termux-change-repo

pkg upgrade

# install python
pkg install python

# 确认是否安装成功
python -V
```

### 3. 安装MYScrcpy所需环境

```bash
# Basic
pkg install build-essential binutils android-tools

# for pyav
pkg install ffmpeg
pkg install python-numpy

# for pyaudio
pkg install portaudio

# for nicegui
pkg install rust
```

### 4. 安装MYScrcpy

```bash
pip install mysc[web]

# 加速：
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple mysc[web]
```

安装需要一定时间，请耐心等待

### 5. 开启设备ADB无线调试模式，并连接设备
1. 使用MYScrcpy连接手机
2. 打开选择设备窗口
3. 选择设备，并修改port（例如55555）
4. 点击SET按钮
5. 进入termux
```termux
adb connect 127.0.0.1:55555
```
6. 在手机弹出的对话框中，选择允许USB调试
（可勾选一律允许选项）
7. 重试 ```adb connect 127.0.0.1:55555```
8. 使用 ```adb devices```查看是否成功连接

### 6. 启动Web服务
```bash
mysc-web
```
当出现 
```bash
NiceGUI ready to go on http://localhost:51000, and http://xxx:51000
```
时 即启动成功
> 注意：设备需连接WIFI，否则只能在设备浏览器上访问localhost:51000 查看效果

### 7. 局域网访问
使用同网段的PC/手机，访问上述服务地址 http://xxx:51000，打开MYScrcpy Web页面进行远程控制