import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from kaggle_environments.envs.cabt import cabt

from src.run_ab_judgment.ab_pair_configs import ab_pair_configs
from src.run_ab_judgment.append_registry_row import append_registry_row
from src.run_ab_judgment.net_delta_j import net_delta_j
from src.run_ab_judgment.pooled_winrate import pooled_winrate
from src.run_ab_judgment.run_ab_judgment import run_ab_judgment
from src.seed_agent.seed_agent import seed_agent


def test_ab_pair_configs_folds_and_error():
    cfgs = ab_pair_configs(6, ["first"])
    assert len(cfgs) == 12  # 6 种子 × 2 席 × 1 成员
    try:
        ab_pair_configs(5, ["first"])
        assert False
    except ValueError:
        pass


def test_net_delta_and_pooled():
    nd = net_delta_j([{"a_reward": 1, "b_reward": -1, "a_selfharm": 0},
                      {"a_reward": -1, "b_reward": 1, "a_selfharm": 0},
                      {"a_reward": 1, "b_reward": 1, "a_selfharm": 0}])
    assert nd["n_folds"] == 3 and nd["mean"] == 0.0  # 每折净账 [2,-2,0] 均值 0
    pw = pooled_winrate({"m1": [{"a_reward": 1, "b_reward": -1}, {"a_reward": 1, "b_reward": -1}],
                         "m2": [{"a_reward": -1, "b_reward": 1}]})
    assert pw["per_proto"]["m1"] == 1.0 and pw["per_proto"]["m2"] == 0.0
    assert pw["robust"] == 0.0  # maximin


def test_registry_row_appends(tmp_path):
    p = str(tmp_path / "registry.jsonl")
    rid = append_registry_row(p, {"id": "t1", "phenomenon": "x", "target": "y",
                                  "expected_signal": "z", "status": "pending"})
    assert rid == "t1"
    row = json.loads(open(p).read().splitlines()[0])
    assert row["date"] and row["scored_in"] == ""
    try:
        append_registry_row(p, {"id": "t2"})
        assert False
    except ValueError:
        pass


def test_ab_full_chain(tmp_path):
    r = run_ab_judgment(seed_agent, cabt.first_agent,
                        pool_config={"members": ["random"], "bo": 1}, folds=12,
                        registry_path=str(tmp_path / "reg.jsonl"))
    assert "A" in r["net_delta_J"] and "B" in r["net_delta_J"]
    assert r["pooled_winrate"]["A"]["robust"] is not None
    assert r["verdict_suggest"].startswith(("keep", "rollback"))
    assert json.loads(open(tmp_path / "reg.jsonl").read().splitlines()[0])["status"] == "pending"
    try:
        run_ab_judgment(seed_agent, cabt.first_agent, folds=6)
        assert False
    except ValueError:
        pass
