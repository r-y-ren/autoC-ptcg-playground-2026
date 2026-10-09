import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.shared.assert_no_network import assert_no_network


def test_clean_dir_passes():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "clean.py"), "w") as f:
            f.write("import json\nimport random\n\ndef agent(obs):\n    return []\n")
        assert assert_no_network(d) == []


def test_network_import_flagged():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "bad.py"), "w") as f:
            f.write("import requests\n\ndef agent(obs):\n    return []\n")
        v = assert_no_network(d)
        assert len(v) == 1 and v[0]["module"] == "requests" and v[0]["line"] == 1


def test_from_import_flagged():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "bad2.py"), "w") as f:
            f.write("from urllib.request import urlopen\n")
        assert any("urllib" in x["module"] for x in assert_no_network(d))


def test_missing_dir_raises():
    try:
        assert_no_network("/nonexistent/dir")
        assert False
    except FileNotFoundError:
        pass
