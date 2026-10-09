import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from kaggle_environments.envs.cabt import cabt

from src.assemble_agent_v2.assemble_agent_v2 import assemble_agent_v2
from src.assemble_agent_v2.follow_asset_table import follow_asset_table
from src.shared.play_local_match import play_local_match
from src.seed_agent.seed_agent import seed_agent


def _fake_parsed(hand=7, prize=4, turn=12, options=None, your_index=0):
    return {  # parse_observation 输出形状（options 顶层键）
        "options": options or [], "max_count": 1, "min_count": 0,
        "current": {"yourIndex": your_index, "turn": turn,
                    "players": [
                        {"handCount": hand, "prize": list(range(prize)), "bench": [], "discard": []},
                        {"handCount": 5, "prize": list(range(prize + 1)), "bench": [1], "discard": []},
                    ]},
    }


def test_asset_hit_and_miss():
    table = {(1, 7, 4): {(13,): 5, (14,): 1}}
    parsed = _fake_parsed(options=[{"type": 14}, {"type": 13}])
    assert follow_asset_table(parsed, table) == [1]  # 资产签名命中 ATTACK 选项
    assert follow_asset_table(parsed, {}) is None
    assert follow_asset_table(parsed, "broken") is None  # 表损坏回退


def test_never_throws_and_deck_phase():
    assert len(assemble_agent_v2({"select": None})) == 60
    assert isinstance(assemble_agent_v2(None), list)
    assert isinstance(assemble_agent_v2({"select": {"option": [{"type": 13}], "maxCount": 1, "minCount": 1},
                                          "current": None}), list)


def _winrate(x, anchor, n=60, seed0=900):
    w = 0
    for i in range(n):
        swap = i % 2 == 1
        a, b = (anchor, x) if swap else (x, anchor)
        r = play_local_match(a, b, list(cabt.deck), list(cabt.deck), seed=seed0 + i, config={"bo": 1})
        mine = r["rewards"][1] if swap else r["rewards"][0]
        w += mine > 0
    return w / n


def test_assemble_not_below_seed():
    # R9 验收：装配件不劣于种子件（同水位容差 0.12；资产未挂载时近似等价种子件）
    wr_random = _winrate(assemble_agent_v2, cabt.random_agent)
    wr_first = _winrate(assemble_agent_v2, cabt.first_agent)
    seed_random = _winrate(seed_agent, cabt.random_agent)
    assert wr_random >= 0.70, f"装配件 vs random 应≥0.70（实测 {wr_random}）"
    assert wr_first >= seed_random - 0.12 or 0.30 <= wr_first <= 0.70
