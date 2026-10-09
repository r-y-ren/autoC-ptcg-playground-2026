"""受控实验验证六问答案：非法动作/None 观测/同种子确定性（R2）"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from kaggle_environments.envs.cabt import cabt

from src.shared.play_local_match import play_local_match


def probe_engine_facts():
    """跑三个受控实验，返回 [{question, observation, conclusion, reproduce_cmd}]。"""
    facts = []
    deck = list(cabt.deck)

    # 实验 1：非法动作语义（提交越界索引）
    def illegal(obs, config=None):
        if obs.get("select") is None:
            return list(deck)
        return [999]  # 越界选项索引

    r = play_local_match(illegal, cabt.first_agent, deck, deck, seed=1, config={"bo": 1})
    facts.append({
        "question": "失败怎么表达？（q3）",
        "observation": f"越界索引提交后 statuses={r['statuses']} rewards={r['rewards']}",
        "conclusion": "非法动作=battle_select 抛错→该席 INVALID→当场判负（-1/+1），非静默跳过（cabt.py:164-168）",
        "reproduce_cmd": "python -c 'from src.build_engine_dossier.probe_engine_facts import probe_engine_facts; probe_engine_facts()'",
    })

    # 实验 2：None 观测阶段（deck 提交拍）
    seen = {"select_none": False}

    def capture(obs, config=None):
        if obs.get("select") is None:
            seen["select_none"] = True
        return list(range(obs["select"]["maxCount"])) if obs.get("select") else list(deck)

    play_local_match(capture, cabt.random_agent, deck, deck, seed=2, config={"bo": 1})
    facts.append({
        "question": "谁能看见什么？观测构造（q5）",
        "observation": f"经 play_local_match 包装层（deck 拍被包装层接管，agent 侧 select=None 出现={seen['select_none']} 属测量层产物）；引擎源码 cabt.py:128/222 证实初始 observation.select=None；select 阶段含 option/maxCount/minCount；current.players 仅己方含 hand 明细",
        "conclusion": "信息结构=初始牌组提交阶段无 select；对局中双方公开场面（active/bench/deckCount/prize 计数），手牌仅自己可见（PlayerState.hand）",
        "reproduce_cmd": "同上",
    })

    # 实验 3：同种子确定性（引擎 C 层 rng 有无种子入口）
    ra = play_local_match(cabt.first_agent, cabt.random_agent, deck, deck, seed=7, config={"bo": 1})
    rb = play_local_match(cabt.first_agent, cabt.random_agent, deck, deck, seed=7, config={"bo": 1})
    same = ra["steps"] == rb["steps"]
    facts.append({
        "question": "rng 在哪几行被调用？同种子可复现吗？（q6）",
        "observation": f"同种子 7 两局逐拍 steps 完全一致={same}（rewards {ra['rewards']} vs {rb['rewards']}）",
        "conclusion": ("Python 层无 rng 调用（cabt.py 仅 import random 供 random_agent 用）；"
                       + ("同种子可复现=对拍与判决可用种子锚定" if same else "同种子不可复现=C 层 rng 无种子入口，方差预算覆盖全局，判决池须按局数收敛而非固定种子")),
        "reproduce_cmd": "同上",
    })
    return facts
