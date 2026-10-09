"""submission_search 部署件验证(验证 A/B/C/D/E;产物只读,不改包)。

用法:
  verify_submission_search.py a <variant>   # variant ∈ a1(cwd探测)/a2(sys.path探测)/a3(wheel兜底)
  verify_submission_search.py bce           # 冒烟对局+一致性+耗时(B/C/E)
  verify_submission_search.py d             # 包自检(D)
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "submission_search")
TAR = os.path.join(PKG, "submission.tar.gz")
for p in (ROOT, os.path.join(ROOT, "src")):
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(ROOT)

META = [96, 96, 96, 96, 92, 92, 93, 93, 150, 150, 917, 917, 709, 709, 710, 710,
        1071, 1071, 140, 920, 1227, 1227, 1227, 1227, 1231, 1231, 1182, 1182, 1184, 1213,
        1121, 1121, 1121, 1121, 1094, 1094, 1094, 1094, 1080, 1261, 1261, 1261, 1261, 1152,
        1152, 1097] + [1] * 14


def load_kaggle_style(pkg_dir):
    """复刻 kaggle_environments.agent.get_last_callable 装载语义:
    compile(path 作文件名)→ exec(code, {}) → sys.path 追加包目录(exec 期)→ 取最后可调用对象。
    返回 (agent_fn, 命名空间 dict)。"""
    path = os.path.join(pkg_dir, "main.py")
    code = compile(open(path, encoding="utf-8").read(), path, "exec")
    env = {}
    sys.path.append(pkg_dir)
    try:
        exec(code, env)
    finally:
        sys.path.pop()
    callables = [v for v in env.values() if callable(v)]
    return callables[-1], env


def extract_tar():
    d = tempfile.mkdtemp(prefix="subm_search_")
    with tarfile.open(TAR, "r:gz") as tf:
        tf.extractall(d)  # noqa: S202 —— 自产包,临时目录
    return d


def run_match(deployed, opponent, seed, swap, deck_opp=None, record=None):
    """跑一局 bo3;record 是 wrapper 工厂(包 deployed 侧观察)。返回 (wall_s, MatchResult)。"""
    from shared.play_local_match import play_local_match
    from kaggle_environments.envs.cabt import cabt
    if isinstance(opponent, str):  # play_local_match 的 wrap 会包死字符串,内建名先解析成函数
        opponent = cabt.agents[opponent]
    a = record(deployed) if (record and not swap) else deployed
    b = record(deployed) if (record and swap) else deployed
    if not swap:
        agents, decks = (a, opponent), (META, deck_opp or META)
    else:
        agents, decks = (opponent, a), (deck_opp or META, META)
    t0 = time.time()
    r = play_local_match(agents[0], agents[1], decks[0], decks[1], seed=seed, config={"bo": 3})
    return time.time() - t0, r


def is_search_point(obs):
    sel = obs.get("select") or {}
    opts = sel.get("option") or []
    k = max(int(sel.get("minCount") or 0), min(int(sel.get("maxCount") or 0) or 1, len(opts)))
    return sel.get("context") == 0 and k == 1 and bool(opts)


def main_a(variant):
    if variant == "a1":
        os.chdir(PKG)  # 任务指定形态:compile+exec({"__name__":"__main__"}),cwd=包目录(cwd 探测)
        code = compile(open("main.py", encoding="utf-8").read(), "main.py", "exec")
        env = {"__name__": "__main__"}
        exec(code, env)
    elif variant == "a2":
        d = extract_tar()  # Kaggle get_last_callable 语义:sys.path 追加包目录
        os.chdir(ROOT)
        fn, env = load_kaggle_style(d)
        env["__loaded_fn__"] = fn
    else:  # a3:中性 cwd、无路径提示 → wheel 兜底
        os.chdir(tempfile.mkdtemp())
        path = os.path.join(PKG, "main.py")
        code = compile(open(path, encoding="utf-8").read(), "main.py", "exec")
        env = {}
        exec(code, env)
    fn = env.get("__loaded_fn__")
    if fn is None:
        callables = [v for v in env.values() if callable(v)]
        fn = callables[-1]
    deck = fn({"select": None})
    print(json.dumps({
        "variant": variant,
        "search_mode": env["_SEARCH_MODE"],
        "lib_path_found": env["_find_bundled_lib"](),
        "agent_is_last_callable": True,
        "agent_name": getattr(fn, "__name__", str(fn)),
        "deck_len": len(deck),
        "deck_is_meta": deck == META,
        "select_smoke": fn({"select": {"context": 5, "option": [{"type": 14}], "maxCount": 1, "minCount": 0}}),
    }, ensure_ascii=False))


def main_bce():
    from shared.load_agent_callable import load_agent_callable
    from learn.search_lookahead import make_search_agent

    out = {"games": [], "timings": []}
    d = extract_tar()
    deployed, denv = load_kaggle_style(d)
    assert denv["_SEARCH_MODE"] == "bundled", f"部署件未用随包库: {denv['_SEARCH_MODE']}"
    out["deployed_search_mode"] = denv["_SEARCH_MODE"]
    out["deck_check"] = {"len": None, "is_meta": None}
    deck = deployed({"select": None})
    out["deck_check"] = {"len": len(deck), "is_meta": deck == META}

    RECORDED = []

    def recorder(fn):
        def wrapped(obs, config=None):
            o = copy.deepcopy(obs)
            if isinstance(o, dict) and o.get("select") is not None:
                RECORDED.append(o)
            return fn(obs, config)
        return wrapped

    v9 = load_agent_callable(os.path.join(ROOT, "submission_v9"))
    out["v9_loaded"] = True

    cases = [
        ("vs_random", "random", None, 7001, False),
        ("vs_random_swap", "random", None, 7002, True),
        ("vs_v9", v9, None, 7003, False),
        ("vs_v9_swap", v9, None, 7004, True),
    ]
    for name, opp, deck_opp, seed, swap in cases:
        wall, r = run_match(deployed, opp, seed, swap, deck_opp, record=recorder)
        out["games"].append({"case": name, "seed": seed, "swap": swap, "wall_s": round(wall, 3),
                             "rewards": r["rewards"], "failed": r["failed"],
                             "statuses": r["statuses"], "n_steps": r["n_steps"],
                             "error": r.get("error") if r.get("failed") else None})
        out["timings"].append(wall)

    # 兜底配额不足则补录(vs first 慢速对手,凑 ≥100 决策点)
    if len(RECORDED) < 100:
        for seed in range(7100, 7120):
            if len(RECORDED) >= 100:
                break
            wall, r = run_match(deployed, "first", seed, seed % 2 == 1, record=recorder)
            out["games"].append({"case": "vs_first_extra", "seed": seed, "swap": seed % 2 == 1,
                                 "wall_s": round(wall, 3), "rewards": r["rewards"],
                                 "failed": r["failed"], "n_steps": r["n_steps"]})
            out["timings"].append(wall)

    # ---- C:决策一致性(本地 search_lookahead 版 vs 部署件,同 obs 逐点对比) ----
    # 引擎搜索在含硬币掷的状态对 rollout 有内禀随机性(净室实证:单副本同 obs 连续两跑
    # 逐候选值即不同,值多重集相同)→ 逐点先各测两次稳定性,稳定点上要求 100% 一致。
    local_fn = make_search_agent(META)
    n_total = n_search = ok_total = ok_search = 0
    n_stable = n_unstable = ok_stable = 0
    mism = []
    for o in RECORDED:
        b1 = local_fn(copy.deepcopy(o))
        a1 = deployed(copy.deepcopy(o))
        b2 = local_fn(copy.deepcopy(o))
        a2 = deployed(copy.deepcopy(o))
        n_total += 1
        ok_total += int(a1 == b1)
        stable = (a1 == a2) and (b1 == b2)
        if stable:
            n_stable += 1
            ok_stable += int(a1 == b1)
        else:
            n_unstable += 1
        if a1 != b1 and len(mism) < 5:
            mism.append({"ctx": (o.get("select") or {}).get("context"),
                         "n_opts": len((o.get("select") or {}).get("option") or []),
                         "deployed": a1, "local": b1, "stable": stable})
        if is_search_point(o):
            n_search += 1
            ok_search += int(a1 == b1)
    out["consistency"] = {"n_points": n_total, "match": ok_total, "rate": ok_total / max(1, n_total),
                          "n_search_points": n_search, "search_match": ok_search,
                          "n_stable_points": n_stable, "stable_match": ok_stable,
                          "stable_rate": ok_stable / max(1, n_stable),
                          "n_unstable_points": n_unstable, "mismatches": mism}

    # ---- 兜底等价:v9 原版 vs 部署件内联 _fallback_agent(同 obs 逐点) ----
    fb = denv["_fallback_agent"]
    n_fb = ok_fb = 0
    fb_mism = []
    for o in RECORDED:
        a = fb(copy.deepcopy(o))
        b = v9(copy.deepcopy(o))
        n_fb += 1
        ok_fb += int(a == b)
        if a != b and len(fb_mism) < 5:
            fb_mism.append({"deployed_fb": a, "v9": b})
    out["fallback_equivalence"] = {"n_points": n_fb, "match": ok_fb, "rate": ok_fb / max(1, n_fb),
                                   "mismatches": fb_mism}
    out["n_recorded"] = len(RECORDED)
    # 诊断:搜索入口在真实 obs 上直接抛错的次数(0=搜索层全程可用)
    cws = denv["choose_with_search"]
    n_err = 0
    first_err = None
    for o in RECORDED:
        try:
            cws(copy.deepcopy(o), META, context=0, weights=None, depth=1, fold="rules")
        except Exception as e:  # noqa: BLE001
            n_err += 1
            if first_err is None:
                first_err = f"{type(e).__name__}: {e}"
    out["search_entry_errors"] = {"n": n_err, "first": first_err}
    secs = out["timings"]
    out["timing"] = {"n": len(secs), "mean_s": round(sum(secs) / len(secs), 3),
                     "max_s": round(max(secs), 3)} if secs else None
    shutil.rmtree(d, ignore_errors=True)
    print(json.dumps(out, ensure_ascii=False, default=str))


def main_d():
    src_so = os.path.join(ROOT, ".venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cg/libcg.so")
    out = {"tar_members": [], "issues": []}
    with tarfile.open(TAR, "r:gz") as tf:
        for m in tf.getmembers():
            out["tar_members"].append({"name": m.name, "size": m.size})
        main_text = tf.extractfile("main.py").read().decode("utf-8")
        deck = tf.extractfile("deck.csv").read().decode("utf-8")
    main_bytes = main_text.encode("utf-8")
    out["sizes"] = {"tar_bytes": os.path.getsize(TAR),
                    "tar_mb": round(os.path.getsize(TAR) / 1048576, 3),
                    "main_py_bytes": len(main_bytes),
                    "main_py_kb": round(len(main_bytes) / 1024, 1)}
    for tok in ("__file__", "/mnt/", "/home/", "open(", "kaggle_simulations"):
        if tok in main_text:
            out["issues"].append(f"main.py 含禁词: {tok}")
    lines = [x for x in deck.splitlines() if x.strip()]
    if len(lines) != 60 or not all(x.strip().isdigit() for x in lines):
        out["issues"].append(f"deck.csv 异常: {len(lines)} 行")
    elif [int(x) for x in lines] != META:
        out["issues"].append("deck.csv 与 META 不一致")
    # libcg.so 与 venv 源字节一致
    with open(os.path.join(PKG, "cg/libcg.so"), "rb") as f:
        h1 = hashlib.sha256(f.read()).hexdigest()
    with open(src_so, "rb") as f:
        h2 = hashlib.sha256(f.read()).hexdigest()
    out["libcg_sha256_match"] = h1 == h2
    out["libcg_sha256"] = h1[:16]
    # 房规结构校验器
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from src.pack_submission.validate_bundle_structure import validate_bundle_structure
    ok, issues = validate_bundle_structure(TAR)
    out["house_structure_ok"] = ok
    out["house_structure_issues"] = issues
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "a":
        main_a(sys.argv[2])
    elif cmd == "bce":
        main_bce()
    elif cmd == "d":
        main_d()
    else:
        raise SystemExit(f"未知子命令 {cmd}")
