"""控制器：按对手画像定战术倾向修正候选动作序（R9）"""
from __future__ import annotations


def decide_tempo(parsed, profile, candidates):
    """战术倾向修正（v1 单规则）：对手奖赏进度领先（prize_left 更少）→ 转抢攻
    （攻击索引提前）；否则保持输入序。返回修正后候选序。
    """
    if not candidates:
        return list(candidates or [])
    res = (profile or {}).get("resources") or {}
    opp_prize, my_prize = res.get("prize_left"), res.get("my_prize_left")
    if opp_prize is None or my_prize is None or opp_prize >= my_prize:
        return list(candidates)

    options = parsed.get("options") or []
    attack_idx = [c for c in candidates
                  if c < len(options) and isinstance(options[c], dict) and options[c].get("type") == 13]
    if not attack_idx:
        return list(candidates)
    rest = [c for c in candidates if c not in attack_idx]
    return attack_idx + rest
