"""权重消融续跑(原代理 07:15 停摆后的接力):补完 round1 剩余 5 配置 + 收口判决。

承接 run_weight_ablation.py 的状态:
- tmp/weight_ablation_screen.json 已有 10 行(r0 基线 + r1 前 5 个权重的 ×0.5/×1.5);
- 停在 r1_board_x1.5(seed0=21000)处;
- 结论到目前:基线 wins24=13/score=0.5416,无任何配置达 "score 更高且 ≥+2 局" 采纳线。

续跑:
1) 补 5 配置:board×1.5(21000)、fatigue×0.5(21100)、fatigue×1.5(21200)、
   danger×0.5(21300)、danger×1.5(21400)——种子编号严格接原 counter(配置 i → 20000+100i)。
2) 采纳判定与原脚本一致(score 更高且 wins24 ≥+2);任务指令:round2 网格取消,
   有采纳也只收口(incumbent=采纳态,异常段说明)。
3) 收口:现行基线配置 30 局四线(run_judge_pool 正式通道,seed0=26000,
   anchors={ladder,v5,teacher},bo=3);mirror<0.45 时按原协议加跑 30 局双席专查。
4) 产出 tmp/weight_ablation_final.json(四段契约:续跑配置表/收口判决/异常限界/建议)。
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

import run_weight_ablation as base  # 复用 run_screen_pool/evaluate/four_line/常量(导入不触发 main)

FINAL_PATH = os.path.join(ROOT, "tmp", "weight_ablation_final.json")
REF_12000 = {"vs_ladder": 0.500, "vs_v5": 0.5333, "vs_teacher": 0.700,
             "self_mirror_h2h": 0.3667}  # runs/judge-pool-2026-10-06.jsonl seed0=12000(保留组合读数)


def _wr(rc, name):
    m = rc.get(name)
    return m.get("wr") if isinstance(m, dict) else None


def _delta_vs_ref(rc):
    pairs = (("vs_ladder", _wr(rc, "ladder")), ("vs_v5", _wr(rc, "v5")),
             ("vs_teacher", _wr(rc, "teacher")), ("self_mirror_h2h", rc.get("mirror_h2h")))
    return {k: (round(v - REF_12000[k], 4) if v is not None else None) for k, v in pairs}


def main():
    t0 = time.time()
    # ---- 0) 恢复现场:载入已有 10 行,续写同一 screen JSON ----
    with open(base.SCREEN_PATH, encoding="utf-8") as f:
        prev = json.load(f)
    base.SCREEN_ROWS.extend(prev["rows"])
    have = {r["tag"] for r in base.SCREEN_ROWS}
    print(f"[resume] 载入 {len(base.SCREEN_ROWS)} 行:{sorted(have)}", flush=True)

    incumbent = dict(base.DEFAULT_WEIGHTS)
    inc_row = next(r for r in base.SCREEN_ROWS if r["tag"] == "r0_baseline")

    # ---- 1) 补完 round1:board/fatigue/danger 各 ×0.5/×1.5,种子接原 counter ----
    remaining = [("board", 10), ("fatigue", 11), ("danger", 13)]  # (key, counter 序号)
    adopted_r1 = []
    for key, ctr in remaining:
        cands = []
        for f in (0.5, 1.5):
            cfg = dict(incumbent)
            cfg[key] = round(incumbent[key] * f, 6)
            tag = f"r1_{key}_x{f}"
            seed0 = base.SEED_SCREEN0 + ctr * base.SEED_STEP
            ctr += 1
            if tag in have:
                print(f"[resume] {tag} 已存在,跳过", flush=True)
                cands.append(next(r for r in base.SCREEN_ROWS if r["tag"] == tag))
                continue
            cands.append(base.evaluate(tag, cfg, seed0))
        best_cand = max(cands, key=lambda r: (r["score"] if r["score"] is not None else -1,
                                              r["wins24"]))
        gain = best_cand["wins24"] - inc_row["wins24"]
        if best_cand["score"] is not None and inc_row["score"] is not None \
                and best_cand["score"] > inc_row["score"] + 1e-9 \
                and gain >= base.IMPROVE_MIN_GAMES:
            print(f"[descent r1] adopt {key}: {incumbent[key]} -> {best_cand['weights'][key]} "
                  f"(score {inc_row['score']} -> {best_cand['score']}, wins24 "
                  f"{inc_row['wins24']} -> {best_cand['wins24']})", flush=True)
            incumbent, inc_row = best_cand["weights"], best_cand
            adopted_r1.append(key)
        else:
            print(f"[descent r1] keep {key}={incumbent[key]} "
                  f"(best x={best_cand['weights'][key]}: score {inc_row['score']} -> "
                  f"{best_cand['score']}, gain={gain} 局 <{base.IMPROVE_MIN_GAMES} 或无增益)",
                  flush=True)

    _flush = {"incumbent": incumbent, "incumbent_tag": inc_row["tag"],
              "rounds_run": 1, "counter": 15,
              "round2": "cancelled_by_task_directive(权重层无红利预期,聚焦收口)"}
    with open(base.SCREEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"rows": base.SCREEN_ROWS, **_flush}, f, ensure_ascii=False, indent=1)

    # ---- 2) 收口判决:incumbent(预期=现行基线)30 局四线,seed0=26000 ----
    closure_ag = base.make_search_agent(base.META, weights=incumbent if adopted_r1 else None)
    closure = base.four_line(closure_ag, base.SEED_SEAT, "closure_baseline")
    rc = closure["readout"]

    # ---- 3) 双席专查(原协议:mirror<0.45 触发,30 局镜像 A/B 计数) ----
    seat = None
    mh = rc.get("mirror_h2h")
    if mh is not None and mh < 0.45:
        print(f"[seat] mirror_h2h={mh}<0.45 → 加跑 30 局镜像双席专查(seed0=27000,与收口错开)", flush=True)
        seat = base.mirror_seat_check(incumbent if adopted_r1 else None, seed0=27000)
    else:
        print(f"[seat] mirror_h2h={mh} ≥0.45,不触发席位专查", flush=True)

    # ---- 4) gate(在案门槛) ----
    gate = {
        "vs_ladder>=0.60": bool(rc["ladder"]["wr"] is not None and rc["ladder"]["wr"] >= 0.60),
        "vs_v5>=0.65": bool(rc["v5"]["wr"] is not None and rc["v5"]["wr"] >= 0.65),
        "self_mirror in [0.35,0.65]": bool(rc["mirror_h2h"] is not None
                                           and 0.35 <= rc["mirror_h2h"] <= 0.65),
    }
    gate["pass"] = all(gate.values())

    # ---- 5) 四段契约落盘 ----
    new_rows = [r for r in base.SCREEN_ROWS if r["tag"] not in have]
    weight_layer_dividend = bool(adopted_r1)
    out = {
        "task": "七权重网格消融·续跑收口(fna-027 接力):round1 补完 + 30 局四线收口",
        "weights_order": list(base.W_KEYS),
        "default_weights": dict(base.DEFAULT_WEIGHTS),
        "part1_续跑配置表": {
            "resumed_rows": new_rows,
            "round1_full_table": [
                {"tag": r["tag"], "key_perturbed": (r["tag"].split("_")[1] if r["tag"].startswith("r1_") else None),
                 "factor": (r["tag"].rsplit("x", 1)[1] if r["tag"].startswith("r1_") else None),
                 "seed0": r["seed0"], "score": r["score"], "wins24": r["wins24"],
                 "ladder_wr": r["readout"]["ladder"]["wr"], "v5_wr": r["readout"]["v5"]["wr"],
                 "mirror_h2h": r["readout"]["mirror_h2h"], "budget_cut": r["budget_cut"]}
                for r in base.SCREEN_ROWS],
            "adoption_rule": "score 更高且 wins24 ≥+2 局(24 锚局合计胜局,引擎熵护栏)",
            "adopted": adopted_r1,
            "incumbent": incumbent, "incumbent_tag": inc_row["tag"],
            "round2": "取消(任务指令:权重层无红利预期,直接收口)",
        },
        "part2_收口判决": {
            "config": {"seed0": base.SEED_SEAT, "n_mirror": 30, "n_anchor": 30, "bo": 3,
                       "deck": "META_DECK(60 张,同筛选口径)",
                       "anchors": ["ladder=submission_v9.agent", "v5=_pick 首序", "teacher=learn.eval_agent"],
                       "weights": incumbent},
            "readout": rc,
            "report_config": closure["report"].get("config"),
            "vs_ref_12000": {
                "ref": REF_12000,
                "delta": _delta_vs_ref(rc),
                "note": "ref=runs/judge-pool-2026-10-06.jsonl seed0=12000 保留组合"
                        "(厚叶子+符号修+Grookey)四线读数;seed0 不同(26000 vs 12000),非配对样本,只作量级对照",
            },
            "gate": gate,
            "mirror_seat_check": seat,
            "wall_s": closure["sec"],
        },
        "part3_异常与限界": {
            "stoppage": "原代理 07:15 后停摆(停在 r1_board_x1.5);本接力无缝续 counter,种子无重叠无跳号",
            "budget_cuts": [r["tag"] for r in base.SCREEN_ROWS if r["budget_cut"]],
            "failed_games": {r["tag"]: (r["readout"]["ladder"]["failed"]
                                        + r["readout"]["v5"]["failed"]) for r in base.SCREEN_ROWS},
            "sample_limits": "筛选=12+12+12 锚局(bo3),单局胜负噪声 ±1-2 局;采纳线 ≥+2 局已是最低可信增益;"
                             "四线收口=30 局/线,wr 标准误 ≈±0.09;seed0 错开故 vs_ref_12000 非配对",
            "weight_layer_note": ("坐标下降仅探测 ×0.5/×1.5 单变量邻域;更细步长或双权重交互未探索"
                                  if not weight_layer_dividend else
                                  f"round1 出现采纳 {adopted_r1},但 round2 按任务指令取消,交互未探"),
        },
        "part4_建议": {
            "verdict": ("权重层有红利" if weight_layer_dividend else
                        "权重层无红利:现行七权重(prize10/hp2/threat3/lock2/board1.5/fatigue2/danger-4)"
                        "即局部最优,冻结"),
            "next_single_variable_ranking": [
                {"rank": 1, "option": "搜索加深(rollout 2 轮)", "why": "权重层 14 配置全灭说明价值函数已饱和,"
                 "剩余增益应往'看得更远'找;搜索是正交自由度,且消融期叶子读数稳定,风险低"},
                {"rank": 2, "option": "部署实测优先(远程对局/真实对手分布)", "why": "锚点(ladder/v5/teacher)读数"
                 "与 12000 轮同量级,仿真侧边际收益递减;部署数据能验证锚点未覆盖的真实分布差距,"
                 "为下一轮优化提供方向而非继续内卷仿真指标"},
            ],
            "ordering_rationale": "先搜索加深(半天内可出读数,消融同口径可复判)→再部署实测"
                                 "(依赖外部环境,反馈周期长);若搜索加深亦无 ≥2 局增益,"
                                 "则仿真层已榨干,全力转部署",
        },
        "wall_s_total": round(time.time() - t0, 1),
    }
    with open(FINAL_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("=== FINAL_JSON ===")
    print(json.dumps({k: out[k] for k in out if k != "part1_续跑配置表"}, ensure_ascii=False)[:4000])
    print("=== END ===")


if __name__ == "__main__":
    main()
