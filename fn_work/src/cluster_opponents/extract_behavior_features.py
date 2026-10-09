"""单 episode→行为指纹向量（开局一致度/出牌节奏/资源结构）（R7 P1）"""
from __future__ import annotations


def extract_behavior_features(episode):
    """episode（record_episode 产物）→ {seat: 特征向量 dict}，双侧分别提取。

    特征（归一到 [0,1]）：
    - firstness：前 12 个决策拍选 index 0 的比例（开局一致度）
    - action_len：平均每次选择长度（节奏）
    - attack_rate/attach_rate/evolve_rate/play_rate/pass_rate：决策类型占比（资源结构）
    字段缺失的 episode 计 warn 跳过（返回 {}）。
    """
    steps = [s for s in episode.get("steps", []) if s.get("active") in (0, 1)]
    if not steps or "option_types" not in steps[0]:
        return {}
    out = {}
    for seat in (0, 1):
        mine = [s for s in steps if s["active"] == seat and s.get("action") is not None]
        if not mine:
            continue
        first_hits = sum(1 for s in mine[:12] if s["action"] and s["action"][0] == 0)
        firstness = first_hits / min(12, len(mine))
        lens = [len(s["action"]) for s in mine]
        action_len = sum(lens) / len(lens)
        type_hits = {"attack": 0, "attach": 0, "evolve": 0, "play": 0, "pass": 0}
        for s in mine:
            chosen = {s["option_types"][i] for i in s["action"] if i < len(s["option_types"])}
            if 13 in chosen:
                type_hits["attack"] += 1
            if 8 in chosen:
                type_hits["attach"] += 1
            if 9 in chosen:
                type_hits["evolve"] += 1
            if 7 in chosen:
                type_hits["play"] += 1
            if not s["action"]:
                type_hits["pass"] += 1
        n = len(mine)
        out[seat] = {
            "firstness": round(firstness, 4),
            "action_len": round(min(action_len / 4, 1.0), 4),
            "attack_rate": round(type_hits["attack"] / n, 4),
            "attach_rate": round(type_hits["attach"] / n, 4),
            "evolve_rate": round(type_hits["evolve"] / n, 4),
            "play_rate": round(type_hits["play"] / n, 4),
            "pass_rate": round(type_hits["pass"] / n, 4),
            "n_decisions": n,
        }
    return out


def vec_of(feat):
    keys = ["firstness", "action_len", "attack_rate", "attach_rate", "evolve_rate", "play_rate", "pass_rate"]
    return [feat.get(k, 0.0) for k in keys]
