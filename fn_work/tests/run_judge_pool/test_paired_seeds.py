"""判决池配对种子设计(报告 §10.1/§14.5):候选与锚打同一 seed 序列,报告带 paired_seeds 标记"""
import importlib
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from kaggle_environments.envs.cabt import cabt


def test_paired_seeds_flag(tmp_path):
    os.environ["FN_WORK_RUNS_DIR"] = str(tmp_path)
    try:
        import src.shared.write_runs_jsonl as wj
        importlib.reload(wj)
        import src.run_judge_pool.run_judge_pool as rp
        importlib.reload(rp)
        report = rp.run_judge_pool({
            "agent": cabt.first_agent, "n_mirror": 2, "n_anchor": 2,
            "anchors": {"first": cabt.first_agent}, "bo": 1, "seed0": 5,
        })
        assert report["paired_seeds"] is True
        assert report["config"]["seed0"] == 5
    finally:
        os.environ.pop("FN_WORK_RUNS_DIR", None)
