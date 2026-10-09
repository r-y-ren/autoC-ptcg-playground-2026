"""可复现性探针:同 seed 单局 rules vs v5,同进程两遍+新进程验证,rewards 与步数对照。"""
import sys, os
ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for p in (ROOT, ROOT + "/src"): sys.path.insert(0, p)
os.chdir(ROOT)
from learn.search_lookahead import make_search_agent, _pick
from src.shared.play_local_match import play_local_match
META = [96,96,96,96,92,92,93,93,150,150,917,917,709,709,710,710,1071,1071,140,920,1227,1227,1227,1227,1231,1231,1182,1182,1184,1213,1121,1121,1121,1121,1094,1094,1094,1094,1080,1261,1261,1261,1261,1152,1152,1097,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
v5 = lambda obs, config=None: _pick((obs or {}).get("select") or {})
ag = make_search_agent(META, fold="rules")
tag = sys.argv[1] if len(sys.argv) > 1 else "A"
out = []
for rep in range(2):
    r = play_local_match(ag, v5, META, META, seed=31003, config={"bo": 3})
    out.append({"rewards": r["rewards"], "steps": r.get("n_steps")})
    print(tag, rep, out[-1], flush=True)
