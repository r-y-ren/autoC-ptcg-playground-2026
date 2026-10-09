"""跑一局并序列化为官方同构 episode JSON 落盘（R3 记录器）"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.record_episode.serialize_episode import serialize_episode
from src.shared.play_local_match import play_local_match


def record_episode(agent_a, agent_b, deck_a, deck_b, seed, out_path, config=None):
    """跑一局并把 episode JSON 原子落盘（先写 .tmp 再 rename）。

    局失败（agent 抛错/非法判负）不写干净 episode，改写 <out_path>.failed 携带原因。
    返回实际写入的文件路径。
    """
    r = play_local_match(agent_a, agent_b, deck_a, deck_b, seed=seed, config=config)
    if r.get("failed"):
        fail_path = out_path + ".failed"
        with open(fail_path + ".tmp", "w", encoding="utf-8") as f:
            json.dump({"failed": True, "reason": r.get("error"), "statuses": r.get("statuses")}, f, ensure_ascii=False)
        os.replace(fail_path + ".tmp", fail_path)
        return fail_path

    ep = serialize_episode(r)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(ep, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(out_path + ".tmp", out_path)
    return out_path
