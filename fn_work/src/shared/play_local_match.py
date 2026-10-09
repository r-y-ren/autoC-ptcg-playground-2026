"""执行一局 cabt 对战→MatchResult（含逐拍 steps；单局失败不抛）（shared）"""
from __future__ import annotations

import random

from kaggle_environments import make


def _call_agent(fn, obs, config):
    """按函数签名自适应调用：兼容 (obs) 与 (obs, config) 两种约定。"""
    try:
        return fn(obs, config)
    except TypeError:
        return fn(obs)


def play_local_match(agent_a, agent_b, deck_a, deck_b, seed, config=None):
    """跑一局本地 cabt 对战。

    agent 在 deck 阶段（obs["select"] is None）由本函数强制返回指定 deck
    （判决口径：双席牌组为受控变量），select 阶段才交给 agent 本体。
    返回 MatchResult dict：rewards/statuses/wins、steps 逐拍摘要；
    agent 抛错/超时由引擎判该席负（status ERROR/TIMEOUT/INVALID），不向上抛。
    """
    random.seed(seed)

    def wrap(agent, deck):
        def wrapped(obs, config=None):
            if obs.get("select") is None:
                return list(deck)
            return _call_agent(agent, obs, config)

        return wrapped

    env = make("cabt", configuration=dict(config or {}), debug=False)
    env.run([wrap(agent_a, deck_a), wrap(agent_b, deck_b)])

    final = env.state
    steps_out = []
    for i, pair in enumerate(env.steps):
        if i == 0:
            steps_out.append({
                "step": 0,
                "active": "both",
                "action": {"deck_lens": [len(pair[0]["action"] or []), len(pair[1]["action"] or [])]},
            })
            continue
        active = 0 if pair[0].get("status") == "ACTIVE" else 1
        action = pair[active].get("action")
        obs = pair[active].get("observation") or {}
        sel = obs.get("select") or {}
        opt_types = [o.get("type") if isinstance(o, dict) else None for o in (sel.get("option") or [])]
        cur = obs.get("current") or {}
        my = (cur.get("players") or [{}])[active] if len(cur.get("players") or []) > active else {}
        steps_out.append({
            "step": i,
            "active": active,
            "action": action if isinstance(action, list) else None,
            "option_types": opt_types,  # 供聚类/资产对齐（B6/B7 增补字段）
            "state": {"turn": cur.get("turn"), "hand": my.get("handCount"),
                      "prize": len(my.get("prize") or [])},
        })

    return {
        "seed": seed,
        "rewards": [final[0]["reward"], final[1]["reward"]],
        "statuses": [final[0]["status"], final[1]["status"]],
        "wins": list(getattr(env, "result", []) or []),
        "n_steps": len(env.steps),
        "steps": steps_out,
        "failed": any(s in ("ERROR", "INVALID", "TIMEOUT") for s in (final[0]["status"], final[1]["status"])),
        "error": next(
            (f"step{si}: {pair[j]['status']}/{pair[j]['observation'].get('error')}"
             for si, pair in enumerate(env.steps) for j in (0, 1)
             if isinstance(pair[j], dict) and pair[j].get("observation", {}).get("error")),
            env.steps[0][0].get("error"),
        ),
    }
