"""自模仿学习（SIL）：自产对局→只学赢家的决策——低方差的自产数据闭环

替代 REINFORCE 的噪声梯度：CE 机器已被蒸馏验证（0.99 收敛）；
赢家轨迹=策略自己打出来的高回报路径，照着学=策略改进的自然循环。
"""
import json, os, random, sys, time
from multiprocessing import Pool

sys.path.insert(0, "src")
import numpy as np

_G = {}

def _base(deck):
    def a(obs, config=None):
        if obs.get("select") is None:
            return list(deck)
        sel = obs["select"]
        return list(range(min(sel.get("maxCount") or 0, len(sel.get("option") or []))))
    return a

def _init_worker():
    from kaggle_environments.envs.cabt import cabt
    from learn.bc_policy import MLP
    from learn.bc_policy_v4 import build_features
    from learn.eval_agent import make_agent as make_eval_agent
    from shared.play_local_match import play_local_match
    _G["deck"] = list(cabt.deck)
    _G["MLP"] = MLP
    _G["build"] = build_features
    _G["eval_agent"] = make_eval_agent(weights=json.load(open("weights/eval_es_v1.json")))  # 整定过的 v9，勿用默认
    # 风格变体池（非传递对策：防 SIL 过拟合单一老师风格）
    import random as _pr
    _base_w = json.load(open("weights/eval_es_v1.json"))
    for si in range(3):
        _prng = _pr.Random(1000 + si)
        vw = dict(_base_w)
        for k in ("oneshot", "damage", "attach_progress", "evolve", "play", "retreat_penalty"):
            vw[k] = vw[k] * _prng.uniform(0.5, 1.6)
        _G[f"style{si}"] = make_eval_agent(weights=vw)
    _G["play"] = play_local_match
    _G["v5"] = _base(_G["deck"])
    try:
        import sys as _sy
        _sy.path.insert(0, os.path.join("references", "opponents", "topdeck"))
        from shared.load_agent_callable import load_agent_callable
        _G["topdeck"] = load_agent_callable(os.path.join("references", "opponents", "topdeck", "main.py"))
    except Exception:
        _G["topdeck"] = _G["v5"]  # 外部对手装载失败降级,勿断训练

def make_policy_agent(model, record, temperature=1.0, seat="a"):
    rng = random.Random(os.getpid() * 13 + sum(map(ord, seat)) % 9999)  # 确定性种子（hash 随机化禁用）
    def agent(obs, config=None):
        sel = (obs or {}).get("select")
        if sel is None:
            return list(_G["deck"])
        opts = sel.get("option") or []
        mc = int(sel.get("maxCount") or 0)
        mn = int(sel.get("minCount") or 0)
        if not opts or mc <= 0:
            return []
        X = np.stack(_G["build"](obs))
        H = np.tanh(X @ model.W1.T + model.b1)
        s = (H @ model.W2.T + model.b2).ravel()
        k = mc if mn == mc else max(mn, min(1, mc))
        k = max(1, min(k, len(opts)))
        if temperature <= 0.05:
            order = sorted(range(len(opts)), key=lambda i: -s[i])
            chosen = order[:k]
        else:
            g = np.array([-np.log(max(rng.random(), 1e-12)) for _ in s])
            noisy = s / max(temperature, 1e-6) - g
            chosen = sorted(range(len(opts)), key=lambda i: -noisy[i])[:k]
        if record is not None:
            record.append({"feats": _G["build"](obs), "chosen": list(chosen)})
        return chosen
    return agent

def fast_ce_train(model, rows, epochs=4, lr=0.05):
    """批量 CE：按选项数分桶，矩阵一次算一桶——消除主进程单线程长空档"""
    from collections import defaultdict
    buckets = defaultdict(list)
    for feats, label, _ in rows:
        buckets[len(feats)].append((feats, label))
    for _ep in range(epochs):
        for n_o, items in buckets.items():
            B = len(items)
            X = np.stack([np.stack(f) for f, _ in items])   # (B, n_o, D)
            y = np.array([l for _, l in items])
            H = np.tanh(X @ model.W1.T + model.b1)           # (B, n, h)
            S = (H @ model.W2.T + model.b2).squeeze(-1)      # (B, n)
            S = S - S.max(axis=1, keepdims=True)
            P = np.exp(S)
            P /= P.sum(axis=1, keepdims=True)
            dS = P.copy()
            dS[np.arange(B), y] -= 1.0
            gW2 = np.einsum("bn,bnh->h", dS, H) / B
            gb2 = dS.sum() / B
            dH = dS[:, :, None] * model.W2.ravel()[None, None, :] * (1 - H ** 2)
            gW1 = np.einsum("bnh,bnd->hd", dH, X) / B
            gb1 = dH.sum(axis=(0, 1)) / B
            model.W2 -= lr * gW2.reshape(1, -1)  # CE 损失做梯度下降（勿写 +=，那是练坏）
            model.b2 -= lr * np.array([gb2])
            model.W1 -= lr * gW1
            model.b1 -= lr * gb1


def play_batch(args):
    model_w, n_games, opponent_mode, seed0, temperature = args
    MLP = _G["MLP"]
    m = MLP(h=96, seed=0, d=model_w["d"])
    m.W1 = np.array(model_w["W1"]); m.b1 = np.array(model_w["b1"])
    m.W2 = np.array(model_w["W2"]); m.b2 = np.array(model_w["b2"])
    play = _G["play"]; deck = _G["deck"]
    winners_rows = []
    n_win = n_loss = 0
    for g in range(n_games):
        rec_a, rec_b = [], []
        ag_a = make_policy_agent(m, rec_a, temperature, seat=f"a{os.getpid()}{g}")
        if opponent_mode == "self":
            ag_b = make_policy_agent(m, rec_b, temperature, seat=f"b{os.getpid()}{g}")
        else:
            ag_b = _G.get(opponent_mode, _G["v5"])
        try:
            r = play(ag_a, ag_b, deck, deck, seed=seed0 + g, config={"bo": 3})
        except Exception:
            continue
        rw = r["rewards"]
        if rw[0] is None or rw[1] is None:
            continue
        for rec, seat in ((rec_a, 0), (rec_b, 1)):
            if opponent_mode != "self" and rec is rec_b:
                continue
            if rw[seat] > 0:
                n_win += 1
                for step in rec:
                    # 只记 top-1（多选行同 feats 异 label 会造成 CE 互斥监督矛盾）
                    if step["chosen"]:
                        winners_rows.append((step["feats"], step["chosen"][0], "sil"))
            else:
                n_loss += 1
    return winners_rows, n_win, n_loss

def main():
    _init_worker()
    t0 = time.time()
    NPROC = 28  # 2026-10-06 升载：12 工人只吃 13% CPU，喂饱 32 核
    pool = Pool(NPROC, initializer=_init_worker)
    MLP = _G["MLP"]

    # 起点=蒸馏专家（BC）
    model = MLP(h=96, seed=11, d=157)  # bc_policy_v4 机制特征维度
    def export_w(m):
        return {"d": int(m.W1.shape[1]), "W1": m.W1.tolist(), "b1": m.b1.tolist(), "W2": m.W2.tolist(), "b2": m.b2.tolist()}
    drows = [r for chunk in pool.map(_distill, [(12, 500000 + k * 100) for k in range(NPROC)]) for r in chunk]
    fast_ce_train(model, drows, epochs=25, lr=0.08)
    print(f"[sil] BC 起点 rows={len(drows)}", flush=True)
    best = {"fit": -1, "w": export_w(model)}
    GAMES, ITERS = 240, 60

    def make_batch(it_, temp_, model_w):
        batch = []
        for mode, n, base in (("self", GAMES * 4 // 10, 2000000), ("v5", GAMES // 5, 2100000),
                              ("eval_agent", GAMES // 5, 2200000),
                              ("style0", 8, 2300000), ("style1", 8, 2400000),
                              ("style2", 8, 2500000), ("topdeck", 8, 2600000)):
            per = 6
            k = max(1, n // per)
            for j in range(k):
                batch.append((model_w, per, mode, base + it_ * 1000 + j * 97, temp_))
        return batch

    # 流水线：打下一棒的同时上一棒开训（SIL 离策略，晚一拍无害）——消脉冲空档
    temp = 0.9
    pending = pool.map_async(play_batch, make_batch(1, temp, export_w(model)))
    for it in range(1, ITERS + 1):
        chunks = pending.get()
        temp = 0.9 if it < ITERS * 0.6 else 0.3
        if it < ITERS:
            pending = pool.map_async(play_batch, make_batch(it + 1, temp, export_w(model)))
        rows = [r for ch in chunks for r in ch[0]]
        nwin = sum(ch[1] for ch in chunks)
        nloss = sum(ch[2] for ch in chunks)
        if len(rows) > 100:
            # 专家地板：赢家行混约 33% 专家行（rows 的一半）——防"学运气赢家"漂离专家（SIL 数据病）
            import random as _r
            mixed = rows + _r.sample(drows, min(len(rows) // 2, len(drows)))
            fast_ce_train(model, mixed, epochs=4, lr=0.05)
        if it % 5 == 0 or it == 1:
            ev = _eval(export_w(model), 20, 810000 + it)
            score = ev["v5"] + ev["eval_agent"]
            mark = ""
            if score > best["fit"]:
                best = {"fit": score, "w": export_w(model)}
                mark = " *BEST*"
                # 跨轮保留：只有优于历史 best 才落盘（防新轮开局覆盖旧纪录——2026-10-06 修复）
                hist = {}
                try:
                    hist = json.load(open("weights/sil_best.json"))
                    if not isinstance(hist, dict):
                        hist = {}
                except Exception:
                    hist = {}
                hist_fit = hist.get("fit")
                hist_fit = hist_fit if isinstance(hist_fit, (int, float)) else -1
                if score >= hist_fit:
                    out = dict(best["w"])
                    out["fit"] = score
                    json.dump(out, open("weights/sil_best.json", "w"))
                else:
                    mark = " (未超历史best {:.2f})".format(hist_fit)
            print(f"[sil] it{it}: win={nwin} loss={nloss} rows={len(rows)} eval={ev}{mark} ({time.time()-t0:.0f}s)", flush=True)
        json.dump(export_w(model), open("weights/sil_latest.json", "w"))
    fin = {"eval": _eval(best["w"], 24, 777000), "best_fit": best["fit"], "elapsed_s": round(time.time() - t0)}
    json.dump(fin, open("sil_results.json", "w"), indent=1)
    print(json.dumps(fin), flush=True)

def _distill(args):
    n_games, seed0 = args
    rows = []
    expert = _G["eval_agent"]
    deck = _G["deck"]
    def recorder(obs, config=None):
        choice = expert(obs, config)
        sel = (obs or {}).get("select")
        if sel and isinstance(choice, list) and len(choice) == 1:
            rows.append((_G["build"](obs), choice[0], "d"))
        return choice
    for g in range(n_games):
        try:
            _G["play"](recorder, expert, deck, deck, seed=seed0 + g, config={"bo": 3})
        except Exception:
            continue
    return rows

def _eval(model_w, games, seed0):
    MLP = _G["MLP"]
    m = MLP(h=96, seed=0, d=model_w["d"])
    m.W1 = np.array(model_w["W1"]); m.b1 = np.array(model_w["b1"])
    m.W2 = np.array(model_w["W2"]); m.b2 = np.array(model_w["b2"])
    play = _G["play"]; deck = _G["deck"]
    res = {}
    for name, y in (("v5", _G["v5"]), ("eval_agent", _G["eval_agent"])):
        won = 0
        for i in range(games):
            ag = make_policy_agent(m, None, temperature=0.05, seat=f"e{os.getpid()}{i}")
            swap = i % 2 == 1
            a, b = (y, ag) if swap else (ag, y)
            r = play(a, b, deck, deck, seed=seed0 + i, config={"bo": 3})
            mine = r["rewards"][1] if swap else r["rewards"][0]
            won += (mine or -1) > 0
        res[name] = won / games
    return res

if __name__ == "__main__":
    # 自我接力：一轮 60 代跑完自动开下一轮（机器不空转，收割交给 2h 自动化）
    import time as _t
    loop = 0
    while True:
        loop += 1
        print(f"===== 第 {loop} 轮开跑 =====", flush=True)
        try:
            main()
        except Exception as _e:
            print(f"[sil] 第 {loop} 轮异常: {_e}", flush=True)
            _t.sleep(30)
