"""引擎探针(一次性):A) 哪些预测列表缺基础怪会触发 error=99;B) 搜索态 yourIndex/players 语义。
打印全在外层(引擎吞 agent 内 stdout);结果收进 FINDINGS。"""
import copy
import json
import os
import sys

ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for p in (ROOT, ROOT + "/src"):
    sys.path.insert(0, p)
os.chdir(ROOT)

from learn import cg_search
from learn.search_lookahead import _pick
from src.shared.play_local_match import play_local_match
from kaggle_environments.envs.cabt import cabt

FINDINGS = []
PROBED_ROUNDS = {"setup": False, "mid": False}
BASIC, EN = 89, 3  # Grookey 基础怪 / Basic {W} 能量(非基础)


def _fill_const(n, cid):
    return [cid] * max(0, int(n or 0))


def probe_agent(obs, config=None):
    sel = (obs or {}).get("select") or {}
    opts = sel.get("option") or []
    if not opts:
        return []
    cur = obs.get("current") or {}
    turn = cur.get("turn") or 0
    want = "mid" if turn >= 2 else "setup"
    if PROBED_ROUNDS[want] or not obs.get("search_begin_input"):
        return _pick(sel)
    PROBED_ROUNDS[want] = True
    my_i = cur.get("yourIndex", 0) or 0
    players = cur.get("players") or []
    my = players[my_i] if len(players) > my_i else {}
    opp = players[1 - my_i] if len(players) > 1 - my_i else {}
    base = dict(
        your_deck=int(my.get("deckCount") or 0),
        your_prize=len(my.get("prize") or []),
        opponent_deck=int(opp.get("deckCount") or 0),
        opponent_prize=len(opp.get("prize") or []),
        opponent_hand=int(opp.get("handCount") or 0),
    )
    # 变体:哪一份预测列表全填非基础能量
    variants = ["all_basic", "your_deck_no_basic", "your_prize_no_basic", "opponent_deck_no_basic",
                "opponent_prize_no_basic", "opponent_hand_no_basic", "all_no_basic"]
    for v in variants:
        preds = {}
        for key, n in base.items():
            cid = EN if (v == "all_no_basic" or v == f"{key}_no_basic") else BASIC
            preds[key] = _fill_const(n, cid)
        preds["opponent_active"] = []
        try:
            st = cg_search.search_begin(copy.deepcopy(obs), **preds)
            out = {"round": want, "turn": turn, "variant": v, "ok": True, "counts": base}
            # 语义探针:推进几步看 yourIndex 是否随换手翻转、players 是否固定;同时看 step 是否报错
            sid = st["searchId"]
            semi = []
            s = st
            try:
                for _ in range(10):
                    o = s["observation"]
                    nxt = o.get("select")
                    c2 = o.get("current") or {}
                    p2 = c2.get("players") or []
                    semi.append({
                        "yourIndex": c2.get("yourIndex"),
                        "p0": (p2[0].get("handCount") if len(p2) > 0 else None,
                               p2[0].get("deckCount") if len(p2) > 0 else None,
                               p2[0].get("prize") and len(p2[0].get("prize"))),
                        "p1": (p2[1].get("handCount") if len(p2) > 1 else None,
                               p2[1].get("deckCount") if len(p2) > 1 else None),
                    })
                    if nxt is None or (isinstance(c2.get("result"), int) and c2["result"] >= 0):
                        break
                    s = cg_search.search_step(sid, _pick(nxt))
            except Exception as e2:
                out["step_err"] = str(e2)[:160]
            out["seat_semantics"] = semi
            cg_search.search_release(sid)
            FINDINGS.append(out)
        except Exception as e:
            FINDINGS.append({"round": want, "turn": turn, "variant": v, "ok": False,
                             "err": str(e)[:160], "counts": base})
    return _pick(sel)


def first_agent(obs, config=None):
    sel = (obs or {}).get("select") or {}
    opts = sel.get("option") or []
    if not opts:
        return []
    return _pick(sel)


r = play_local_match(probe_agent, first_agent, list(cabt.deck), list(cabt.deck), seed=7, config={"bo": 1})
print("game:", r["rewards"], r["statuses"], "failed=", r["failed"], "n_steps=", r["n_steps"])
print("=== FINDINGS ===")
print(json.dumps(FINDINGS, ensure_ascii=False, indent=1))
