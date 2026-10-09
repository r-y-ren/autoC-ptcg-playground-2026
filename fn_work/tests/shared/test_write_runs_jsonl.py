import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.shared.write_runs_jsonl import write_runs_jsonl


def test_append_and_format(tmp_env=None):
    with tempfile.TemporaryDirectory() as d:
        os.environ["FN_WORK_RUNS_DIR"] = d
        try:
            import importlib
            import src.shared.write_runs_jsonl as m
            importlib.reload(m)
            p1 = m.write_runs_jsonl("test-cat", {"k": 1})
            p2 = m.write_runs_jsonl("test-cat", {"k": 2})
            assert p1 == p2 and os.path.isfile(p1)
            with open(p1) as f:
                lines = [json.loads(x) for x in f if x.strip()]
            assert len(lines) == 2
            assert lines[0]["category"] == "test-cat" and lines[0]["k"] == 1
            assert "ts" in lines[0]
        finally:
            os.environ.pop("FN_WORK_RUNS_DIR", None)
