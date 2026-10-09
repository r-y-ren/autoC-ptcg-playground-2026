"""装载两份 episode 逐拍对比，输出首个分叉拍（R3 对拍器）"""
from __future__ import annotations

import json
import os

from src.diff_episode.first_divergence import first_divergence


def _load(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"episode 文件不存在: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"{path} 第 {e.lineno} 行 JSON 破损: {e.msg}") from e


def _comparable(steps):
    return [(s.get("active"), s.get("action")) for s in steps]


def diff_episode(path_a, path_b):
    """对拍两份 episode：返回首个分叉 {diverged, step, action_a, action_b} 或 {diverged: False}。

    格式破损抛异常含行号；steps 为空抛异常。
    """
    ea, eb = _load(path_a), _load(path_b)
    ca, cb = _comparable(ea["steps"]), _comparable(eb["steps"])
    idx = first_divergence(ca, cb)
    if idx is None:
        return {"diverged": False}
    return {
        "diverged": True,
        "step": ea["steps"][idx].get("step", idx),
        "action_a": ca[idx][1],
        "action_b": cb[idx][1],
    }
