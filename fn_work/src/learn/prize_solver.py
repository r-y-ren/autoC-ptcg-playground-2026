"""终局奖赏清算求解器（算法格·第一件）——档案 §七 奖赏竞速数学的落地

纯算术前瞻（不依赖引擎状态克隆）：给定可见场面，算"这一击之后奖赏竞速谁赢"。
能量匹配=类型多重集（0=无色任意支付），可达即精确；引擎能量语义未明时退化为数量启发式。
接进评分器=终局覆盖层。
"""
from __future__ import annotations

import json

_CARDS = None
_ATTACKS = None


def load_db():
    global _CARDS, _ATTACKS
    if _CARDS is None:
        import os
        base = os.path.join(os.path.dirname(__file__), "..", "..", "..", "references", "engine")
        _CARDS = {c["cardId"]: c for c in json.load(open(os.path.join(base, "cabt-cards.json")))}
        _ATTACKS = {a["attackId"]: a for a in json.load(open(os.path.join(base, "cabt-attacks.json")))}
    return _CARDS, _ATTACKS


def _card(cid):
    load_db()
    return _CARDS.get(cid) if isinstance(cid, int) else None


def _prize_value(card):
    """奖赏值(引擎 KOProc3 口径,报告 §5.1):卡框 pokemonType==3(ex)→2 张、==4(Mega ex)→3 张、其他→1 张。

    pokemonType 是卡框类别不是属系(§12.1)。卡效"少拿/多拿 1 张"修正(引擎 Card+0x69 二进制偏移,
    如 Legacy Energy 整局一次)在 JSON 卡库无对应字段——卡效修正待效果文本解析,不在此估数。
    megaEx 布尔仅作 pokemonType 缺失时的 fallback(ex/megaEx 两标志互斥,§8.3)。
    1/2/3 是严格上界:终局截断下领取不超过对方剩余奖赏,余张不取(§5.2/§5.3)。
    """
    if not card:
        return 1.0
    pt = card.get("pokemonType")
    if isinstance(pt, int):
        return {3: 2.0, 4: 3.0}.get(pt, 1.0)
    if card.get("megaEx"):
        return 3.0
    return 2.0 if card.get("ex") else 1.0


def _eff_damage(attack, my_card, opp_card):
    """引擎实证公式:属系=攻击方 energyType;弱点 ×2 → 抗性 −30(下限 0)"""
    if not attack:
        return 0
    d = attack.get("damage") or 0
    if opp_card and my_card:
        t = my_card.get("energyType")
        if isinstance(t, int) and opp_card.get("weakness") == t:
            d *= 2
        if isinstance(t, int) and opp_card.get("resistance") == t:
            d = max(0, d - 30)
    return d


def can_ko(attacker_pokemon, defender_pokemon):
    """攻击方能否一击打倒防守方（能量够+伤害足）"""
    if not isinstance(attacker_pokemon, dict) or not isinstance(defender_pokemon, dict):
        return False
    a_card = _card(attacker_pokemon.get("id"))
    d_card = _card(defender_pokemon.get("id"))
    if not a_card or not d_card:
        return False
    hp = defender_pokemon.get("hp") or 999
    for aid in (a_card.get("attacks") or []):
        atk = _ATTACKS.get(aid)
        if not atk:
            continue
        if energy_covered(atk.get("energies"), attacker_pokemon.get("energies")) \
                and _eff_damage(atk, a_card, d_card) >= hp:
            return True
    return False


def energy_covered(cost, energies):
    """能量需求匹配：cost=类型多重集（0=无色可由任意能量支付），energies=已附能量类型表。"""
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


def race_bonus(my, opp, my_active, opp_active):
    """奖赏清算覆盖层 → 给 ATTACK 选项的加成（元组：win_now, race_edge, danger）

    终局截断(报告 §5.3):领取使对方剩余奖赏归零的瞬间对局结束(reason 1),余张不取——
    竞速清算不得越过该边界继续累计假想领取;win_now 即"本次击杀是否清空剩余奖赏"的边界判断
    (can_ko/prize 竞速逻辑已隐含:清空即胜走 win_now 分支,不再算后续反击)。
    """
    my_prize = len(my.get("prize") or [])
    opp_prize = len(opp.get("prize") or [])
    my_card = _card(my_active.get("id")) if isinstance(my_active, dict) else None
    opp_card = _card(opp_active.get("id")) if isinstance(opp_active, dict) else None

    win_now = 0.0
    race_edge = 0.0
    danger = 0.0

    # 进攻侧：我这击 KO 且清空奖赏=当场胜利
    if isinstance(opp_active, dict) and isinstance(my_active, dict):
        if can_ko(my_active, opp_active):
            taken = _prize_value(opp_card)
            if my_prize - taken <= 0:
                win_now = 1.0
            else:
                # KO 后对手反击能力（下一手大概率用他替补/主动位打我）
                retaliation = can_ko(opp_active, my_active) or any(
                    can_ko(b, my_active) for b in (opp.get("bench") or []) if isinstance(b, dict))
                if not retaliation and my_prize - taken <= 2:
                    race_edge = 1.0   # 我先收官且他反杀不动=竞速锁定
                elif not retaliation:
                    race_edge = 0.5

    # 防守侧：他一击打倒我的主动位且这会让他清奖赏=当场输
    if isinstance(opp_active, dict) and isinstance(my_active, dict):
        if can_ko(opp_active, my_active):
            my_card_value = _prize_value(my_card)
            if opp_prize - my_card_value <= 0:
                danger = 1.0          # 我的主动位站场=送他当场胜利
            else:
                danger = 0.4          # 被 KO 亏节奏
    return win_now, race_edge, danger
