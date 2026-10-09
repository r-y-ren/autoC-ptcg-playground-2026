import sys, os, time, json
ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for p in (ROOT, ROOT + "/src"): sys.path.insert(0, p)
os.chdir(ROOT)
from shared.load_agent_callable import load_agent_callable
from learn.eval_agent import make_agent as make_teacher
from learn.search_lookahead import make_search_agent, _pick
from src.run_judge_pool.run_judge_pool import run_judge_pool
from src.shared.play_local_match import play_local_match
from kaggle_environments.envs.cabt import cabt

META = [96,96,96,96,92,92,93,93,150,150,917,917,709,709,710,710,1071,1071,140,920,1227,1227,1227,1227,1231,1231,1182,1182,1184,1213,1121,1121,1121,1121,1094,1094,1094,1094,1080,1261,1261,1261,1261,1152,1152,1097,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
DEF = list(cabt.deck)
search_ag = make_search_agent(META)
def v5(obs, config=None):
    sel = (obs or {}).get("select")
    return list(DEF) if sel is None else _pick(sel)
teacher = make_teacher()
ladder = load_agent_callable("submission_v9", "agent")
print("loaded all agents ok", flush=True)

for label, opp in (("mirror", search_ag), ("v5", v5), ("teacher", teacher), ("ladder", ladder)):
    t0 = time.time()
    r = play_local_match(search_ag, opp, META, META, seed=9000, config={"bo": 3})
    dt = time.time() - t0
    print(json.dumps({"smoke": label, "sec": round(dt,2), "rewards": r["rewards"],
                      "statuses": r["statuses"], "failed": r["failed"], "n_steps": r["n_steps"]}, ensure_ascii=False), flush=True)
