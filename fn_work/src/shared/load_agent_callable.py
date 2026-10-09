"""从文件装载 agent 函数，模拟线上装载语义（shared）"""
from __future__ import annotations

import importlib.util
import os


def load_agent_callable(path, fn_name="agent"):
    """从文件（或目录——按 Kaggle 提交语义找其中 main.py）装载函数。

    返回 callable；失败抛异常并带精确原因。
    """
    if os.path.isdir(path):
        main = os.path.join(path, "main.py")
        if not os.path.isfile(main):
            raise FileNotFoundError(f"目录 {path} 下无 main.py（Kaggle 提交语义）")
        path = main
    if not os.path.isfile(path):
        raise FileNotFoundError(f"agent 文件不存在: {path}")

    spec = importlib.util.spec_from_file_location(f"_loaded_agent_{os.path.basename(path)}", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:  # noqa: BLE001 —— 装载失败要带原文上报
        raise ImportError(f"agent 模块 import 失败: {path}: {e}") from e

    fn = getattr(module, fn_name, None)
    if not callable(fn):
        raise AttributeError(f"{path} 中不存在可调用函数 {fn_name}")
    return fn
