"""最终四线 30 局判决(最有希望模式):seed0=29000,anchors={ladder,v5,teacher},deck=META,n_mirror=30,n_anchor=30,bo=3。
用法: .venv/bin/python tmp/run_depth2_final_verdict.py <arm>   # arm∈A_depth2|B_rules|C_depth2_rules
对照带(历史四线,线序 ladder/v5/teacher/mirror):@9000 .400/.433/.667/.567 @12000 .500/.533/.700/.367 @25000 .333/.633/.533/.467
"""
import sys, os, time, json, statistics
ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for p in (ROOT, ROOT + "/src"): sys.path.insert(0, p)
os.chdir(ROOT)
ARM = sys.argv[1] if len(sys.argv) > 1 else "C_depth2_rules"
KW = {"A_depth2": dict(depth=2), "B_rules": dict(fold="rules"),
      "C_depth2_rules": dict(depth=2, fold="rules")}[ARM]

from shared.load_agent_callable import load_agent_callable
from learn.eval_agent import make_agent as make_teacher
from learn.search_lookahead import make_search_agent, _pick
import src.run_judge_pool.run_judge_pool as rjp_mod
from src.run_judge_pool.run_judge_pool import run_judge_pool
from src.shared.play_local_match import play_local_match as _plm_raw

META = [96,96,96,96,92,92,93,93,150,150,917,917,709,709,710,710,1071,1071,140,920,1227,1227,1227,1227,1231,1231,1182,1182,1184,1213,1121,1121,1121,1121,1094,1094,1094,1094,1080,1261,1261,1261,1261,1152,1152,1097,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

ladder = load_agent_callable("submission_v9", "agent")
def v5(obs, config=None):
    sel = (obs or {}).get("select")
    return _pick(sel)
teacher = make_teacher()

acc = {"t": 0.0, "n": 0}
base_make = make_search_agent
raw_agent = base_make(META, **KW)
def timed_ag(obs, config=None):
    if (obs or {}).get("select") is None:
        return list(META)
    t0 = time.time()
    r = raw_agent(obs, config)
    acc["t"] += time.time() - t0
    acc["n"] += 1
    return r

GAMES = []
_state = {"idx": 0, "group": "pool"}
def _plm_timed(a, b, deck_a, deck_b, seed, config=None):
    t0 = time.time()
    r = _plm_raw(a, b, deck_a, deck_b, seed=seed, config=config)
    GAMES.append({"idx": _state["idx"], "group": _state["group"], "sec": round(time.time() - t0, 3),
                  "rewards": r["rewards"], "failed": r["failed"], "seed": seed, "n_steps": r["n_steps"]})
    _state["idx"] += 1
    return r
rjp_mod.play_local_match = _plm_timed

t0 = time.time()
rep = run_judge_pool({"agent": timed_ag, "n_mirror": 30, "n_anchor": 30,
                      "anchors": {"ladder": ladder, "v5": v5, "teacher": teacher},
                      "deck": META, "seed0": 29000, "bo": 3})
pool_wall = time.time() - t0

def self_wr(name):
    m = rep["members"][name]
    n = m["win"] + m["loss"]
    return round(m["loss"] / n, 3) if n else None
lines = {"vs_ladder": self_wr("ladder"), "vs_v5": self_wr("v5"),
         "vs_teacher": self_wr("teacher"), "self_mirror_h2h": rep["self_mirror_h2h"]}
dec_ms = round(1000 * acc["t"] / acc["n"], 1) if acc["n"] else None
pool_secs = [g["sec"] for g in GAMES]
out = {"arm": ARM, "kw": KW, "seed0": 29000, "report": rep, "lines": lines,
       "timing": {"pool_wall_s": round(pool_wall, 1), "n_games": len(GAMES),
                  "mean_s": round(statistics.fmean(pool_secs), 2) if pool_secs else None,
                  "max_s": max(pool_secs) if pool_secs else None,
                  "dec_ms": dec_ms, "n_dec": acc["n"]},
       "failed": [g for g in GAMES if g["failed"]]}
with open(ROOT + f"/tmp/depth2_final_verdict_{ARM}.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(json.dumps({"FINAL": ARM, "lines": lines, "timing": out["timing"],
                  "n_failed": len(out["failed"])}), flush=True)
