"""修复续跑 seed 撞车:r1_fatigue_x0.5 原落在 seed0=21100(与 r1_board_x1.5 撞号)。
在全新 seed0=21600 重跑该配置,替换 screen JSON 中旧行,保证配置间种子全错开。
读数只用于配置表;该配置 score/wins24 远低于采纳线,重跑仅为种子纪律。
"""
from __future__ import annotations

import json
import os
import sys

ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for _p in (ROOT, ROOT + "/src", ROOT + "/tmp"):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(ROOT)

import run_weight_ablation as base

TAG, NEW_SEED0 = "r1_fatigue_x0.5", 21600

with open(base.SCREEN_PATH, encoding="utf-8") as f:
    prev = json.load(f)
base.SCREEN_ROWS.extend(prev["rows"])
old = next(r for r in base.SCREEN_ROWS if r["tag"] == TAG)
print(f"[redo] {TAG} 旧 seed0={old['seed0']} score={old['score']} wins24={old['wins24']}(与 board_x1.5 撞号,弃)", flush=True)
base.SCREEN_ROWS[:] = [r for r in base.SCREEN_ROWS if r["tag"] != TAG]
cfg = dict(old["weights"])
new = base.evaluate(TAG, cfg, NEW_SEED0)
# evaluate 内部已全量 flush(含替换后的行);补写收口期 incumbent 元数据
with open(base.SCREEN_PATH, "w", encoding="utf-8") as f:
    json.dump({"rows": base.SCREEN_ROWS, "incumbent": dict(base.DEFAULT_WEIGHTS),
               "incumbent_tag": "r0_baseline", "rounds_run": 1, "counter": 17,
               "round2": "cancelled_by_task_directive(权重层无红利预期,聚焦收口)",
               "seed_fix": f"{TAG} 因与 r1_board_x1.5 撞 seed0=21100 重跑于 {NEW_SEED0}"},
              f, ensure_ascii=False, indent=1)
print(f"[redo] 完成: {TAG} seed0={NEW_SEED0} score={new['score']} wins24={new['wins24']}", flush=True)
