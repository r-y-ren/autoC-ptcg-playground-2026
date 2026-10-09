"""obs 三段规范化：缺失补 None 标记，提取 options/maxCount（R5/R9）"""
from __future__ import annotations


def parse_observation(obs):
    """obs → {logs, current, select, options, max_count, min_count, missing:[字段名]}。

    永不抛错：obs 为 None/缺段时标 missing 并给安全缺省（options=[]、max/min=0）。
    """
    missing = []
    if obs is None:
        obs = {}
        missing.extend(["obs"])
    logs = obs.get("logs")
    current = obs.get("current")
    select = obs.get("select")
    if logs is None:
        missing.append("logs")
    if current is None:
        missing.append("current")
    if select is None:
        missing.append("select")
        return {"logs": logs, "current": current, "select": None,
                "options": [], "max_count": 0, "min_count": 0, "missing": missing}
    options = list(select.get("option") or [])
    return {
        "logs": logs,
        "current": current,
        "select": select,
        "options": options,
        "max_count": int(select.get("maxCount") or 0),
        "min_count": int(select.get("minCount") or 0),
        "missing": missing,
    }
