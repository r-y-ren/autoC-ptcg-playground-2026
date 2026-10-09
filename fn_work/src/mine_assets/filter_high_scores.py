"""按终局分位筛选高分局，输出带入选原因（R8 P1）"""
from __future__ import annotations


def filter_high_scores(episodes, quantile=0.5):
    """决出胜负的局（|r0-r1|>0）按胜方用步数升序（越快胜越优）取前 quantile 分位。

    附 reason={rank, n_steps}。空集返回空。v1 口径：reward=±1 无分差，速度=统治力度代理。
    """
    decisive = []
    for ep in episodes:
        r0, r1 = ep["metadata"]["rewards"]
        if abs(r0 - r1) > 0 and not ep["metadata"].get("failed"):
            decisive.append(ep)
    decisive.sort(key=lambda e: e["metadata"]["n_steps"])
    n_keep = int(len(decisive) * quantile)
    kept = decisive[:n_keep]
    for rank, ep in enumerate(kept):
        ep["reason"] = {"rank": rank, "n_steps": ep["metadata"]["n_steps"]}
    return kept
