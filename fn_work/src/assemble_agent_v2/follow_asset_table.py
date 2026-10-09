"""清单层：局面查资产表取设定点动作序，缺格回退（R9）"""
from __future__ import annotations

from src.mine_assets.aggregate_state_action import _state_key
from src.seed_agent.greedy_priority import greedy_priority  # noqa: F401 —— 回退路径由调用方使用


def follow_asset_table(parsed, asset_table):
    """按 (turn桶,hand,prize) 查资产表取该局面最优动作签名；映射回当前选项索引。

    映射：选项 type∈资产签名时选其索引（首匹配）；缺格/无匹配返回 None（调用方回退种子件贪心）。
    表损坏（非 dict）返回 None 触发回退。
    """
    if not isinstance(asset_table, dict) or not asset_table:
        return None
    cur = parsed.get("current") or {}
    my_idx = cur.get("yourIndex", 0)
    players = cur.get("players") or []
    me = players[my_idx] if len(players) > my_idx else {}
    k = _state_key({"state": {"turn": cur.get("turn"), "hand": me.get("handCount"),
                              "prize": len(me.get("prize") or [])}})
    cell = asset_table.get(k)
    if not cell:
        return None
    best_sig = max(cell.items(), key=lambda kv: kv[1])[0]
    for i, opt in enumerate(parsed.get("options") or []):
        if isinstance(opt, dict) and opt.get("type") in best_sig:
            return [i]
    return None
