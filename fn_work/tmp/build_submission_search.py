"""组装 search+META 部署件 fn_work/submission_search/(可提交态,不提交)。

产物:main.py(全内联:投影卡库/技库 + META 常量 + 叶子评估 + 规则折叠 + 搜索绑定
+ v9.2 评估器贪心兜底)、deck.csv、cg/libcg.so、submission.tar.gz。
受测语义 = learn.search_lookahead.make_search_agent(META)(depth=1/fold=rules/weights 默认,
verdict 2026-10-06)。自包含:不 import learn.*,不读本地文件,无 __file__。

数据同源断言:v9 内联 blob 与 references/engine/*.json 投影逐卡逐技全等(0 段差才放行)。
"""
import json
import os
import re
import shutil
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "submission_search")

META = [96, 96, 96, 96, 92, 92, 93, 93, 150, 150, 917, 917, 709, 709, 710, 710,
        1071, 1071, 140, 920, 1227, 1227, 1227, 1227, 1231, 1231, 1182, 1182, 1184, 1213,
        1121, 1121, 1121, 1121, 1094, 1094, 1094, 1094, 1080, 1261, 1261, 1261, 1261, 1152,
        1152, 1097] + [1] * 14

# ---- 1. 数据:投影(卡 8 字段/技 3 字段,搜索路径全用到;键名保持引擎原名) ----
raw_cards = json.load(open(os.path.join(ROOT, "references/engine/cabt-cards.json")))
raw_attacks = json.load(open(os.path.join(ROOT, "references/engine/cabt-attacks.json")))
CARD_FIELDS = ("cardId", "energyType", "weakness", "resistance", "attacks",
               "cardType", "pokemonType", "hp")
ATTACK_FIELDS = ("attackId", "damage", "energies")
proj_cards = [{k: c.get(k) for k in CARD_FIELDS} for c in raw_cards]
proj_attacks = [{k: a.get(k) for k in ATTACK_FIELDS} for a in raw_attacks]
cards_json = json.dumps(proj_cards, separators=(",", ":"), ensure_ascii=False)
attacks_json = json.dumps(proj_attacks, separators=(",", ":"), ensure_ascii=False)

# ---- 2. v9 blob 同源断言(映射逐位等价才放行) ----
v9_src = open(os.path.join(ROOT, "submission_v9/main.py"), encoding="utf-8").read()
v9_cards = json.loads(re.search(r"_CARDS = json\.loads\(r'''(.*?)'''\)", v9_src, re.S).group(1))
v9_attacks = json.loads(re.search(r"_ATTACKS = json\.loads\(r'''(.*?)'''\)", v9_src, re.S).group(1))


def derive_v9_card(c):
    return {"ct": c.get("cardType"), "hp": c.get("hp"), "wt": c.get("weakness"),
            "pt": c.get("pokemonType"), "ex": bool(c.get("ex") or c.get("megaEx")),
            "rc": c.get("retreatCost"), "at": list(c.get("attacks") or []),
            "et": c.get("energyType"), "rt": c.get("resistance"),
            "mx": bool(c.get("megaEx"))}


def derive_v9_atk(a):
    return {"d": a.get("damage") or 0, "e": list(a.get("energies") or [])}


bad_c = [c["cardId"] for c in raw_cards if v9_cards.get(str(c["cardId"])) != derive_v9_card(c)]
bad_a = [a["attackId"] for a in raw_attacks if v9_attacks.get(str(a["attackId"])) != derive_v9_atk(a)]
assert not bad_c and not bad_a, f"投影与 v9 blob 不等价: cards={bad_c[:5]} attacks={bad_a[:5]}"
assert len(META) == 60 and all(any(c["cardId"] == i for c in raw_cards) for i in META)

# ---- 3. v9 兜底块:从 submission_v9/main.py 程序化抽取+改名(防手抄漂移) ----
w_line = re.search(r"^W = .*$", v9_src, re.M).group(0)
helper_block = v9_src[v9_src.index("def _card(cid):"):v9_src.index("def agent(obs, config=None):")]
agent_block = v9_src[v9_src.index("def agent(obs, config=None):"):]
assert helper_block.count("def ") == 5, "helper 块应含 _card/_pv/_eff/energy_covered/_can_ko"
assert "def " not in agent_block.replace("def agent(obs, config=None):", ""), "agent 块不含其他 def"

# v9 的 energy_covered 与共享版(bc_policy_v4 语义)规范化后必须全等→兜底块改用共享版,去重
i_ec = helper_block.index("def energy_covered(")
j_ec = helper_block.index("def ", i_ec + 10)  # 下一函数(def _can_ko)
ec_txt = helper_block[i_ec:j_ec]
assert "leftover" in ec_txt and "except Exception" in ec_txt, "v9 energy_covered 内容校验失败"
helper_block = helper_block[:i_ec] + helper_block[j_ec:]

RENAMES = [  # 先占位再落名,避免连锁误伤
    (r"\bDEFAULT_DECK\b", "PLACE6"), (r"\b_can_ko\b", "PLACE3"),
    (r"\b_eff\b", "PLACE2"), (r"\b_card\b", "PLACE1"),
    (r"\b_ATTACKS\b", "PLACE4"), (r"\b_CARDS\b", "PLACE5"),
    (r"\bagent\b", "PLACE7"),
    ("PLACE1", "_fb_card"), ("PLACE2", "_fb_eff"), ("PLACE3", "_fb_can_ko"),
    ("PLACE4", "_FB_ATTACKS"), ("PLACE5", "_FB_CARDS"),
    ("PLACE6", "META_DECK"), ("PLACE7", "_fallback_agent"),
]
fb_block = helper_block + "\n\n" + agent_block
for pat, rep in RENAMES:
    fb_block = re.sub(pat, rep, fb_block)

# ---- 4. 搜索块:search_lookahead + cg_search 内联(去 learn 依赖,lib 随包定位) ----
SEARCH_BLOCK = '''
# ================= 搜索层(内联自 src/learn/cg_search.py + search_lookahead.py) =================
# 受测语义 = make_search_agent(META):depth=1 / fold="rules" / weights 默认(verdict 2026-10-06)。

_SEARCH_MODE = "off"
_LIB = None


def _find_bundled_lib():
    """随包 cg/libcg.so 相对定位:装载期 sys.path(Kaggle exec 会追加提交包目录)→ cwd。
    不引用源文件路径内置名(Kaggle exec 装载语义不提供);全部探测仅在 import 期执行。"""
    seen = set()
    for d in list(sys.path) + [os.getcwd()]:
        if not d or d in seen:
            continue
        seen.add(d)
        try:
            p = os.path.join(d, "cg", "libcg.so")
            if os.path.isfile(p):
                return p
        except Exception:
            pass
    return None


def _load_search_lib():
    """装载搜索原语库:①随包 cg/libcg.so(自 GameInitialize,与 wheel 引擎副本互不串扰)
    ②wheel kaggle_environments 的 lib(其 sim 导入期已初始化)→ 都不可用则禁搜索。"""
    global _LIB, _SEARCH_MODE
    p = _find_bundled_lib()
    if p:
        try:
            lib = ctypes.cdll.LoadLibrary(p)
            lib.GameInitialize()
            _LIB, _SEARCH_MODE = lib, "bundled"
            return
        except Exception:
            pass
    try:
        from kaggle_environments.envs.cabt.cg import sim as _cg_sim
        _LIB, _SEARCH_MODE = _cg_sim.lib, "wheel"
    except Exception:
        _LIB, _SEARCH_MODE = None, "off"


_load_search_lib()

if _LIB is not None:
    _INT = ctypes.c_int
    _ARR = ctypes.POINTER(_INT)

    _LIB.AgentStart.restype = ctypes.c_void_p
    _LIB.AgentStart.argtypes = []
    _LIB.SearchBegin.restype = ctypes.c_char_p
    _LIB.SearchBegin.argtypes = [ctypes.c_void_p, ctypes.c_char_p, _INT,
                                 _ARR, _ARR, _ARR, _ARR, _ARR, _ARR, _INT]
    _LIB.SearchStep.restype = ctypes.c_char_p
    _LIB.SearchStep.argtypes = [ctypes.c_void_p, ctypes.c_int64, _ARR, _INT]
    _LIB.SearchEnd.restype = None
    _LIB.SearchEnd.argtypes = [ctypes.c_void_p]
    _LIB.SearchRelease.restype = None
    _LIB.SearchRelease.argtypes = [ctypes.c_void_p, ctypes.c_int64]

_search_ptr = [None]


def _arr(xs):
    xs = list(xs or [])
    return (_INT * len(xs))(*xs)


def _decode(raw):
    if raw is None:
        raise RuntimeError("search 返回空")
    return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)


def _agent():
    if _search_ptr[0] is None:
        _search_ptr[0] = _LIB.AgentStart()
    return _search_ptr[0]


def search_begin(obs, your_deck, your_prize, opponent_deck, opponent_prize,
                 opponent_hand, opponent_active, manual_coin=False):
    """开搜索:返回 {"observation": {...}, "searchId": int}"""
    sbi = obs.get("search_begin_input") if isinstance(obs, dict) else None
    if not sbi:
        raise ValueError("Not agent observation.(观测缺 search_begin_input)")
    cur = obs.get("current") or {}
    my_i = cur.get("yourIndex", 0) or 0
    players = cur.get("players") or []
    my = players[my_i] if len(players) > my_i else {}
    opp = players[1 - my_i] if len(players) > 1 - my_i else {}
    if len(your_prize) < len(my.get("prize") or []):
        raise ValueError("your_prize 张数不足")
    if len(opponent_deck) < (opp.get("deckCount") or 0):
        raise ValueError("opponent_deck 张数不足")
    if len(opponent_prize) < len(opp.get("prize") or []):
        raise ValueError("opponent_prize 张数不足")
    if len(opponent_hand) < (opp.get("handCount") or 0):
        raise ValueError("opponent_hand 张数不足")
    bs = _LIB.SearchBegin(_agent(), sbi.encode("ascii"), len(sbi),
                          _arr(your_deck), _arr(your_prize), _arr(opponent_deck),
                          _arr(opponent_prize), _arr(opponent_hand),
                          _arr(opponent_active), int(bool(manual_coin)))
    out = _decode(bs)
    if out.get("error"):
        raise RuntimeError(f"SearchBegin error={out['error']}")
    return out["state"]


def search_step(search_id, select):
    bs = _LIB.SearchStep(_agent(), int(search_id), _arr(select), len(select))
    out = _decode(bs)
    if out.get("error"):
        raise RuntimeError(f"SearchStep error={out['error']}")
    return out["state"]


def search_end():
    _LIB.SearchEnd(_agent())


def search_release(search_id):
    _LIB.SearchRelease(_agent(), int(search_id))


# ---- 叶子评估 + 折叠 + 选优(与 search_lookahead.py 逐行同源) ----
_FILL_P, _FILL_E = 89, 3  # Grookey(基础怪) / Basic {W} 能量
_STEP_CAP = 12
_TIME_CAP_S = 1.2  # 单次决策搜索总预算


def _fill(n):
    return [_FILL_P] + [_FILL_E] * max(0, int(n or 0) - 1)


def _card(cid):
    return _CARDS.get(cid) if isinstance(cid, int) else None


def _pick(sel):
    opts = sel.get("option") or []
    mc = int(sel.get("maxCount") or 0)
    mn = int(sel.get("minCount") or 0)
    if not opts:
        return []
    k = max(mn, min(mc if mc > 0 else 1, len(opts)))
    return list(range(k))


def _pick_greedy(sel, my_seat):
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


# ---- 规则感知折叠(v0.2):OptionType 7=PLAY 8=ATTACH 9=EVOLVE 14=END;AreaType 4=ACTIVE;支援者 cardType=3
_OPT_PLAY, _OPT_ATTACH, _OPT_EVOLVE, _OPT_END = 7, 8, 9, 14
_AREA_ACTIVE = 4
_CARDTYPE_SUPPORTER = 3


def _eff_damage(base, my_card, opp_card):
    """引擎实证:属系=攻击方 energyType;×2(弱点) → −30(抗性,下限 0)"""
    d = base or 0
    if my_card and opp_card:
        t = my_card.get("energyType")
        if isinstance(t, int) and opp_card.get("weakness") == t:
            d *= 2
        if isinstance(t, int) and opp_card.get("resistance") == t:
            d = max(0, d - 30)
    return d


def _attacks_of(card):
    out = []
    for aid in ((card or {}).get("attacks") or []):
        a = _ATTACKS.get(aid)
        if a:
            out.append(a)
    return out


def energy_covered(cost, energies):
    """能量需求=类型多重集(0=无色任意支付);元素非 int 时退化数量比"""
    if not cost:
        return True
    try:
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


def _attack_eff(aid, my_a, opp_a):
    """攻击有效伤害(W×2/R−30 同款);非攻击/无卡=0。"""
    if not isinstance(aid, int):
        return 0.0
    a = _ATTACKS.get(aid)
    if not a:
        return 0.0
    return _eff_damage(a.get("damage") or 0, _card((my_a or {}).get("id")),
                       _card((opp_a or {}).get("id")))


def _attack_ko(aid, my_a, opp_a):
    """一击 KO 判定(attack_feats oneshot 同款):eff≥对方 hp>0 且能量覆盖。"""
    if not isinstance(aid, int) or not isinstance(opp_a, dict):
        return False
    hp = opp_a.get("hp") or 0
    if not hp > 0:
        return False
    if _attack_eff(aid, my_a, opp_a) < hp:
        return False
    a = _ATTACKS.get(aid)
    return bool(a) and energy_covered(a.get("energies") or [], (my_a or {}).get("energies") or [])


def _active_ready_attack(my_a, foe_a):
    """出战位已存在能量覆盖且 eff>0 的攻击(贴能止盈判据,fna-029)。"""
    card = _card((my_a or {}).get("id"))
    en = (my_a or {}).get("energies") or []
    for a in _attacks_of(card):
        if (a.get("damage") or 0) <= 0:
            continue
        if not energy_covered(a.get("energies") or [], en):
            continue
        if _eff_damage(a.get("damage"), card, _card((foe_a or {}).get("id"))) > 0:
            return True
    return False


def _pick_rules_fold(sel, obs, my_seat):
    """规则感知折叠(攻击即回合终局化→先资源后攻击),对行动方同律。

    优先序:①贴能(出战位优先;出战位攻击已可发即止盈降⑥档,fna-029)
    ②支援者 ③进化 ④其他行动(守引擎序)⑤一击 KO 攻击 ⑥普通攻击(eff 大优先)
    ⑦END。就绪后攻击档位 −2/−1 反超全部资源档(攻击即发威胁模型)。
    """
    opts = sel.get("option") or []
    if not opts:
        return []
    mc = int(sel.get("maxCount") or 0)
    mn = int(sel.get("minCount") or 0)
    k = max(mn, min(mc if mc > 0 else 1, len(opts)))
    cur = (obs or {}).get("current") or {}
    players = cur.get("players") or []
    actor_i = cur.get("yourIndex", 0) or 0
    actor = players[actor_i] if len(players) > actor_i else {}
    foe = players[1 - actor_i] if len(players) > 1 - actor_i else {}
    hand = actor.get("hand") or []
    actor_a = (actor.get("active") or [None])[0] or {}
    foe_a = (foe.get("active") or [None])[0] or {}

    def hand_card(o):
        if o.get("type") not in (_OPT_PLAY, _OPT_ATTACH):
            return None
        idx = o.get("index")
        if not isinstance(idx, int) or not 0 <= idx < len(hand):
            return None
        c = hand[idx]
        return _card(c.get("id")) if isinstance(c, dict) else None

    ready = _active_ready_attack(actor_a, foe_a)

    def key(pair):
        i, o = pair
        t = o.get("type")
        if t == _OPT_ATTACH:
            if ready:
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
        return (3, i, 0)

    return [i for i, _ in sorted(enumerate(opts), key=key)[:k]]


_STATUS_HORIZON = 2.0    # 状态期望伤害流折算回合数
_POISON_DMG = 10.0       # 毒:poisonValue×10/回合,取默认 10
_BURN_DMG = 20.0         # 灼伤:20/回合,Checkup 后掷币正面解
_CONFUSE_SELF = 30.0     # 混乱攻击掷币反面自伤 30
_W_PRIZE, _W_HP, _W_THREAT = 10.0, 2.0, 3.0
_W_LOCK, _W_BOARD, _W_FATIGUE = 2.0, 1.5, 2.0
_DANGER = -4.0           # 后备空+出战濒死(清场速败高危)
_DECK_REF = 30.0         # 长盘价值衰减参考牌库余量

W_KEYS = ("prize", "hp", "threat", "lock", "board", "fatigue", "danger")
DEFAULT_WEIGHTS = {
    "prize": _W_PRIZE, "hp": _W_HP, "threat": _W_THREAT, "lock": _W_LOCK,
    "board": _W_BOARD, "fatigue": _W_FATIGUE, "danger": _DANGER,
}


def resolve_weights(weights=None):
    """合并七权重:weights 按名覆盖默认值(仅认 W_KEYS 内的键);None/空=现行值。"""
    w = dict(DEFAULT_WEIGHTS)
    for k, v in (weights or {}).items():
        if k in w:
            w[k] = float(v)
    return w


def _prize_score(taken):
    """奖赏进度非线性计价:g(t)=6×(t/6)^1.5(中间进度打折,终局边际抬升)。"""
    t = max(0, min(6, int(taken)))
    return 6.0 * (t / 6.0) ** 1.5


def _is_fossil(card):
    """Antique 化石(pokemonType==2)免疫全部特殊状态(简化假设)。"""
    return bool(card) and (card or {}).get("pokemonType") == 2


def _status_flags(P, card):
    """出战位状态五槽(观测 PlayerState 布尔);化石免疫→全假。"""
    keys = ("poisoned", "burned", "asleep", "paralyzed", "confused")
    if _is_fossil(card):
        return {k: False for k in keys}
    return {k: bool(P.get(k)) for k in keys}


def _status_flow(flags):
    """状态期望伤害流(HP/回合):毒 10+灼伤 20;睡/麻无掉血。"""
    return (_POISON_DMG if flags["poisoned"] else 0.0) + \\
           (_BURN_DMG if flags["burned"] else 0.0)


def state_value(obs, my_i, weights=None):
    """叶子状态价值(我方视角):奖赏竞速主轴+状态/清场/牌库风险。"""
    w = resolve_weights(weights)
    cur = obs.get("current") or {}
    players = cur.get("players") or []
    my = players[my_i] if len(players) > my_i else {}
    opp = players[1 - my_i] if len(players) > 1 - my_i else {}
    res = cur.get("result")
    if isinstance(res, int) and res >= 0:
        return 1000.0 if res == my_i else -1000.0

    t_m = max(0, 6 - len(my.get("prize") or []))
    t_o = max(0, 6 - len(opp.get("prize") or []))
    prize = w["prize"] * (_prize_score(t_m) - _prize_score(t_o))

    my_a = (my.get("active") or [None])[0] or {}
    opp_a = (opp.get("active") or [None])[0] or {}
    my_c, opp_c = _card(my_a.get("id")), _card(opp_a.get("id"))
    my_st = _status_flags(my, my_c)
    opp_st = _status_flags(opp, opp_c)

    my_hp = max(0.0, (my_a.get("hp") or 0) - _STATUS_HORIZON * _status_flow(my_st)) / 380.0
    opp_hp = max(0.0, (opp_a.get("hp") or 0) - _STATUS_HORIZON * _status_flow(opp_st)) / 380.0

    def threat(atk_card, def_card, def_p, atk_st):
        """一击威胁(0/1 基准):睡/麻禁攻→0;混乱→50% 失效+反面自伤 30 期望折价。"""
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

    my_lock = 1.0 if (my_st["asleep"] or my_st["paralyzed"]) else 0.0
    opp_lock = 1.0 if (opp_st["asleep"] or opp_st["paralyzed"]) else 0.0

    my_n = 1 + len([b for b in (my.get("bench") or []) if isinstance(b, dict)])
    opp_n = 1 + len([b for b in (opp.get("bench") or []) if isinstance(b, dict)])
    my_max_hp = (my_c or {}).get("hp") or 380
    danger = w["danger"] if (my_n == 1 and (my_a.get("hp") or 0) < 0.35 * my_max_hp) else 0.0

    my_deck_n = my.get("deckCount") or 0
    fatigue = w["fatigue"] * (my_deck_n - (opp.get("deckCount") or 0)) / 60.0
    long_scale = min(1.0, my_deck_n / _DECK_REF)

    return (prize
            + long_scale * (w["hp"] * (my_hp - opp_hp)
                            + w["threat"] * (my_shot - opp_shot)
                            + w["lock"] * (opp_lock - my_lock))
            + w["board"] * (my_n - opp_n) + danger + fatigue)


def _rollout_value(st, sid, context, my_i, depth, weights, t0, rules_fold):
    """贪心折叠到我方第 depth 次再决策(或终局/步帽),返回叶子状态价值。"""
    arrival, n = 0, 0
    while n < _STEP_CAP:
        o = st["observation"]
        nxt = o.get("select")
        cur2 = o.get("current") or {}
        if nxt is None or (isinstance(cur2.get("result"), int) and cur2["result"] >= 0):
            break
        if nxt.get("context") == context and cur2.get("yourIndex") == my_i:
            arrival += 1
            if arrival >= depth:
                break
        if depth > 1 and time.time() - t0 > _TIME_CAP_S:
            break
        step = _pick_rules_fold(nxt, o, my_i) if rules_fold else _pick_greedy(nxt, my_i)
        st = search_step(sid, step)
        n += 1
    return state_value(st["observation"], my_i, weights)


def choose_with_search(obs, deck, context=0, weights=None, depth=1, fold="greedy"):
    """在当前选择点用 rollout 选优;任何失败回退贪心。仅对给定 context 启用搜索。"""
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
    if k != 1:  # 多选 v0 只按贪心;搜索用于单选决策点
        return _pick(sel)
    for i in range(len(opts)):
        if time.time() - t0 > _TIME_CAP_S:
            break
        try:
            st = search_begin(copy.deepcopy(obs), **preds)
            sid = st["searchId"]
            s = search_step(sid, [i])
            v = _rollout_value(s, sid, context, my_i, depth, weights, t0, rules_fold)
            search_release(sid)
            if best_score is None or v > best_score:
                best_score, best = v, i
        except Exception:
            continue
    if best is None:
        return _pick(sel)
    return [best]
'''

TEMPLATE = '''"""PTCG search+META 部署件(depth=1 搜索前瞻 × META 牌组,规则折叠)
2026-10-06 组装:内联 src/learn/{cg_search,search_lookahead}.py 与投影卡库/技库,
受测语义 = make_search_agent(META)(fna-028/fna-029;fold=rules/weights 默认)。
双保险:搜索层任何异常回退内联 v9.2 评估器贪心(submission_v9 同源逻辑)。
Kaggle exec 装载语义:不引用源文件路径内置名/不读本地文件/命名空间最后可调用对象 = agent。
随包 cg/libcg.so 相对定位(装载期 sys.path/cwd 探测),不可用降级 wheel 库,
再不可用禁搜索走兜底评估器;deck 阶段恒返回 META 牌组(60 张)。
"""
import copy
import json
import os
import sys
import time
import ctypes
from collections import Counter

# ================= 数据层(投影自 references/engine/cabt-{cards,attacks}.json,2026-10-05 抓) =================
# 卡 8 字段/技 3 字段=搜索路径全量所需;与 submission_v9 内联 blob 逐卡逐技等价(组装期断言)。
_CARD_ROWS = json.loads(r\'\'\'@CARDS_JSON@\'\'\')
_ATTACK_ROWS = json.loads(r\'\'\'@ATTACKS_JSON@\'\'\')
_CARDS = {c["cardId"]: c for c in _CARD_ROWS}
_ATTACKS = {a["attackId"]: a for a in _ATTACK_ROWS}

META_DECK = @META_DECK@

@SEARCH_BLOCK@

# ================= 兜底评估器(内联自 submission_v9/main.py,程序化改名防漂移) =================
# 触发条件:搜索库不可用(_LIB=None)或 choose_with_search 外层异常。评分公式/权重与 v9.2 同源。
# v9 blob 视图:由上方投影数据派生(组装期已断言与 v9 内联 blob 逐卡逐技等价),字符串键同 v9。
_FB_CARDS = {str(cid): {"ct": c.get("cardType"), "hp": c.get("hp"), "wt": c.get("weakness"),
                        "pt": c.get("pokemonType"), "ex": bool(c.get("ex") or c.get("megaEx")),
                        "rc": c.get("retreatCost"), "at": list(c.get("attacks") or []),
                        "et": c.get("energyType"), "rt": c.get("resistance"),
                        "mx": bool(c.get("megaEx"))} for cid, c in _CARDS.items()}
_FB_ATTACKS = {str(aid): {"d": a.get("damage") or 0, "e": list(a.get("energies") or [])}
               for aid, a in _ATTACKS.items()}
@W_LINE@

@FB_BLOCK@

# ================= 出口 agent(必须保持命名空间最后可调用对象) =================
def agent(obs, config=None):
    sel = (obs or {}).get("select")
    if sel is None:
        return list(META_DECK)
    if _LIB is not None:
        try:
            return choose_with_search(obs, META_DECK, context=0, weights=None, depth=1, fold="rules")
        except Exception:
            pass
    return _fallback_agent(obs)
'''


def main():
    assert "'''" not in cards_json and "'''" not in attacks_json, "blob 内有三引号冲突"
    os.makedirs(OUT, exist_ok=True)
    main_py = (TEMPLATE
               .replace("@CARDS_JSON@", cards_json)
               .replace("@ATTACKS_JSON@", attacks_json)
               .replace("@META_DECK@", repr(META))
               .replace("@SEARCH_BLOCK@", SEARCH_BLOCK)
               .replace("@W_LINE@", w_line)
               .replace("@FB_BLOCK@", fb_block.strip()))
    # 出口纪律:agent 必须是文件里最后一个 def(exec 装载取命名空间最后一个可调用对象)
    assert main_py.rindex("def ") == main_py.index("def agent(obs, config=None):")
    assert "__file__" not in main_py and "/mnt/" not in main_py and "/home/" not in main_py
    compile(main_py, "main.py", "exec")  # 语法预验
    with open(os.path.join(OUT, "main.py"), "w", encoding="utf-8") as f:
        f.write(main_py)
    with open(os.path.join(OUT, "deck.csv"), "w", encoding="utf-8") as f:
        f.write("\n".join(str(i) for i in META) + "\n")
    cg_dir = os.path.join(OUT, "cg")
    os.makedirs(cg_dir, exist_ok=True)
    src_so = os.path.join(ROOT, ".venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cg/libcg.so")
    shutil.copy2(src_so, os.path.join(cg_dir, "libcg.so"))
    tar_path = os.path.join(OUT, "submission.tar.gz")
    with tarfile.open(tar_path, "w:gz") as tf:
        for rel in ("deck.csv", "main.py"):
            tf.add(os.path.join(OUT, rel), arcname=rel)
        tf.add(os.path.join(cg_dir, "libcg.so"), arcname="cg/libcg.so")
    print("built:", OUT)
    print("main.py bytes:", os.path.getsize(os.path.join(OUT, "main.py")))
    print("tar bytes:", os.path.getsize(tar_path))


if __name__ == "__main__":
    main()
