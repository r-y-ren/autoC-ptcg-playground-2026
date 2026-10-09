"""编排采集：CLI 拉回放→去重→INDEX 登记（R6）"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.fetch_episodes.dedup_register import dedup_register
from src.fetch_episodes.kaggle_cli_pull import kaggle_cli_pull
from src.shared.write_runs_jsonl import write_runs_jsonl

_SEEN_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "runs", "episode-seen-ids.json"))


def fetch_episodes(targets, store_dir="references/episodes", index_path=None):
    """拉取并登记。targets=[{"kind","competition",...}]；单目标失败重试后跳过并计数不中断。

    返回 {"fetched": n_new, "skipped": n_dup, "failed": [{"target","err"}]}。
    """
    index_path = index_path or os.path.join(store_dir, "INDEX.md")
    seen = set()
    if os.path.isfile(_SEEN_PATH):
        seen = {str(x) for x in json.load(open(_SEEN_PATH))}
    os.makedirs(store_dir, exist_ok=True)

    failed = []
    total_new = total_dup = 0
    for t in targets:
        try:
            eps = kaggle_cli_pull(t)
        except Exception as e:  # noqa: BLE001 —— 单目标失败不中断
            failed.append({"target": t, "err": str(e)[:200]})
            continue
        for ep in eps:
            ep.setdefault("source", f"kaggle-cli:{t.get('kind')}/{t.get('competition')}")
        # id 类型归一为 str（跨进程持久化一致，B3-B7 评审修复）
        for ep in eps:
            if "id" in ep:
                ep["id"] = str(ep["id"])
            elif "episodeId" in ep:
                ep["id"] = str(ep.pop("episodeId"))
        n_new, n_dup, seen = dedup_register(eps, index_path, seen)
        total_new += n_new
        total_dup += n_dup
        fresh_ids = {e["id"] for e in eps if e["id"] in {m for m in seen}}  # 本批新入库
        for ep in eps:
            if ep["id"] in fresh_ids and not os.path.exists(os.path.join(store_dir, f"{ep['id']}.json")):
                with open(os.path.join(store_dir, f"{ep['id']}.json"), "w", encoding="utf-8") as fh:
                    json.dump(ep, fh, ensure_ascii=False)

    os.makedirs(os.path.dirname(_SEEN_PATH), exist_ok=True)
    json.dump(sorted(str(x) for x in seen), open(_SEEN_PATH, "w"))
    result = {"fetched": total_new, "skipped": total_dup, "failed": failed, "targets": len(targets)}
    write_runs_jsonl("fetch-episodes", result)
    return result
