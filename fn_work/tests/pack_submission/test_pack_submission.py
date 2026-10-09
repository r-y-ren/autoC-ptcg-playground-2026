import os
import sys
import tarfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.pack_submission.count_daily_quota import count_daily_quota
from src.pack_submission.pack_submission import pack_submission
from src.pack_submission.sandbox_selfplay_once import sandbox_selfplay_once
from src.pack_submission.validate_bundle_structure import validate_bundle_structure

SUB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "submission"))


def test_count_quota(tmp_path, monkeypatch):
    monkeypatch.setenv("FN_WORK_RUNS_DIR", str(tmp_path))
    import importlib
    import src.pack_submission.count_daily_quota as m
    importlib.reload(m)
    assert m.count_daily_quota() == (0, 5)
    (tmp_path / "pack-quota-2026-10-05.jsonl").write_text('{"a":1}\n{"a":2}\n')
    assert m.count_daily_quota("2026-10-05") == (2, 3)


def test_validate_ok_and_bad(tmp_path):
    good = str(tmp_path / "good.tar.gz")
    with tarfile.open(good, "w:gz") as tf:
        tf.add(os.path.join(SUB, "main.py"), arcname="main.py")
        tf.add(os.path.join(SUB, "deck.csv"), arcname="deck.csv")
    ok, issues = validate_bundle_structure(good)
    assert ok and not issues, issues

    bad = str(tmp_path / "bad.tar.gz")
    with tarfile.open(bad, "w:gz") as tf:
        tf.add(os.path.join(SUB, "main.py"), arcname="pkg/main.py")  # 嵌套
    ok2, issues2 = validate_bundle_structure(bad)
    assert not ok2 and any("嵌套" in x or "缺 main.py" in x for x in issues2)


def test_sandbox_selfplay():
    good = "/tmp/_test_sub_bundle.tar.gz"
    with tarfile.open(good, "w:gz") as tf:
        tf.add(os.path.join(SUB, "main.py"), arcname="main.py")
        tf.add(os.path.join(SUB, "deck.csv"), arcname="deck.csv")
    ok, summary = sandbox_selfplay_once(good)
    assert ok and not summary["failed"], summary


def test_pack_full_flow(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FN_WORK_RUNS_DIR", str(tmp_path))
    import importlib
    import src.shared.write_runs_jsonl as wj
    importlib.reload(wj)
    import src.pack_submission.count_daily_quota as cq
    importlib.reload(cq)
    import src.pack_submission.pack_submission as pp
    importlib.reload(pp)
    out = str(tmp_path / "submission.tar.gz")
    r = pp.pack_submission(SUB, out)
    outtxt = capsys.readouterr().out
    assert r["ok"], r["issues"]
    assert "tar structure OK" in outtxt and "local self-play OK" in outtxt
    # 配额消耗 1
    assert cq.count_daily_quota()[0] == 1
