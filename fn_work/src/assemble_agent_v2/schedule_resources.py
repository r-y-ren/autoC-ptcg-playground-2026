"""调度层：能量/进化/撤退时机资源计划（查表不在线求解）（R9）"""
from __future__ import annotations


def schedule_resources(parsed, asset_table=None):
    """回合内资源计划（v1=启发规则）：是否可攻击（有 attack 选项即视为可）。

    返回 {"can_attack", "should_attach", "plan_note"}——供控制器参考，不直接产动作。
    """
    options = parsed.get("options") or []
    types = {o.get("type") for o in options if isinstance(o, dict)}
    return {
        "can_attack": 13 in types,
        "should_attach": 8 in types,  # v1 启发：有附着机会就用（待语料定标）
        "plan_note": f"options types={sorted(t for t in types if t is not None)}",
    }
