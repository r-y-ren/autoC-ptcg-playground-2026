"""BC v4:机制做全语义特征——伤害公式 W×2/R−30(energyType 属系)+能量多重集对账
+效果文本关键词+特性/状态/进化经济。评估逻辑做特征,不做规则。

与 v3 的差异(单变量="机制特征包",d 124→新维度):
- 修弱点判定字段 bug(v3 拿 pokemonType 卡框比属系);补抗性 −30;伤害公式全对齐引擎(libcg CalcDamage)
- 能量覆盖从"数个数"升为类型多重集(对齐 eval_agent.energy_covered)
- 技能效果文本关键词 10 位(1161/1755 技能带文本:抽牌/铺伤/换位/找牌/治疗/弃牌/状态/硬币/保护)
- 反向对局信号(对手克我弱点→撤退压力)、双方奖赏风险、状态条件、特性存在位
"""
from __future__ import annotations

import json
import math

import numpy as np

CTX_N = 49
TYPE_N, AREA_N = 17, 13
_CARDS = None
_ATTACKS = None
_TEXT_FLAGS = ("draw", "counter", "switch_opp", "switch_self", "search",
               "heal", "discard", "status", "coin", "prevent")


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


def energy_covered(cost, energies):
    """能量需求=类型多重集(0=无色任意支付);元素非 int 时退化数量比(与 eval_agent 同语义)"""
    if not cost:
        return True
    try:
        from collections import Counter
        if not all(isinstance(t, int) for t in cost):
            return len(energies or []) >= len(cost)
        need = Counter(t for t in cost if t != 0)
        have = Counter(e for e in (energies or []) if isinstance(e, int))
        for t, n in need.items():
            if have.get(t, 0) < n:
                return False
        leftover = len(energies or []) - sum(need.values())
        return leftover >= sum(1 for t in cost if t == 0)
    except Exception:
        return len(energies or []) >= len(cost)


def eff_damage(base, my_card, opp_card):
    """引擎实证:属系=攻击方 energyType;×2(弱点) → −30(抗性,下限 0)"""
    d = base or 0
    if my_card and opp_card:
        t = my_card.get("energyType")
        if isinstance(t, int) and opp_card.get("weakness") == t:
            d *= 2
        if isinstance(t, int) and opp_card.get("resistance") == t:
            d = max(0, d - 30)
    return d


def text_flags(text):
    t = (text or "").lower()
    return np.array([
        1.0 if "draw" in t else 0.0,
        1.0 if "damage counter" in t else 0.0,
        1.0 if ("switch out" in t and "opponent" in t) or "opponent switches" in t else 0.0,
        1.0 if "switch" in t and not (("switch out" in t and "opponent" in t) or "opponent switches" in t) else 0.0,
        1.0 if "search" in t or "from your deck" in t else 0.0,
        1.0 if "heal" in t else 0.0,
        1.0 if "discard" in t else 0.0,
        1.0 if any(s in t for s in ("asleep", "burned", "poisoned", "paralyzed", "confused")) else 0.0,
        1.0 if "coin flip" in t or "flip a coin" in t else 0.0,
        1.0 if "prevent" in t or "can't be" in t or "ignore" in t else 0.0,
    ])


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
        return np.zeros(11)
    hp = (c.get("hp") or 0) / 380.0
    stage = 0.5 if c.get("stage1") else (1.0 if c.get("stage2") else 0.0)
    return np.array([
        1.0, hp, stage,
        1.0 if c.get("ex") or c.get("megaEx") else 0.0,
        (c.get("retreatCost") or 0) / 4.0,
        1.0 if c.get("cardType") == 0 else 0.0,
        1.0 if c.get("cardType") in (5, 6) else 0.0,
        1.0 if c.get("cardType") in (1, 2, 3, 4) else 0.0,
        1.0 if c.get("tera") else 0.0,
        1.0 if c.get("aceSpec") else 0.0,
        1.0 if c.get("skills") else 0.0,
    ])


def attack_feats(o, my, opp):
    _, attacks = load_db()
    aid = o.get("attackId") if isinstance(o, dict) else None
    a = attacks.get(aid) if isinstance(aid, int) else None
    if not a:
        return np.zeros(10 + len(_TEXT_FLAGS))
    base = a.get("damage") or 0
    cost = a.get("energies") or []
    have = (my.get("energies") if isinstance(my, dict) else None) or []
    covered = 1.0 if energy_covered(cost, have) else 0.0
    my_card = _card(my.get("id")) if isinstance(my, dict) else None
    opp_card = _card((opp.get("id") if isinstance(opp, dict) else None))
    opp_hp = ((opp.get("hp") or 0) / 380.0) if isinstance(opp, dict) else 0.0
    w_hit = 0.0
    r_hit = 0.0
    if opp_card and my_card:
        t = my_card.get("energyType")
        if isinstance(t, int):
            w_hit = 1.0 if opp_card.get("weakness") == t else 0.0
            r_hit = 1.0 if opp_card.get("resistance") == t else 0.0
    eff = eff_damage(base, my_card, opp_card)
    oneshot = 1.0 if (isinstance(opp, dict) and eff >= (opp.get("hp") or 0) > 0 and covered) else 0.0
    tko = 0.0
    if covered and eff > 0 and isinstance(opp, dict) and (opp.get("hp") or 0) > 0:
        tko = min(4.0, math.ceil((opp.get("hp") or 0) / eff)) / 4.0
    cost_typed = sum(1 for t in cost if isinstance(t, int) and t != 0)
    return np.concatenate([
        np.array([
            base / 350.0, len(cost) / 5.0, cost_typed / 5.0, covered, opp_hp,
            w_hit, r_hit, eff / 350.0, oneshot, tko,
        ]),
        text_flags(a.get("text")),
    ])


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
        st = np.array([1.0 if P.get(k) else 0.0 for k in
                       ("poisoned", "burned", "asleep", "paralyzed", "confused")])
        return np.concatenate([[hp_a, energy_a, len(bench) / 5.0, bench_prize_risk], ac, st])

    my_active = (my.get("active") or [None])[0]
    opp_active = (opp.get("active") or [None])[0]
    my_ac = _card(my_active.get("id")) if isinstance(my_active, dict) else None
    opp_ac = _card(opp_active.get("id")) if isinstance(opp_active, dict) else None

    def matchup(atk_card, def_card):
        if not (atk_card and def_card):
            return [0.0, 0.0]
        t = atk_card.get("energyType")
        if not isinstance(t, int):
            return [0.0, 0.0]
        return [1.0 if def_card.get("weakness") == t else 0.0,
                1.0 if def_card.get("resistance") == t else 0.0]

    my_w, my_r = matchup(my_ac, opp_ac)     # 我克他/我被抗
    opp_w, opp_r = matchup(opp_ac, my_ac)   # 他克我/他被我抗
    prize_risk = [
        (2.0 if (my_ac and (my_ac.get("ex") or my_ac.get("megaEx"))) else 1.0) / 2.0,
        (2.0 if (opp_ac and (opp_ac.get("ex") or opp_ac.get("megaEx"))) else 1.0) / 2.0,
    ]

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
        np.array([my_w, my_r, opp_w, opp_r] + prize_risk),
    ])

    opts = sel.get("option") or []
    n = len(opts)
    rows = []
    for i, o in enumerate(opts):
        t = _onehot(o.get("type") if isinstance(o, dict) else None, TYPE_N)
        a = _onehot((o.get("area") or 0) - 1 if isinstance(o, dict) and isinstance(o.get("area"), int) else None, AREA_N)
        order = np.array([i / (n - 1) if n > 1 else 0.0])
        cardf = sem_card_feats(resolve_card(cur, my_i, o)) if isinstance(o, dict) else np.zeros(11)
        atkf = attack_feats(o, my_active, opp_active) if isinstance(o, dict) else np.zeros(10 + len(_TEXT_FLAGS))
        rows.append(np.concatenate([g_state, t, a, order, cardf, atkf, [0.0]]))  # is_pass=0
    if int(sel.get("minCount") or 0) == 0:
        rows.append(np.concatenate([g_state, np.zeros(TYPE_N + AREA_N + 1 + 11 + 10 + len(_TEXT_FLAGS)), [1.0]]))
    return rows
