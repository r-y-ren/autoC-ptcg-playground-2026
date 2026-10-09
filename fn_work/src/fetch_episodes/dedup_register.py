"""episodeId 去重+references/episodes/INDEX.md 追加来源行（R6）"""
from __future__ import annotations

import datetime as _dt
import os
import re

# INDEX 登记行：| 日期 | episodeId/范围 | 来源 | 备注 |（INDEX 不存在则建头）


def dedup_register(episodes, index_path, seen_ids=None):
    """按 episodeId 去重（seen_ids 可传入历史集合；返回值含更新后的集合）。

    新条目追加 INDEX.md 登记行（来源 URL+抓取日期）。INDEX 不可写抛异常。
    返回 (新入库数, 重复跳过数, seen_ids 更新集)。
    """
    seen = set(seen_ids or ())
    fresh, skipped = [], 0
    for ep in episodes:
        eid = ep.get("id") or ep.get("episodeId")
        if eid is None:
            eid = f"raw-{abs(hash(str(ep)[:200])) % 10**10}"
        if eid in seen:
            skipped += 1
            continue
        seen.add(eid)
        fresh.append((eid, ep))

    if fresh:
        d = os.path.dirname(index_path)
        os.makedirs(d, exist_ok=True)
        if not os.path.isfile(index_path):
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("# episodes INDEX（来源登记）\n\n| 抓取日期 | episodeId | 来源 | 备注 |\n|---|---|---|---|\n")
        today = _dt.date.today().isoformat()
        with open(index_path, "a", encoding="utf-8") as f:
            for eid, ep in fresh:
                src = ep.get("source", "kaggle-cli")
                note = re.sub(r"[|\n]", " ", str(ep.get("note", "")))[:80]
                f.write(f"| {today} | {eid} | {src} | {note} |\n")
    return len(fresh), skipped, seen
