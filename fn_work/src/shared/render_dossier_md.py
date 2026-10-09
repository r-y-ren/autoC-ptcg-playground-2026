"""六问答案+锚点→T1/T2 Markdown 骨架装配（shared）"""
from __future__ import annotations

import os

QUESTIONS = ["q1_money", "q2_opponent", "q3_failure", "q4_time", "q5_info", "q6_rng"]
QUESTION_TITLES = {
    "q1_money": "钱/分怎么算出来的？",
    "q2_opponent": "对手在哪个函数里影响我？",
    "q3_failure": "失败怎么表达？",
    "q4_time": "时间结构是什么？",
    "q5_info": "谁能看见什么？",
    "q6_rng": "rng 在哪几行被调用？",
}
LEVELS = ["可控", "可影响", "可观测不可推", "不可控随机"]


def render_dossier_md(answers, anchors, out_dir):
    """装配 T1 世界参数表与 T2 受控坐标表 Markdown，返回 (t1_path, t2_path)。

    answers: {q1_money: {answer, decision}, ...} 六问必备；coords: [{coord, level, note}]
    为 T2 四级行（每级至少一行由调用方保证）。锚点行以引用块附在 T1 尾部。
    """
    missing = [q for q in QUESTIONS if q not in answers]
    if missing:
        raise ValueError(f"六问答案缺失: {missing}")
    coords = answers.get("coords", [])
    bad_levels = [c["level"] for c in coords if c.get("level") not in LEVELS]
    if bad_levels:
        raise ValueError(f"coords 含非法四级标签: {bad_levels}")

    os.makedirs(out_dir, exist_ok=True)
    t1 = os.path.join(out_dir, "t1-world-params.md")
    t2 = os.path.join(out_dir, "t2-controlled-coords.md")

    rows = []
    for q in QUESTIONS:
        a = answers[q]
        rows.append(f"| {QUESTION_TITLES[q]} | {a['answer']} | {a.get('decision', '')} |")
    anchor_lines = "\n".join(
        f"- `{a['symbol']}` → 第 {a['line']} 行：`{a['source_line'][:120]}`" for a in anchors
    ) or "（无锚点）"
    with open(t1, "w", encoding="utf-8") as f:
        f.write("# T1 世界参数表（引擎六问）\n\n| 六问 | 答案（带源码行号/实验证据） | 决定了什么 |\n|---|---|---|\n")
        f.write("\n".join(rows))
        f.write("\n\n## 源码锚点\n\n" + anchor_lines + "\n")

    with open(t2, "w", encoding="utf-8") as f:
        f.write("# T2 受控坐标表（四级可控性）\n\n| 状态坐标 | 可控性四级 | 说明 |\n|---|---|---|\n")
        for c in coords:
            f.write(f"| {c['coord']} | {c['level']} | {c.get('note', '')} |\n")
    return t1, t2
