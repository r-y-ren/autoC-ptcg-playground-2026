"""编排打包自检：配额→打包→结构校验→沙箱自对弈（R4）"""
from __future__ import annotations

import os
import sys
import tarfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.pack_submission.count_daily_quota import count_daily_quota
from src.pack_submission.sandbox_selfplay_once import sandbox_selfplay_once
from src.pack_submission.validate_bundle_structure import validate_bundle_structure
from src.shared.write_runs_jsonl import write_runs_jsonl


def pack_submission(src_dir, out_tar, force=False):
    """打包自检编排：配额检查（剩余 0 且未 force → 拒绝）→ tar.gz（顶层平铺）→
    结构校验 → 沙箱自对弈 → 记账落 runs。stdout 两行 OK；任一失败非零退出由调用方定。

    返回 {"ok": bool, "tar": path, "issues": [...], "selfplay": {...}, "quota": (used, remaining)}。
    """
    used, remaining = count_daily_quota()
    if remaining <= 0 and not force:
        return {"ok": False, "tar": None, "issues": [f"当日配额已用尽 ({used}/{5})"],
                "selfplay": None, "quota": (used, remaining)}

    os.makedirs(os.path.dirname(os.path.abspath(out_tar)), exist_ok=True)
    with tarfile.open(out_tar, "w:gz") as tf:
        for fname in sorted(os.listdir(src_dir)):
            fpath = os.path.join(src_dir, fname)
            if os.path.isfile(fpath):
                tf.add(fpath, arcname=fname)  # 顶层平铺，不嵌套

    ok_struct, issues = validate_bundle_structure(out_tar)
    selfplay = None
    if ok_struct:
        ok_play, selfplay = sandbox_selfplay_once(out_tar)
        ok = ok_play
        if not ok_play:
            issues.append(f"沙箱自对弈失败: {selfplay}")
    else:
        ok = False

    write_runs_jsonl("pack-quota", {"tar": os.path.basename(out_tar), "ok": ok,
                                    "issues": issues, "force": bool(force and remaining <= 0)})
    print("tar structure OK" if ok_struct else f"tar structure FAIL: {issues}")
    print("local self-play OK" if ok and selfplay else f"local self-play FAIL: {selfplay}")
    return {"ok": ok, "tar": out_tar if ok else None, "issues": issues,
            "selfplay": selfplay, "quota": count_daily_quota()}
