"""BC 打分策略 v2：手牌直方图+宝可梦细节+选项卡身份解析（补隐藏状态缺口）"""
from __future__ import annotations

import glob
import json

import numpy as np

TYPE_N, AREA_N = 17, 13
BUCKET_N = 28  # card id//50 → 0..27
G_N = 18 + BUCKET_N + 4 + 3 + 2 + 1   # 基础18 + 手牌直方图 + 己方active + 己方bench + 对手active + 对手bench
O_N = TYPE_N + AREA_N + 3 + 5          # 类型/区域/idx/player/order + (bucket_norm, is_pokemon, hp_ratio, n_energy, has_tool)
D_N = G_N + O_N + 1


def _bucket(card_id):
    if not isinstance(card_id, int):
        return BUCKET_N - 1
    return min(max(card_id, 0) // 50, BUCKET_N - 1)


def _pokemon_stats(p):
    if not isinstance(p, dict):
        return [0.0, 0.0, 0.0, 0.0]
    hp = (p.get("hp") or 0) / max(1, (p.get("maxHp") or 1))
    return [min(hp, 1.5), len(p.get("energies") or []) / 6.0, 1.0 if p.get("tools") else 0.0, 1.0]


def featurize_global(cur):
    cur = cur or {}
    my_i = cur.get("yourIndex", 0) or 0
    players = cur.get("players") or []
    my = players[my_i] if len(players) > my_i else {}
    opp = players[1 - my_i] if len(players) > 1 - my_i else {}

    def cnt(v):
        return len([x for x in (v or []) if x])

    hist = np.zeros(BUCKET_N)
    for c in (my.get("hand") or []):
        if isinstance(c, dict):
            hist[_bucket(c.get("id"))] += 1.0
    hist = hist / 10.0

    base = [
        min(cur.get("turn") or 0, 400) / 400.0,
        (my.get("handCount") or 0) / 10.0, (opp.get("handCount") or 0) / 10.0,
        (my.get("deckCount") or 0) / 60.0, (opp.get("deckCount") or 0) / 60.0,
        cnt(my.get("bench")) / 5.0, cnt(opp.get("bench")) / 5.0,
        cnt(my.get("prize")) / 6.0, cnt(opp.get("prize")) / 6.0,
        min(len(my.get("discard") or []), 30) / 30.0,
        min(len(opp.get("discard") or []), 30) / 30.0,
        1.0 if my.get("active") else 0.0, 1.0 if opp.get("active") else 0.0,
        1.0 if cur.get("supporterPlayed") else 0.0,
        1.0 if cur.get("energyAttached") else 0.0,
        1.0 if cur.get("retreated") else 0.0,
        min(cur.get("turnActionCount") or 0, 10) / 10.0,
        1.0 if cur.get("firstPlayer") == my_i else 0.0,
    ]
    ma = (my.get("active") or [None])[0] if my.get("active") else None
    oa = (opp.get("active") or [None])[0] if opp.get("active") else None
    bench_stats = [_pokemon_stats(b) for b in (my.get("bench") or []) if isinstance(b, dict)]
    avg_hp = sum(b[0] for b in bench_stats) / max(1, len(bench_stats))
    tot_en = sum(b[1] for b in bench_stats)
    return np.concatenate([base, hist, _pokemon_stats(ma),
                           [cnt(my.get("bench")) / 5.0, avg_hp, tot_en / 5.0],
                           _pokemon_stats(oa)[:2], [cnt(opp.get("bench")) / 5.0]])


def resolve_card(cur, my_i, o):
    """option 的 area/index → 手牌/场上的卡对象（可见面才解析）"""
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


def featurize_option(o, pos, n_opts, cur, my_i):
    t = np.zeros(TYPE_N)
    a = np.zeros(AREA_N)
    idx = pi = 0.0
    if isinstance(o, dict):
        tt = o.get("type")
        if isinstance(tt, int) and 0 <= tt < TYPE_N:
            t[tt] = 1.0
        ar = o.get("area")
        if isinstance(ar, int) and 1 <= ar <= 12:
            a[ar - 1] = 1.0
        else:
            a[12] = 1.0
        idx = (o.get("index") or 0) / 60.0
        pi = (o.get("playerIndex") or 0) / 2.0
    else:
        a[12] = 1.0
    order = pos / (n_opts - 1) if n_opts > 1 else 0.0
    card = resolve_card(cur, my_i, o) if isinstance(o, dict) else None
    cid = card.get("id") if isinstance(card, dict) else None
    card_feats = [_bucket(cid) / BUCKET_N, 1.0 if isinstance(card, dict) else 0.0] + _pokemon_stats(card)[:2] + [1.0 if (isinstance(card, dict) and card.get("tools")) else 0.0]
    return np.concatenate([t, a, [idx, pi, order], card_feats])


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
                cur = obs.get("current") or {}
                my_i = cur.get("yourIndex", 0) or 0
                g = featurize_global(cur)
                opts = sel.get("option") or []
                n = len(opts)
                feats = [np.concatenate([g, featurize_option(o, i, n, cur, my_i), [0.0]]) for i, o in enumerate(opts)]
                label = act[0]
                if not (0 <= label < n):
                    continue
                if int(sel.get("minCount") or 0) == 0:
                    feats.append(np.concatenate([g, np.zeros(O_N), [1.0]]))
                rows.append((feats, label, eid))
        if rows:
            by_ep.append((eid, rows))
    return by_ep
