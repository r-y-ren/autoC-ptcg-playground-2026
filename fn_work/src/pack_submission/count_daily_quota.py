"""读本地记账返回当日提交 (已用, 剩余)，剩余 0 拒绝（R4）"""
from __future__ import annotations

import datetime as _dt
import glob
import os

DAILY_LIMIT = 5
_RUNS_DIR = os.environ.get(
    "FN_WORK_RUNS_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "runs")),
)


def count_daily_quota(day=None):
    """读 runs/pack-quota-<day>.jsonl 计当日打包次数 → (used, remaining)。

    记账文件破损按 0 用量处理并告警（print 到 stderr）。
    """
    day = day or _dt.date.today().isoformat()
    path = os.path.join(_RUNS_DIR, f"pack-quota-{day}.jsonl")
    used = 0
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                used = sum(1 for line in f if line.strip())
        except OSError:
            print(f"[warn] 记账文件破损按 0 计: {path}")
            used = 0
    return used, max(0, DAILY_LIMIT - used)
