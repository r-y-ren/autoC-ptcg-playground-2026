"""结构化结果行追加落 runs/<类别>-<日期>.jsonl（shared）"""
from __future__ import annotations

import datetime as _dt
import json
import os

_RUNS_DIR = os.environ.get(
    "FN_WORK_RUNS_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "runs")),
)


def write_runs_jsonl(category, row):
    """把一行结构化结果追加落 runs/<category>-<YYYYMMDD>.jsonl。

    行自动带 ts 与 category；返回行文件路径。序列化失败抛异常。
    """
    payload = {"ts": _dt.datetime.now().isoformat(timespec="seconds"), "category": str(category)}
    payload.update(row)
    line = json.dumps(payload, ensure_ascii=False)
    os.makedirs(_RUNS_DIR, exist_ok=True)
    path = os.path.join(_RUNS_DIR, f"{category}-{_dt.date.today().isoformat()}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return path
