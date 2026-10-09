"""编排探活：双通道探测→runs 落行→上线即提示四页核验（R12）"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.probe_gsk_launch.check_competition_page import check_competition_page
from src.shared.write_runs_jsonl import write_runs_jsonl


def probe_gsk_launch():
    """探活一轮：status=not-live/live（任一通道见赛即 live）；runs 落行。

    live 时 stdout 打印四页核验清单（rules/timeline/prizes/evaluation——KB 条目最高待办）。
    网络失败落 unknown 不抛。
    """
    ev = check_competition_page()
    cli_found = ev.get("cli", {}).get("found")
    http_status = ev.get("http", {}).get("status")
    if cli_found or http_status == 200:
        status = "live"
    elif cli_found is None and http_status is None:
        status = "unknown"
    else:
        status = "not-live"
    result = {"status": status, "evidence": ev}
    write_runs_jsonl("gsk-probe", result)
    print(f"gsk-simulation: {status} (cli={cli_found}, http={http_status})")
    if status == "live":
        print("!! 上线核验清单：rules / timeline / prizes / evaluation 四页实抓回填 KB 条目（最高优先待办）")
    return result
