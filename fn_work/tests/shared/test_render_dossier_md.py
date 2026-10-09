import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.shared.render_dossier_md import render_dossier_md

ANSWERS = {
    "q1_money": {"answer": "奖赏卡数（cabt.py:179-210）", "decision": "终局求解器"},
    "q2_opponent": {"answer": "锁步共享局面（cabt.py:160）", "decision": "对手建模必选"},
    "q3_failure": {"answer": "非法动作判负（cabt.py:164-168）", "decision": "防御层刚需"},
    "q4_time": {"answer": "BO3 分轮（cabt.py:187-195）", "decision": "按轮规划"},
    "q5_info": {"answer": "手牌仅自己可见", "decision": "观测器"},
    "q6_rng": {"answer": "C 库内部", "decision": "方差预算"},
    "coords": [
        {"coord": "出牌选项", "level": "可控", "note": "直接决定"},
        {"coord": "场面局势", "level": "可影响", "note": "双方共推"},
        {"coord": "对手手牌", "level": "可观测不可推", "note": "仅数量"},
        {"coord": "开局抽卡", "level": "不可控随机", "note": "洗牌随机"},
    ],
}


def test_renders_t1_t2():
    with tempfile.TemporaryDirectory() as d:
        t1, t2 = render_dossier_md(ANSWERS, [{"symbol": "s", "line": 1, "source_line": "x"}], d)
        assert os.path.isfile(t1) and os.path.isfile(t2)
        c1 = open(t1, encoding="utf-8").read()
        for q in ["钱/分", "对手", "失败", "时间", "看见", "rng"]:
            assert q in c1
        c2 = open(t2, encoding="utf-8").read()
        for lv in ["可控", "可影响", "可观测不可推", "不可控随机"]:
            assert lv in c2


def test_missing_question_raises():
    bad = {k: v for k, v in ANSWERS.items() if k != "q3_failure"}
    try:
        render_dossier_md(bad, [], "/tmp/never")
        assert False
    except ValueError as e:
        assert "q3_failure" in str(e)
