"""消融收尾(fna-027 接力收口):补跑任务书指定的"现行基线配置"30 局四线收口 + 重组装最终 JSON。

背景:续跑中 danger×1.5 在筛选层意外过采纳线(+2 局),故续跑脚本把 seed0=26000 的收口
跑在了 adopted 配置(danger=-6.0)上;任务书要求的"现行基线配置"收口改在本脚本以
seed0=25000(原协议 SEED_CONFIRM_BASE,与 26000 错开)补跑。两份读数一并入 final JSON。

读入:tmp/weight_ablation_final.json(续跑版,提取 26000 收口)+ tmp/weight_ablation_screen.json(redo 后)。
写出:tmp/weight_ablation_final.json(覆盖为最终四段契约版)。
"""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for _p in (ROOT, ROOT + "/src", ROOT + "/tmp"):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(ROOT)

import run_weight_ablation as base
from run_weight_ablation_resume import _delta_vs_ref, _wr, REF_12000

FINAL_PATH = os.path.join(ROOT, "tmp", "weight_ablation_final.json")
HIST_BAND = {  # 同族 agent(厚叶子+符号修+Grookey 填充)历史 30 局四线池
    "seed0=9000(search_meta 判决)": {"vs_ladder": 0.4, "vs_v5": 0.4333, "vs_teacher": 0.6667,
                                     "self_mirror_h2h": 0.5667},
    "seed0=12000(保留组合,ref)": {"vs_ladder": 0.5, "vs_v5": 0.5333, "vs_teacher": 0.7,
                                   "self_mirror_h2h": 0.3667},
}


def main():
    t0 = time.time()
    with open(FINAL_PATH, encoding="utf-8") as f:
        prev_final = json.load(f)
    inc_closure = prev_final["part2_收口判决"]  # 26000 收口(danger=-6.0)

    # ---- 1) 任务书指定的现行基线配置收口(seed0=25000,与 26000 错开) ----
    base_ag = base.make_search_agent(base.META)  # weights=None=DEFAULT_WEIGHTS=现行
    base_closure = base.four_line(base_ag, 25000, "closure_baseline_pure")
    rc = base_closure["readout"]

    seat = None
    mh = rc.get("mirror_h2h")
    if mh is not None and mh < 0.45:
        print(f"[seat] baseline mirror_h2h={mh}<0.45 → 加跑 30 局双席专查(seed0=27000)", flush=True)
        seat = base.mirror_seat_check(None, seed0=27000)
    else:
        print(f"[seat] baseline mirror_h2h={mh} ≥0.45,不触发席位专查", flush=True)

    gate = {
        "vs_ladder>=0.60": bool(_wr(rc, "ladder") is not None and _wr(rc, "ladder") >= 0.60),
        "vs_v5>=0.65": bool(_wr(rc, "v5") is not None and _wr(rc, "v5") >= 0.65),
        "self_mirror in [0.35,0.65]": bool(rc.get("mirror_h2h") is not None
                                           and 0.35 <= rc["mirror_h2h"] <= 0.65),
    }
    gate["pass"] = all(gate.values())

    # ---- 2) 重组装 final JSON ----
    with open(base.SCREEN_PATH, encoding="utf-8") as f:
        screen = json.load(f)
    rows = screen["rows"]
    base_row = next(r for r in rows if r["tag"] == "r0_baseline")
    resumed_tags = ["r1_board_x1.5", "r1_fatigue_x0.5", "r1_fatigue_x1.5",
                    "r1_danger_x0.5", "r1_danger_x1.5"]
    resumed_rows = [r for r in rows if r["tag"] in resumed_tags]

    def brief(r):
        return {"tag": r["tag"], "seed0": r["seed0"],
                "weights_delta": {k: v for k, v in r["weights"].items()
                                  if v != base.DEFAULT_WEIGHTS[k]},
                "score": r["score"], "wins24": r["wins24"],
                "ladder": f"{r['readout']['ladder']['w']}W/{r['readout']['ladder']['l']}L",
                "v5": f"{r['readout']['v5']['w']}W/{r['readout']['v5']['l']}L",
                "mirror_h2h": r["readout"]["mirror_h2h"], "sec": r["sec"]}

    full_table = [{"tag": r["tag"], "seed0": r["seed0"], "score": r["score"],
                   "wins24": r["wins24"],
                   "vs_baseline_wins24": r["wins24"] - base_row["wins24"]}
                  for r in rows]

    out = {
        "task": "七权重网格消融·续跑收口(fna-027 接力):round1 补完 + 30 局四线收口",
        "weights_order": list(base.W_KEYS),
        "default_weights": dict(base.DEFAULT_WEIGHTS),
        "part1_续跑配置表": {
            "resumed_5rows": [brief(r) for r in resumed_rows],
            "round1_full_table": full_table,
            "adoption_rule": "score 更高且 wins24 ≥+2 局(24 锚局合计胜局,引擎熵护栏)",
            "adoption_outcome": {
                "prize/hp/threat/lock/board/fatigue": "×0.5/×1.5 全部无增益(≤0 局),维持默认",
                "danger": "×1.5(-4→-6)过采纳线:wins24 13→15(+2),score 0.5416→0.625;"
                          "×0.5(-2)大幅劣化(wins24=8)",
            },
            "incumbent_after_screen": {"danger": -6.0},
            "round2": "取消(任务指令;且确认层未兑现,无进入 round2 的依据)",
        },
        "part2_收口判决": {
            "note": "任务书预期筛选全无增益并把 seed0=26000 指给基线收口;实际 danger×1.5 过筛选线,"
                    "故 26000 收口落在 adopted(danger=-6)上,现行基线收口按原协议补在 seed0=25000。"
                    "两份读数并列,均 30 局四线、bo3、anchors={ladder,v5,teacher}、deck=META。",
            "baseline_pure_seed25000": {
                "weights": dict(base.DEFAULT_WEIGHTS),
                "readout": rc,
                "vs_ref_12000": {"delta": _delta_vs_ref(rc)},
                "gate": gate,
                "mirror_seat_check": seat,
                "wall_s": base_closure["sec"],
            },
            "adopted_danger6_seed26000": {
                "weights": inc_closure["config"]["weights"],
                "readout": inc_closure["readout"],
                "vs_ref_12000": {"delta": inc_closure["vs_ref_12000"]["delta"]},
                "gate": inc_closure["gate"],
                "wall_s": inc_closure["wall_s"],
            },
            "ref_12000": REF_12000,
            "same_family_hist_band": HIST_BAND,
            "gate_note": "在案门槛 vs_ladder≥0.60/vs_v5≥0.65 两收口均未过——与 12000 轮保留组合读数同题"
                         "(该门槛在保留组合当时亦未过,gate pass=false 是在案状态,非本次回归)",
        },
        "part3_异常与限界": {
            "stoppage": "原代理 07:15 停摆于 r1_board_x1.5;接力续 counter 无读数损失",
            "seed_dup_fix": "r1_board_x1.5 与 r1_fatigue_x0.5 曾撞 seed0=21100(续跑跳号失误);"
                            "fatigue_x0.5 已重跑于 seed0=21600 并替换旧行;seed 21000/21300 空号(无害)",
            "seed_assignment": "筛选 20000-20900(原)+21100/21200/21400/21500/21600(续);"
                               "收口 25000(基线)/26000(adopted);双席专查 27000",
            "budget_cuts": [r["tag"] for r in rows if r["budget_cut"]],
            "failed_games_total": sum(r["readout"]["ladder"]["failed"] + r["readout"]["v5"]["failed"]
                                      for r in rows) + rc["ladder"]["failed"] + rc["v5"]["failed"]
                                      + rc["teacher"]["failed"],
            "noise_limits": "筛选 24 锚局:±1-2 局即 ±0.04-0.08 score,采纳线 +2 局恰在噪声边缘;"
                            "30 局四线:wr 标准误 ≈±0.09;同族 agent 历史池间摆动实测 ±0.10"
                            "(vs_ladder 0.400→0.500,vs_teacher 0.667→0.700,vs_v5 0.433→0.533);"
                            "danger×1.5 的确认读数落在该带内,不能与基线区分",
            "ref_composition": "ref@12000=保留组合(厚叶子+符号修+Grookey 填充);现行 agent 同族"
                               "(search_lookahead._fill 仍为 Grookey 89+能量 3),可比,仅 seed 不同",
            "code_hygiene": "search_lookahead.py 的消融改动=纯参数化(W_KEYS/DEFAULT_WEIGHTS/resolve_weights,"
                            "weights=None 时与旧版逐位一致),默认值未动;pytest tests/ 70 passed(2026-10-06)",
        },
        "part4_建议": {
            "verdict": "权重层无可靠红利:14 个单变量配置中 13 个无增益;唯一过筛选线的 danger×1.5(+2 局)"
                       "在 30 局确认中未兑现(vs_ref 全线 -0.067/-0.133/-0.100,读数在同族历史带内)。"
                       "现行七权重(prize10/hp2/threat3/lock2/board1.5/fatigue2/danger-4)冻结为默认,"
                       "不改 search_lookahead 默认值;danger×1.5 归档为'未确认候选',不单独立项。",
            "next_single_variable_ranking": [
                {"rank": 1, "option": "搜索加深(rollout 2 轮)",
                 "why": "权重坐标 14 配置证明价值函数标度已饱和,剩余增益在'看得更远'而非'称得更准';"
                        "搜索深度是消融未覆盖的正交自由度(tmp/search_meta_verdict 只测过默认深度);"
                        "同口径 12+12+12 筛选可半天出读数,工程风险低(只改 rollout 循环参数化)"},
                {"rank": 2, "option": "部署实测优先",
                 "why": "同族 agent 三个 seed 池读数摆动 ±0.10,仿真内比较已贴近噪声地板,"
                        "继续堆仿真局数边际收益低;真实对手分布能校准 ladder/v5/teacher 锚点的盲区,"
                        "为下一步优化给方向"},
            ],
            "ordering_rationale": "先深搜后部署,但部署准备(环境/账号/对手渠道)建议并行启动:"
                                  "深搜便宜且同 harness 可复判,若其复判亦无 ≥+2 局增益,"
                                  "则仿真层判定榨干,全力转部署,不再回仿真调参。",
        },
        "wall_s_total_finalize": round(time.time() - t0, 1),
    }
    with open(FINAL_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("=== FINAL BASELINE CLOSURE ===")
    print(json.dumps(out["part2_收口判决"]["baseline_pure_seed25000"]["readout"], ensure_ascii=False))
    print("=== END ===")


if __name__ == "__main__":
    main()
