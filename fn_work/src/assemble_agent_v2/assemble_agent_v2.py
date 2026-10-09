"""正式件主函数：五层依次过，guard_rails 兜底，永不抛错（R9）"""
from __future__ import annotations

from src.assemble_agent_v2.decide_tempo import decide_tempo
from src.assemble_agent_v2.follow_asset_table import follow_asset_table
from src.assemble_agent_v2.guard_rails import guard_rails
from src.assemble_agent_v2.observe_opponent import observe_opponent
from src.assemble_agent_v2.schedule_resources import schedule_resources
from src.seed_agent.greedy_priority import greedy_priority
from src.seed_agent.parse_observation import parse_observation
from src.seed_agent.seed_agent import DEFAULT_DECK

# 挂载点：m2 资产/原型库落盘后从此加载（v0=None→五层走启发/回退路径）
ASSET_TABLE = None
PROTO_LIBRARY = None


def assemble_agent_v2(obs, config=None):
    """五层装配：观测器→清单层（资产查表）→调度层→控制器→防御层。

    任一层异常由整体 try 兜底为 first 语义（永不抛错）。资产未挂载时等价种子件 v5
    +观测器画像记录（供回放分析）。"""
    try:
        parsed = parse_observation(obs)
        if parsed["select"] is None:
            return list(DEFAULT_DECK)
        if not parsed["options"] or parsed["max_count"] <= 0:
            return []

        profile = observe_opponent(parsed, PROTO_LIBRARY)      # 观测层
        asset_move = follow_asset_table(parsed, ASSET_TABLE)   # 清单层
        schedule_resources(parsed, ASSET_TABLE)                # 调度层（记录性，v1 不产动作）
        if asset_move is not None:
            candidates = asset_move                            # 资产命中：设定点优先
        else:
            candidates = greedy_priority(parsed["options"], parsed["max_count"], parsed["min_count"])
        candidates = decide_tempo(parsed, profile, candidates) # 控制层
        return guard_rails(candidates, parsed["options"], parsed["max_count"],
                           {"min_count": parsed["min_count"]})  # 防御层
    except Exception:  # noqa: BLE001 —— 防御层总兜底：first 语义
        try:
            sel = (obs or {}).get("select") or {}
            if sel:
                return list(range(min(int(sel.get("maxCount") or 0), len(sel.get("option") or []))))
            return list(DEFAULT_DECK)
        except Exception:  # noqa: BLE001
            return []
