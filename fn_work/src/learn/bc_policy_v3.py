"""BC v3：引擎深读后的语义特征（context 谱+卡牌语义+奖赏竞速状态）——评估逻辑做特征，不做规则"""
from __future__ import annotations

import glob
import json

import numpy as np

CTX_N = 49
TYPE_N, AREA_N = 17, 13
_CARDS = None
_ATTACKS = None


def load_db():
    global _CARDS, _ATTACKS
    if _CARDS is None:
        _CARDS = {c["cardId"]: c for c in json.load(open("references/engine/cabt-cards.json"))}
        _ATTACKS = {a["attackId"]: a for a in json.load(open("references/engine/cabt-attacks.json"))}
    return _CARDS, _ATTACKS


def _card(cid):
    load_db()
    return _CARDS.get(cid) if isinstance(cid, int) else None


def _onehot(v, n):
    o = np.zeros(n)
    if isinstance(v, int) and 0 <= v < n:
        o[v] = 1.0
    return o


def resolve_card(cur, my_i, o):
    players = (cur or {}).get("players") or []
    pi = o.get("playerIndex")
    pi = my_i if pi is None else pi
    P = players[pi] if len(players) > pi else {}
    area, idx = o.get("area"), o.get("index")
    if area == 2:
        hand = P.get("hand") or []
        return hand[idx] if isinstance(idx, int) and 0 <= idx < len(hand) else None
    if area == 4:
        a = P.get("active")
        return (a or [None])[0]
    if area == 5:
        bench = P.get("bench") or []
        return bench[idx] if isinstance(idx, int) and 0 <= idx < len(bench) else None
    return None


def sem_card_feats(card_obj):
    c = _card(card_obj.get("id")) if isinstance(card_obj, dict) else None
    if not c:
        return np.zeros(8)
    hp = (c.get("hp") or 0) / 380.0
    stage = 0.5 if c.get("stage1") else (1.0 if c.get("stage2") else 0.0)
    return np.array([
        1.0, hp, stage,
        1.0 if c.get("ex") or c.get("megaEx") else 0.0,
        (c.get("retreatCost") or 0) / 4.0,
        1.0 if c.get("cardType") == 0 else 0.0,
        1.0 if c.get("cardType") in (5, 6) else 0.0,
        1.0 if c.get("cardType") in (1, 2, 3, 4) else 0.0,
    ])


def attack_feats(o, my, opp):
    _, attacks = load_db()
    aid = o.get("attackId") if isinstance(o, dict) else None
    a = attacks.get(aid) if isinstance(aid, int) else None
    if not a:
        return np.zeros(6)
    dmg = (a.get("damage") or 0) / 350.0
    cost_n = len(a.get("energies") or [])
    have_n = len((my.get("energies") if isinstance(my, dict) else None) or [])
    covered = 1.0 if have_n >= cost_n else 0.0
    opp_card = _card((opp.get("id") if isinstance(opp, dict) else None))
    opp_hp = ((opp.get("hp") or 0) / 380.0) if isinstance(opp, dict) else 0.0
    my_card = _card(my.get("id")) if isinstance(my, dict) else None
    weakness_hit = 0.0
    if opp_card and my_card and opp_card.get("weakness") is not None and my_card.get("pokemonType") is not None:
        weakness_hit = 1.0 if opp_card.get("weakness") == my_card.get("pokemonType") else 0.0
    eff = (a.get("damage") or 0) * (2.0 if weakness_hit else 1.0)
    oneshot = 1.0 if (isinstance(opp, dict) and eff >= (opp.get("hp") or 0) > 0 and covered) else 0.0
    return np.array([dmg, cost_n / 5.0, covered, opp_hp, weakness_hit, oneshot])


def build_features(obs):
    cur = obs.get("current") or {}
    my_i = cur.get("yourIndex", 0) or 0
    players = cur.get("players") or []
    my = players[my_i] if len(players) > my_i else {}
    opp = players[1 - my_i] if len(players) > 1 - my_i else {}
    sel = obs.get("select") or {}
    ctx = _onehot(sel.get("context"), CTX_N)

    def agg_player(P):
        active = (P.get("active") or [None])[0]
        bench = [b for b in (P.get("bench") or []) if isinstance(b, dict)]
        hp_a = ((active.get("hp") or 0) / 380.0) if isinstance(active, dict) else 0.0
        energy_a = (len(active.get("energies") or []) / 6.0) if isinstance(active, dict) else 0.0
        bench_prize_risk = sum(1.0 for b in bench if (_card(b.get("id")) or {}).get("ex")) / 5.0
        ac = sem_card_feats(active)[:4]
        return np.concatenate([[hp_a, energy_a, len(bench) / 5.0, bench_prize_risk], ac])

    g_state = np.concatenate([
        ctx,
        agg_player(my), agg_player(opp),
        [len(my.get("prize") or []) / 6.0, len(opp.get("prize") or []) / 6.0,
         (my.get("deckCount") or 0) / 60.0, (opp.get("deckCount") or 0) / 60.0,
         1.0 if cur.get("supporterPlayed") else 0.0,
         1.0 if cur.get("energyAttached") else 0.0,
         1.0 if cur.get("retreated") else 0.0,
         (my.get("handCount") or 0) / 10.0, (opp.get("handCount") or 0) / 10.0],
        np.array([
            sum(1 for c in (my.get("hand") or []) if (_card(c.get("id")) or {}).get("cardType") == 0) / 10.0,
            sum(1 for c in (my.get("hand") or []) if (_card(c.get("id")) or {}).get("cardType") in (5, 6)) / 10.0,
            sum(1 for c in (my.get("hand") or []) if (_card(c.get("id")) or {}).get("cardType") == 3) / 5.0,
            sum(1 for c in (my.get("hand") or []) if (_card(c.get("id")) or {}).get("cardType") in (1, 2, 4)) / 10.0,
        ]),
    ])

    my_active = (my.get("active") or [None])[0]
    opp_active = (opp.get("active") or [None])[0]
    opts = sel.get("option") or []
    n = len(opts)
    rows = []
    for i, o in enumerate(opts):
        t = _onehot(o.get("type") if isinstance(o, dict) else None, TYPE_N)
        a = _onehot((o.get("area") or 0) - 1 if isinstance(o, dict) and isinstance(o.get("area"), int) else None, AREA_N)
        order = np.array([i / (n - 1) if n > 1 else 0.0])
        cardf = sem_card_feats(resolve_card(cur, my_i, o)) if isinstance(o, dict) else np.zeros(8)
        atkf = attack_feats(o, my_active, opp_active) if isinstance(o, dict) else np.zeros(6)
        rows.append(np.concatenate([g_state, t, a, order, cardf, atkf, [0.0]]))  # is_pass=0
    if int(sel.get("minCount") or 0) == 0:
        rows.append(np.concatenate([g_state, np.zeros(TYPE_N + AREA_N + 1 + 8 + 6), [1.0]]))
    return rows


def extract_pairs(raw_glob="references/episodes/episode-*-replay.json", winners_only=True):
    by_ep = []
    for p in sorted(glob.glob(raw_glob)):
        d = json.load(open(p))
        eid = p.split("episode-")[-1].split("-")[0]
        winners = set()
        for pair in d.get("steps", []):
            for j in (0, 1):
                r = pair[j].get("reward")
                if r is not None and r > 0:
                    winners.add(j)
        rows = []
        for pair in d.get("steps", []):
            for j in (0, 1):
                st = pair[j]
                if st.get("status") != "ACTIVE":
                    continue
                obs = st.get("observation") or {}
                sel = obs.get("select")
                act = st.get("action")
                if not sel or not isinstance(act, list) or len(act) != 1 or sel.get("maxCount") != 1:
                    continue
                if winners_only and j not in winners:
                    continue
                feats = build_features(obs)
                label = act[0]
                if not (0 <= label < len(sel.get("option") or [])):
                    continue
                rows.append((feats, label, eid))
        if rows:
            by_ep.append((eid, rows))
    return by_ep
