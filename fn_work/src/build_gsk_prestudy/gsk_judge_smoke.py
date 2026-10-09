"""pyxis 自镜像 h2h 校准；内置 AI 可编程则加锚点局（R11）"""
from __future__ import annotations

from kaggle_environments import make


def _do_nothing(obs, config=None):
    return None  # pyxis 空动作=跳过（actionMask 全 False 的合法默认）


def gsk_judge_smoke(n_games=20):
    """pyxis 判决池 v0：do-nothing 种子自镜像 n 局。

    返回 {self_mirror_h2h, decided, draws, n_games, builtin_ai}；h2h 基于 decided 局
    （全平局则 None——do-nothing 对 do-nothing 预期全平，此为噪声地板校准起点）。
    builtin_ai="manual-template"：gsk.ai/play 内置对手不可编程接入（2026-10-05 判定），
    人工实测模板随预研包交付。
    """
    a_wins = decided = draws = failed = 0
    for i in range(n_games):
        env = make("pyxis", debug=True)
        try:
            env.run([_do_nothing, _do_nothing])
            r0, r1 = env.state[0]["reward"], env.state[1]["reward"]
            if r0 is None or r1 is None:
                failed += 1
            elif r0 > r1:
                a_wins += 1
                decided += 1
            elif r1 > r0:
                decided += 1
            else:
                draws += 1
        except Exception:  # noqa: BLE001 —— 单局失败隔离
            failed += 1
    return {
        "self_mirror_h2h": round(a_wins / decided, 4) if decided else None,
        "decided": decided, "draws": draws, "failed": failed, "n_games": n_games,
        "builtin_ai": "manual-template",
    }
