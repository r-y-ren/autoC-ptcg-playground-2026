"""引擎探针(一次性):搜索态座位语义——yourIndex 是否随换手翻转、players[] 是否固定、
手牌可见性归属谁。用攻击优先折叠走深(至 120 步),外层打印。"""
import copy
import json
import os
import sys

ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for p in (ROOT, ROOT + "/src"):
    sys.path.insert(0, p)
os.chdir(ROOT)

from learn import cg_search
from learn.search_lookahead import _pick, _pick_greedy, _fill
from src.shared.play_local_match import play_local_match
from kaggle_environments.envs.cabt import cabt

FINDINGS = {}
DONE = {"v": False}


def probe_agent(obs, config=None):
    sel = (obs or {}).get("select") or {}
    if not sel.get("option") or DONE["v"] or not obs.get("search_begin_input"):
        return _pick(sel)
    cur = obs.get("current") or {}
    if (cur.get("turn") or 0) < 3:
        return _pick(sel)
    DONE["v"] = True
    my_i = cur.get("yourIndex", 0) or 0
    players = cur.get("players") or []
    my = players[my_i] if len(players) > my_i else {}
    opp = players[1 - my_i] if len(players) > 1 - my_i else {}
    preds = dict(
        your_deck=_fill(my.get("deckCount") or 0),
        your_prize=_fill(len(my.get("prize") or [])),
        opponent_deck=_fill(opp.get("deckCount") or 0),
        opponent_prize=_fill(len(opp.get("prize") or [])),
        opponent_hand=_fill(opp.get("handCount") or 0),
        opponent_active=[],
    )
    root_fp = {"my_i": my_i, "my_hand": my.get("handCount"), "my_deck": my.get("deckCount"),
               "opp_hand": opp.get("handCount"), "opp_deck": opp.get("deckCount"),
               "my_hand_visible": my.get("hand") is not None,
               "opp_hand_visible": opp.get("hand") is not None}
    seq = []
    try:
        st = cg_search.search_begin(copy.deepcopy(obs), **preds)
        sid = st["searchId"]
        s = st
        for step_i in range(120):
            o = s["observation"]
            nxt = o.get("select")
            c2 = o.get("current") or {}
            p2 = c2.get("players") or []
            rec = {
                "i": step_i, "yourIndex": c2.get("yourIndex"), "turn": c2.get("turn"),
                "ctx": (nxt or {}).get("context") if nxt else None,
                "p0": (p2[0].get("handCount"), p2[0].get("deckCount"), len(p2[0].get("prize") or []),
                       p2[0].get("hand") is not None) if len(p2) > 0 else None,
                "p1": (p2[1].get("handCount"), p2[1].get("deckCount"), len(p2[1].get("prize") or []),
                       p2[1].get("hand") is not None) if len(p2) > 1 else None,
            }
            seq.append(rec)
            if nxt is None or (isinstance(c2.get("result"), int) and c2["result"] >= 0):
                break
            s = cg_search.search_step(sid, _pick_greedy(nxt, my_i))
        cg_search.search_release(sid)
    except Exception as e:
        FINDINGS["step_err"] = str(e)[:200]
    FINDINGS["root"] = root_fp
    FINDINGS["seq"] = seq
    return _pick(sel)


def first_agent(obs, config=None):
    sel = (obs or {}).get("select") or {}
    return _pick(sel) if sel.get("option") else []


r = play_local_match(probe_agent, first_agent, list(cabt.deck), list(cabt.deck), seed=11, config={"bo": 1})
print("game:", r["rewards"], r["statuses"], "n_steps=", r["n_steps"])
print("root:", FINDINGS.get("root"))
print("step_err:", FINDINGS.get("step_err"))
seq = FINDINGS.get("seq") or []
print("n seq:", len(seq))
prev = None
for rec in seq:
    key = (rec["yourIndex"], rec["p0"], rec["p1"], rec["ctx"])
    if key != prev:
        print(rec["i"], "yourIndex=", rec["yourIndex"], "turn=", rec["turn"], "ctx=", rec["ctx"],
              "p0=", rec["p0"], "p1=", rec["p1"])
        prev = key
