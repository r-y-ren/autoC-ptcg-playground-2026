import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.prepare_metrics_shards.collect_runs_shards import collect_runs_shards
from src.prepare_metrics_shards.prepare_metrics_shards import prepare_metrics_shards
from src.prepare_metrics_shards.validate_ladder_readback import validate_ladder_readback


def test_collect_last_row_per_category(tmp_path):
    (tmp_path / "judge-pool-2026-10-05.jsonl").write_text(
        '{"ts":"t","category":"judge-pool","self_mirror_h2h":0.5}\n{"ts":"t2","category":"judge-pool","self_mirror_h2h":0.6}\n')
    s = collect_runs_shards(str(tmp_path))
    assert len(s) == 1 and s[0]["metrics"]["self_mirror_h2h"] == 0.6
    assert "L2" in s[0]["source"]


def test_validate_readback():
    ok = validate_ladder_readback({"ladder_mu": 612.3, "ladder_mu_date": "2026-10-05",
                                   "source_url": "https://www.kaggle.com/competitions/x/leaderboard"})
    assert ok["metrics"]["ladder_mu"] == 612.3
    for bad in [{"ladder_mu_date": "x", "source_url": "y"},  # 缺 mu
                {"ladder_mu": 9999, "ladder_mu_date": "2026-10-05", "source_url": "https://x"},
                {"ladder_mu": 600, "ladder_mu_date": "2026/10/05", "source_url": "https://x"}]:
        try:
            validate_ladder_readback(bad)
            assert False
        except ValueError:
            pass


def test_prepare_end_to_end(tmp_path):
    (tmp_path / "runs").mkdir(); (tmp_path / "runs" / "a-2026-10-05.jsonl").write_text(
        '{"ts":"t","category":"a","v":1}\n')
    rb = tmp_path / "readback.json"
    rb.write_text(json.dumps({"ladder_mu": 600, "ladder_mu_date": "2026-10-05", "source_url": "https://kaggle.com/x"}))
    import os
    os.environ["FN_WORK_RUNS_DIR"] = str(tmp_path / "runs")
    try:
        out = prepare_metrics_shards(str(tmp_path / "runs"), str(rb), out_dir=str(tmp_path / "shards"))
        assert os.path.isfile(os.path.join(out, "ladder-readback.json"))
        assert os.path.isfile(os.path.join(out, "a.json"))
    finally:
        os.environ.pop("FN_WORK_RUNS_DIR")
