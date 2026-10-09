import importlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from kaggle_environments.envs.cabt import cabt

from src.run_judge_pool.run_judge_pool import run_judge_pool
from src.run_judge_pool.summarize_pool import summarize_pool


def test_summarize_basic():
    rows = [
        {"label_a": "self", "label_b": "self", "rewards": [1, -1], "failed": False},
        {"label_a": "self", "label_b": "self", "rewards": [-1, 1], "failed": False},
        {"label_a": "self", "label_b": "first", "rewards": [1, -1], "failed": False},
        {"label_a": "self", "label_b": "first", "rewards": [-1, 1], "failed": False},
        {"label_a": "self", "label_b": "first", "rewards": [-1, 1], "failed": True},
    ]
    r = summarize_pool(rows)
    assert r["self_mirror_h2h"] == 0.5 and r["self_mirror_decided"] == 2
    assert r["members"]["first"]["winrate"] == 0.5  # 1W1L（第三局 failed 不计）


def test_summarize_empty_raises():
    try:
        summarize_pool([])
        assert False
    except ValueError:
        pass


def test_pool_runs_small(capsys, tmp_path):
    os.environ["FN_WORK_RUNS_DIR"] = str(tmp_path)
    try:
        import src.shared.write_runs_jsonl as wj
        importlib.reload(wj)
        import src.run_judge_pool.run_judge_pool as rp
        importlib.reload(rp)
        report = rp.run_judge_pool({
            "agent": cabt.first_agent, "n_mirror": 4, "n_anchor": 2,
            "anchors": {"random": cabt.random_agent}, "bo": 1, "seed0": 3,
        })
        out = capsys.readouterr().out
        assert "self-mirror h2h:" in out and "vs random:" in out
        assert report["self_mirror_h2h"] is not None
        assert 0.0 <= report["self_mirror_h2h"] <= 1.0
        runs_files = list(tmp_path.glob("judge-pool-*.jsonl"))
        assert runs_files and json.loads(runs_files[0].read_text().splitlines()[-1])["self_mirror_h2h"] is not None
    finally:
        os.environ.pop("FN_WORK_RUNS_DIR", None)
