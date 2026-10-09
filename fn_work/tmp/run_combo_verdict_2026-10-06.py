"""组合态(对手模型升级补丁 + 叶子奖赏符号修正)复判:B 小样本对照 + C 四线 30 局判决。
受测体: learn.search_lookahead.make_search_agent(META_DECK)(默认 pred_deck=META、fold=老师式;
state_value 奖赏项已按 已拿=6−剩余 修正)。两改均未 commit,即测即此态。
打印全部在外层(引擎吞 agent 内 stdout)。判决行由 run_judge_pool 自动写
runs/judge-pool-2026-10-06.jsonl(seed0=11000,与 fna-025 的 9000 / fna-026 的 8000 错开)。"""
import sys, os, time, json, statistics

ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for p in (ROOT, ROOT + "/src"): sys.path.insert(0, p)
os.chdir(ROOT)

from shared.load_agent_callable import load_agent_callable
from learn.eval_agent import make_agent as make_teacher
from learn.search_lookahead import make_search_agent, _pick, META_DECK
import src.run_judge_pool.run_judge_pool as rjp_mod
from src.run_judge_pool.run_judge_pool import run_judge_pool
from src.shared.play_local_match import play_local_match as _plm_raw
from kaggle_environments.envs.cabt import cabt

META = list(META_DECK)
DEF = list(cabt.deck)
search_ag = make_search_agent(META)  # pred_deck 默认 META_DECK、fold 默认老师式
def v5(obs, config=None):
    sel = (obs or {}).get("select")
    return list(DEF) if sel is None else _pick(sel)
teacher = make_teacher()
ladder = load_agent_callable("submission_v9", "agent")

# ---- 逐局计时/留痕包装(run_judge_pool 内部按名调用,补丁其模块命名空间) ----
GAMES = []
_state = {"idx": 0, "group": "pool"}

def _plm_timed(a, b, deck_a, deck_b, seed, config=None):
    t0 = time.time()
    r = _plm_raw(a, b, deck_a, deck_b, seed=seed, config=config)
    dt = time.time() - t0
    GAMES.append({
        "idx": _state["idx"], "group": _state["group"], "sec": round(dt, 3),
        "rewards": r["rewards"], "statuses": r["statuses"], "failed": r["failed"],
        "seed": seed, "n_steps": r["n_steps"],
        "error": r.get("error") if r.get("failed") else None,
    })
    _state["idx"] += 1
    return r

rjp_mod.play_local_match = _plm_timed

# ---- B. 小样本对照(各 6 局 bo3,seed=600+g,奇数局交换席位) ----
def run_control2(name, opp, n=6, seed0=600, bo=3):
    _state["group"] = f"ctrl_{name}"
    w = l = d = fl = 0
    detail = []
    for g in range(n):
        swap = g % 2 == 1
        a, b = (opp, search_ag) if swap else (search_ag, opp)
        r = _plm_timed(a, b, META, META, seed=seed0 + g, config={"bo": bo})
        ra, rb = r["rewards"]
        self_r = rb if swap else ra
        opp_r = ra if swap else rb
        if r["failed"]:
            fl += 1
            detail.append({"seed": seed0 + g, "swap": swap, "result": "failed"})
        elif self_r > opp_r:
            w += 1; detail.append({"seed": seed0 + g, "swap": swap, "result": "win"})
        elif self_r < opp_r:
            l += 1; detail.append({"seed": seed0 + g, "swap": swap, "result": "loss"})
        else:
            d += 1; detail.append({"seed": seed0 + g, "swap": swap, "result": "draw"})
    return {"opponent": name, "n": n, "bo": bo, "seed0": seed0,
            "self_win": w, "self_loss": l, "draw": d, "failed": fl, "games": detail}

ctrl_random = run_control2("random", cabt.random_agent)
ctrl_v5 = run_control2("v5", v5)
ctrl_teacher = run_control2("teacher", teacher)

# ---- C. 四线 30 局判决池 ----
t0 = time.time()
_state["group"] = "pool"
rep = run_judge_pool({"agent": search_ag, "n_mirror": 30, "n_anchor": 30,
                      "anchors": {"ladder": ladder, "v5": v5, "teacher": teacher},
                      "deck": META, "seed0": 11000, "bo": 3})
pool_wall = time.time() - t0

# ---- 读数汇总(受测体视角;self_winrate=members[名].loss/members[名].n) ----
def self_wr(name):
    m = rep["members"][name]
    n = m["n"]
    return (m["loss"] / n) if n else None

lines = {
    "vs_ladder": self_wr("ladder"),
    "vs_v5": self_wr("v5"),
    "vs_teacher": self_wr("teacher"),
    "self_mirror_h2h": rep["self_mirror_h2h"],
}
gate = {
    "vs_ladder>=0.60": bool(lines["vs_ladder"] is not None and lines["vs_ladder"] >= 0.60),
    "vs_v5>=0.65": bool(lines["vs_v5"] is not None and lines["vs_v5"] >= 0.65),
    "self_mirror in [0.35,0.65]": bool(lines["self_mirror_h2h"] is not None and 0.35 <= lines["self_mirror_h2h"] <= 0.65),
}
gate["pass"] = all(gate.values())

# ---- 逐局胜负明细(按池内顺序重建:0-29 镜像,30-59 ladder,60-89 v5,90-119 teacher) ----
pool_games = [g for g in GAMES if g["group"] == "pool"]
order = [("mirror", 0), ("ladder", 30), ("v5", 60), ("teacher", 90)]
games_detail = {}
for name, off in order:
    seq = []
    for i in range(30):
        g = pool_games[off + i]
        if name == "mirror":
            ra, rb = g["rewards"]
            res = "draw" if ra == rb else ("seat0_win" if ra > rb else "seat1_win")
            seq.append({"i": i, "seed": g["seed"], "result": res, "n_steps": g["n_steps"]})
        else:
            swap = i % 2 == 1
            ra, rb = g["rewards"]
            self_r, opp_r = (rb, ra) if swap else (ra, rb)
            res = "failed" if g["failed"] else ("win" if self_r > opp_r else ("loss" if self_r < opp_r else "draw"))
            seq.append({"i": i, "seed": g["seed"], "swap": swap, "result": res, "n_steps": g["n_steps"]})
    games_detail[name] = seq

secs = [g["sec"] for g in GAMES]
out = {
    "change": "组合态=对手模型层升级(_fill 真实分布抽样+_pick_greedy 老师式折叠)+叶子奖赏项符号修正(已拿=6−剩余);权重冻结;两改均未 commit",
    "report": rep,
    "lines": lines,
    "gate": gate,
    "baselines": {
        "fna-025_旧叶子+Grookey填充": {"vs_ladder": 0.400, "vs_v5": 0.433, "vs_teacher": 0.667, "self_mirror_h2h": 0.567, "seed0": 9000},
        "fna-026_反号叶子+对手模型": {"vs_ladder": 0.300, "vs_v5": 0.367, "vs_teacher": 0.433, "self_mirror_h2h": 0.633, "seed0": 8000},
    },
    "controls": {"vs_random_6": ctrl_random, "vs_v5_6": ctrl_v5, "vs_teacher_6": ctrl_teacher},
    "games_detail": games_detail,
    "timing": {
        "pool_wall_s": round(pool_wall, 1),
        "n_games_timed": len(GAMES),
        "mean_s": round(statistics.fmean(secs), 2) if secs else None,
        "max_s": max(secs) if secs else None,
        "min_s": min(secs) if secs else None,
        "by_group": {gname: {"n": len([x for x in GAMES if x["group"] == gname]),
                             "mean_s": round(statistics.fmean([x["sec"] for x in GAMES if x["group"] == gname]), 2),
                             "max_s": max([x["sec"] for x in GAMES if x["group"] == gname])}
                     for gname in sorted(set(g["group"] for g in GAMES))},
    },
    "anomalies": [g for g in GAMES if g["failed"]],
    "paired_seeds": rep.get("paired_seeds"),
    "determinism_field": rep.get("determinism"),
}

with open(os.path.join(ROOT, "tmp", "combo_verdict_2026-10-06.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print("=== SUMMARY ===")
print(json.dumps({"lines": lines, "gate": gate,
                  "controls": {k: {kk: v[kk] for kk in ("self_win", "self_loss", "draw", "failed")}
                               for k, v in out["controls"].items()},
                  "timing": out["timing"], "anomalies": out["anomalies"],
                  "self_members": rep["members"]}, ensure_ascii=False, indent=1))
print("=== END ===")
