import sys, os, json
ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for p in (ROOT, ROOT + "/src"): sys.path.insert(0, p)
os.chdir(ROOT)
from learn.search_lookahead import make_search_agent, _pick
from src.shared.play_local_match import play_local_match
from learn.eval_agent import make_agent as make_teacher
from shared.load_agent_callable import load_agent_callable
from kaggle_environments.envs.cabt import cabt
META = [96,96,96,96,92,92,93,93,150,150,917,917,709,709,710,710,1071,1071,140,920,1227,1227,1227,1227,1231,1231,1182,1182,1184,1213,1121,1121,1121,1121,1094,1094,1094,1094,1080,1261,1261,1261,1261,1152,1152,1097,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
DEF = list(cabt.deck)
search_ag = make_search_agent(META)
def v5(obs, config=None):
    sel = (obs or {}).get("select")
    return list(DEF) if sel is None else _pick(sel)
ladder = load_agent_callable("submission_v9", "agent")
out = []
for label, opp, seeds in (("mirror", search_ag, (9000, 9003)), ("v5", v5, (10000, 10003)), ("ladder", ladder, (10001, 10005))):
    for sd in seeds:
        r = play_local_match(search_ag, opp, META, META, seed=sd, config={"bo": 3})
        out.append({"label": label, "seed": sd, "n_steps": r["n_steps"], "rewards": r["rewards"], "failed": r["failed"]})
print(json.dumps(out))
