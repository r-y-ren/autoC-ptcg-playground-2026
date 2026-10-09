"""tar.gz 结构校验：顶层 main.py+deck.csv 60 行纯数字、无嵌套（R4）"""
from __future__ import annotations

import tarfile


def validate_bundle_structure(tar_path):
    """校验提交包：顶层 main.py 与 deck.csv；deck 60 行纯数字；main.py 不得在子目录。

    返回 (ok, 违规清单)；文件不存在抛异常。
    """
    issues = []
    with tarfile.open(tar_path, "r:gz") as tf:
        names = tf.getnames()
        if "main.py" not in names:
            issues.append("顶层缺 main.py")
        if "deck.csv" not in names:
            issues.append("顶层缺 deck.csv")
        nested_main = [n for n in names if n.endswith("main.py") and n != "main.py"]
        if nested_main:
            issues.append(f"main.py 被嵌套: {nested_main}")
        if "deck.csv" in names:
            deck = tf.extractfile("deck.csv").read().decode("utf-8")
            lines = [x for x in deck.splitlines() if x.strip()]
            if len(lines) != 60:
                issues.append(f"deck 非 60 行: {len(lines)}")
            elif not all(x.strip().isdigit() for x in lines):
                issues.append("deck 含非数字行")
    return (not issues), issues
