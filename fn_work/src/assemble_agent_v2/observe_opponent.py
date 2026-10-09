"""观测器：公开信息→对手原型匹配与资源估计（R9）"""
from __future__ import annotations


def observe_opponent(parsed, proto_library):
    """从规范化 obs 推对手画像。proto_library=[{proto_id, profile, centroid, features}]。

    v1 证据=公开计数（handCount/deckCount/discard 数/prize 剩余）与节奏（turn 内已行动）。
    返回 {proto_id, confidence, hand_estimate, resources}；库空返回 unknown 画像。
    """
    cur = parsed.get("current") or {}
    my_idx = cur.get("yourIndex", 0)
    players = cur.get("players") or []
    if len(players) < 2:
        return {"proto_id": None, "confidence": 0.0, "hand_estimate": None, "resources": None}
    opp = players[1 - my_idx] or {}
    mine = players[my_idx] or {}

    proto_id = None
    confidence = 0.0
    if proto_library:
        proto_id = proto_library[0]["proto_id"]  # v1：取首原型占位（真匹配待原型库特征接入）
        confidence = 0.1
    return {
        "proto_id": proto_id,
        "confidence": confidence,
        "hand_estimate": opp.get("handCount"),
        "resources": {
            "bench": len([b for b in (opp.get("bench") or []) if b]),
            "prize_left": len(opp.get("prize") or []),
            "discard": len(opp.get("discard") or []),
            "my_prize_left": len(mine.get("prize") or []),
        },
    }
