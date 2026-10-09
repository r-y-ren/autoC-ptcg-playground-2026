"""fna-029 修复验证:v5 线 30 局(seed0=31000 口径,seeds 32000+i)+ 四线全套(seed0=32000,seeds 33000+)。
四线口径同 tmp/run_depth2_final_verdict.py(n_mirror=30,n_anchor=30,bo=3,anchors ladder/v5/teacher)。
用法: .venv/bin/python tmp/v5reg_verify.py v5|four
"""
import sys, os, json, time, statistics
ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for p in (ROOT, ROOT + "/src"): sys.path.insert(0, p)
os.chdir(ROOT)

from shared.load_agent_callable import load_agent_callable
from learn.eval_agent import make_agent as make_teacher
from learn.search_lookahead import make_search_agent, _pick
from src.shared.play_local_match import play_local_match

META = [96,96,96,96,92,92,93,93,150,150,917,917,709,709,710,710,1071,1071,140,920,1227,1227,1227,1227,1231,1231,1182,1182,1184,1213,1121,1121,1121,1121,1094,1094,1094,1094,1080,1261,1261,1261,1261,1152,1152,1097,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
v5_def = lambda obs, config=None: _pick((obs or {}).get("select") or {})

def line(agent, opp, opp_name, seeds, n=30):
    rows = []
    for i in range(n):
        swap = i % 2 == 1
        a, b = (opp, agent) if swap else (agent, opp)
        r = play_local_match(a, b, META, META, seed=seeds[i], config={"bo": 3})
        my = r["rewards"][1] if swap else r["rewards"][0]
        oppv = r["rewards"][0] if swap else r["rewards"][1]
        res = "W" if my > oppv else ("L" if my < oppv else "D")
        rows.append({"i": i, "seed": seeds[i], "swap": swap, "res": res,
                     "rewards": r["rewards"], "failed": r["failed"]})
        print(f"  [{opp_name}] {i:02d} seed={seeds[i]} swap={int(swap)} {res}", flush=True)
    w = sum(1 for x in rows if x["res"] == "W"); l = sum(1 for x in rows if x["res"] == "L")
    return {"opp": opp_name, "n": n, "W": w, "L": l, "D": n - w - l,
            "wr": round(w / (w + l), 3) if (w + l) else None, "games": rows}

MODE = sys.argv[1] if len(sys.argv) > 1 else "v5"
agent = make_search_agent(META, fold="rules")  # 修复后(现行默认)
out = {"mode": MODE, "fold": "rules+fna029_fix", "ts": time.strftime("%F %T")}
if MODE == "v5":
    SEED0 = 31000
    out["protocol"] = {"seed0": SEED0, "anchor_seeds": "seed0+1000+i", "n": 30, "bo": 3}
    out["v5_line"] = line(agent, v5_def, "v5", [SEED0 + 1000 + i for i in range(30)])
    print("V5_LINE", json.dumps({k: v for k, v in out["v5_line"].items() if k != "games"}, ensure_ascii=False), flush=True)
else:
    SEED0 = 32000
    ladder = load_agent_callable("submission_v9", "agent")
    teacher = make_teacher()
    out["protocol"] = {"seed0": SEED0, "anchor_seeds": "seed0+1000+i", "mirror_seeds": "seed0+i", "n": 30, "bo": 3}
    out["v5_line"] = line(agent, v5_def, "v5", [SEED0 + 1000 + i for i in range(30)])
    out["ladder_line"] = line(agent, ladder, "ladder", [SEED0 + 1000 + i for i in range(30)])
    out["teacher_line"] = line(agent, teacher, "teacher", [SEED0 + 1000 + i for i in range(30)])
    out["mirror_line"] = line(agent, agent, "mirror(self)", [SEED0 + i for i in range(30)])
    summ = {k: {kk: vv for kk, vv in v.items() if kk != "games"} for k, v in out.items()
            if isinstance(v, dict) and "wr" in v}
    print("FOUR_LINES", json.dumps(summ, ensure_ascii=False), flush=True)
with open(ROOT + f"/tmp/v5reg_verify_{MODE}.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
