import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.build_gsk_prestudy.build_gsk_prestudy import build_gsk_prestudy
from src.build_gsk_prestudy.load_pyxis_env import load_pyxis_env


def test_load_pyxis_locked():
    info = load_pyxis_env()
    assert info["version"] == "1.33.0" and info["agents"] in ([2], 2)


def test_prestudy_end_to_end(tmp_path):
    r = build_gsk_prestudy(out_dir=str(tmp_path))
    assert os.path.isfile(r["t1"]) and os.path.isfile(r["t2"])
    c1 = open(r["t1"], encoding="utf-8").read()
    for kw in ["净现金流", "1/n^α", "PTRS", "500 步"]:
        assert kw in c1
    assert r["smoke"]["n_games"] == 6
    assert r["smoke"]["builtin_ai"] == "manual-template"
