import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.probe_gsk_launch.probe_gsk_launch import probe_gsk_launch


def test_probe_not_live_or_unknown(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FN_WORK_RUNS_DIR", str(tmp_path))
    import src.probe_gsk_launch.probe_gsk_launch as m
    import src.shared.write_runs_jsonl as wj
    import importlib
    importlib.reload(wj)
    importlib.reload(m)
    r = m.probe_gsk_launch()  # 真实网络探测（CLI+HTTP）
    assert r["status"] in ("not-live", "live", "unknown")
    out = capsys.readouterr().out
    assert "gsk-simulation:" in out
    if r["status"] == "live":
        assert "核验清单" in out
