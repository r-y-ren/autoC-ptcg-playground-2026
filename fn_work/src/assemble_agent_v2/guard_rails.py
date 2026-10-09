"""防御层终检：合法性/数量/自伤上限/兜底首选项（R9/R5）

引擎失败语义（cabt.py:164-168）：battle_select 抛错→该席 INVALID→reward -1、
对手 +1、整场立即结束——非法动作不是静默跳过而是**当场判负**，防御层是刚需。
"""
from __future__ import annotations


def guard_rails(candidates, options, max_count, state=None):
    """终检并修正候选动作 → 合法 list[int]。

    处理：越界剔除、去重保序、截到 max_count；不足 minCount 补未选的首个合法索引；
    全空兜底=前 max_count 个合法索引（first_agent 语义）。永不抛错。
    """
    n = len(options)
    if n == 0 or max_count <= 0:
        return []
    min_count = int((state or {}).get("min_count", 0))

    seen = set()
    legal = []
    for c in candidates or []:
        if isinstance(c, bool) or not isinstance(c, int):
            continue
        if 0 <= c < n and c not in seen:
            seen.add(c)
            legal.append(c)
        if len(legal) >= max_count:
            break
    legal = legal[:max_count]

    for i in range(n):  # minCount 补足
        if len(legal) >= max_count:
            break
        if len(legal) >= min_count:
            break
        if i not in seen:
            seen.add(i)
            legal.append(i)

    if not legal:  # 兜底
        legal = list(range(min(max_count, n)))
    return legal
