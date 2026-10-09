"""prize_solver 计价换引擎口径(pokemonType 卡框)与终局截断语义(报告 §5)"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.learn.prize_solver import _prize_value


def test_prize_value_by_pokemon_type():
    # 引擎 KOProc3 分支:卡框 3(ex)=2 张、4(Mega ex)=3 张、其他=1 张(§5.1)
    assert _prize_value({"pokemonType": 3, "ex": True}) == 2.0
    assert _prize_value({"pokemonType": 4, "megaEx": True}) == 3.0
    assert _prize_value({"pokemonType": 1}) == 1.0
    assert _prize_value({"pokemonType": 2}) == 1.0  # Antique 化石卡框,按普通 1 张
    assert _prize_value({"pokemonType": 0}) == 1.0
    assert _prize_value(None) == 1.0


def test_prize_value_flag_fallback():
    # pokemonType 缺失才退 megaEx/ex 布尔;有卡框时以卡框为准(§8.3 互斥红线)
    assert _prize_value({"megaEx": True}) == 3.0
    assert _prize_value({"ex": True}) == 2.0
    assert _prize_value({"ex": True, "megaEx": True, "pokemonType": 3}) == 2.0
    assert _prize_value({}) == 1.0


def test_race_bonus_terminal_truncation(monkeypatch):
    # 终局截断(§5.3):本次击杀清空剩余奖赏即 win_now,余张不取,不清算后续假想领取
    import src.learn.prize_solver as ps
    monkeypatch.setattr(ps, "_card", lambda cid: None)
    monkeypatch.setattr(ps, "can_ko", lambda a, b: True)
    monkeypatch.setattr(ps, "_prize_value", lambda c: 3.0)
    my = {"prize": [None, None], "bench": []}
    opp = {"prize": [None] * 6, "bench": []}
    wn, re_, danger = ps.race_bonus(my, opp, {"id": 1}, {"id": 2})
    assert wn == 1.0 and re_ == 0.0
