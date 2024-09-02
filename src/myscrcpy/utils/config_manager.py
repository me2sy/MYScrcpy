# -*- coding: utf-8 -*-
"""
    配置管理工具
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-31 1.4.1 Me2sY  使用SQLite3 取代原 TinyDB，进行KeyValue管理

        2024-08-24 1.3.7 Me2sY  utils中抽离
"""

__author__ = 'Me2sY'
__version__ = '1.4.1'

__all__ = [
    'CfgHandler',
    'KeyValue', 'KVManager',
    'kv_global'
]

from dataclasses import dataclass
import json
import pathlib
import pickle
import sqlite3
from typing import Any, ClassVar, Tuple

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


@dataclass
class KeyValue:
    """
        值记录
    """
    PICKLE_PROTOCOL: ClassVar[int] = 4

    key: str
    value: Any
    info: str = ''

    @classmethod
    def _encode(cls, value: Any) -> bytes:
        return pickle.dumps(value, protocol=cls.PICKLE_PROTOCOL)

    @classmethod
    def _decode(cls, data: bytes) -> Any:
        return pickle.loads(data)

    @classmethod
    def loads(cls, record: Tuple[str, bytes, str]) -> 'KeyValue':
        return cls(record[0], cls._decode(record[1]), record[2])

    def dumps(self) -> Tuple[str, bytes, str]:
        return self.key, self._encode(self.value), self.info


class KVManager:
    """
        使用 SQLite3 进行 KeyValue 管理
        Value 进行 pickle 处理，以 bytes存储至 blob
    """

    @staticmethod
    def get_connection(db_name: str) -> sqlite3.Connection:
        return sqlite3.connect(Param.PATH_CONFIGS / f"{db_name}.db")

    @staticmethod
    def _run_check(table_name: str):
        """
            初始化检查
        :return:
        """
        with KVManager.get_connection(table_name) as db:
            db.execute(
                f"""
                    CREATE TABLE IF NOT EXISTS 
                    {table_name} (
                        k    TEXT not null constraint {table_name}_pk primary key,
                        v    BLOB,
                        info TEXT
                    );
                """
            )

    @staticmethod
    def _get(table_name: str, key: str, default_value: Any = None) -> Any:
        """
            获取全局属性
        :param table_name:
        :param key:
        :param default_value: 默认值
        :return:
        """
        sql = f"SELECT * FROM {table_name} WHERE k = ?"

        db = KVManager.get_connection(table_name)
        cur = db.cursor()
        cur.execute(sql, (key,))
        values = cur.fetchone()
        cur.close()
        db.close()

        if values is None:
            return default_value
        else:
            return KeyValue.loads(values).value

    @staticmethod
    def _set(table_name: str, key: str, value: Any, info: str = '') -> None:
        """
            设置全局属性
        :param table_name:
        :param key:
        :param value:
        :param info:
        :return:
        """
        sql = f"INSERT OR REPLACE INTO {table_name} VALUES(?, ?, ?)"
        with KVManager.get_connection(table_name) as db:
            db.execute(sql, KeyValue(key, value, info).dumps())

    @staticmethod
    def _del(table_name: str, key: str) -> None:
        """
            删除键
        :param table_name:
        :param key:
        :param info:
        :return:
        """
        sql = f"DELETE FROM {table_name} WHERE k = ?"
        with KVManager.get_connection(table_name) as db:
            db.execute(sql, (key,))

    def __init__(self, table_name: str):
        """
            独立KV表
        :param table_name:
        """
        self.table_name = ('kvm_' + str(table_name)[:60]) if table_name else f"kvm_unknown"
        # self.db = sqlite3.connect(Param.PATH_CONFIGS / f"{self.table_name}.db")
        self._run_check(self.table_name)

    def get(self, key: str, default_value=None) -> Any:
        return self.__class__._get(self.table_name, key, default_value)

    def set(self, key: str, value: Any, info: str = ''):
        self.__class__._set(self.table_name, key, value, info)

    def delete(self, key: str):
        self.__class__._del(self.table_name, key)


kv_global = KVManager('global')
