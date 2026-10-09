import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.shared.index_source_anchors import index_source_anchors


def test_anchor_extraction():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "engine.py")
        with open(p, "w") as f:
            f.write("import json\n\n\ndef market_price(item):\n    return 1\n\n\ndef battle_select(a):\n    pass\n")
        anchors = index_source_anchors(p, [r"def market_price", r"def battle_select", r"import json"])
        syms = {a["symbol"] for a in anchors}
        assert r"def market_price" in syms and r"import json" in syms
        mp = next(a for a in anchors if "market_price" in a["symbol"])
        assert mp["line"] == 4 and "def market_price" in mp["source_line"]


def test_no_match_returns_empty():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.py")
        with open(p, "w") as f:
            f.write("a = 1\n")
        assert index_source_anchors(p, [r"def nothing"]) == []
