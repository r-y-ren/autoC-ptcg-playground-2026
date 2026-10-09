"""strict_judge 尺子健康带换新(43-148,§12.6)与 reason 叠加判据(§14.3)"""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "entries"))

import strict_judge as sj
from kaggle_environments.envs.cabt import cabt


def _row(active, turn, prize):
    return {"step": 0, "active": active, "action": None,
            "state": {"turn": turn, "hand": 7, "prize": prize}}


def test_game_segments_split_and_drop_terminal():
    steps = [{"step": 0, "active": "both", "action": {}}]
    steps += [_row(0, 0, 0), _row(0, 0, 6), _row(1, 1, 6)]  # 局1(铺场 turn=0)
    steps += [_row(1, 0, 0), _row(0, 1, 6), _row(1, 2, 5)]  # 局2(turn 回 0 再起=新局)
    steps += [_row(1, 1, 6)]  # 末行=终局态冗余(旧状态副本),剔除不计决策
    segs = sj._game_segments(steps)
    assert [len(s) for s in segs] == [3, 3]


def test_reason_guess_buckets():
    # 全程 6 张无人领=非奖赏线(清场/爆牌);领至见底≈1;中间=1/3 未分;未发奖=None 桶
    assert sj._reason_guess([_row(0, 1, 6), _row(1, 2, 6)]) == "≈2/3"
    assert sj._reason_guess([_row(0, 1, 6), _row(1, 2, 1)]) == "≈1"
    assert sj._reason_guess([_row(0, 1, 5), _row(1, 2, 4)]) == "1/3"
    assert sj._reason_guess([_row(0, 0, 0), _row(1, 0, 0)]) == "未发奖"


def test_determinism_check_returns_pass_or_warn():
    # 不过只 WARN 不阻断(随机策略/引擎 RNG 非固定种子均合法),值域恒为 pass|warn
    assert sj.determinism_check(cabt.first_agent, list(cabt.deck)) in ("pass", "warn")
