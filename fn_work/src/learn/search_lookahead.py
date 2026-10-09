"""搜索前瞻 v0(fna-022/fna-010):引擎 search API rollout 行动选优。

设计(借鉴 ronniepiku/bot/search.py 的贪心折叠 MDP 思路,Apache-2.0):
- 只在我方决策点分支(优先 MAIN ctx=0),强制子选择与对手回合用贪心策略折叠;
- 每个候选项:search_begin(确定化)→ 走我方这步 → 贪心 rollout 到"我方再决策/终局/步数帽";
- 叶子=奖赏竞速状态评估(档案 §二 J 数学+W/R 有效伤害);异常/超预算=回退贪心。
- 隐藏信息预测 v0:基础怪+能量填充(数量对齐);对手模型后续用 meta 牌组换。

实测(2026-10-06):单次 12 步 rollout ≈1ms;活局内搜索与本地对局引擎共存无冲突。

v0.1 叶子增厚(2026-10-06,引擎规则总报告 f7e752 §5/§6/§7/§10/§14):
状态条件期望伤害流+行动锁、清场线风险、牌库耗尽、奖赏非线性终局折价、混乱威胁折价。

v0.2 搜索加深×规则折叠(2026-10-06,规则总报告 f7e752 §3 回合结构;两个正交单变量):
- depth(默认 1=旧版逐位一致):rollout 折到我方第 depth 次再决策才停。depth=2=
  「我动→对手回→我再动(贪心/规则折叠代打)→对手回→评叶子」;中途(非末次)抵达
  我方再决策不再分支(候选数不变),用折叠策略代打。depth>1 时循环内每步查钟,
  超时回退当层(已折到处)评估;depth=1 循环内不查钟,与旧版逐位一致。
- fold(默认 "greedy"=旧版攻击优先折叠):"rules"=规则感知折叠 _pick_rules_fold
  (f7e752 §3.5 攻击即终局化→资源优先序:①贴能 ②支援者 ③进化 ④其他行动
  ⑤一击 KO 才攻击 ⑥普通攻击 ⑦END;对手回合同律)。
"""
from __future__ import annotations

import copy
import time

from learn import cg_search

_FILL_P, _FILL_E = 89, 3  # Grookey(基础怪) / Basic {W} 能量
_STEP_CAP = 12
_TIME_CAP_S = 1.2  # 单次决策搜索总预算


def _fill(n):
    return [_FILL_P] + [_FILL_E] * max(0, int(n or 0) - 1)


def _pick(sel: dict) -> list[int]:
    opts = sel.get("option") or []
    mc = int(sel.get("maxCount") or 0)
    mn = int(sel.get("minCount") or 0)
    if not opts:
        return []
    k = max(mn, min(mc if mc > 0 else 1, len(opts)))
    return list(range(k))


def _pick_greedy(sel: dict, my_seat: int) -> list[int]:
    """折叠策略:能攻击就攻击(对己方/对方同律),否则守 min/max 取前排。"""
    opts = sel.get("option") or []
    mc = int(sel.get("maxCount") or 0)
    mn = int(sel.get("minCount") or 0)
    if not opts:
        return []
    k = max(mn, min(mc if mc > 0 else 1, len(opts)))
    atk = [i for i, o in enumerate(opts) if isinstance(o, dict) and o.get("attackId") is not None]
    if atk:
        return atk[:k]
    return list(range(k))


# ---- 规则感知折叠(v0.2,f7e752 §3 回合结构) ----
# OptionType(引擎 api.py):7=PLAY(手牌 index) 8=ATTACH(area=2 手牌→inPlayArea/Index)
# 9=EVOLVE 10=ABILITY 12=RETREAT 13=ATTACK(attackId) 14=END;AreaType:4=ACTIVE 5=BENCH。
_OPT_PLAY, _OPT_ATTACH, _OPT_EVOLVE, _OPT_END = 7, 8, 9, 14
_AREA_ACTIVE = 4
_CARDTYPE_SUPPORTER = 3


def _attack_eff(aid, my_a: dict, opp_a: dict) -> float:
    """攻击有效伤害(W×2/R−30 同款);非攻击/无卡=0。"""
    if not isinstance(aid, int):
        return 0.0
    from learn.bc_policy_v4 import load_db
    _, attacks = load_db()
    a = attacks.get(aid)
    if not a:
        return 0.0
    return _eff_damage(a.get("damage") or 0, _card((my_a or {}).get("id")),
                       _card((opp_a or {}).get("id")))


def _attack_ko(aid, my_a: dict, opp_a: dict) -> bool:
    """一击 KO 判定(attack_feats oneshot 同款):eff≥对方 hp>0 且能量覆盖。"""
    if not isinstance(aid, int) or not isinstance(opp_a, dict):
        return False
    hp = opp_a.get("hp") or 0
    if not hp > 0:
        return False
    if _attack_eff(aid, my_a, opp_a) < hp:
        return False
    from learn.bc_policy_v4 import energy_covered, load_db
    _, attacks = load_db()
    a = attacks.get(aid)
    return bool(a) and energy_covered(a.get("energies") or [], (my_a or {}).get("energies") or [])


def _active_ready_attack(my_a: dict, foe_a: dict) -> bool:
    """出战位已存在能量覆盖且 eff>0 的攻击(贴能止盈判据,fna-029)。

    背景实测(vs v5 六局):确定化对手手牌=deckCount 填充(1 基础怪+余量全 Basic
    Energy),折叠优先序①贴能恒可满足——2483 次对手回合折叠 100% 选 ATTACH、
    0 攻击,_STEP_CAP=12 步全吃满,叶子从不评估对手攻击伤害。此判据让"攻击已
    可发"后贴能不再排攻击之前(攻击即终局化,f7e752 §3.5)。
    """
    card = _card((my_a or {}).get("id"))
    en = (my_a or {}).get("energies") or []
    for a in _attacks_of(card):
        if (a.get("damage") or 0) <= 0:
            continue
        from learn.bc_policy_v4 import energy_covered
        if not energy_covered(a.get("energies") or [], en):
            continue
        if _eff_damage(a.get("damage"), card, _card((foe_a or {}).get("id"))) > 0:
            return True
    return False


def _pick_rules_fold(sel: dict, obs: dict, my_seat: int) -> list[int]:
    """规则感知折叠(f7e752 §3.5 攻击即回合终局化→先资源后攻击),对行动方同律。

    优先序:①贴能(ATTACH,出战位优先——出手节奏硬门槛;出战位攻击已可发即止盈
    降⑥档,fna-029)②打支援者(手牌 cardType=3)
    ③进化 ④其他行动(道具/竞技场 PLAY、特性、撤退、弃置,守引擎序)⑤一击 KO 攻击
    ⑥普通攻击(eff 大优先)⑦END。手牌不可观测(搜索态对手视角)时②退化为引擎序
    (归④档),①③⑤⑥仍可用(只凭 type/attackId)。分类不出的选项归④守引擎序,
    与旧 _pick_greedy 的 range(k) 兜底同形。fna-029 止盈:出战位攻击能量已覆盖且
    eff>0 时,该攻击升为最优先(−2/−1 档,模拟对手"能攻即攻"威胁模型)——
    否则手牌填充(几乎全能量)令①恒可满足,折叠对手在 12 步视界内 0 攻击
    (vs v5 六局 2483 次对手折叠 100% 贴能实证),叶子漏计对手伤害流。
    """
    opts = sel.get("option") or []
    if not opts:
        return []
    mc = int(sel.get("maxCount") or 0)
    mn = int(sel.get("minCount") or 0)
    k = max(mn, min(mc if mc > 0 else 1, len(opts)))
    cur = (obs or {}).get("current") or {}
    players = cur.get("players") or []
    actor_i = cur.get("yourIndex", 0) or 0  # 折叠以行动方视角取手牌/出战(对手回合同律)
    actor = players[actor_i] if len(players) > actor_i else {}
    foe = players[1 - actor_i] if len(players) > 1 - actor_i else {}
    hand = actor.get("hand") or []
    actor_a = (actor.get("active") or [None])[0] or {}
    foe_a = (foe.get("active") or [None])[0] or {}

    def hand_card(o: dict):
        if o.get("type") not in (_OPT_PLAY, _OPT_ATTACH):
            return None
        idx = o.get("index")
        if not isinstance(idx, int) or not 0 <= idx < len(hand):
            return None
        c = hand[idx]
        return _card(c.get("id")) if isinstance(c, dict) else None

    # 出战位攻击已可发(能量覆盖且 eff>0)——止盈开关,fna-029:就绪后折叠改打
    # "攻击即发"威胁模型(攻击档位 −2/−1 反超全部资源档,贴能降⑥档)。动机:手牌
    # 填充(1 基础怪+余量全能量)使①贴能恒可满足,修复前模拟对手 100% 贴能、
    # 12 步视界内 0 攻击(vs v5 六局 2483 次对手折叠实证),叶子漏计对手伤害流;
    # 中间档(撤退/道具)同样会吃掉视界——就绪后攻击必须最先。
    ready = _active_ready_attack(actor_a, foe_a)

    def key(pair):
        i, o = pair
        t = o.get("type")
        if t == _OPT_ATTACH:
            if ready:  # 贴能止盈:出战/备战同律(备战贴能视界内不解锁伤害)→ END 档
                return (6, i, 0)
            return (0, 0 if o.get("inPlayArea") == _AREA_ACTIVE else 1, i)
        if t == _OPT_PLAY:
            c = hand_card(o)
            return (1, i, 0) if (c or {}).get("cardType") == _CARDTYPE_SUPPORTER else (3, i, 0)
        if t == _OPT_EVOLVE:
            return (2, i, 0)
        if t == _OPT_END:
            return (6, i, 0)
        if o.get("attackId") is not None:
            eff = -_attack_eff(o.get("attackId"), actor_a, foe_a)
            if _attack_ko(o.get("attackId"), actor_a, foe_a):
                return (-2, eff, i) if ready else (4, eff, i)
            return (-1, eff, i) if ready else (5, eff, i)
        return (3, i, 0)  # 道具/竞技场/特性/撤退/弃置等未列类型:守引擎序

    return [i for i, _ in sorted(enumerate(opts), key=key)[:k]]


def _card(cid):
    from learn.bc_policy_v4 import _card as _c
    return _c(cid)


def _eff_damage(base, my_card, opp_card):
    from learn.bc_policy_v4 import eff_damage
    return eff_damage(base, my_card, opp_card)


def _attacks_of(card):
    from learn.bc_policy_v4 import load_db
    _, attacks = load_db()
    out = []
    for aid in ((card or {}).get("attacks") or []):
        a = attacks.get(aid)
        if a:
            out.append(a)
    return out


_STATUS_HORIZON = 2.0    # 状态期望伤害流折算回合数(假设:灼伤掷币 50% 解期望持续恰 2 回合)
_POISON_DMG = 10.0       # 毒:poisonValue×10/回合,取默认 10(EffectPoison 可改 2→20,无实测)
_BURN_DMG = 20.0         # 灼伤:20/回合,Checkup 后掷币正面解
_CONFUSE_SELF = 30.0     # 混乱攻击掷币反面自伤 30
_W_PRIZE, _W_HP, _W_THREAT = 10.0, 2.0, 3.0
_W_LOCK, _W_BOARD, _W_FATIGUE = 2.0, 1.5, 2.0
_DANGER = -4.0           # 后备空+出战濒死(§7.4 清场速败高危)
_DECK_REF = 30.0         # 长盘价值衰减参考牌库余量

# 七权重可覆盖表(网格消融入口):默认=现行常量;state_value/choose_with_search/
# make_search_agent 均收可选 weights=(按名覆盖,未知键忽略),weights=None 时语义与旧版逐位一致。
W_KEYS = ("prize", "hp", "threat", "lock", "board", "fatigue", "danger")
DEFAULT_WEIGHTS = {
    "prize": _W_PRIZE, "hp": _W_HP, "threat": _W_THREAT, "lock": _W_LOCK,
    "board": _W_BOARD, "fatigue": _W_FATIGUE, "danger": _DANGER,
}


def resolve_weights(weights: dict | None = None) -> dict:
    """合并七权重:weights 按名覆盖默认值(仅认 W_KEYS 内的键);None/空=现行值。"""
    w = dict(DEFAULT_WEIGHTS)
    for k, v in (weights or {}).items():
        if k in w:
            w[k] = float(v)
    return w


def _prize_score(taken: int) -> float:
    """奖赏进度非线性计价(§5.3 终局截断):按"距离拿完 6 张还有几步"凸折价。

    g(t)=6×(t/6)^1.5——中间进度相对线性打折(3 张=2.12×10 分,线性为 30 分),
    越接近拿完边际越高(第 6 张边际≈第 1 张的 4.7 倍,"领先 5 张≈接近胜利");
    两端 ±60 与旧线性 10×adv 同标定,终局仍由 ±1000 截断。
    """
    t = max(0, min(6, int(taken)))
    return 6.0 * (t / 6.0) ** 1.5


def _is_fossil(card) -> bool:
    """Antique 化石(pokemonType==2)免疫全部特殊状态(§6.2/§12 隐藏规则;简化假设)。"""
    return bool(card) and (card or {}).get("pokemonType") == 2


def _status_flags(P: dict, card) -> dict:
    """出战位状态五槽(观测 PlayerState 布尔);化石免疫→全假(简化,不建模道具/特性豁免)。"""
    keys = ("poisoned", "burned", "asleep", "paralyzed", "confused")
    if _is_fossil(card):
        return {k: False for k in keys}
    return {k: bool(P.get(k)) for k in keys}


def _status_flow(flags: dict) -> float:
    """状态期望伤害流(HP/回合):毒 10+灼伤 20;睡/麻无掉血,混乱自伤折进威胁项。"""
    return (_POISON_DMG if flags["poisoned"] else 0.0) + \
           (_BURN_DMG if flags["burned"] else 0.0)


def state_value(obs: dict, my_i: int, weights: dict | None = None) -> float:
    """叶子状态价值(我方视角,报告 §5/§6/§7/§10/§14):奖赏竞速主轴+状态/清场/牌库风险。

    项:奖赏 10×非线性折价(§5.3)| 血差 2×(含状态期望伤害流按 2 回合折算)|
    一击威胁 3×(混乱 50% 失效+自伤 30 期望折价)| 行动锁 2×(睡/麻禁攻禁撤,§6)|
    清场 1.5×场上存量差+后备空且出战濒死 −4(§7.4 reason 3 占 18.5%)|
    疲劳 2×牌库差(§10 reason 2 回合开始硬判负)| 长盘衰减:我方牌库 <30 时
    慢转换项(血差/威胁/行动锁)按余量折价。
    假设(毒/烧/睡/麻 0 实测样本,§6.4):毒取默认 poisonValue=10;状态伤害流按
    2 回合折算;化石(pokemonType==2)免疫全部状态;濒死阈=出战剩余 HP<35%。
    weights:七权重按名覆盖(DEFAULT_WEIGHTS 默认=现行值;None=旧语义逐位一致)。
    """
    w = resolve_weights(weights)
    cur = obs.get("current") or {}
    players = cur.get("players") or []
    my = players[my_i] if len(players) > my_i else {}
    opp = players[1 - my_i] if len(players) > 1 - my_i else {}
    res = cur.get("result")
    if isinstance(res, int) and res >= 0:
        return 1000.0 if res == my_i else -1000.0

    # 奖赏项:prize 列表=剩余奖赏堆(发奖 6→递减归 0 即胜,f7e752 §5.4 口径)——已拿=6−剩余;非线性折价(§5.3 终局截断)
    t_m = max(0, 6 - len(my.get("prize") or []))
    t_o = max(0, 6 - len(opp.get("prize") or []))
    prize = w["prize"] * (_prize_score(t_m) - _prize_score(t_o))

    my_a = (my.get("active") or [None])[0] or {}
    opp_a = (opp.get("active") or [None])[0] or {}
    my_c, opp_c = _card(my_a.get("id")), _card(opp_a.get("id"))
    my_st = _status_flags(my, my_c)
    opp_st = _status_flags(opp, opp_c)

    # 血差:状态期望伤害流(毒/灼伤)折进有效剩余血量
    my_hp = max(0.0, (my_a.get("hp") or 0) - _STATUS_HORIZON * _status_flow(my_st)) / 380.0
    opp_hp = max(0.0, (opp_a.get("hp") or 0) - _STATUS_HORIZON * _status_flow(opp_st)) / 380.0

    def threat(atk_card, def_card, def_p, atk_st):
        """一击威胁(0/1 基准):睡/麻禁攻→0;混乱→50% 失效+反面自伤 30 的期望折价。"""
        if atk_st["asleep"] or atk_st["paralyzed"]:
            return 0.0
        t = 0.0
        for a in _attacks_of(atk_card):
            eff = _eff_damage(a.get("damage") or 0, atk_card, def_card)
            if eff >= (def_p.get("hp") or 0) > 0:
                t = max(t, 1.0)
        if atk_st["confused"]:
            t = 0.5 * t - 0.5 * _CONFUSE_SELF / 380.0
        return t

    my_shot = threat(my_c, opp_c, opp_a, my_st)
    opp_shot = threat(opp_c, my_c, my_a, opp_st)

    # 行动锁:睡/麻禁攻禁撤,出战位被锁死(混乱自伤/失效已在威胁项,不重复)
    my_lock = 1.0 if (my_st["asleep"] or my_st["paralyzed"]) else 0.0
    opp_lock = 1.0 if (opp_st["asleep"] or opp_st["paralyzed"]) else 0.0

    # 清场风险(§7.4):场上存量=出战+备战,差值独立权重;后备空+出战濒死=高危
    my_n = 1 + len([b for b in (my.get("bench") or []) if isinstance(b, dict)])
    opp_n = 1 + len([b for b in (opp.get("bench") or []) if isinstance(b, dict)])
    my_max_hp = (my_c or {}).get("hp") or 380
    danger = w["danger"] if (my_n == 1 and (my_a.get("hp") or 0) < 0.35 * my_max_hp) else 0.0

    # 牌库耗尽(§10):差值进疲劳项;长盘价值随我方牌库余量衰减
    my_deck_n = my.get("deckCount") or 0
    fatigue = w["fatigue"] * (my_deck_n - (opp.get("deckCount") or 0)) / 60.0
    long_scale = min(1.0, my_deck_n / _DECK_REF)

    return (prize
            + long_scale * (w["hp"] * (my_hp - opp_hp)
                            + w["threat"] * (my_shot - opp_shot)
                            + w["lock"] * (opp_lock - my_lock))
            + w["board"] * (my_n - opp_n) + danger + fatigue)


def _rollout_value(st: dict, sid: int, context: int, my_i: int, depth: int,
                   weights: dict | None, t0: float, rules_fold: bool) -> float:
    """贪心折叠到我方第 depth 次再决策(或终局/步帽),返回叶子状态价值。

    depth=1 与旧版逐位一致(循环内不查钟);depth>1 每步前查钟,超时回退当层
    (已折到处)评估——不弃候选。中途(非末次)抵达我方再决策用折叠策略代打,
    不再分支(候选数不变)。rules_fold=True 用 _pick_rules_fold(行动方同律)。
    """
    arrival, n = 0, 0
    while n < _STEP_CAP:
        o = st["observation"]
        nxt = o.get("select")
        cur2 = o.get("current") or {}
        if nxt is None or (isinstance(cur2.get("result"), int) and cur2["result"] >= 0):
            break
        # 轮到我方决策才停(第 depth 次抵达才停);敌方回合/强制选择继续折叠
        # (敌我凭 current.yourIndex 判——搜索态里它随换手翻转)
        if nxt.get("context") == context and cur2.get("yourIndex") == my_i:
            arrival += 1
            if arrival >= depth:
                break
        if depth > 1 and time.time() - t0 > _TIME_CAP_S:
            break  # 深搜超时:回退当层评估
        step = _pick_rules_fold(nxt, o, my_i) if rules_fold else _pick_greedy(nxt, my_i)
        st = cg_search.search_step(sid, step)
        n += 1
    return state_value(st["observation"], my_i, weights)


def choose_with_search(obs: dict, deck: list[int], context: int = 0,
                       weights: dict | None = None, depth: int = 1,
                       fold: str = "greedy") -> list[int]:
    """在当前选择点用 rollout 选优;任何失败回退贪心。仅对给定 context 启用搜索。

    depth=折叠轮数(默认 1=旧版);fold="greedy"(默认,旧版攻击优先)|"rules"
    (规则感知资源优先序,见 _pick_rules_fold)。depth=1+greedy 与旧版逐位一致。
    """
    sel = (obs or {}).get("select") or {}
    if sel.get("context") != context:
        return _pick(sel)
    opts = sel.get("option") or []
    if not opts:
        return []
    mc = int(sel.get("maxCount") or 0)
    mn = int(sel.get("minCount") or 0)
    k = max(mn, min(mc if mc > 0 else 1, len(opts)))
    cur = obs.get("current") or {}
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
    rules_fold = fold == "rules"
    t0 = time.time()
    best_score, best = None, None
    # 多选(maxCount>1)v0 只按贪心;搜索用于单选决策点
    if k != 1:
        return _pick(sel)
    for i in range(len(opts)):
        if time.time() - t0 > _TIME_CAP_S:
            break
        try:
            st = cg_search.search_begin(copy.deepcopy(obs), **preds)
            sid = st["searchId"]
            s = cg_search.search_step(sid, [i])
            v = _rollout_value(s, sid, context, my_i, depth, weights, t0, rules_fold)
            cg_search.search_release(sid)
            if best_score is None or v > best_score:
                best_score, best = v, i
        except Exception:
            continue
    if best is None:
        return _pick(sel)
    return [best]


def make_search_agent(deck: list[int], context: int = 0, weights: dict | None = None,
                      depth: int = 1, fold: str = "rules"):
    """受测体工厂;weights=七权重按名覆盖(默认现行值);depth=rollout 轮数(默认 1);
    fold 折叠策略默认 "rules"(资源优先序,fna-028 判决:对在梯 0.700 历史新高;
    "greedy"=旧攻击优先,仅回退用)。"""
    def agent(obs, config=None):
        sel = (obs or {}).get("select")
        if sel is None:
            return list(deck)
        return choose_with_search(obs, deck, context=context, weights=weights,
                                  depth=depth, fold=fold)
    return agent
