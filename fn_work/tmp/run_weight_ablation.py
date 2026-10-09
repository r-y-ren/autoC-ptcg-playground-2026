"""七权重网格消融(fna-027):search_lookahead.state_value 叶子权重坐标下降 + 30 局复判。

阶段:
1) screen   坐标下降:每配置 12 镜像+12 vs ladder+12 vs v5(bo3),排序=ladder+v5 均值;
            改进需 ≥2 局(24 局合计胜局)才算数(引擎熵护栏);单配置 180s 预算,超时砍样本;
            最多 2 轮(第 2 轮仅在第 1 轮有改进时启动)。筛选池与 run_judge_pool 同口径
            (镜像 seed0+i、锚 seed0+1000+i、奇数局换席、bo3、deck=META),自实现仅为了
            带预算早停;不写 runs/ 正式通道。
2) confirm  最优配置 vs 现行基线,各 30 局四线(镜像/ladder/v5/teacher),
            run_judge_pool 原样调用(落 runs/ 正式通道),seed0=24000 vs 25000 错开。
3) seat     最优配置镜像 h2h<0.45 时加跑 30 局镜像双席 A/B 计数+二项检验。
结果增量落 tmp/weight_ablation_{screen,confirm}.json(stdout 打印全部在外层)。
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for _p in (ROOT, ROOT + "/src"):
    sys.path.insert(0, _p)
os.chdir(ROOT)

from learn.eval_agent import make_agent as make_teacher
from learn.search_lookahead import DEFAULT_WEIGHTS, W_KEYS, _pick, make_search_agent
from src.run_judge_pool.summarize_pool import summarize_pool
from src.shared.load_agent_callable import load_agent_callable
from src.shared.play_local_match import play_local_match

META = [96, 96, 96, 96, 92, 92, 93, 93, 150, 150, 917, 917, 709, 709, 710, 710,
        1071, 1071, 140, 920, 1227, 1227, 1227, 1227, 1231, 1231, 1182, 1182,
        1184, 1213, 1121, 1121, 1121, 1121, 1094, 1094, 1094, 1094, 1080, 1261,
        1261, 1261, 1261, 1152, 1152, 1097, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
assert len(META) == 60

N_SCREEN_MIRROR, N_SCREEN_ANCHOR = 12, 12
CONFIG_BUDGET_S = 180.0
SEED_SCREEN0, SEED_STEP = 20000, 100          # 筛选:配置间错开
SEED_CONFIRM_BEST, SEED_CONFIRM_BASE = 24000, 25000
SEED_SEAT = 26000
IMPROVE_MIN_GAMES = 2                          # 筛选差异 <2 局不作数


def v5(obs, config=None):
    sel = (obs or {}).get("select")
    return list(META) if sel is None else _pick(sel)


teacher = make_teacher()
ladder = load_agent_callable("submission_v9", "agent")


def readout(rep):
    out = {"mirror_h2h": rep["self_mirror_h2h"], "mirror_decided": rep["self_mirror_decided"]}
    for name in ("ladder", "v5", "teacher"):
        if name in rep["members"]:
            m = rep["members"][name]
            w, l = m["loss"], m["win"]   # 受测体视角:该锚的负场=受测体胜场
            dec = w + l
            out[name] = {"w": w, "l": l, "d": m["draw"], "failed": m["failed"],
                         "wr": round(w / dec, 4) if dec else None}
    return out


def run_screen_pool(weights, seed0, bo=3):
    """筛选池(run_judge_pool 同口径 + 180s 预算早停砍样本)。返回 (聚合读数, meta)。"""
    ag = make_search_agent(META, weights=weights)
    anchors = {"ladder": ladder, "v5": v5}
    rows, t0, cut = [], time.time(), False
    for i in range(N_SCREEN_MIRROR):
        if time.time() - t0 > CONFIG_BUDGET_S:
            cut = True
            break
        r = play_local_match(ag, ag, META, META, seed=seed0 + i, config={"bo": bo})
        rows.append({"label_a": "self", "label_b": "self",
                     **{k: r[k] for k in ("rewards", "failed")}})
    if not cut:
        for name, anchor in anchors.items():
            for i in range(N_SCREEN_ANCHOR):
                if time.time() - t0 > CONFIG_BUDGET_S:
                    cut = True
                    break
                swap = i % 2 == 1
                a, b = (anchor, ag) if swap else (ag, anchor)
                r = play_local_match(a, b, META, META, seed=seed0 + 1000 + i, config={"bo": bo})
                rows.append({"label_a": name if swap else "self",
                             "label_b": "self" if swap else name,
                             **{k: r[k] for k in ("rewards", "failed")}})
            if cut:
                break
    rep = summarize_pool(rows)
    ro = readout(rep)
    lg, v5r = ro.get("ladder"), ro.get("v5")
    score = round((lg["wr"] + v5r["wr"]) / 2, 4) if (lg and v5r and lg["wr"] is not None
                                                    and v5r["wr"] is not None) else None
    return ro, {"seed0": seed0, "n_rows": len(rows), "budget_cut": cut,
                "sec": round(time.time() - t0, 1), "score": score,
                "wins24": (lg["w"] if lg else 0) + (v5r["w"] if v5r else 0)}


SCREEN_ROWS = []
SCREEN_PATH = os.path.join(ROOT, "tmp", "weight_ablation_screen.json")


def _flush_screen(extra):
    with open(SCREEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"rows": SCREEN_ROWS, **extra}, f, ensure_ascii=False, indent=1)


def evaluate(tag, weights, seed0):
    t0 = time.time()
    ro, meta = run_screen_pool(weights, seed0)
    row = {"tag": tag, "weights": dict(weights), **meta, "readout": ro,
           "wall_s": round(time.time() - t0, 1)}
    SCREEN_ROWS.append(row)
    _flush_screen({"best_so_far": _best_so_far()})
    lg, v5r, mh = ro.get("ladder"), ro.get("v5"), ro.get("mirror_h2h")
    print(f"[screen] {tag:24s} seed0={seed0} score={meta['score']} "
          f"ladder={lg['w']}W/{lg['l']}L/{lg['d']}D v5={v5r['w']}W/{v5r['l']}L/{v5r['d']}D "
          f"mirror={mh} wins24={meta['wins24']} {meta['sec']}s"
          f"{' CUT' if meta['budget_cut'] else ''}", flush=True)
    return row


def _best_so_far():
    valid = [r for r in SCREEN_ROWS if r["score"] is not None and not r["budget_cut"]]
    return max(valid, key=lambda r: (r["score"], r["wins24"]))["tag"] if valid else None


def descent_round(round_no, incumbent, inc_row, counter):
    """一轮坐标下降:每权重 ×{0.5,1.5},改进需 score 更高且 wins24 ≥+2 局。"""
    improved = False
    for key in W_KEYS:
        cands = []
        for f in (0.5, 1.5):
            cfg = dict(incumbent)
            cfg[key] = round(incumbent[key] * f, 6)
            seed0 = SEED_SCREEN0 + counter[0] * SEED_STEP
            counter[0] += 1
            cands.append(evaluate(f"r{round_no}_{key}_x{f}", cfg, seed0))
        best_cand = max(cands, key=lambda r: (r["score"] if r["score"] is not None else -1,
                                              r["wins24"]))
        gain = best_cand["wins24"] - inc_row["wins24"]
        if best_cand["score"] is not None and inc_row["score"] is not None \
                and best_cand["score"] > inc_row["score"] + 1e-9 and gain >= IMPROVE_MIN_GAMES:
            print(f"[descent r{round_no}] adopt {key}: {incumbent[key]} -> "
                  f"{best_cand['weights'][key]} (score {inc_row['score']} -> {best_cand['score']}, "
                  f"wins24 {inc_row['wins24']} -> {best_cand['wins24']})", flush=True)
            incumbent, inc_row = best_cand["weights"], best_cand
            improved = True
        else:
            print(f"[descent r{round_no}] keep {key}={incumbent[key]} "
                  f"(best x={best_cand['weights'][key]}: score {inc_row['score']} -> "
                  f"{best_cand['score']}, gain={gain} 局 <{IMPROVE_MIN_GAMES} 或无增益)", flush=True)
    return incumbent, inc_row, improved


def binom_two_sided(k, n):
    if n == 0:
        return None
    p = sum(math.comb(n, i) for i in range(0, min(k, n - k) + 1)) / 2 ** n
    return round(min(1.0, 2 * p), 4)


def mirror_seat_check(weights, seed0=SEED_SEAT, n=30, bo=3):
    """镜像双席专查:自镜像 A 席(先手位)胜局占比 + 二项检验(席位差是否系统性)。"""
    ag = make_search_agent(META, weights=weights)
    a_w = b_w = dr = fl = 0
    games = []
    for i in range(n):
        r = play_local_match(ag, ag, META, META, seed=seed0 + i, config={"bo": bo})
        ra, rb = r["rewards"]
        if r["failed"]:
            fl += 1
            res = "failed"
        elif ra > rb:
            a_w += 1
            res = "seatA"
        elif rb > ra:
            b_w += 1
            res = "seatB"
        else:
            dr += 1
            res = "draw"
        games.append({"seed": seed0 + i, "rewards": r["rewards"], "result": res})
        print(f"[seat] {i + 1}/{n} seed={seed0 + i} {res} {r['rewards']}", flush=True)
    dec = a_w + b_w
    return {"n": n, "seed0": seed0, "seatA_win": a_w, "seatB_win": b_w,
            "draw": dr, "failed": fl, "decided": dec,
            "seatA_wr": round(a_w / dec, 4) if dec else None,
            "binom_p_two_sided": binom_two_sided(a_w, dec), "games": games}


def four_line(ag, seed0, tag):
    """30 局四线判决池(run_judge_pool 原样调用,落 runs/ 正式通道)。"""
    from src.run_judge_pool.run_judge_pool import run_judge_pool
    t0 = time.time()
    rep = run_judge_pool({"agent": ag, "n_mirror": 30, "n_anchor": 30,
                          "anchors": {"ladder": ladder, "v5": v5, "teacher": teacher},
                          "deck": META, "seed0": seed0, "bo": 3})
    ro = readout(rep)
    print(f"[confirm] {tag} seed0={seed0} {json.dumps(ro, ensure_ascii=False)} "
          f"({round(time.time() - t0, 1)}s)", flush=True)
    return {"tag": tag, "seed0": seed0, "readout": ro, "report": rep,
            "sec": round(time.time() - t0, 1)}


def main():
    t_start = time.time()
    counter = [0]
    # ---- 0) 基线筛选读数(同 12+12+12 样本,坐标下降的参照点) ----
    base_row = evaluate("r0_baseline", dict(DEFAULT_WEIGHTS),
                        SEED_SCREEN0 + counter[0] * SEED_STEP)
    counter[0] += 1

    # ---- 1) 坐标下降(最多 2 轮) ----
    incumbent, inc_row, improved = dict(DEFAULT_WEIGHTS), base_row, True
    rounds = 0
    while improved and rounds < 2:
        rounds += 1
        incumbent, inc_row, improved = descent_round(rounds, incumbent, inc_row, counter)
    _flush_screen({"incumbent": incumbent, "incumbent_tag": inc_row["tag"],
                   "rounds_run": rounds, "counter": counter[0]})

    # ---- 2) 30 局四线复判:最优 vs 基线(seed0=24000 vs 25000) ----
    best_ag = make_search_agent(META, weights=incumbent)
    base_ag = make_search_agent(META)  # 现行基线:weights=None=DEFAULT_WEIGHTS
    conf_best = four_line(best_ag, SEED_CONFIRM_BEST, f"best({inc_row['tag']})")
    conf_base = four_line(base_ag, SEED_CONFIRM_BASE, "baseline")

    # ---- 3) 镜像席位专查(最优 mirror<0.45 才跑) ----
    seat = None
    mh = conf_best["readout"].get("mirror_h2h")
    if mh is not None and mh < 0.45:
        print(f"[seat] mirror_h2h={mh}<0.45 → 加跑 30 局镜像双席专查", flush=True)
        seat = mirror_seat_check(incumbent)
    else:
        print(f"[seat] mirror_h2h={mh} ≥0.45,不触发席位专查", flush=True)

    # ---- 4) gate(沿用在案门槛:vs_ladder≥0.60 / vs_v5≥0.65 / mirror∈[0.35,0.65]) ----
    rb = conf_best["readout"]
    gate = {
        "vs_ladder>=0.60": bool(rb["ladder"]["wr"] is not None and rb["ladder"]["wr"] >= 0.60),
        "vs_v5>=0.65": bool(rb["v5"]["wr"] is not None and rb["v5"]["wr"] >= 0.65),
        "self_mirror in [0.35,0.65]": bool(rb["mirror_h2h"] is not None
                                           and 0.35 <= rb["mirror_h2h"] <= 0.65),
    }
    gate["pass"] = all(gate.values())

    out = {
        "task": "七权重网格消融:search_lookahead.state_value 权重坐标下降 + 30 局复判",
        "weights_order": list(W_KEYS),
        "default_weights": dict(DEFAULT_WEIGHTS),
        "screening": {"sample": {"mirror": N_SCREEN_MIRROR, "ladder": N_SCREEN_ANCHOR,
                                 "v5": N_SCREEN_ANCHOR, "bo": 3},
                      "rule": "排序=ladder+v5 均值(仅判定局);采纳需 score 更高且 wins24 ≥+2 局",
                      "seeds": f"配置 i: seed0={SEED_SCREEN0}+{SEED_STEP}i,镜像 seed0+i/锚 seed0+1000+i",
                      "rounds_run": rounds, "incumbent": incumbent,
                      "incumbent_tag": inc_row["tag"],
                      "baseline_row": base_row,
                      "n_configs": len(SCREEN_ROWS)},
        "confirm": {"best": conf_best, "baseline": conf_base,
                    "delta": {k: round((rb[k]["wr"] or 0) - (conf_base["readout"][k]["wr"] or 0), 4)
                              for k in ("ladder", "v5", "teacher")},
                    "delta_mirror": round((rb["mirror_h2h"] or 0)
                                          - (conf_base["readout"]["mirror_h2h"] or 0), 4),
                    "paired_note": "run_judge_pool 内配对种子设计(seed0+i/seed0+1000+i);"
                                   "两配置间 seed0=24000 vs 25000 错开(防种子过拟合,故为非配对样本)"},
        "mirror_seat_check": seat,
        "gate": gate,
        "wall_s_total": round(time.time() - t_start, 1),
    }
    with open(os.path.join(ROOT, "tmp", "weight_ablation_confirm.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("=== FINAL_JSON ===")
    print(json.dumps(out, ensure_ascii=False))
    print("=== END ===")


if __name__ == "__main__":
    main()
