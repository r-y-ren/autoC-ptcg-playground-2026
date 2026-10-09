"""三模式小样本筛选(2026-10-06 扩展任务):4 臂×2 线(ladder/v5)×12 局 bo3,seed 28000 起。
臂:baseline(现行 depth=1+greedy) / A(depth=2) / B(rules fold) / C(depth=2×rules)。
逐臂逐局计时+逐决策(agent 内)计时;打印全部在外层。"""
import sys, os, time, json, statistics
ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for p in (ROOT, ROOT + "/src"): sys.path.insert(0, p)
os.chdir(ROOT)
from shared.load_agent_callable import load_agent_callable
from learn.search_lookahead import make_search_agent, _pick

META = [96,96,96,96,92,92,93,93,150,150,917,917,709,709,710,710,1071,1071,140,920,1227,1227,1227,1227,1231,1231,1182,1182,1184,1213,1121,1121,1121,1121,1094,1094,1094,1094,1080,1261,1261,1261,1261,1152,1152,1097,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

ladder = load_agent_callable("submission_v9", "agent")
def v5(obs, config=None):
    sel = (obs or {}).get("select")
    return _pick(sel)

ARMS = {
    "baseline": dict(),
    "A_depth2": dict(depth=2),
    "B_rules": dict(fold="rules"),
    "C_depth2_rules": dict(depth=2, fold="rules"),
}
LINES = {"ladder": ladder, "v5": v5}
N, SEED0, BO = 12, 28000, 3

def timed_agent(ag, acc):
    def wrapped(obs, config=None):
        if (obs or {}).get("select") is None:
            return list(META)
        t0 = time.time()
        r = ag(obs, config)
        acc["t"] += time.time() - t0
        acc["n"] += 1
        return r
    return wrapped

out = {"n": N, "seed0": SEED0, "bo": BO, "arms": {}}
for arm, kw in ARMS.items():
    ag = timed_agent(make_search_agent(META, **kw), (acc := {"t": 0.0, "n": 0}))
    arm_out = {"lines": {}, "agent_t": acc}
    for line, opp in LINES.items():
        w = l = d = fl = 0
        secs = []
        for g in range(N):
            swap = g % 2 == 1
            a, b = (opp, ag) if swap else (ag, opp)
            t0 = time.time()
            from src.shared.play_local_match import play_local_match
            r = play_local_match(a, b, META, META, seed=SEED0 + g, config={"bo": BO})
            secs.append(time.time() - t0)
            ra, rb = r["rewards"]
            sr, orr = (rb, ra) if swap else (ra, rb)
            if r["failed"]:
                fl += 1
            elif sr > orr: w += 1
            elif sr < orr: l += 1
            else: d += 1
        wr = round(w / (w + l), 3) if (w + l) else None
        arm_out["lines"][line] = {"w": w, "l": l, "d": d, "failed": fl, "wr": wr,
                                  "mean_s": round(statistics.fmean(secs), 2),
                                  "max_s": round(max(secs), 2)}
        print(json.dumps({"arm": arm, "line": line, **arm_out["lines"][line]}), flush=True)
    arm_out["dec_ms"] = round(1000 * acc["t"] / acc["n"], 1) if acc["n"] else None
    arm_out["n_dec"] = acc["n"]
    out["arms"][arm] = arm_out
    print(json.dumps({"arm": arm, "dec_ms": arm_out["dec_ms"], "n_dec": acc["n"]}), flush=True)

with open(ROOT + "/tmp/depth2_rules_screen.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("SCREEN DONE", flush=True)
