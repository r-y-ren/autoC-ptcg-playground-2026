import importlib
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.fetch_episodes.dedup_register import dedup_register
from src.fetch_episodes.fetch_episodes import fetch_episodes


def test_dedup_and_index(tmp_path):
    idx = str(tmp_path / "INDEX.md")
    eps = [{"id": 1, "source": "x", "note": "a"}, {"id": 2}, {"id": 1}]
    n, dup, seen = dedup_register(eps, idx)
    assert (n, dup) == (2, 1) and seen == {1, 2}
    n2, dup2, _ = dedup_register([{"id": 1}], idx, seen)
    assert (n2, dup2) == (0, 1)
    head = open(idx, encoding="utf-8").read()
    assert "| 1 |" in head and "x" in head


def test_fetch_flow_with_mock_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("FN_WORK_RUNS_DIR", str(tmp_path))
    import src.shared.write_runs_jsonl as wj
    importlib.reload(wj)
    import src.fetch_episodes.kaggle_cli_pull as kp
    importlib.reload(kp)

    calls = {"n": 0}
    def fake_pull(target):
        calls["n"] += 1
        if target.get("kind") == "episode" and target.get("id") == 99:
            raise RuntimeError("boom")
        return [{"id": 100 + calls["n"], "reward": 1}]

    monkeypatch.setattr(kp, "kaggle_cli_pull", fake_pull)
    import src.fetch_episodes.fetch_episodes as fe
    importlib.reload(fe)
    monkeypatch.setattr(fe, "kaggle_cli_pull", fake_pull)
    import src.fetch_episodes.dedup_register as dr
    monkeypatch.setattr(fe, "_SEEN_PATH", str(tmp_path / "seen.json"))

    store = str(tmp_path / "eps")
    r = fe.fetch_episodes(
        [{"kind": "episodes", "competition": "c"}, {"kind": "episode", "competition": "c", "id": 99}],
        store_dir=store, index_path=str(tmp_path / "INDEX.md"))
    assert calls["n"] == 2
    assert len(r["failed"]) == 1 and "boom" in r["failed"][0]["err"]
    stored = [f for f in os.listdir(store) if f.endswith(".json")]
    assert len(stored) == 1  # 第二目标失败，第一目标的 1 条已存
    assert os.path.isfile(tmp_path / "INDEX.md")
