import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from kaggle_environments.envs.cabt import cabt

from src.diff_episode.diff_episode import diff_episode
from src.diff_episode.first_divergence import first_divergence
from src.record_episode.record_episode import record_episode


def test_first_divergence_pure():
    assert first_divergence([1, 2, 3], [1, 2, 3]) is None
    assert first_divergence([1, 2, 3], [1, 9, 3]) == 1
    assert first_divergence([1, 2], [1, 2, 3]) == 2
    try:
        first_divergence([], [1])
        assert False
    except ValueError:
        pass


def test_self_diff_no_divergence(tmp_path):
    a = str(tmp_path / "a.json")
    record_episode(cabt.first_agent, cabt.random_agent, list(cabt.deck), list(cabt.deck), 21, a, config={"bo": 1})
    assert diff_episode(a, a) == {"diverged": False}


def test_tampered_step_detected(tmp_path):
    a = str(tmp_path / "a.json")
    b = str(tmp_path / "b.json")
    record_episode(cabt.first_agent, cabt.random_agent, list(cabt.deck), list(cabt.deck), 21, a, config={"bo": 1})
    ep = json.load(open(a))
    tamper_at = None
    for i, s in enumerate(ep["steps"]):
        if s["active"] in (0, 1) and s.get("action") is not None:
            tamper_at = i
            break
    assert tamper_at is not None
    ep["steps"][tamper_at]["action"] = [9999]
    json.dump(ep, open(b, "w"))
    d = diff_episode(a, b)
    assert d["diverged"] and d["step"] == ep["steps"][tamper_at]["step"]


def test_broken_json_reports_line(tmp_path):
    a = str(tmp_path / "a.json")
    record_episode(cabt.first_agent, cabt.random_agent, list(cabt.deck), list(cabt.deck), 21, a, config={"bo": 1})
    bad = str(tmp_path / "bad.json")
    open(bad, "w").write('{\n  "steps": oops\n')
    try:
        diff_episode(a, bad)
        assert False
    except ValueError as e:
        assert "行" in str(e)
