"""编排六问档案：锚点扫描+受控实验+装配 T1/T2 落盘（R2）"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.build_engine_dossier.probe_engine_facts import probe_engine_facts
from src.shared.index_source_anchors import index_source_anchors
from src.shared.render_dossier_md import render_dossier_md

ANCHOR_PATTERNS = [
    r"^deck = \[", r"def random_agent", r"def first_agent", r"def interpreter",
    r"battle_start\(", r"battle_select\(", r"status.*INVALID", r"status.*ERROR",
    r"status.*TIMEOUT", r"\.reward = -1", r"\.reward = 1", r"result\[", r"yourIndex",
    r"remainingOverageTime", r"import random", r"bo.*=.*3", r"win.*=", r"select.*=.*None",
]


def build_engine_dossier(source_path, conclusions, out_dir):
    """六问档案生成：锚点索引+受控实验证据+调用方结论 → T1/T2 写盘。

    conclusions 六问必备（q1_money/q2_opponent/q3_failure/q4_time/q5_info/q6_rng），
    缺问抛异常；probe 证据追加到 T1 尾部。返回 (t1_path, t2_path)。
    """
    facts = probe_engine_facts()
    anchors = index_source_anchors(source_path, ANCHOR_PATTERNS)
    t1, t2 = render_dossier_md(conclusions, anchors, out_dir)

    fact_lines = "\n".join(
        f"### {f['question']}\n- 观测：{f['observation']}\n- 结论：{f['conclusion']}\n" for f in facts
    )
    with open(t1, "a", encoding="utf-8") as f:
        f.write("\n## 受控实验证据（probe_engine_facts 实跑）\n\n" + fact_lines + "\n")
    return t1, t2
