# -*- coding: utf-8 -*-
"""
    配置管理工具
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-24 1.3.7 Me2sY  utils中抽离
"""

__author__ = 'Me2sY'
__version__ = '1.3.7'

__all__ = [
    'CfgHandler',
    'ValueRecord', 'ValueManager'
]


import base64
from dataclasses import dataclass
import json
import pathlib
import pickle
from typing import Any

from tinydb import TinyDB, Query

from myscrcpy.utils.params import Param


class CfgHandler:
    """
        Configuration Handler
    """

    @classmethod
    def load(cls, config_path: pathlib.Path) -> dict:
        return json.load(config_path.open('r'))

    @classmethod
    def save(cls, config_path: pathlib.Path, config: dict) -> None:
        json.dump(config, config_path.open('w'), indent=4)


VR_TYPE_RAW = 1
VR_TYPE_OBJ = 0
PICKLE_PROTOCOL = 4


@dataclass
class ValueRecord:
    """
        值记录
    """

    _key: str
    _conditions: dict | None
    _value: Any
    _type: int

    @classmethod
    def encode(cls, key: str, value: Any, conditions: Any = None) -> 'ValueRecord':
        _type, _value = cls.encode_value(value)
        return cls(_key=key, _conditions=conditions, _value=value, _type=_type)

    @classmethod
    def encode_value(cls, value: Any) -> (Any, int):
        """
            格式化值
        """
        _type = VR_TYPE_RAW
        try:
            json.dumps(value)
        except TypeError:
            value = base64.urlsafe_b64encode(pickle.dumps(value, protocol=PICKLE_PROTOCOL)).decode('utf-8')
            _type = VR_TYPE_OBJ

        return _type, value

    @property
    def value(self) -> Any:
        """
            真实值
        """
        if self._type:
            return self._value
        else:
            return pickle.loads(base64.urlsafe_b64decode(self._value.encode('utf-8')))

    def save(self, td):
        """
            格式化保存
        """
        cond = Query()['k'] == self._key
        if self._conditions:
            cond = cond & (Query()['c'] == self._conditions)
        self._type, self._value = self.encode_value(self._value)
        td.upsert(
            document={
                'k': self._key,
                'c': self._conditions,
                'v': self._value,
                't': self._type
            },
            cond=cond
        )


class ValueManager:
    """
        Value Manager
    """

    db = TinyDB(Param.PATH_CONFIGS / f"{Param.PROJECT_NAME}.json", indent=4)
    t_global = db.table('t_global', cache_size=30)

    @classmethod
    def get_global(cls, key: str, default_value: Any = None) -> Any:
        """
            获取全局属性
        """
        r = cls.t_global.search(Query()['k'] == key)
        if r:
            return r[0]['v']
        else:
            return default_value

    @classmethod
    def set_global(cls, key: str, value: dict) -> None:
        """
            设置全局属性
        """
        cls.t_global.upsert({'k': key, 'v': value}, Query()['k'] == key)

    @classmethod
    def del_global(cls, key: str) -> None:
        """
            删除全局属性
        """
        cls.t_global.remove(Query()['k'] == key)

    def __init__(self, part_name: str):
        self.part_name = part_name

        self.t_part = self.__class__.db.table(f"t_part_{self.part_name}", cache_size=30)

    def set_value(self, key: str, value: Any, conditions: Any = None) -> ValueRecord:
        """
            设置值
        """
        vr = ValueRecord.encode(key, value, conditions)
        vr.save(self.t_part)
        return vr

    def update_value(self, value_record: ValueRecord):
        """
            更新值
        """
        value_record.save(self.t_part)

    def get_records(self, key: str, conditions: Any = None) -> Any:
        """
            获取记录列表
        """
        cond = Query()['k'] == key
        if conditions:
            cond = cond & (Query()['c'] == conditions)

        vrs = []
        for _ in self.t_part.search(cond=cond):
            vrs.append(
                ValueRecord(_key=_['k'], _value=_['v'], _type=_['t'], _conditions=_.get('c', None))
            )

        return vrs

    def get_value(self, key: str, conditions: Any = None, default_value: Any = None):
        """
            获取属性值
        """
        vrs = self.get_records(key, conditions)
        if vrs:
            return vrs[0].value
        else:
            return default_value
