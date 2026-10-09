"""逐局结果聚合：各成员胜/平/失败率、自镜像 h2h、分差均值方差（R1）"""
from __future__ import annotations

import statistics


def summarize_pool(results):
    """聚合带标签的对局行 [{label_a, label_b, rewards:[r0,r1], failed}] → 读数 dict。

    自镜像 h2h = 同标签对局中 label_a 席胜局占比（应≈0.5）；失败局计入 failed 不计胜负。
    空列表抛异常。
    """
    if not results:
        raise ValueError("results 为空")

    stats = {}
    mirror_a = mirror_decided = 0

    for row in results:
        la, lb = row["label_a"], row["label_b"]
        for name in (la, lb):
            stats.setdefault(name, {"win": 0, "loss": 0, "draw": 0, "failed": 0, "n": 0})
        ra, rb = row["rewards"]
        for name in (la, lb):
            stats[name]["n"] += 1
        if row.get("failed"):
            stats[la]["failed"] += 1
            stats[lb]["failed"] += 1
            continue
        if la == lb:  # 自镜像行：胜局归 a 席计数
            if ra > rb:
                mirror_a += 1
                stats[la]["win"] += 1
                stats[lb]["loss"] += 1
            elif rb > ra:
                stats[lb]["win"] += 1
                stats[la]["loss"] += 1
            else:
                stats[la]["draw"] += 1
                stats[lb]["draw"] += 1
            if ra != rb:
                mirror_decided += 1
            continue
        if ra > rb:
            stats[la]["win"] += 1
            stats[lb]["loss"] += 1
        elif rb > ra:
            stats[lb]["win"] += 1
            stats[la]["loss"] += 1
        else:
            stats[la]["draw"] += 1
            stats[lb]["draw"] += 1

    for name, s in stats.items():
        decided = s["win"] + s["loss"]
        s["winrate"] = round(s["win"] / decided, 4) if decided else None

    out = {
        "members": stats,
        "self_mirror_h2h": round(mirror_a / mirror_decided, 4) if mirror_decided else None,
        "self_mirror_decided": mirror_decided,
        "n": len(results),
    }
    rewards = [r for row in results for r in row["rewards"]]
    if len(rewards) >= 2:
        out["reward_mean"] = round(statistics.fmean(rewards), 4)
        out["reward_stdev"] = round(statistics.pstdev(rewards), 4)
    return out
