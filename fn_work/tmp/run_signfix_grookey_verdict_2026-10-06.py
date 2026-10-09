"""2×2 收口第 4 格复判:新号(叶子奖赏符号修正)+Grookey 通用填充,对手模型补丁已回滚。
受测体: learn.search_lookahead.make_search_agent(META)(厚叶子/凸折价/攻击优先折叠;
state_value 奖赏项已按 已拿=6−剩余 修正;_fill=Grookey 89+Basic{W} 3)。
打印全部在外层(引擎吞 agent 内 stdout)。判决行由 run_judge_pool 自动写
runs/judge-pool-2026-10-06.jsonl(seed0=12000,与 fna-025 的 9000 / fna-026 的 8000 /
新号+对手模型的 11000 错开)。"""
import sys, os, time, json, statistics

ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for p in (ROOT, ROOT + "/src"): sys.path.insert(0, p)
os.chdir(ROOT)

from shared.load_agent_callable import load_agent_callable
from learn.eval_agent import make_agent as make_teacher
from learn.search_lookahead import make_search_agent, _pick
import src.run_judge_pool.run_judge_pool as rjp_mod
from src.run_judge_pool.run_judge_pool import run_judge_pool
from src.shared.play_local_match import play_local_match as _plm_raw
from kaggle_environments.envs.cabt import cabt

META = [96,96,96,96,92,92,93,93,150,150,917,917,709,709,710,710,1071,1071,140,920,1227,1227,1227,1227,1231,1231,1182,1182,1184,1213,1121,1121,1121,1121,1094,1094,1094,1094,1080,1261,1261,1261,1261,1152,1152,1097,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
assert len(META) == 60 == len(cabt.deck), len(META)
DEF = list(cabt.deck)
search_ag = make_search_agent(META)
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
                      "deck": META, "seed0": 12000, "bo": 3})
pool_wall = time.time() - t0

# ---- 读数汇总(受测体视角) ----
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

secs = [g["sec"] for g in GAMES]
out = {
    "cell": "新号+Grookey(符号修正+通用填充;对手模型补丁已回滚)",
    "change": "2×2 第 4 格:fna-025 基线上仅改叶子奖赏项符号(prize=剩余堆→已拿=6−剩余);_fill=Grookey 89/Basic{W} 3、_pick_greedy 攻击优先折叠、厚叶子五项与凸折价全部保持 fna-025 态",
    "seed0": 12000,
    "report": rep,
    "lines": lines,
    "gate": gate,
    "controls": {"vs_random_6": ctrl_random, "vs_v5_6": ctrl_v5, "vs_teacher_6": ctrl_teacher},
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

with open(os.path.join(ROOT, "tmp", "signfix_grookey_verdict_2026-10-06.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print("=== FINAL_JSON ===")
print(json.dumps(out, ensure_ascii=False))
print("=== END ===")
