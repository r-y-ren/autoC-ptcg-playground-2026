"""状态评估型 agent（fna-006）：奖赏差期望为通货的评分骨架，权重=可整定旋钮（ES 候选）

引擎深读战略翻译（docs/methodology/engine-deep-parse.md）：
- KO=奖赏竞速（普通1/ex2）；一击线>期望伤害；能量附着 1/回合=输出节奏；retreat=节奏成本
"""
from __future__ import annotations

import json

_CARDS = None
_ATTACKS = None

# 默认旋钮（v0 拍脑袋初值——ES 整定对象；血统：档案 §七 战略翻译，样本=0，置信=低）
W = {
    "oneshot": 6.0,       # 本回合一击线（奖赏直接到手）
    "damage": 1.2,        # 伤害进度
    "covered": 0.8,       # 能量已够
    "attach_progress": 2.0,  # 附着推进攻击就绪
    "evolve": 1.5,        # 进化（HP/伤害跃迁）
    "play": 0.9,          # 打出训练家/特性
    "retreat_penalty": -1.2,
    "retreat_escape": 2.5,   # 濒死逃脱
    "end": 0.0,
    # 2026-10-06 扩展旋钮（默认 0=ES 搜索起点）：
    "weakness_progress": 0.0,  # 弱点利用的磨血价值（damage 被整负后单独通道）
    "ko_desperation": 0.0,     # 落后时强攻倾向（奖赏差驱动）
    "ex_retreat_boost": 0.0,   # ex 主动位濒死时的撤退加成
    "fatigue_push": 0.0,       # 我方牌库更薄时的强攻（防疲劳判负）
    # 算法格：终局奖赏清算求解器覆盖层（prize_solver，2026-10-06）
    "win_now": 0.0,            # 当场清奖赏胜利
    "race_edge": 0.0,          # 竞速锁定（KO 后他反杀不动且我接近收官）
    "danger_flee": 0.0,        # 主动位送他当场胜利→撤退加成
}


def energy_covered(cost, energies):
    """能量需求匹配：cost=类型多重集（0=无色可由任意能量支付），energies=已附能量类型表。

    元素非 int（引擎语义未知）时退化为数量比较。严于数量比、不误报覆盖。
    """
    if not cost:
        return True
    try:
        from collections import Counter
        need = Counter(t for t in cost if t != 0)
        have = Counter(e for e in (energies or []) if isinstance(e, int))
        if not all(isinstance(t, int) for t in cost):
            return len(energies or []) >= len(cost)  # 语义未知退化
        for t, n in need.items():
            if have.get(t, 0) < n:
                return False
        leftover = len(energies or []) - sum(need.values())
        return leftover >= sum(1 for t in cost if t == 0)
    except Exception:
        return len(energies or []) >= len(cost)


def load_db():
    global _CARDS, _ATTACKS
    if _CARDS is None:
        _CARDS = {c["cardId"]: c for c in json.load(open("references/engine/cabt-cards.json"))}
        _ATTACKS = {a["attackId"]: a for a in json.load(open("references/engine/cabt-attacks.json"))}


def _card(cid):
    load_db()
    return _CARDS.get(cid) if isinstance(cid, int) else None


def _prize_value(card):
    """奖赏值(官方 CardData 文档):普通 1 / ex 2 / **Mega ex 3**——megaEx 此前误按 2"""
    if not card:
        return 1.0
    if card.get("megaEx"):
        return 3.0
    return 2.0 if card.get("ex") else 1.0


def _effective_damage(attack, my_card, opp_card):
    """引擎实证伤害公式(libcg CalcDamage 反汇编+62 回放+3 开源实现互证):
    属系=攻击方宝可梦 energyType(与附着能量无关);弱点 ×2 → 抗性 −30(下限 0)。
    注意 pokemonType 是卡框类别(普通/ex/Mega)不是属系,勿混用。"""
    if not attack:
        return 0
    dmg = attack.get("damage") or 0
    if opp_card and my_card:
        t = my_card.get("energyType")
        if isinstance(t, int) and opp_card.get("weakness") == t:
            dmg *= 2
        if isinstance(t, int) and opp_card.get("resistance") == t:
            dmg = max(0, dmg - 30)
    return dmg


def make_agent(weights=None, deck=None):
    Wt = dict(W)
    if weights:
        Wt.update(weights)
    if deck is None:
        from kaggle_environments.envs.cabt import cabt
        deck = list(cabt.deck)

    def agent(obs, config=None):
        sel = (obs or {}).get("select")
        if sel is None:
            return list(deck)
        opts = sel.get("option") or []
        mc = int(sel.get("maxCount") or 0)
        mn = int(sel.get("minCount") or 0)
        if not opts or mc <= 0:
            return []
        if sel.get("context") != 0:  # 非 MAIN：效果分辨率，保守取前 mn..mc
            k = max(mn, min(1, mc)) if mn <= 1 else mn
            return list(range(min(k, len(opts))))

        cur = obs.get("current") or {}
        my_i = cur.get("yourIndex", 0) or 0
        players = cur.get("players") or []
        my = players[my_i] if len(players) > my_i else {}
        opp = players[1 - my_i] if len(players) > 1 - my_i else {}
        my_active = (my.get("active") or [None])[0]
        opp_active = (opp.get("active") or [None])[0]
        my_prize_left = len(my.get("prize") or [])
        opp_card = _card(opp_active.get("id")) if isinstance(opp_active, dict) else None
        my_card = _card(my_active.get("id")) if isinstance(my_active, dict) else None

        # 我方主动位濒死判定（对手可一击）
        doomed = 0.0
        if isinstance(opp_active, dict) and isinstance(my_active, dict):
            my_hp = my_active.get("hp") or 999
            for aid in ((opp_card or {}).get("attacks") or []):
                a = _ATTACKS.get(aid)
                if not a:
                    continue
                cost = len(a.get("energies") or [])
                have = len(opp_active.get("energies") or [])
                if have >= cost and _effective_damage(a, opp_card, my_card) >= my_hp:
                    doomed = 1.0
                    break

        # 局面级调制项
        opp_prize_left = len(opp.get("prize") or [])
        desperation = max(0.0, my_prize_left - opp_prize_left) / 6.0
        fatigue = max(0.0, (opp.get("deckCount") or 0) - (my.get("deckCount") or 0)) / 60.0
        # 算法格覆盖层：防守侧判定（全局一次）
        try:
            from . import prize_solver as _ps  # 同包相对导入（脚本模式亦可用）
            _wn, _re, danger = _ps.race_bonus(my, opp, my_active, opp_active)
        except Exception as _e:
            if not globals().get("_PS_WARNED"):
                globals()["_PS_WARNED"] = True
                print(f"[eval_agent] prize_solver 加载失败（覆盖层静默关闭）: {_e}", flush=True)
            _ps = None
            danger = 0.0
        scores = []
        for i, o in enumerate(opts):
            if not isinstance(o, dict):
                scores.append(0.0)
                continue
            t = o.get("type")
            s = 0.0
            if t == 13:  # ATTACK
                a = _ATTACKS.get(o.get("attackId"))
                cost = len(a.get("energies") or []) if a else 0
                have = len(my_active.get("energies") or []) if isinstance(my_active, dict) else 0
                covered = have >= cost
                eff = _effective_damage(a, my_card, opp_card)
                opp_hp = (opp_active.get("hp") or 0) if isinstance(opp_active, dict) else 0
                if covered:
                    s += Wt["covered"]
                    if eff >= opp_hp > 0:
                        s += Wt["oneshot"] * _prize_value(opp_card)
                        # 逐选项求解：这一击清奖赏=当场胜利；这一击锁竞速
                        if _ps is not None:
                            try:
                                taken = _ps._prize_value(opp_card)
                                if my_prize_left - taken <= 0:
                                    s += Wt["win_now"]
                                else:
                                    retaliation = _ps.can_ko(opp_active, my_active) or any(
                                        _ps.can_ko(b, my_active) for b in (opp.get("bench") or []) if isinstance(b, dict))
                                    if not retaliation and my_prize_left - taken <= 2:
                                        s += Wt["race_edge"]
                            except Exception:
                                pass
                    s += Wt["damage"] * eff / 100.0
                    weakness_hit = (opp_card and my_card and opp_card.get("weakness") is not None
                                    and opp_card.get("weakness") == my_card.get("energyType"))
                    if weakness_hit:
                        s += Wt["weakness_progress"] * eff / 100.0
                    s += Wt["ko_desperation"] * desperation + Wt["fatigue_push"] * fatigue
                else:
                    s -= 2.0  # 能量不够硬打=浪费输出位（引擎会禁？ATTACK 不应出现）——防御
            elif t == 8:  # ATTACH（目标=area/index 指的宝可梦）
                s += Wt["attach_progress"]
            elif t == 9:  # EVOLVE
                s += Wt["evolve"]
            elif t in (7, 10, 15):  # PLAY/ABILITY/SKILL
                s += Wt["play"]
            elif t == 12:  # RETREAT
                ex_risk = 1.0 if (doomed and my_card and my_card.get("ex")) else 0.0
                s += Wt["retreat_penalty"] + (Wt["retreat_escape"] if doomed else 0.0) + Wt["ex_retreat_boost"] * ex_risk + Wt["danger_flee"] * danger
            elif t == 14:  # END
                s += Wt["end"]
            elif t == 11:  # DISCARD（代价）
                s -= 0.5
            elif t in (1, 2):  # YES/NO
                s += 0.2 if t == 1 else -0.2
            scores.append(s)

        order = sorted(range(len(opts)), key=lambda i: -scores[i])
        k = mc
        out = order[:k]
        return out[:mc] if mn <= 0 else (out[:max(mn, min(len(out), mc))] + [i for i in range(len(opts)) if i not in out])[:mc]

    return agent
