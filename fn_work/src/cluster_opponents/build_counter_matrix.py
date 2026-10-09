"""原型对原型对局胜率统计出克制矩阵 CSV（R7 P1）"""
from __future__ import annotations

import csv
import os


def build_counter_matrix(assignment, episodes, out_path):
    """assignment={episode_id: {0: proto, 1: proto}}；episodes=[episode]（metadata.rewards）。

    统计 proto×proto 胜率（对局数）→ CSV（行=proto_a 席，列=proto_b 席，值=胜率(局数)）。
    无跨原型对局输出空矩阵+告警。返回 CSV 路径。
    """
    wins = {}
    counts = {}
    protos = set()
    for ep in episodes:
        eid = ep.get("id")
        asg = assignment.get(eid)
        if not asg:
            continue
        r0, r1 = ep["metadata"]["rewards"]
        pa, pb = asg.get(0), asg.get(1)
        protos.update(x for x in (pa, pb) if x is not None)
        if pa is None or pb is None:
            continue
        counts[(pa, pb)] = counts.get((pa, pb), 0) + 1
        if r0 > r1:
            wins[(pa, pb)] = wins.get((pa, pb), 0) + 1
        elif r0 < r1:
            wins[(pb, pa)] = wins.get((pb, pa), 0) + 1
    protos = sorted(protos)
    if not any(a != b for a in protos for b in protos):
        print("[warn] 无跨原型对局，矩阵为空")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["seatA\\seatB"] + [f"P{b}" for b in protos])
        for a in protos:
            row = [f"P{a}"]
            for b in protos:
                n = counts.get((a, b), 0)
                wr = round(wins.get((a, b), 0) / n, 3) if n else ""
                row.append(f"{wr}({n})" if n else "-")
            w.writerow(row)
    return out_path
