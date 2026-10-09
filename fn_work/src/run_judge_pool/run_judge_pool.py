"""编排判决池跑批：自镜像+锚点局，汇总读数并落 runs/，stdout 打印摘要（R1）"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from kaggle_environments.envs.cabt import cabt

from src.run_judge_pool.summarize_pool import summarize_pool
from src.shared.play_local_match import play_local_match
from src.shared.write_runs_jsonl import write_runs_jsonl


def run_judge_pool(config):
    """判决池跑批。config 键：
    agent（受测智能体 callable，必填）、n_mirror（自镜像局数，默认 20）、
    n_anchor（每锚局数，默认 10）、anchors（{名: callable}，默认引擎 first/random）、
    deck（默认引擎 deck）、seed0（默认 1）、bo（默认 3）。
    返回 PoolReport dict 并打摘要行；单局失败隔离计数。种子走配对设计（paired_seeds 恒 True）。
    """
    agent = config.get("agent")
    if agent is None:
        raise ValueError("config['agent'] 必填（受测智能体）")
    n_mirror = int(config.get("n_mirror", 20))
    n_anchor = int(config.get("n_anchor", 10))
    anchors = config.get("anchors") or {"first": cabt.first_agent, "random": cabt.random_agent}
    deck = list(config.get("deck") or cabt.deck)
    seed0 = int(config.get("seed0", 1))
    bo = int(config.get("bo", 3))
    if n_mirror < 1 or n_anchor < 1 or not anchors:
        raise ValueError("局数非法或锚点为空")

    rows = []
    for i in range(n_mirror):
        # 配对种子(报告 §10.1/§14.5):自镜像双席同 seed,共享该 seed 的随机流(共同随机数)
        r = play_local_match(agent, agent, deck, deck, seed=seed0 + i, config={"bo": bo})
        rows.append({"label_a": "self", "label_b": "self", **{k: r[k] for k in ("rewards", "failed")}})
    for name, anchor in anchors.items():
        for i in range(n_anchor):
            swap = i % 2 == 1  # 半数局交换席位，抵消先后手偏差
            a, b = (anchor, agent) if swap else (agent, anchor)
            # 配对种子:各锚共用同一 seed 序列 seed0+1000+i,候选与锚打同一随机流降对比方差;
            # 双席同 seed(引擎洗牌 RNG 无种子入口时,配对性只及 Python 侧随机,见 B1 评审实证)
            r = play_local_match(a, b, deck, deck, seed=seed0 + 1000 + i, config={"bo": bo})
            rows.append({
                "label_a": name if swap else "self",
                "label_b": "self" if swap else name,
                **{k: r[k] for k in ("rewards", "failed")},
            })

    report = summarize_pool(rows)
    report["paired_seeds"] = True  # 配对种子设计:候选与锚打同一 seed 序列(共同随机数,§10.1)
    report["config"] = {"n_mirror": n_mirror, "n_anchor": n_anchor, "bo": bo,
                        "seed0": seed0, "seeds": {"mirror": "seed0+i", "anchor": "seed0+1000+i"},
                        "anchors": sorted(anchors)}
    write_runs_jsonl("judge-pool", report)

    h2h = report["self_mirror_h2h"]
    n_dec = report["self_mirror_decided"]
    print(f"self-mirror h2h: {h2h} (decided={n_dec}/{n_mirror})")
    for name in sorted(k for k in report["members"] if k != "self"):
        m = report["members"][name]
        # 受测体视角：winrate = self 对该锚的胜率（锚的 W/L 与 self 互补）
        self_w = m["loss"]
        self_l = m["win"]
        decided = self_w + self_l
        self_wr = round(self_w / decided, 4) if decided else None
        print(f"vs {name}: self_winrate={self_wr} ({self_w}W/{self_l}L/{m['draw']}D, failed={m['failed']})")
    return report
