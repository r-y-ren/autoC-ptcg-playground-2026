"""make(pyxis) 装载+版本锁 1.33.0 断言+能力描述（R11）"""
from __future__ import annotations

import kaggle_environments as ke
from kaggle_environments import make

LOCKED_VERSION = "1.33.0"


def load_pyxis_env():
    """装载 pyxis 环境并断言版本锁（本地=线上同构前提）。

    返回 {version, agents, obs_keys, action_mask_sample}；版本不符/装载失败抛异常。
    """
    if ke.__version__ != LOCKED_VERSION:
        raise RuntimeError(f"kaggle-environments 版本漂移: {ke.__version__} != {LOCKED_VERSION}")
    env = make("pyxis", debug=True)
    spec = env.specification
    return {
        "version": ke.__version__,
        "agents": spec.get("agents"),
        "episodeSteps_default": spec.get("configuration", {}).get("episodeSteps", {}).get("default"),
        "runTimeout_default": spec.get("configuration", {}).get("runTimeout", {}).get("default"),
    }
