## Extensions / 众人拾柴火焰高

全新Extension架构，现已加入MYScrcpy 1.6.0

## 基本介绍

插件体系由以下两个模块实现
```python
# 核心插件
myscrcpy.core.extension

# DPG 窗口插件
myscrcpy.gui.dpg.dpg_extension
```

### 存在形式
1. 官方插件/Module形式
    - 包含在mysc包中，无需额外安装，通过pip或clone即可引入。位置位于`src\extensions\`

2. ZIP包形式
    - ZIP包为Module压缩包形式，便于发布、下载、引用。将ZIP文件保存至 `~\.myscrcpy\extensions\`即可

### 基本结构
```
|- ext_name
|-- __init__.py
|-- ext.py
|-- extension.toml
|-- ...
```
将以上文件打包至ZIP文件，即变成ZIP包形式
```
|- ext_name.zip
|-- ext_name
|---__init__.py
|--- ext.py
|--- extension.toml
|--- ...
```
### 结构介绍
```python
# __init__.py
# 必须
# 需在文件中暴露实际功能类，该类需继承至 myscrcpy.gui.dpg.dpg_extension.DPGExtension
# 本处以 Capture 为示例，可以参照现有官方插件 src\extensions\capture

__all__ = ['Capture']

from .capture import Capture
```

```toml
# extension.toml
# 必须
# 插件信息/配置/注入文件

[info]
# Your extension name
ext_name = "Capture"

# Use N.N.N Format
version = "0.1.0"

author = "Me2sY"
email = "Me2sY@outlook.com"
web = "https://github.com/me2sy/MYScrcpy"
contact = "Q:579618095"
desc = """A Extension to Capture Image"""


# Defined Required Here
# Not Check For Now
# Only show information for reader
[required]
mysc_version = ">= 1.6.0"
dependencies = []


# Defined Settings In this Dict
# Auto Loaded when class Called
[settings]
Enabled = true
color.cross = [255, 0, 0, 255]
color.random = true
Thickness = 1

# screen_shot
ss.show_rect = true
ss.show_cross = true
ss.cut_raw = true
ss.lock_rect = false
ss.width = 320
ss.height = 320
ss.mode = "cut"

Scale = 2.0


# Extension - keys
# Auto Register to keyboard handler
# Rewrite callback_key_xxx function in DPGExtension to defined your own function
# Struct:
# [keys.XXX]              keys.XXX  XXX is the key name
# * space = 1/2/3         myscrcpy 1.6.x support 3 space for extensions. 0 is for proxy
# * uk_name = ""          myscrcpy.utils.keys.UnifiedKey.name, bind function to this key
# * desc = ""             function desc

[keys.switch]
space = 1
uk_name = "KB_Q"
desc = "On/Off"

[keys.screenshot]
space = 1
uk_name = "KB_C"
desc = "Take a ScreenShot"

[keys.lock_rect]
space = 1
uk_name = "KB_X"
desc = "Lock Rect"


# Extension - Mouse gestures
# Auto Register to mouse handler gesAction
# Notice that only ges >= 2 is effective. Level1 is for system use
# Visit Moosegesture https://github.com/asweigart/moosegesture
# Rewrite callback_mg_xxx function in DPGExtension to defined your own function
# Struct:
# [mouse_ga.XXX]            mouse.XXX  XXX is the key name
# * space = 0/1/2           MYScrcpy 1.6.x support 3 space for extensions, 0 is for mysc system use so NOT Recommended!
# * gestures = ""           gesAction Command use | to split. Directions: U/D/L/R/UL/UR/DL/DR
# * desc                    function desc

[mouse_ga.switch]
space = 1
gestures = "D|L"    # Means Mouse go Down -> Left. Use | to split gestures
desc = "On/Off"
```

```python
# capture.py
# 实际功能类，随意命名
# 实现具体功能

from myscrcpy.core import AdvDevice, Session
from myscrcpy.utils import UnifiedKey, Action
from myscrcpy.gui.dpg.dpg_extension import *


class Capture(DPGExtension):
    """
        DPGExtension 实现了很多注入方法
        
        其中
        self.value_manager 为 值管理器，用于实现值的加载、共享及保存
        通过在配置文件 [settings] 定义键值对实现注入
        Enabled = true
        
        则通过 self.value_manager.register() / 或 实例化 VmDPGItem
        传入键名 Enabled
        则自动对值管理，实现配置加载、存储功能        
        
        
        tag_layer = self.register_layer()
        在主显示模板注册一个显示 layer 实现绘制功能
        
        tag_tab = self.register_pad()
        在左侧注册一个（仅一个）控制面板，用于实现插件功能、控制等
        
        tag_menu = self.register_menu()
        在菜单栏 exts/ 下 注册一个（仅一个）插件菜单栏        
        
    """

    def start(self):
        """
            GUI加载插件时，执行该回调函数
        """
    
    def stop(self):
        """
            GUI结束加载插件时，执行该回调函数
        """
    
    def device_connect(self, adv_device: AdvDevice, session: Session):
        """
            当设备连接时，执行该回调函数，传入当前连接的 AdvDevice 及 Session 对象
        """

    def device_disconnect(self):
        """
            设备断联时，执行该回调函数
        """

    # 在加载插件时，根据用户自定义，可注入对应方法，重写即可实现相应功能
    # 例如 若定义 
    # [keys.switch]
    # space = 1
    # uk_name = "KB_Q"
    # desc = "ON/OFF"
    # 则自动生成 callback_key_switch 方法，其中 callback_key_为固定格式， switch 为 keys名称
    # 在KB_Q按键按下/弹起时，会调用 callback_key_switch函数
    # KB_Q 为统一按键 用法参见 myscrcpy.utils.UnifiedKeys
    
    def callback_key_switch(self, key: UnifiedKey, action: Action):
        """
            key为事件key action为Down/Release 动作
        """
        ...
    
    # 鼠标手势回调
    # 定义 [mouse_ga.switch] 生成，当绘制鼠标手势后，回调
    def callback_mg_switch(self):
        """
            注册 mouse gesture 事件回调函数
        """
        ...
```

## 插件管理

### 使用 ExtensionManager 进行插件管理

**菜单栏 -> Exts -> Manager**

![ExtensionManager](/files/doc/help/extensions/ext_manager.jpg)

可以选择是否加载插件

点击 `>` 按钮，查看/修改插件配置

![ExtensionDetails](/files/doc/help/extensions/ext_details.jpg)



## 注意

### 1. 因加载插件暴露设备相关信息，通过方法可获取安卓设备信息，并进行操作。在选择插件时一定要仔细甄别，选择加载安全的插件，避免产生安全风险！
### 2. 不可开发违法及恶意插件！产生不良后果，由恶意插件开发者承担全部责任！与本项目及作者无关！
### 3. 插件功能需 mysc 版本 >= 1.6.0 使用 ```pip install -U mysc``` 获取最新版本后使用