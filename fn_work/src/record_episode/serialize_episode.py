"""MatchResult→episode JSON 结构：metadata/逐拍 steps/outcome（R3）"""
from __future__ import annotations

SCHEMA_VERSION = 1  # 与官方回放字段对齐：B5 拉到首条官方 episode 后校准


def serialize_episode(match):
    """play_local_match 的 MatchResult → 可 json.dump 的 episode dict。

    schema_version=1：metadata（seed/rewards/statuses/wins/n_steps/failed）+ steps 逐拍。
    steps 缺失抛异常。
    """
    if not match.get("steps"):
        raise ValueError("MatchResult 缺 steps，无法序列化")
    return {
        "schema_version": SCHEMA_VERSION,
        "metadata": {
            "seed": match.get("seed"),
            "rewards": match.get("rewards"),
            "statuses": match.get("statuses"),
            "wins": match.get("wins"),
            "n_steps": match.get("n_steps"),
            "failed": match.get("failed"),
            "error": match.get("error"),
        },
        "steps": match["steps"],
    }
