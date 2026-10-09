"""PTCG Playground 参赛件 seed v5（自包含，不依赖本地工程 import）。

来源：fn_work/src/seed_agent/*（v5=引擎原序选满 first 语义+guard_rails 终检）。
同步标记：seed_agent.py 改动时此文件须同步重生成（pack 前对拍验证）。
"""
DEFAULT_DECK = [
    721, 721, 722, 722, 722, 722, 723, 723, 723, 723, 1092, 1121, 1121, 1145, 1145,
    1163, 1163, 1219, 1219, 1219, 1219, 1227, 1227, 1227, 1227, 1262, 1262,
] + [3] * 33  # 引擎 cabt.py:9-70 逐行拷贝（60 卡；34 张 bug 已修）


def parse_observation(obs):
    missing = []
    if obs is None:
        obs = {}
        missing.extend(["obs"])
    select = obs.get("select")
    if select is None:
        missing.append("select")
        return {"select": None, "options": [], "max_count": 0, "min_count": 0, "missing": missing}
    return {
        "select": select,
        "options": list(select.get("option") or []),
        "max_count": int(select.get("maxCount") or 0),
        "min_count": int(select.get("minCount") or 0),
        "missing": missing,
    }


def greedy_priority(options, max_count):
    """v5：引擎原序选满（first 语义基线；血统链见 fn_work/src/seed_agent/greedy_priority.py）。"""
    if not options or max_count <= 0:
        return []
    return list(range(min(max_count, len(options))))


def guard_rails(candidates, options, max_count, min_count=0):
    """防御终检：非法动作=当场判负（cabt.py:164-168），永不抛错。"""
    n = len(options)
    if n == 0 or max_count <= 0:
        return []
    seen, legal = set(), []
    for c in candidates or []:
        if isinstance(c, int) and not isinstance(c, bool) and 0 <= c < n and c not in seen:
            seen.add(c)
            legal.append(c)
        if len(legal) >= max_count:
            break
    for i in range(n):
        if len(legal) >= min_count or len(legal) >= max_count:
            break
        if i not in seen:
            seen.add(i)
            legal.append(i)
    return legal if legal else list(range(min(max_count, n)))


def agent(obs, config=None):
    parsed = parse_observation(obs)
    if parsed["select"] is None:
        return list(DEFAULT_DECK)
    if not parsed["options"] or parsed["max_count"] <= 0:
        return []
    cands = greedy_priority(parsed["options"], parsed["max_count"])
    return guard_rails(cands, parsed["options"], parsed["max_count"], parsed["min_count"])
