"""净室 A/B:单库副本子进程内对留档 obs 逐候选评估,两副本跨进程首跑是否逐位一致。

用法:ab_clean.py <bundled|wheel> [--repeat N]
"""
import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.join(ROOT, "src")):
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(ROOT)

META = [96, 96, 96, 96, 92, 92, 93, 93, 150, 150, 917, 917, 709, 709, 710, 710,
        1071, 1071, 140, 920, 1227, 1227, 1227, 1227, 1231, 1231, 1182, 1182, 1184, 1213,
        1121, 1121, 1121, 1121, 1094, 1094, 1094, 1094, 1080, 1261, 1261, 1261, 1261, 1152,
        1152, 1097] + [1] * 14

which = sys.argv[1]
repeat = int(sys.argv[3]) if len(sys.argv) > 3 else 3
obs = json.load(open(os.path.join(ROOT, "tmp", "subm_search_mismatch_obs.json")))

if which == "bundled":
    sys.path.append(os.path.join(ROOT, "submission_search"))
    code = compile(open(os.path.join(ROOT, "submission_search/main.py"), encoding="utf-8").read(),
                   "main.py", "exec")
    env = {}
    exec(code, env)
    ns = {k: env[k] for k in ("_fill", "search_begin", "search_step", "search_release",
                              "_rollout_value", "_SEARCH_MODE")}
else:
    from learn import cg_search as lcs
    from learn import search_lookahead as lsl
    ns = {"_fill": lsl._fill, "search_begin": lcs.search_begin, "search_step": lcs.search_step,
          "search_release": lcs.search_release, "_rollout_value": lsl._rollout_value,
          "_SEARCH_MODE": "wheel-local"}

sel = obs.get("select") or {}
cur = obs.get("current") or {}
my_i = cur.get("yourIndex", 0) or 0
players = cur.get("players") or []
my = players[my_i] if len(players) > my_i else {}
opp = players[1 - my_i] if len(players) > 1 - my_i else {}

runs = []
for r in range(repeat):
    vals = []
    for i in range(len(sel.get("option") or [])):
        st = ns["search_begin"](copy.deepcopy(obs),
                                your_deck=ns["_fill"](my.get("deckCount") or 0),
                                your_prize=ns["_fill"](len(my.get("prize") or [])),
                                opponent_deck=ns["_fill"](opp.get("deckCount") or 0),
                                opponent_prize=ns["_fill"](len(opp.get("prize") or [])),
                                opponent_hand=ns["_fill"](opp.get("handCount") or 0),
                                opponent_active=[])
        sid = st["searchId"]
        s = ns["search_step"](sid, [i])
        v = ns["_rollout_value"](s, sid, 0, my_i, 1, None, 0.0, True)
        ns["search_release"](sid)
        vals.append(round(v, 6))
    runs.append(vals)
print(json.dumps({"mode": ns["_SEARCH_MODE"], "which": which, "runs": runs}))
