"""编排分片：runs 归集+回读校验→全局 merge_metrics 消费目录（R10）"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.prepare_metrics_shards.collect_runs_shards import collect_runs_shards
from src.prepare_metrics_shards.validate_ladder_readback import validate_ladder_readback
from src.shared.write_runs_jsonl import write_runs_jsonl

KEY_INVENTORY = ["pooled_winrate", "net_delta_J", "alignment_rate", "prototype_count", "ladder_mu"]


def prepare_metrics_shards(runs_dir, readback_file, out_dir="metrics_shards"):
    """分片准备：runs 聚合 + 回读校验 → out_dir/<category>.json（全局 merge_metrics 消费）。

    回读文件不存在/三要素缺失抛异常。返回分片目录路径。
    """
    if not os.path.isfile(readback_file):
        raise FileNotFoundError(f"回读录入文件不存在: {readback_file}（天梯 μ 须官方回读人工录入）")
    readback = json.load(open(readback_file, encoding="utf-8"))
    shards = collect_runs_shards(runs_dir)
    shards.append(validate_ladder_readback(readback))

    os.makedirs(out_dir, exist_ok=True)
    for s in shards:
        with open(os.path.join(out_dir, f"{s['category']}.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=1)
    write_runs_jsonl("metrics-shards", {"n_shards": len(shards), "out_dir": out_dir})
    return os.path.abspath(out_dir)
