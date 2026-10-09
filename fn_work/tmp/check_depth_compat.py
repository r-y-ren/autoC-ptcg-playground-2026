"""逐位兼容校验:旧版(git HEAD)vs 新版 depth=1+greedy,同一批实抓观测逐决策对照。"""
import sys, os, json, importlib.util
ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for p in (ROOT, ROOT + "/src"): sys.path.insert(0, p)
os.chdir(ROOT)
from learn import search_lookahead as new_sl
spec = importlib.util.spec_from_file_location("old_sl", ROOT + "/tmp/_old_search_lookahead_v01.py")
old_sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_sl)
from src.shared.play_local_match import play_local_match
from kaggle_environments.envs.cabt import cabt

META = [96,96,96,96,92,92,93,93,150,150,917,917,709,709,710,710,1071,1071,140,920,1227,1227,1227,1227,1231,1231,1182,1182,1184,1213,1121,1121,1121,1121,1094,1094,1094,1094,1080,1261,1261,1261,1261,1152,1152,1097,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

OBS = []  # 实抓主选观测(ctx=0,k==1)
def probe(obs, config=None):
    sel = (obs or {}).get("select")
    if sel is None:
        return list(META)
    if sel.get("context") == 0 and len(sel.get("option") or []) > 1 and \
       int(sel.get("maxCount") or 0) == 1 and len(OBS) < 40:
        OBS.append(json.loads(json.dumps(obs)))
    return old_sl._pick(sel)

for seed in (28000, 28001, 28002):
    play_local_match(probe, probe, META, META, seed=seed, config={"bo": 1})
print(f"captured {len(OBS)} main observations", flush=True)

mismatch = 0
for j, obs in enumerate(OBS):
    a = old_sl.choose_with_search(obs, META)
    b = new_sl.choose_with_search(obs, META)                       # depth=1 默认
    c = new_sl.choose_with_search(obs, META, depth=1, fold="greedy")
    if not (a == b == c):
        mismatch += 1
        print(json.dumps({"idx": j, "old": a, "new_default": b, "new_explicit": c}))
print(json.dumps({"compat": "PASS" if mismatch == 0 else "FAIL", "n_obs": len(OBS), "mismatch": mismatch}))
