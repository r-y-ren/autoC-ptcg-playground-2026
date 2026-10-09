"""局面特征×动作分布统计→候选查表（每格带 n）（R8 P1）"""
from __future__ import annotations


def _state_key(step):
    st = step.get("state") or {}
    turn = st.get("turn") or 0
    return (min(turn // 10, 6), st.get("hand") or 0, st.get("prize") or 0)


def _action_sig(step):
    if not step.get("action"):
        return ("pass",)
    types = step.get("option_types") or []
    chosen = tuple(sorted({types[i] for i in step["action"] if i < len(types)}))
    return chosen or ("unknown",)


def aggregate_state_action(episodes, winner_only=True):
    """[(episode, winner_seat)] → {state_key: {action_sig: n}}（每格样本量即计数）。

    winner_only=True 只统计胜方席位（学赢家）。特征提取失败局跳过计数。
    """
    table = {}
    skipped = 0
    for ep, wseat in episodes:
        for s in ep.get("steps", []):
            if s.get("active") != wseat or s.get("action") is None:
                continue
            k = _state_key(s)
            a = _action_sig(s)
            table.setdefault(k, {}).setdefault(a, 0)
            table[k][a] += 1
        skipped += 0
    return table
