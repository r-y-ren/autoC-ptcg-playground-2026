"""runs/*.jsonl 按类别聚合成指标分片（每指标带 source）（R10）"""
from __future__ import annotations

import glob
import json
import os


def collect_runs_shards(runs_dir):
    """读 runs/*.jsonl → [{category, metrics: {key: value}, source}]（每类取最后一行快照）。

    目录空返回空+告警。source=文件名+行号。
    """
    files = sorted(glob.glob(os.path.join(runs_dir, "*.jsonl")))
    if not files:
        print(f"[warn] runs 目录无 jsonl: {runs_dir}")
        return []
    last_by_cat = {}
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cat = row.get("category") or os.path.basename(fp).rsplit("-", 1)[0]
                last_by_cat[cat] = {"category": cat, "row": row, "source": f"{os.path.basename(fp)}:L{lineno}"}
    shards = []
    for cat, item in sorted(last_by_cat.items()):
        metrics = {k: v for k, v in item["row"].items() if k not in ("ts", "category")}
        shards.append({"category": cat, "metrics": metrics, "source": item["source"]})
    return shards
