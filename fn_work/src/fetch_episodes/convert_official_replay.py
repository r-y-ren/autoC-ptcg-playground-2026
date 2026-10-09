"""官方回放 JSON→内部 episode 格式适配器（R6 真实语料接入，fn-divide 快速通道 2026-10-05 新增）"""
from __future__ import annotations

import json
import os


def convert_official_replay(path, out_path=None):
    """Kaggle 官方 replay（episode-<id>-replay.json）→ 内部 episode schema。

    内部格式：{id, metadata:{teams, rewards, winner, n_steps}, steps:[{step, active,
    action, option_types, state{turn,hand,prize}}]}——与 record_episode 产物同构
    （B6/B7 聚类与资产管线直接可吃）。返回输出路径。
    """
    d = json.load(open(path, encoding="utf-8"))
    eid = d.get("id") or os.path.basename(path).split("-")[1]
    steps_out = []
    raw = d.get("steps", [])
    for i, pair in enumerate(raw):
        if i == 0:
            continue  # deck 提交拍：内部格式以 deck_lens 概括
        active = 0 if (pair[0].get("status") == "ACTIVE") else 1
        st = pair[active]
        obs = st.get("observation") or {}
        sel = obs.get("select") or {}
        cur = obs.get("current") or {}
        players = cur.get("players") or []
        my = players[active] if len(players) > active else {}
        steps_out.append({
            "step": i,
            "active": active,
            "action": st.get("action") if isinstance(st.get("action"), list) else None,
            "option_types": [o.get("type") if isinstance(o, dict) else None for o in (sel.get("option") or [])],
            "options_raw": sel.get("option") or [],  # 2026-10-06 迭代：身份级克隆所需完整字段
            "context": sel.get("context"),
            "state": {"turn": cur.get("turn"), "hand": my.get("handCount"), "prize": len(my.get("prize") or [])},
        })
    rewards = d.get("rewards") or [raw[-1][i].get("reward") for i in (0, 1)] if raw else [None, None]
    decks = []
    if len(raw) > 1:
        decks = [raw[1][i].get("action") if isinstance(raw[1][i].get("action"), list) else [] for i in (0, 1)]
    ep = {
        "id": str(eid),
        "metadata": {
            "teams": (d.get("info") or {}).get("TeamNames"),
            "rewards": rewards,
            "winner": 0 if (rewards[0] or 0) > (rewards[1] or 0) else (1 if (rewards[1] or 0) > (rewards[0] or 0) else None),
            "n_steps": len(raw),
            "decks": decks,
        },
        "steps": steps_out,
    }
    out_path = out_path or path.replace("-replay.json", ".conv.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ep, f, ensure_ascii=False)
    return out_path
