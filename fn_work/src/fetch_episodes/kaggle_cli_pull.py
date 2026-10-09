"""封装 kaggle CLI 子进程调用拉 episode/榜单，限速+重试 1 次（R6）"""
from __future__ import annotations

import json
import subprocess
import time

SAME_HOST_INTERVAL = 1.5  # budget.yaml 同主机限速口径


def kaggle_cli_pull(target):
    """target 形态：
    {"kind": "episodes", "competition": str}            —— 拉最近 episode 列表
    {"kind": "episode", "competition": str, "id": int}  —— 拉单条 episode JSON
    {"kind": "leaderboard", "competition": str}         —— 拉榜单
    返回 [dict]；重试 1 次后仍失败抛异常含 stderr。
    """
    if target.get("kind") == "episode":
        cmd = ["kaggle", "competitions", "episodes", "-c", target["competition"],
               "--episode-id", str(target["id"])]
    elif target.get("kind") == "episodes":
        cmd = ["kaggle", "competitions", "episodes", "-c", target["competition"]]
    elif target.get("kind") == "leaderboard":
        cmd = ["kaggle", "competitions", "leaderboard", "-c", target["competition"], "--show"]
    else:
        raise ValueError(f"未知拉取目标: {target}")

    last_err = ""
    for attempt in range(2):
        if attempt:
            time.sleep(SAME_HOST_INTERVAL)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                return _parse(cmd, r.stdout)
            last_err = r.stderr.strip() or r.stdout.strip()
        except subprocess.TimeoutExpired:
            last_err = f"timeout: {' '.join(cmd)}"
    raise RuntimeError(f"kaggle CLI 重试后仍失败: {' '.join(cmd)} :: {last_err[:300]}")


def _parse(cmd, stdout):
    if "episodes" in cmd and "--episode-id" in cmd:
        return [json.loads(stdout)] if stdout.strip().startswith("{") else [{"raw": stdout}]
    if "leaderboard" in cmd:
        lines = [l for l in stdout.splitlines() if l.strip()]
        return [{"raw": l} for l in lines]
    return [{"raw": stdout}]
