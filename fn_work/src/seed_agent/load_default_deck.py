"""从引擎 all_card_data() 取官方示例牌组写 60 行 deck.csv（R5）"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def load_default_deck(out_path):
    """把引擎默认 deck（cabt.py:9-70，60 卡）写成 deck.csv：60 行纯数字、无表头。

    卡数≠60 抛异常。返回写入路径。
    """
    from kaggle_environments.envs.cabt import cabt

    deck = list(cabt.deck)
    if len(deck) != 60:
        raise ValueError(f"引擎默认牌组非 60 卡: {len(deck)}")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(str(c) for c in deck) + "\n")
    return out_path
