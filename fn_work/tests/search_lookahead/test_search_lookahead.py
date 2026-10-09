"""search_lookahead v0.1 叶子增厚的语义锁定测试(状态/清场/牌库/终局折价/混乱)"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))  # references 相对路径

from learn import search_lookahead as sl


def _P(prize=0, deck=30, bench=0, hp=200, **st):
    p = {"prize": list(range(prize)), "deckCount": deck, "handCount": 5, "bench": [{}] * bench,
         "active": [{"id": 1, "hp": hp}]}
    p.update({k: bool(st.get(k, False)) for k in
              ("poisoned", "burned", "asleep", "paralyzed", "confused")})
    return p


def _obs(my, opp, result=-1, your=0):
    return {"current": {"yourIndex": your, "result": result, "players": [my, opp]}}


def test_terminal_and_prize_nonlinear():
    assert sl.state_value(_obs(_P(), _P()), 0) != 1000.0  # 未终局不给终局值
    assert sl.state_value(_obs(_P(), _P(), result=0), 0) == 1000.0
    assert sl.state_value(_obs(_P(), _P(), result=1), 0) == -1000.0
    # §5.3:中间进度相对线性打折、越接近拿完边际越高(凸)
    g = sl._prize_score
    assert g(6) - g(5) > g(1) - g(0)          # 第 6 张边际 > 第 1 张
    assert sl._W_PRIZE * g(3) < 30.0           # 3 张领先低于线性 30 分
    v_lead5 = sl.state_value(_obs(_P(prize=5), _P(prize=4)), 0)
    v_lead1 = sl.state_value(_obs(_P(prize=1), _P(prize=0)), 0)
    assert v_lead5 > 2.0 * v_lead1             # 第 5 张边际≈第 1 张的 3 倍(非线性接近胜利)


def test_status_flow_and_lock():
    neutral = sl.state_value(_obs(_P(), _P()), 0)
    opp_poison = sl.state_value(_obs(_P(), _P(poisoned=True)), 0)
    my_poison = sl.state_value(_obs(_P(poisoned=True), _P()), 0)
    assert opp_poison > neutral > my_poison     # 毒 10/回合进期望伤害流
    assert sl.state_value(_obs(_P(), _P(burned=True)), 0) > opp_poison  # 灼伤 20>毒 10
    # 睡/麻=禁攻禁撤(行动锁):锁对方加分,被锁减分
    assert sl.state_value(_obs(_P(), _P(asleep=True)), 0) > neutral
    assert sl.state_value(_obs(_P(paralyzed=True), _P()), 0) < neutral


def test_fossil_status_immune(monkeypatch):
    monkeypatch.setattr(sl, "_card", lambda cid: {"hp": 380, "pokemonType": 2})
    assert sl.state_value(_obs(_P(poisoned=True, burned=True), _P()), 0) == \
           sl.state_value(_obs(_P(), _P()), 0)  # 化石免疫状态(§6.2 简化假设)


def test_confusion_folds_into_threat(monkeypatch):
    monkeypatch.setattr(sl, "_card", lambda cid: {"hp": 380, "pokemonType": 1})
    monkeypatch.setattr(sl, "_attacks_of", lambda c: [{"damage": 999}])
    monkeypatch.setattr(sl, "_eff_damage", lambda base, a, b: 999)
    neutral = sl.state_value(_obs(_P(), _P()), 0)
    my_confused = sl.state_value(_obs(_P(confused=True), _P()), 0)
    opp_confused = sl.state_value(_obs(_P(), _P(confused=True)), 0)
    assert my_confused < neutral < opp_confused  # 我方混乱威胁打 5 折+自伤期望
    # 睡/麻禁攻→威胁 0(对方睡着打不了我)
    assert sl.state_value(_obs(_P(), _P(asleep=True)), 0) > neutral


def test_board_risk_and_deck_fatigue():
    neutral = sl.state_value(_obs(_P(), _P()), 0)
    assert sl.state_value(_obs(_P(bench=3), _P(bench=1)), 0) > neutral  # 存量差独立权重
    # 后备空+出战濒死=高危(§7.4)
    danger = sl.state_value(_obs(_P(hp=50), _P()), 0)
    safe = sl.state_value(_obs(_P(hp=300), _P()), 0)
    assert danger < safe
    assert sl.state_value(_obs(_P(bench=1, hp=50), _P()), 0) > danger + 1.0  # 有后备不触发
    # 牌库差进疲劳项(权重 2.0):余牌多者占优
    assert sl.state_value(_obs(_P(deck=50), _P(deck=10)), 0) > neutral
    assert sl.state_value(_obs(_P(deck=10), _P(deck=50)), 0) < neutral
    # 长盘衰减:我方牌库枯竭时慢转换项(如血差)折价
    lead = sl.state_value(_obs(_P(deck=50, hp=380), _P(deck=50, hp=1)), 0)
    starved = sl.state_value(_obs(_P(deck=3, hp=380), _P(deck=3, hp=1)), 0)
    assert starved < lead


# ---- v0.2 规则感知折叠 _pick_rules_fold + depth(f7e752 §3 回合结构;三模式单变量) ----

def _sel(opts, mc=1, mn=1, ctx=0):
    return {"context": ctx, "option": opts, "maxCount": mc, "minCount": mn}


def _fold_obs(hand=(), my_a=None, opp_a=None, your=0):
    act = {"id": 920, "hp": 140, "energies": [1]}
    return {"current": {"yourIndex": your, "result": -1, "players": [
        {"hand": list(hand), "active": [my_a if my_a is not None else dict(act)],
         "prize": [], "deckCount": 30},
        {"hand": [], "active": [opp_a if opp_a is not None else dict(act)],
         "prize": [], "deckCount": 30}]}}


def test_rules_fold_resource_order(monkeypatch):
    # ①贴能 > 攻击(即使可 KO):攻击即终局化(§3.5),先资源后攻击
    monkeypatch.setattr(sl, "_eff_damage", lambda *a: 999)
    sel = _sel([{"type": 13, "attackId": 114},
                {"type": 8, "area": 2, "index": 0, "inPlayArea": 4, "inPlayIndex": 0},
                {"type": 14}])
    hand = [{"id": 3}]  # Basic {W} Energy
    assert sl._pick_rules_fold(sel, _fold_obs(hand=hand), 0) == [1]
    # ①贴能出战位优先于备战
    sel2 = _sel([{"type": 8, "area": 2, "index": 0, "inPlayArea": 5, "inPlayIndex": 0},
                 {"type": 8, "area": 2, "index": 0, "inPlayArea": 4, "inPlayIndex": 0}])
    assert sl._pick_rules_fold(sel2, _fold_obs(hand=hand), 0) == [1]
    # ②支援者(cardType=3)>普通道具;⑦END 殿后(支援者在选项序 2 号位)
    sel3 = _sel([{"type": 14}, {"type": 7, "index": 1}, {"type": 7, "index": 0}])
    hand3 = [{"id": 1227}, {"id": 1071}]  # Lillie's Determination(支援者) / 道具
    assert sl._pick_rules_fold(sel3, _fold_obs(hand=hand3), 0) == [2]
    # ③进化 > ④其他行动
    sel4 = _sel([{"type": 7, "index": 0},
                 {"type": 9, "area": 2, "index": 1, "inPlayArea": 4, "inPlayIndex": 0}])
    hand4 = [{"id": 1071}, {"id": 3}]
    assert sl._pick_rules_fold(sel4, _fold_obs(hand=hand4), 0) == [1]


def test_rules_fold_attack_tiers(monkeypatch):
    # ⑤一击 KO > ⑥普通攻击 > ⑦END(旧贪心会拿 0 号=END)
    monkeypatch.setattr(sl, "_attack_ko", lambda aid, ma, oa: aid == 5)
    sel = _sel([{"type": 14}, {"type": 13, "attackId": 6}, {"type": 13, "attackId": 5}])
    assert sl._pick_rules_fold(sel, _fold_obs(), 0) == [2]
    # ⑥普通攻击取 eff 最大(同档 eff 平手守引擎序)
    monkeypatch.setattr(sl, "_attack_ko", lambda aid, ma, oa: False)
    monkeypatch.setattr(sl, "_attack_eff", lambda aid, ma, oa: {6: 10, 7: 60}.get(aid, 0))
    sel2 = _sel([{"type": 13, "attackId": 6}, {"type": 13, "attackId": 7}])
    assert sl._pick_rules_fold(sel2, _fold_obs(), 0) == [1]
    sel3 = _sel([{"type": 13, "attackId": 7}, {"type": 13, "attackId": 6}])
    assert sl._pick_rules_fold(sel3, _fold_obs(), 0) == [0]


def test_rules_fold_ko_needs_energy_covered(monkeypatch):
    # attack_feats 同款判定:eff 够但能量不覆盖→不算 KO(降普通攻击档)
    monkeypatch.setattr(sl, "_eff_damage", lambda *a: 999)
    covered = sl._pick_rules_fold(
        _sel([{"type": 13, "attackId": 114}]), _fold_obs(my_a={"id": 920, "hp": 140, "energies": [1]}), 0)
    uncovered = sl._pick_rules_fold(
        _sel([{"type": 13, "attackId": 114}]), _fold_obs(my_a={"id": 920, "hp": 140, "energies": [4]}), 0)
    assert covered == uncovered == [0]  # 单攻击选项两者仍选攻击,分类差异只影响档位
    ko_tier = sl._attack_ko(114, {"id": 920, "energies": [1]}, {"id": 920, "hp": 5})
    no_tier = sl._attack_ko(114, {"id": 920, "energies": [4]}, {"id": 920, "hp": 5})
    assert ko_tier is True and no_tier is False


def test_rules_fold_actor_perspective_and_fallback():
    # 行动方视角:yourIndex=1 时按 1 号位手牌/出战分类(对手回合同律)
    obs = _fold_obs(hand=[{"id": 1227}], your=1)
    sel = _sel([{"type": 14}, {"type": 7, "index": 0}])
    assert sl._pick_rules_fold(sel, obs, 0) == [1]
    # 手牌不可观测(搜索态对手视角)→支援者识别退化为④档(普通行动),仍先于⑦END,不抛
    assert sl._pick_rules_fold(sel, _fold_obs(hand=[]), 1) == [1]
    # ④档内守引擎序(两选项同为未分类行动)
    assert sl._pick_rules_fold(_sel([{"type": 1}, {"type": 2}]), _fold_obs(), 0) == [0]
    assert sl._pick_rules_fold(_sel([]), _fold_obs(), 0) == []


def test_choose_with_search_new_args_fallback():
    # depth/fold 为新参:不可搜索观测走异常回退=贪心;非本 context 走 _pick,老调用不受影响
    deck = [1, 2, 3]
    obs = {"select": _sel([{"type": 7, "index": 0}, {"type": 14}])}
    assert sl.choose_with_search(obs, deck) == sl._pick(obs["select"])
    assert sl.choose_with_search(obs, deck, depth=2, fold="rules") == sl._pick(obs["select"])
    other = {"select": _sel([{"type": 1}, {"type": 2}], ctx=9)}
    assert sl.choose_with_search(other, deck) == sl._pick(other["select"])
    ag = sl.make_search_agent(deck, depth=2, fold="rules")
    assert ag({"select": None}) == list(deck)
    assert ag(obs) == sl._pick(obs["select"])
