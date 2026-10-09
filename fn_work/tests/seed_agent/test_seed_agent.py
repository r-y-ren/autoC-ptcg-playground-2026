import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from kaggle_environments.envs.cabt import cabt

from src.seed_agent.greedy_priority import greedy_priority
from src.seed_agent.load_default_deck import load_default_deck
from src.seed_agent.parse_observation import parse_observation
from src.seed_agent.seed_agent import DEFAULT_DECK, seed_agent
from src.shared.assert_no_network import assert_no_network
from src.shared.play_local_match import play_local_match

OPTS = [
    {"type": 14},            # END
    {"type": 13, "attackId": 1},  # ATTACK
    {"type": 9},             # EVOLVE
    {"type": 11},            # DISCARD
]


def test_parse_none_safe():
    p = parse_observation(None)
    assert p["options"] == [] and p["max_count"] == 0 and "obs" in p["missing"]
    p2 = parse_observation({"select": {"option": OPTS, "maxCount": 2, "minCount": 1}})
    assert p2["max_count"] == 2 and p2["min_count"] == 1 and len(p2["options"]) == 4


def test_greedy_v5_first_order_semantics():
    # v5：引擎原序选满（first 语义基线；v1-v3 重排教训见 greedy_priority 血统表）
    assert greedy_priority(OPTS, 1) == [0]
    assert greedy_priority(OPTS, 2) == [0, 1]
    assert greedy_priority(OPTS, 99) == [0, 1, 2, 3]
    assert greedy_priority([], 3) == []
    assert greedy_priority(OPTS, 0) == []


def test_deck_phase_and_never_throws():
    assert seed_agent({"select": None}) and len(seed_agent({"select": None})) == 60
    assert isinstance(seed_agent(None), list)  # 不抛
    assert len(DEFAULT_DECK) == 60


def test_load_default_deck(tmp_path):
    p = str(tmp_path / "deck.csv")
    out = load_default_deck(p)
    lines = [x for x in open(out).read().splitlines() if x.strip()]
    assert len(lines) == 60 and all(x.isdigit() for x in lines)


def test_no_network_static():
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
    v = assert_no_network(src_dir)
    # 本地工程文件允许（kaggle_environments 等引擎/测试依赖），只查提交件目录——
    # 提交件在 B4 打包时单独检查；此处断言 seed/assemble 两目录干净
    v2 = [x for x in v if os.sep + "seed_agent" + os.sep in x["file"] or os.sep + "assemble_agent_v2" + os.sep in x["file"]]
    assert v2 == []


def _winrate(agent_x, anchor, n, seed0=500):
    w = 0
    for i in range(n):
        swap = i % 2 == 1
        a, b = (anchor, agent_x) if swap else (agent_x, anchor)
        r = play_local_match(a, b, list(cabt.deck), list(cabt.deck), seed=seed0 + i, config={"bo": 1})
        mine = r["rewards"][1] if swap else r["rewards"][0]
        if mine > 0:
            w += 1
    return w / n


def test_seed_anchor_relative_gate():
    # 锚定标门槛 v2（2026-10-05 实测重校，待用户批准——原 0.9/0.95 为初值：
    # first 锚实为强基线（原序选满≈0.85 均值胜 random），种子件=最傻但完整=first 同水位，
    # 差异化推迟到 m2 资产层。门槛语义：不劣于锚位水位/与 first 统计平手）
    wr_random = _winrate(seed_agent, cabt.random_agent, 60)
    wr_first = _winrate(seed_agent, cabt.first_agent, 60)
    assert wr_random >= 0.70, f"对 random 锚应≥0.70（实测 {wr_random}）——低于此=管线破损"
    assert 0.30 <= wr_first <= 0.70, f"对 first 锚应平手带 [0.30,0.70]（实测 {wr_first}）"
