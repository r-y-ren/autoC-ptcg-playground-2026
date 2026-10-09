"""单次双通道探测：CLI 查询+赛站 HTTP 状态→证据（R12）"""
from __future__ import annotations

import datetime as _dt
import subprocess
import urllib.request


def check_competition_page():
    """双通道探测 gsk-simulation 是否上线。永不抛（失败信息入证据）。"""
    ev = {"ts": _dt.datetime.now().isoformat(timespec="seconds")}
    try:
        r = subprocess.run(["kaggle", "competitions", "list", "-s", "gsk"],
                           capture_output=True, text=True, timeout=60)
        found = "gsk" in (r.stdout or "").lower() and "no competitions" not in (r.stdout or "").lower()
        ev["cli"] = {"found": found, "stdout_head": (r.stdout or r.stderr)[:200]}
    except Exception as e:  # noqa: BLE001
        ev["cli"] = {"found": False, "error": str(e)[:200]}
    try:
        req = urllib.request.Request("https://www.kaggle.com/competitions/gsk-simulation",
                                     method="GET", headers={"User-Agent": "probe/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            ev["http"] = {"status": resp.status}
    except urllib.error.HTTPError as e:
        ev["http"] = {"status": e.code}
    except Exception as e:  # noqa: BLE001
        ev["http"] = {"status": None, "error": str(e)[:200]}
    return ev
