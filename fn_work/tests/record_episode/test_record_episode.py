import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from kaggle_environments.envs.cabt import cabt

from src.record_episode.record_episode import record_episode
from src.record_episode.serialize_episode import serialize_episode


def test_record_and_load_roundtrip(tmp_path):
    p = str(tmp_path / "ep1.json")
    out = record_episode(cabt.first_agent, cabt.random_agent, list(cabt.deck), list(cabt.deck), 11, p, config={"bo": 1})
    assert out == p and os.path.isfile(p)
    ep = json.load(open(p))
    assert ep["schema_version"] == 1 and ep["steps"] and ep["metadata"]["n_steps"] == len(ep["steps"])


def test_serialize_missing_steps_raises():
    try:
        serialize_episode({"rewards": [1, -1]})
        assert False
    except ValueError:
        pass


def test_failed_match_writes_marker(tmp_path):
    def broken(obs, config=None):
        raise RuntimeError("boom")

    p = str(tmp_path / "ep2.json")
    out = record_episode(broken, cabt.first_agent, list(cabt.deck), list(cabt.deck), 5, p, config={"bo": 1})
    assert out.endswith(".failed") and not os.path.exists(p)
    marker = json.load(open(out))
    assert marker["failed"] is True
