"""资产驱动复刻 vs 官方回放逐拍对齐率（复用 first_divergence）（R8 P1）"""
from __future__ import annotations

from src.diff_episode.first_divergence import first_divergence
from src.mine_assets.aggregate_state_action import _action_sig, _state_key


def _predict(asset_table, step):
    cell = asset_table.get(_state_key(step))
    if not cell:
        return None
    best = max(cell.items(), key=lambda kv: kv[1])[0]
    return best


def measure_alignment(asset_table, episodes):
    """对每局（按胜方席位）逐拍比较资产预测与实际动作签名，对齐率=首个不一致拍/总决策拍。

    缺格（资产无该局面）不计入分母（保守：也可算不对齐，v1 取缺格即分叉口径）。
    返回 {per_episode: {eid: rate}, mean}。
    """
    per = {}
    for ep in episodes:
        r0, r1 = ep["metadata"]["rewards"]
        wseat = 0 if r0 > r1 else 1
        decisions = [s for s in ep.get("steps", [])
                     if s.get("active") == wseat and s.get("action") is not None]
        if not decisions:
            continue
        actual = [_action_sig(s) for s in decisions]
        predicted = []
        for s in decisions:
            p = _predict(asset_table, s)
            predicted.append(p if p is not None else ("miss",))
        idx = first_divergence(actual, predicted)
        per[ep.get("id", "?")] = round((len(decisions) if idx is None else idx) / len(decisions), 4)  # None=全程一致→1.0（B3-B7 评审纠反正反转 bug）
    mean = round(sum(per.values()) / len(per), 4) if per else None
    return {"per_episode": per, "mean": mean}
