"""严判入口(layer-change-protocol 判决口径):尺子健康检查→四线 30 局双席判决电池。

用法: cd fn_work && .venv/bin/python entries/strict_judge.py [weights.json] [标签]
受测体=SIL 权重装载的策略网;锚={在梯版 submission_v9, v5 引擎原序, teacher eval_es_v1};
自镜像 n_mirror=30,每锚 n_anchor=30(双席),bo=3。
fna-013(口径换新,报告 §12.6/§14.3):判决电池前必跑尺子健康检查——健康带=每局单方决策 43-148
(中位 73,打印上报);<10 决策且 reason=3(清场速败)是合法签名不是崩溃;判"秒死/崩溃"须叠加证据
(决策数<10 且 reason≠3,或有异常状态 INVALID/ERROR/TIMEOUT)。不过即中止,先修装载(真赢一局保留)。
评测走配对种子(报告 §10.1/§14.5):受测体与锚打同一 seed 序列(共同随机数);开跑前做确定性自检
(同一 (agent, seed) 连跑 2 局比对,不过只 WARN 不阻断——随机策略合法地不同)。
"""
import json
import os
import statistics
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "remote"))
os.chdir(_ROOT)  # 权重/references 相对路径解析与远程 ~/ptcg-train 布局一致(勿信调用方 cwd)

from kaggle_environments.envs.cabt import cabt

from learn.bc_policy import MLP
from learn.bc_policy_v4 import build_features
from learn.eval_agent import make_agent as make_eval_agent
from shared.load_agent_callable import load_agent_callable
from shared.play_local_match import play_local_match
from src.run_judge_pool.run_judge_pool import run_judge_pool
import train_sil as ts


def load_policy(path):
    w = json.load(open(path))
    m = MLP(h=96, seed=0, d=w["d"])
    m.W1 = __import__("numpy").array(w["W1"])
    m.b1 = __import__("numpy").array(w["b1"])
    m.W2 = __import__("numpy").array(w["W2"])
    m.b2 = __import__("numpy").array(w["b2"])
    ts._G["build"] = build_features
    ts._G["deck"] = list(cabt.deck)
    return ts.make_policy_agent(m, None, temperature=0.05, seat="judge")


_BAND = (43, 148)  # 报告 §12.6:每局单方决策健康带(中位 73;43-148 为健康主体,带外非崩溃判据)


def _game_segments(steps):
    """steps 逐拍 → 每局段 [[拍,...], ...](bo 多局拆开)。

    切分:turn 回 0 再起 = 新局(铺场段 turn=0);末行=终局态冗余(双席 DONE 后 obs 为旧值,
    12/12 局实测恒为前拍状态副本)先剔除,不计决策。
    """
    rows = [s for s in steps if (s.get("state") or {}).get("turn") is not None]
    if rows and rows[-1] is steps[-1]:
        rows = rows[:-1]
    segs, cur = [], []
    for s in rows:
        if cur and s["state"]["turn"] == 0 and cur[-1]["state"]["turn"] > 0:
            segs.append(cur)
            cur = []
        cur.append(s)
    if cur:
        segs.append(cur)
    return segs


def _reason_guess(seg):
    """按奖赏轨迹推断局终 reason 桶(play_local_match 的 steps 不带 RESULT 日志,精确值拿不到):
    领至见底(≤1)→ "≈1"(拿完即胜,终局领取帧常不可见);全程 6 张无人领 → "≈2/3"(非奖赏线=
    清场/爆牌,<10 决策时爆牌不可能发生,即清场速败签名);有领取未见底 → "1/3"(reason 1/3 同帧
    时引擎取 3,不猜);铺场未发奖 → "未发奖"。
    """
    post = [s["state"]["prize"] for s in seg
            if not (s["state"]["turn"] == 0 and s["state"]["prize"] == 0)]
    if not post:
        return "未发奖"
    if min(post) <= 1:
        return "≈1"
    if max(post) == 6:
        return "≈2/3"
    return "1/3"


def ruler_health(agent, deck):
    """fna-013(口径换新,报告 §12.6/§14.3):尺子健康检查,不过即中止判决电池(先修装载)。

    健康带=每局单方决策 43-148(中位 73),打印上报;判"秒死/崩溃"须叠加证据:
    决策数<10 且 reason≠3(reason 桶"≈1"=奖赏见底,非清场线),或有异常状态(INVALID/ERROR/TIMEOUT);
    <10 决策且 reason=3(清场速败)是合法签名不是崩溃,reason 拿不到时只按决策数+异常状态判。
    保留 fna-013 原意:真赢一局。带内局数为读数,不作硬门(官方语料 43 带外亦占 25%+,§12.6)。
    """
    wins = 0
    samples = []      # 每局每方决策数
    games = []        # (opp, i, gi, 席0决策, 席1决策, reason 桶)
    reasons = {"≈1": 0, "≈2/3": 0, "1/3": 0, "未发奖": 0, "异常": 0}
    crash = []
    for opp_name, opp in (("random", cabt.random_agent), ("first", cabt.first_agent)):
        for i in range(2):
            r = play_local_match(agent, opp, deck, deck, seed=5000 + i, config={"bo": 3})
            wins += (r["rewards"][0] or -1) > 0
            abnormal = [s for s in (r.get("statuses") or []) if s in ("ERROR", "INVALID", "TIMEOUT")]
            if abnormal:
                crash.append(f"{opp_name}#{i} 异常状态{abnormal}")
            segs = _game_segments(r.get("steps") or [])
            for gi, seg in enumerate(segs):
                cnt = [sum(1 for s in seg if s["active"] == seat) for seat in (0, 1)]
                samples.extend(cnt)
                guess = _reason_guess(seg)
                if abnormal and gi == len(segs) - 1:
                    guess = "异常"  # 异常中止即该局终局
                reasons[guess] += 1
                games.append((opp_name, i, gi, cnt[0], cnt[1], guess))
                # 秒死/崩溃判据(单方口径,§12.6):<10 决策且 reason≠3 才算崩溃证据
                if guess == "≈1":
                    for seat in (0, 1):
                        if cnt[seat] < 10:
                            crash.append(f"{opp_name}#{i} g{gi} 席{seat} 决策{cnt[seat]}<10 且 reason≠3(奖赏见底)")
    in_band = sum(1 for n in samples if _BAND[0] <= n <= _BAND[1])
    med = statistics.median(samples) if samples else 0
    ok = wins >= 1 and not crash
    gtxt = " ".join(f"{o}#{i}g{gi}={a}/{b}:{g}" for o, i, gi, a, b, g in games)
    print(f"[ruler] 每局单方决策[席0/席1:reason] {gtxt}")
    print(f"[ruler] 中位={med} 带内{_BAND}={in_band}/{len(samples)} wins={wins}/4 crash={len(crash)} -> {'PASS' if ok else 'FAIL'}")
    # reason 分布行:steps 不带 RESULT 日志,按奖赏轨迹+statuses 推断;拿不到精确 reason,秒死只按决策数+异常判
    print(f"[ruler] reason 分布(推断,steps 不带 RESULT 拿不到精确值,只按决策数+异常状态判): {reasons}")
    for c in crash:
        print(f"[ruler] crash-evidence: {c}")
    return ok


def determinism_check(agent, deck):
    """确定性自检(报告 §10.1/§14.5,开跑前置,不过只 WARN 不阻断):同一 (agent, seed) 连跑 2 局,
    rewards 一致即算过(更严可比 steps 哈希)。不一致合法成因=随机策略,或引擎洗牌 RNG 非固定种子
    (libcg.so 无种子入口,B1 评审实证)——只对确定性 agent 强制,故告警不中止。返回 "pass"|"warn"。
    """
    seed = 9100
    r1 = play_local_match(agent, cabt.first_agent, deck, deck, seed=seed, config={"bo": 3})
    r2 = play_local_match(agent, cabt.first_agent, deck, deck, seed=seed, config={"bo": 3})
    det = "pass" if r1["rewards"] == r2["rewards"] else "warn"
    if det == "warn":
        print(f"[determinism] WARN seed={seed} 连跑 rewards 不一致 {r1['rewards']} vs {r2['rewards']}"
              f"(steps {r1['n_steps']}/{r2['n_steps']};随机策略/引擎 RNG 非固定种子均合法,不阻断)")
    else:
        print(f"[determinism] pass seed={seed} rewards 一致 {r1['rewards']}(steps {r1['n_steps']})")
    return det


def main():
    weights = sys.argv[1] if len(sys.argv) > 1 else "weights/sil_best_new.json"
    label = sys.argv[2] if len(sys.argv) > 2 else "sil_best_new"
    deck = list(cabt.deck)

    agent = load_policy(weights)
    if not ruler_health(agent, deck):
        print("RULER UNHEALTHY — 判决电池中止(先修尺子)")
        sys.exit(2)
    det = determinism_check(agent, deck)  # 开跑前置:不过只 WARN 不阻断

    anchors = {
        "ladder": load_agent_callable("submission_v9", "agent"),
        "v5": ts._base(deck),
        "teacher": make_eval_agent(weights=json.load(open("weights/eval_es_v1.json"))),
    }
    rep = run_judge_pool({
        "agent": agent, "n_mirror": 30, "n_anchor": 30,
        "anchors": anchors, "deck": deck, "seed0": 7000, "bo": 3,
    })

    mir = rep["self_mirror_h2h"]
    vs = {k: v["loss"] / v["n"] for k, v in rep["members"].items() if k != "self"}
    gate = vs.get("ladder", 0) >= 0.60 and vs.get("v5", 0) >= 0.65 and 0.35 <= mir <= 0.65
    print(json.dumps({
        "label": label, "weights": weights,
        "self_mirror": mir, "vs_ladder": round(vs.get("ladder", 0), 4),
        "vs_v5": round(vs.get("v5", 0), 4), "vs_teacher": round(vs.get("teacher", 0), 4),
        "paired_seeds": rep.get("paired_seeds", True),
        "determinism_check": det,
        "breakthrough_gate": gate,
    }, ensure_ascii=False, indent=1))
    return gate


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
