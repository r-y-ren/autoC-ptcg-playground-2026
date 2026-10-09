import os
import shutil
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from kaggle_environments.envs.cabt import cabt

from src.cluster_opponents.cluster_opponents import cluster_opponents
from src.record_episode.record_episode import record_episode


def _make_episodes(d, n=12):
    for i in range(n):
        record_episode(cabt.first_agent, cabt.random_agent, list(cabt.deck), list(cabt.deck),
                       100 + i, os.path.join(d, f"ep{i}.json"), config={"bo": 1})


def test_cluster_separates_first_random(tmp_path):
    d1 = str(tmp_path / "eps")
    _make_episodes(d1, n=12)
    r1 = cluster_opponents(d1, str(tmp_path / "out1"))
    assert r1["n_episodes"] == 12
    assert r1["n_prototypes"] >= 2, "first vs random 两类行为应至少聚成 2 原型"
    # 稳定性：同数据重跑原型数 ±1、矩阵文件存在
    r2 = cluster_opponents(d1, str(tmp_path / "out2"))
    assert abs(r1["n_prototypes"] - r2["n_prototypes"]) <= 1
    # 成员漂移 <10%：同数据重跑各原型成员集 Jaccard ≥0.9
    m1 = {p["proto_id"]: set(p["members"]) for p in r1["prototypes"]}
    m2 = {p["proto_id"]: set(p["members"]) for p in r2["prototypes"]}
    for pid, members in m1.items():
        if pid in m2:
            inter = len(members & m2[pid])
            union = len(members | m2[pid])
            assert union and inter / union >= 0.9, f"原型 {pid} 成员漂移超限"
    assert os.path.isfile(r1["matrix"]) and os.path.isfile(r1["cards_md"])


def test_cluster_too_few_raises(tmp_path):
    try:
        cluster_opponents(str(tmp_path), str(tmp_path / "o"))
        assert False
    except ValueError:
        pass
