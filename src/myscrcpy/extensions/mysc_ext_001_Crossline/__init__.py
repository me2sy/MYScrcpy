# -*- coding: utf-8 -*-
"""
    CrossLine Extension
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-09-12 1.0.0 Me2sY
            十字线绘制插件
"""

__author__ = 'Me2sY'
__version__ = '1.0.0'

__all__ = [
    'Crossline'
]

# mysc_ext_NNN_XXXX_yyy 或 mysc_ext_NNN_XXXX_yyy.py
# |||||||  ||| |||| |||--- 版本信息 其他信息等 可选
# |||||||  ||| |||| ------ 类名(大小写敏感)
# |||||||  ||| ----------- 三位数字序号，序号小的先加载，图层在下
# |||||||  --------------- 固定格式 mysc_ext_


from .obj import Crossline
