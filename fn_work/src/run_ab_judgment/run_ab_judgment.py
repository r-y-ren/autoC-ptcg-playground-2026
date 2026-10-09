"""编排 A/B 判决：双席折叠跑批→双读数→T5 台账（R9）"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from kaggle_environments.envs.cabt import cabt

from src.run_ab_judgment.ab_pair_configs import ab_pair_configs
from src.run_ab_judgment.append_registry_row import append_registry_row
from src.run_ab_judgment.net_delta_j import net_delta_j
from src.run_ab_judgment.pooled_winrate import pooled_winrate
from src.shared.play_local_match import play_local_match
from src.shared.write_runs_jsonl import write_runs_jsonl


def run_ab_judgment(agent_a, agent_b, pool_config=None, folds=12, registry_path=None):
    """A/B 判决全链：对每个池成员跑 folds 折（双席对开）→ 净账+稳健胜率双读数
    → 判负输出回滚建议 → T5 台账行。folds<12 抛异常（尺子纪律）。

    返回 {net_delta_J, pooled_winrate_a/b, verdict_suggest, registry_id}。
    """
    if folds < 12:
        raise ValueError(f"折数下限 12（当前 {folds}）——尺子纪律")
    cfg = pool_config or {}
    members = cfg.get("members") or ["first", "random"]
    anchors = {"first": cabt.first_agent, "random": cabt.random_agent}
    deck = list(cfg.get("deck") or cabt.deck)
    bo = int(cfg.get("bo", 1))

    rows_a, rows_b = [], []
    grouped_a, grouped_b = {}, {}
    for member in members:
        grouped_a[member], grouped_b[member] = [], []
        for i in range(folds):
            # A 对成员（双席对开）
            swap = i % 2 == 1
            a, b = (anchors[member] if member in anchors else agent_b, agent_a) if swap else (agent_a, anchors[member] if member in anchors else agent_b)
            r = play_local_match(a, b, deck, deck, seed=20000 + i, config={"bo": bo})
            ar = r["rewards"][1] if swap else r["rewards"][0]
            br = r["rewards"][0] if swap else r["rewards"][1]
            rows_a.append({"fold": i, "a_reward": ar, "b_reward": br, "a_selfharm": 0})
            grouped_a[member].append({"a_reward": ar, "b_reward": br})
            # B 对成员
            swap_b = i % 2 == 0
            a2, b2 = (anchors[member] if member in anchors else agent_b, agent_b) if swap_b else (agent_b, anchors[member] if member in anchors else agent_b)
            r2 = play_local_match(a2, b2, deck, deck, seed=30000 + i, config={"bo": bo})
            br2 = r2["rewards"][1] if swap_b else r2["rewards"][0]
            rows_b.append({"fold": i, "a_reward": r2["rewards"][0] if swap_b else r2["rewards"][1], "b_reward": br2})
            grouped_b[member].append(rows_b[-1])

    ndj_a = net_delta_j(rows_a)
    ndj_b = net_delta_j(rows_b)
    pwr_a = pooled_winrate(grouped_a)
    pwr_b = pooled_winrate(grouped_b)

    a_better = (ndj_a["mean"] > ndj_b["mean"]) and (pwr_a["robust"] or 0) >= (pwr_b["robust"] or 0)
    verdict = "keep-A" if a_better else "rollback-A(判负)"

    out = {
        "net_delta_J": {"A": ndj_a, "B": ndj_b},
        "pooled_winrate": {"A": pwr_a, "B": pwr_b},
        "verdict_suggest": verdict,
        "config": {"folds": folds, "members": members, "bo": bo},
    }
    write_runs_jsonl("ab-judgment", out)
    if registry_path:
        out["registry_id"] = append_registry_row(registry_path, {
            "id": f"ab-{_dt_date()}-{folds}",
            "phenomenon": "A/B 判决（双席折叠）",
            "target": "assemble_agent_v2 A/B",
            "expected_signal": "net_delta_J(A)>net_delta_J(B) 且 robust(A)≥robust(B)",
            "status": "pending",
        })
    return out


def _dt_date():
    import datetime as _d
    return _d.date.today().isoformat()
