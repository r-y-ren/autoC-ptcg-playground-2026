"""PTCG Playground 参赛件 v6（首序基线+榜首牌组移植，自包含）。

来源：fn_work/src/seed_agent/*（v5=引擎原序选满 first 语义+guard_rails 终检）。
同步标记：seed_agent.py 改动时此文件须同步重生成（pack 前对拍验证）。
"""
DEFAULT_DECK = [96, 96, 96, 96, 92, 92, 93, 93, 150, 150, 917, 917, 709, 709, 710, 710, 1071, 1071, 140, 920, 1227, 1227, 1227, 1227, 1231, 1231, 1182, 1182, 1184, 1213, 1121, 1121, 1121, 1121, 1094, 1094, 1094, 1094, 1080, 1261, 1261, 1261, 1261, 1152, 1152, 1097, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]  # v6：榜首 Schott 获胜局 60 卡逐字节移植（本地单变量 A/B 净零，天梯实测） + [3] * 33  # 引擎 cabt.py:9-70 逐行拷贝（60 卡；34 张 bug 已修）


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
