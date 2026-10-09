import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from kaggle_environments.envs.cabt import cabt

from src.mine_assets.filter_high_scores import filter_high_scores
from src.mine_assets.mine_assets import mine_assets
from src.mine_assets.aggregate_state_action import aggregate_state_action
from src.record_episode.record_episode import record_episode


def _fake_ep(eid, steps, rewards, failed=False):
    return {"id": eid, "metadata": {"rewards": rewards, "n_steps": len(steps), "failed": failed}, "steps": steps}


def test_filter_quantile_and_decisive():
    eps = [_fake_ep(i, [{"step": i, "active": 0, "action": [0], "option_types": [13], "state": {"turn": 1, "hand": 7, "prize": 6}}] * (10 + i),
                    [1, -1] if i % 3 else [0, 0]) for i in range(10)]
    kept = filter_high_scores(eps, 0.5)
    assert len(kept) == 3  # 10 局中 7 局决出胜负（i%3!=0），50%=3
    assert all(abs(e["metadata"]["rewards"][0] - e["metadata"]["rewards"][1]) > 0 for e in kept)
    assert kept[0]["reason"]["n_steps"] <= kept[-1]["reason"]["n_steps"]


def test_alignment_semantics():
    # 完美对齐=1.0 / 首拍分叉=0 / 中途分叉=idx/n（B3-B7 评审纠反转 bug 后的语义锁定）
    from src.mine_assets.measure_alignment import measure_alignment
    mk = lambda acts: {"id": "x", "metadata": {"rewards": [1, -1]},
                       "steps": [{"step": i + 1, "active": 0, "action": [0],
                                  "option_types": [a], "state": {"turn": 1, "hand": 7, "prize": 6}}
                                 for i, a in enumerate(acts)]}
    table = {(0, 7, 6): {(13,): 1}}
    perfect = measure_alignment(table, [mk([13, 13, 13])])
    assert perfect["mean"] == 1.0
    first_div = measure_alignment(table, [mk([14, 13, 13])])
    assert first_div["mean"] == 0.0
    mid_div = measure_alignment(table, [mk([13, 13, 14])])
    assert mid_div["mean"] == 0.6667  # 第 3 拍分叉：前 2/3 对齐


def test_aggregate_counts_and_sig():
    s = [{"step": 1, "active": 0, "action": [0], "option_types": [13, 14], "state": {"turn": 2, "hand": 7, "prize": 6}},
         {"step": 2, "active": 0, "action": [1], "option_types": [13, 14], "state": {"turn": 2, "hand": 7, "prize": 6}}]
    t = aggregate_state_action([(_fake_ep(1, s, [1, -1]), 0)])
    cell = t[(0, 7, 6)]
    assert cell[(13,)] == 1 and cell[(14,)] == 1


def test_mine_assets_end_to_end(tmp_path):
    d = str(tmp_path / "eps")
    os.makedirs(d)
    for i in range(8):
        record_episode(cabt.first_agent, cabt.random_agent, list(cabg := cabt.deck), list(cabt.deck),
                       200 + i, os.path.join(d, f"e{i}.json"), config={"bo": 1})
    r = mine_assets(d, 0.5, out_dir=str(tmp_path / "out"))
    assert r["n_kept"] >= 1 and os.path.isfile(r["spec"])
    assert r["directional"] is True  # <30 局，标方向性
    # 可复跑：同输入再跑同输出行数
    r2 = mine_assets(d, 0.5, out_dir=str(tmp_path / "out2"))
    assert open(r["spec"]).read() == open(r2["spec"]).read()
