"""净账计算：ΔA−ΔB−自伤，按 fold 汇总均值与置信区间（R9）"""
from __future__ import annotations

import statistics


def net_delta_j(results):
    """results=[{fold, a_reward, b_reward, a_selfharm}] → {mean, ci95, n_folds}。

    每折净账=mean(a_reward − b_reward − a_selfharm)；<2 折抛异常；CI=1.96×SE。
    """
    if len(results) < 2:
        raise ValueError("折数不足（<2）")
    per_fold = [r["a_reward"] - r["b_reward"] - r.get("a_selfharm", 0) for r in results]
    mean = statistics.fmean(per_fold)
    se = statistics.stdev(per_fold) / len(per_fold) ** 0.5
    return {"mean": round(mean, 4), "ci95": round(1.96 * se, 4), "n_folds": len(per_fold)}
