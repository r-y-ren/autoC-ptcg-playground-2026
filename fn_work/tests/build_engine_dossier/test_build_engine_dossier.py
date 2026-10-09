import os
import sys

import kaggle_environments.envs.cabt.cabt as cabt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.build_engine_dossier.build_engine_dossier import build_engine_dossier

CONCLUSIONS = {
    "q1_money": {"answer": "奖赏卡先手 6 后手 3? 以实测为准（实验证据节）", "decision": "打点→拿奖→终局求解"},
    "q2_opponent": {"answer": "锁步共享 Battle 状态（cabt.py:160 yourIndex 交替）", "decision": "对手建模必选"},
    "q3_failure": {"answer": "非法动作当场判负（cabt.py:164-168）", "decision": "防御层刚需"},
    "q4_time": {"answer": "BO3 分轮（cabt.py:187-195 result 计数）+ 回合内行动数（turnActionCount）", "decision": "按轮规划"},
    "q5_info": {"answer": "手牌仅自己可见（PlayerState.hand）", "decision": "观测器窄而深"},
    "q6_rng": {"answer": "Python 层无 rng；C 层实验证据见尾部", "decision": "方差预算"},
    "coords": [
        {"coord": "出牌选项", "level": "可控", "note": "option 索引直接决定"},
        {"coord": "场面局势", "level": "可影响", "note": "双方共推"},
        {"coord": "对手手牌", "level": "可观测不可推", "note": "仅 handCount"},
        {"coord": "开局抽卡", "level": "不可控随机", "note": "C 层洗牌"},
    ],
}


def test_dossier_with_real_engine(tmp_path):
    src = os.path.abspath(cabt.__file__)
    t1, t2 = build_engine_dossier(src, CONCLUSIONS, str(tmp_path))
    c1 = open(t1, encoding="utf-8").read()
    c2 = open(t2, encoding="utf-8").read()
    assert "受控实验证据" in c1 and "def interpreter" in c1  # 锚点含源码行
    for lv in ["可控", "可影响", "可观测不可推", "不可控随机"]:
        assert lv in c2
    # 实验证据三节
    for kw in ["失败怎么表达", "观测构造", "同种子"]:
        assert kw in c1
