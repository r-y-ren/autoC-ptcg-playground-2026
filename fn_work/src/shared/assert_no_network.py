"""静态自检：import 树无网络模块，命中返违规清单（shared）"""
from __future__ import annotations

import ast
import os

# 赛规禁联网：对局评测环境禁止一切网络出站。宁可误报（urllib.parse 也报），
# 由人工裁决豁免——静态白名单比黑名单漏检安全。
NETWORK_MODULES = {
    "socket", "ssl", "asyncio", "http", "http.client", "http.server",
    "urllib", "urllib.request", "urllib.parse", "urllib.error",
    "requests", "aiohttp", "httpx", "httpcore", "ftplib", "telnetlib",
    "smtplib", "poplib", "imaplib", "nntplib", "websocket", "websockets",
    "xmlrpc", "xmlrpc.client", "paramiko",
}


def assert_no_network(src_dir):
    """扫描 src_dir 下 *.py 的 import 树，返回违规清单 [{file, module, line}]。

    空列表=通过。目录不存在抛异常。
    """
    if not os.path.isdir(src_dir):
        raise FileNotFoundError(f"源码目录不存在: {src_dir}")

    violations = []
    for root, _dirs, files in os.walk(src_dir):
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read(), filename=fpath)
                except SyntaxError:
                    violations.append({"file": fpath, "module": "<syntax-error>", "line": 0})
                    continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_mod = alias.name.split(".")[0]
                        if alias.name in NETWORK_MODULES or root_mod in NETWORK_MODULES:
                            violations.append({"file": fpath, "module": alias.name, "line": node.lineno})
                elif isinstance(node, ast.ImportFrom):
                    root_mod = (node.module or "").split(".")[0]
                    if node.module in NETWORK_MODULES or root_mod in NETWORK_MODULES:
                        violations.append({"file": fpath, "module": node.module or ".", "line": node.lineno})
    return violations
