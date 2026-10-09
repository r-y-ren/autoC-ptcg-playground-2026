"""定位部署件 vs 本地版在单个搜索决策点上的分叉原因(2026-10-06 冒烟 330/331)。

复刻 bce 的调用序列(先全程录像,后逐点 local→deployed 对比,保证两库状态序列一致)
→ 找到分叉 obs → 双版重复调用测稳定性 → 双库逐候选叶子值对比。
"""
import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.join(ROOT, "src")):
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(ROOT)

from verify_submission_search import META, extract_tar, load_kaggle_style, run_match
from learn.search_lookahead import make_search_agent


def main():
    d = extract_tar()
    deployed, denv = load_kaggle_style(d)
    local_fn = make_search_agent(META)

    # pass 1:纯录像(不调用任何搜索,保持库状态序列与 bce 一致)
    RECORDED = []

    def recorder(fn):
        def wrapped(obs, config=None):
            o = copy.deepcopy(obs)
            if isinstance(o, dict) and o.get("select") is not None:
                RECORDED.append(o)
            return fn(obs, config)
        return wrapped

    from shared.load_agent_callable import load_agent_callable
    from kaggle_environments.envs.cabt import cabt
    v9 = load_agent_callable(os.path.join(ROOT, "submission_v9"))
    for opp, seed, swap in ((cabt.agents["random"], 7001, False), (cabt.agents["random"], 7002, True),
                            (v9, 7003, False), (v9, 7004, True)):
        run_match(deployed, opp, seed, swap, record=recorder)
    print("n_recorded:", len(RECORDED))

    # pass 2:与 bce 相同顺序逐点对比(local 先,deployed 后)
    mism = []
    for idx, o in enumerate(RECORDED):
        b = local_fn(copy.deepcopy(o))
        a = deployed(copy.deepcopy(o))
        if a != b:
            mism.append((idx, copy.deepcopy(o), a, b))
    print("n_mismatch:", len(mism), [(i, a, b) for i, a, b, _ in [(m[0], m[2], m[3], m[1]) for m in mism]])
    if not mism:
        return
    idx, obs, a, b = mism[0]
    sel = obs.get("select") or {}
    print("mismatch at", idx, "deployed:", a, "local:", b,
          "n_opts:", len(sel.get("option") or []), "ctx:", sel.get("context"))

    # 稳定性:部署件重复 5 次
    rep = [tuple(denv["choose_with_search"](copy.deepcopy(obs), META, context=0,
                                            weights=None, depth=1, fold="rules")) for _ in range(5)]
    print("deployed repeats:", rep)

    # 逐候选叶子值:部署件(随包库)
    def per_candidate(ns, use_learn):
        out = {}
        obs_c = copy.deepcopy(obs)
        cur = obs_c.get("current") or {}
        my_i = cur.get("yourIndex", 0) or 0
        players = cur.get("players") or []
        my = players[my_i] if len(players) > my_i else {}
        opp = players[1 - my_i] if len(players) > 1 - my_i else {}
        if use_learn:
            import learn.cg_search as lcs
            import learn.search_lookahead as lsl
            fill, sbegin, sstep, srel, rol = (lsl._fill, lcs.search_begin, lcs.search_step,
                                              lcs.search_release, lsl._rollout_value)
        else:
            fill, sbegin, sstep, srel, rol = (ns["_fill"], ns["search_begin"], ns["search_step"],
                                              ns["search_release"], ns["_rollout_value"])
        for i in range(len(sel.get("option") or [])):
            try:
                st = sbegin(copy.deepcopy(obs_c),
                            your_deck=fill(my.get("deckCount") or 0),
                            your_prize=fill(len(my.get("prize") or [])),
                            opponent_deck=fill(opp.get("deckCount") or 0),
                            opponent_prize=fill(len(opp.get("prize") or [])),
                            opponent_hand=fill(opp.get("handCount") or 0),
                            opponent_active=[])
                sid = st["searchId"]
                s = sstep(sid, [i])
                v = rol(s, sid, 0, my_i, 1, None, 0.0, True)
                srel(sid)
                out[i] = round(v, 6)
            except Exception as e:  # noqa: BLE001
                out[i] = f"ERR {type(e).__name__}: {e}"
        return out

    pc_bundled = per_candidate(denv, False)
    pc_wheel = per_candidate(None, True)
    print("per-candidate bundled:", json.dumps(pc_bundled))
    print("per-candidate wheel:  ", json.dumps(pc_wheel))
    diff = {k: (pc_bundled[k], pc_wheel[k]) for k in pc_bundled if pc_bundled[k] != pc_wheel.get(k)}
    print("value diffs:", json.dumps(diff))
    # 分叉 obs 留档
    with open(os.path.join(ROOT, "tmp", "subm_search_mismatch_obs.json"), "w", encoding="utf-8") as f:
        json.dump(obs, f, ensure_ascii=False)
    print("obs saved to tmp/subm_search_mismatch_obs.json")


if __name__ == "__main__":
    main()
