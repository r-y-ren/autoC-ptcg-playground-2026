"""模拟线上装载路径解包自对弈一局断言不抛错（R4）"""
from __future__ import annotations

import os
import sys
import tarfile
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.shared.load_agent_callable import load_agent_callable
from src.shared.play_local_match import play_local_match


def sandbox_selfplay_once(tar_path):
    """解包到临时目录（模拟 /kaggle_simulations/agent/ 装载）→ 自对弈一局。

    返回 (ok, 摘要)；装载失败抛异常含原因。
    """
    with tempfile.TemporaryDirectory() as d:
        with tarfile.open(tar_path, "r:gz") as tf:
            tf.extractall(d)  # noqa: S202 —— 自产包，临时目录
        agent = load_agent_callable(d)  # 目录→main.py（Kaggle 语义）
        deck = [int(x) for x in open(os.path.join(d, "deck.csv")).read().split() if x.strip()]
        r = play_local_match(agent, agent, deck, deck, seed=1, config={"bo": 1})
    ok = not r["failed"] and r["n_steps"] > 1
    return ok, {"rewards": r["rewards"], "n_steps": r["n_steps"], "failed": r["failed"], "error": r.get("error")}
