"""池内稳健胜率：分原型胜率→稳健口径（非平均）（R9）"""
from __future__ import annotations


def pooled_winrate(grouped):
    """grouped={member: [{a_reward, b_reward}]} → {per_proto, robust}。

    稳健口径=各成员胜率的最差值（maximin：非传递世界里"平均"无意义，最差原型加权）。
    某成员 0 局标 unknown 不计入 robust。
    """
    per = {}
    for member, rows in grouped.items():
        if not rows:
            per[member] = None
            continue
        wins = sum(1 for r in rows if r["a_reward"] > r["b_reward"])
        per[member] = round(wins / len(rows), 4)
    decided = {m: v for m, v in per.items() if v is not None}
    robust = min(decided.values()) if decided else None
    return {"per_proto": per, "robust": robust}
