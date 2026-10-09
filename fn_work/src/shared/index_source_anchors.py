"""引擎源码符号→行号→源码行索引表（shared）"""
from __future__ import annotations

import re


def index_source_anchors(source_path, patterns):
    """对源码逐行匹配 patterns（字符串或正则），返回 [{symbol, line, source_line}]。

    行号 1 起；文件不存在抛异常；无命中返回空列表。
    """
    with open(source_path, encoding="utf-8") as f:
        lines = f.readlines()

    anchors = []
    for idx, raw in enumerate(lines, 1):
        for pat in patterns:
            if re.search(pat, raw):
                anchors.append({"symbol": pat, "line": idx, "source_line": raw.rstrip("\n")})
                break  # 每行只挂第一个命中的模式
    return anchors
