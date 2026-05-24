# -*- coding: utf-8 -*-
"""
    i18n_compile
    ~~~~~~~~~~~~~~~~~~

    Pure-Python .po -> .mo compiler.
    Adapted from CPython Tools/i18n/msgfmt.py (Python Software Foundation License).
    无外部依赖，便于在打包流程或开发期直接调用。

    Log:
        2026-04-27 0.1.0 Me2sY 创建
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = ['compile_po_file', 'compile_locales']

import ast
import pathlib
import re
import struct
import sys
from typing import Iterable


def _unq(s: str) -> bytes:
    """解析 PO 字符串字面量为 bytes（UTF-8 编码）。"""
    return ast.literal_eval(s).encode('utf-8')


def _parse_po(po_path: pathlib.Path) -> dict[bytes, bytes]:
    """解析 .po 文件，返回 {msgid: msgstr} 字节映射。
    支持 msgctxt（使用 \x04 分隔）和 msgid_plural（拼接 \0）。
    """
    messages: dict[bytes, bytes] = {}

    section: int = 0  # 0=none, 1=msgid, 2=msgstr
    msgctxt: bytes | None = None
    msgid: bytes = b''
    msgstr: bytes = b''
    plurals: dict[int, bytes] = {}
    is_plural: bool = False

    def commit():
        nonlocal msgctxt, msgid, msgstr, plurals, is_plural
        if not msgid and not msgctxt:
            # 文件头 entry：msgid "" 也要保留，作为 metadata
            key = b''
        else:
            key = msgid
            if msgctxt is not None:
                key = msgctxt + b'\x04' + msgid

        if is_plural and plurals:
            value = b'\x00'.join(plurals[i] for i in sorted(plurals))
        else:
            value = msgstr

        messages[key] = value
        msgctxt = None
        msgid = b''
        msgstr = b''
        plurals = {}
        is_plural = False

    plural_re = re.compile(r'^msgstr\[(\d+)\]\s*(.*)$')

    lines = po_path.read_text(encoding='utf-8').splitlines()
    lines.append('')  # sentinel 触发最后 entry 的 commit

    for raw in lines:
        line = raw.strip()

        if line.startswith('#') or (not line and section == 0):
            continue

        if not line:
            # 空行：分隔 entry
            if section != 0:
                commit()
                section = 0
            continue

        if line.startswith('msgctxt'):
            if section != 0:
                commit()
            section = 1
            msgctxt = _unq(line[len('msgctxt'):].strip())
            continue

        if line.startswith('msgid_plural'):
            section = 1
            is_plural = True
            continue  # 复数原文不重要，只看 msgstr[i]

        if line.startswith('msgid'):
            if section == 2:
                commit()
            section = 1
            msgid = _unq(line[len('msgid'):].strip())
            continue

        m = plural_re.match(line)
        if m:
            section = 2
            is_plural = True
            idx = int(m.group(1))
            plurals[idx] = _unq(m.group(2)) if m.group(2) else b''
            continue

        if line.startswith('msgstr'):
            section = 2
            msgstr = _unq(line[len('msgstr'):].strip())
            continue

        # 续行（"..."）
        if section == 1:
            msgid += _unq(line)
        elif section == 2:
            if is_plural and plurals:
                last_idx = max(plurals)
                plurals[last_idx] += _unq(line)
            else:
                msgstr += _unq(line)

    return messages


def _generate_mo(messages: dict[bytes, bytes]) -> bytes:
    """根据 messages 生成 .mo 二进制内容。"""
    # 跳过空 msgstr（除文件头 b'' -> metadata）
    keys = sorted(
        k for k, v in messages.items()
        if v != b'' or k == b''
    )

    offsets = []
    ids = b''
    strs = b''
    for k in keys:
        v = messages[k]
        offsets.append((len(ids), len(k), len(strs), len(v)))
        ids += k + b'\x00'
        strs += v + b'\x00'

    n = len(keys)
    keystart = 7 * 4 + 16 * n
    valuestart = keystart + len(ids)

    koffsets: list[int] = []
    voffsets: list[int] = []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]
    offsets_packed = koffsets + voffsets

    output = struct.pack(
        'Iiiiiii',
        0x950412de,       # magic
        0,                # version
        n,                # number of strings
        7 * 4,            # offset of orig table
        7 * 4 + 8 * n,    # offset of trans table
        0, 0,             # hash size & offset (no hash table)
    )
    output += struct.pack('i' * 4 * n, *offsets_packed)
    output += ids
    output += strs

    return output


def compile_po_file(po_path: pathlib.Path, mo_path: pathlib.Path | None = None) -> pathlib.Path:
    """编译单个 .po → .mo。返回 .mo 路径。"""
    po_path = pathlib.Path(po_path)
    if mo_path is None:
        mo_path = po_path.with_suffix('.mo')
    else:
        mo_path = pathlib.Path(mo_path)

    messages = _parse_po(po_path)
    mo_bytes = _generate_mo(messages)
    mo_path.parent.mkdir(parents=True, exist_ok=True)
    mo_path.write_bytes(mo_bytes)
    return mo_path


def compile_locales(locales_dir: pathlib.Path) -> Iterable[pathlib.Path]:
    """遍历 locales 目录下所有 .po 文件并编译为 .mo。"""
    locales_dir = pathlib.Path(locales_dir)
    for po in locales_dir.rglob('*.po'):
        yield compile_po_file(po)


if __name__ == '__main__':
    # 直接运行：python -m mysc.utils.i18n_compile [locales_dir]
    if len(sys.argv) > 1:
        target = pathlib.Path(sys.argv[1])
    else:
        from mysc.utils.params import Param
        target = Param.PATH_LOCALES

    if target.is_file():
        out = compile_po_file(target)
        print(f'Compiled: {out}')
    else:
        for out in compile_locales(target):
            print(f'Compiled: {out}')
