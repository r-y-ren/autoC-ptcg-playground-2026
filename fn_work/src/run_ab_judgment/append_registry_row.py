"""T5 台账 JSON 行追加（只追加不改历史）（R9）"""
from __future__ import annotations

import datetime as _dt
import json
import os

REQUIRED = {"id", "phenomenon", "target", "expected_signal", "status"}


def append_registry_row(registry_path, row):
    """追加 T5 台账行（id/日期/现象/目标/预期信号/状态/判定出处）。

    字段缺失抛异常；日期缺省自动补今天；只追加不改历史。返回行 id。
    """
    missing = REQUIRED - set(row)
    if missing:
        raise ValueError(f"台账行缺字段: {sorted(missing)}")
    row = dict(row)
    row.setdefault("date", _dt.date.today().isoformat())
    row.setdefault("scored_in", "")
    os.makedirs(os.path.dirname(os.path.abspath(registry_path)), exist_ok=True)
    with open(registry_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row["id"]
