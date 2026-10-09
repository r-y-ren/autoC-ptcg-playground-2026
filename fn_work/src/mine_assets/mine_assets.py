"""编排资产开采：高分局筛选→统计→对齐率→T3 规格书（R8 P1）"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.mine_assets.aggregate_state_action import aggregate_state_action
from src.mine_assets.emit_asset_spec import emit_asset_spec
from src.mine_assets.filter_high_scores import filter_high_scores
from src.mine_assets.measure_alignment import measure_alignment
from src.shared.write_runs_jsonl import write_runs_jsonl


def mine_assets(episode_dir, score_quantile=0.5, out_dir="docs/methodology/assets"):
    """编排：读 episode 目录→高分局→胜方状态-动作表→留出对齐率→规格书。

    高分局<30 标注"方向性"继续产出（样本量入血统）。返回 {asset, spec, alignment, n_kept}。
    """
    import json
    eps = []
    for fname in sorted(os.listdir(episode_dir)):
        if fname.endswith(".json"):
            ep = json.load(open(os.path.join(episode_dir, fname), encoding="utf-8"))
            ep.setdefault("id", fname[:-5])
            eps.append(ep)
    kept = filter_high_scores(eps, score_quantile)
    directional = len(kept) < 30
    pairs = [(ep, 0 if ep["metadata"]["rewards"][0] > ep["metadata"]["rewards"][1] else 1) for ep in kept]
    table = aggregate_state_action(pairs)
    alignment = measure_alignment(table, kept)  # v1：训练集自对齐（乐观口径，正式口径待独立留出集）
    os.makedirs(out_dir, exist_ok=True)
    spec = emit_asset_spec(table, {
        "asset_name": f"state_action_table@q{score_quantile}",
        "source": f"{len(kept)}/{len(eps)} 局决出胜方局（快胜优先），episode_dir={episode_dir}",
        "n_gen": "fn_work/src/mine_assets/mine_assets.py::mine_assets（同输入同输出）",
        "acceptance": [
            f"留出对齐率 ≥0.85（当前 v1=训练集口径 {alignment['mean']}，正式口径待独立留出集）",
            f"样本量 {'<30（方向性，不入定标）' if directional else '≥30（可入定标）'}",
        ],
    }, os.path.join(out_dir, f"state-action-table-q{int(score_quantile * 100)}.md"))
    result = {"n_kept": len(kept), "n_total": len(eps), "alignment_mean": alignment["mean"],
              "directional": directional, "spec": spec}
    write_runs_jsonl("mine-assets", result)
    return result
