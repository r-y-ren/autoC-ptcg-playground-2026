"""种子件主函数：obs→贪心选项索引，永不抛错（R5）"""
from __future__ import annotations

# 默认牌组：kaggle-environments cabt.py:9-70 引擎自带 deck 的字面拷贝。
# 提交件必须自包含（线上只保底 /kaggle_simulations/agent/ 装载），不依赖本地 import。
DEFAULT_DECK = [
    721, 721, 722, 722, 722, 722, 723, 723, 723, 723, 1092, 1121, 1121, 1145, 1145,
    1163, 1163, 1219, 1219, 1219, 1219, 1227, 1227, 1227, 1227, 1262, 1262,
] + [3] * 33  # 引擎 cabt.py:37-69 共 33 张（手抄 34 张=61 卡 bug，测试逮住）

from src.assemble_agent_v2.guard_rails import guard_rails
from src.seed_agent.greedy_priority import greedy_priority
from src.seed_agent.parse_observation import parse_observation


def seed_agent(obs, config=None):
    """参赛主函数。deck 阶段（select=None）返回默认 60 卡牌组；
    select 阶段贪心打分→guard_rails 终检。永不抛错（防御层兜底）。"""
    parsed = parse_observation(obs)
    if parsed["select"] is None:
        return list(DEFAULT_DECK)
    if not parsed["options"] or parsed["max_count"] <= 0:
        return []
    cands = greedy_priority(parsed["options"], parsed["max_count"], parsed["min_count"])
    return guard_rails(cands, parsed["options"], parsed["max_count"],
                       {"min_count": parsed["min_count"]})
