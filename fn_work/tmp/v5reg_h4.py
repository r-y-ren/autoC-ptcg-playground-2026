"""H4 定性:v5 线 30 局 fold=rules(seed0=30000 口径,seeds 31000+i)+ 同种子 fold=greedy 配对对照。
单变量=fold;同 seed 同席位,直接读 fold 增益/损失(局级配对)。
用法: .venv/bin/python tmp/v5reg_h4.py
"""
import sys, os, json
ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for p in (ROOT, ROOT + "/src"): sys.path.insert(0, p)
os.chdir(ROOT)

from shared.load_agent_callable import load_agent_callable
from learn.search_lookahead import make_search_agent, _pick
from src.shared.play_local_match import play_local_match

META = [96,96,96,96,92,92,93,93,150,150,917,917,709,709,710,710,1071,1071,140,920,1227,1227,1227,1227,1231,1231,1182,1182,1184,1213,1121,1121,1121,1121,1094,1094,1094,1094,1080,1261,1261,1261,1261,1152,1152,1097,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
SEED0 = 30000
N = 30

ladder_like = None
v5_def = lambda obs, config=None: _pick((obs or {}).get("select") or {})

def run_line(agent, tag):
    rows = []
    for i in range(N):
        swap = i % 2 == 1
        seed = SEED0 + 1000 + i
        a, b = (v5_def, agent) if swap else (agent, v5_def)
        r = play_local_match(a, b, META, META, seed=seed, config={"bo": 3})
        # 受测体=agent;rewards=[ seat0, seat1 ]
        my = r["rewards"][1] if swap else r["rewards"][0]
        opp = r["rewards"][0] if swap else r["rewards"][1]
        res = "W" if my > opp else ("L" if my < opp else "D")
        rows.append({"i": i, "seed": seed, "swap": swap, "res": res,
                     "rewards": r["rewards"], "failed": r["failed"], "n_steps": r.get("n_steps")})
        print(f"[{tag}] {i:02d} seed={seed} swap={int(swap)} {res} rewards={r['rewards']} steps={r.get('n_steps')}", flush=True)
    w = sum(1 for x in rows if x["res"] == "W"); l = sum(1 for x in rows if x["res"] == "L")
    return {"tag": tag, "seed0": SEED0, "n": N, "W": w, "L": l, "D": N - w - l,
            "wr": round(w / (w + l), 3) if (w + l) else None, "games": rows}

out = {"rules": run_line(make_search_agent(META, fold="rules"), "rules"),
       "greedy": run_line(make_search_agent(META, fold="greedy"), "greedy")}
# 配对差:同 i 同 seed 同席位,两 fold 结果对照
pair = []
for i in range(N):
    rr, gg = out["rules"]["games"][i], out["greedy"]["games"][i]
    pair.append({"i": i, "rules": rr["res"], "greedy": gg["res"]})
out["paired"] = pair
n_diff_w = sum(1 for p in pair if p["rules"] == "W" and p["greedy"] == "L")
n_diff_l = sum(1 for p in pair if p["rules"] == "L" and p["greedy"] == "W")
out["pair_delta"] = {"rules_only_W": n_diff_w, "greedy_only_W": n_diff_l}
with open(ROOT + "/tmp/v5reg_h4.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("SUMMARY", json.dumps({k: out[k] for k in ("rules", "greedy", "pair_delta")},
                            default=lambda o: {kk: vv for kk, vv in o.items() if kk != "games"},
                            ensure_ascii=False), flush=True)
