"""自对弈 RL 训练器（msdsm 路线复刻：BC 蒸馏热启动 → 自对弈 REINFORCE）

数据主粮=自产对局（32 核并行，日百万级）；真实回放仅作验证添头。
观测编码=机制做全语义特征（bc_policy_v4.build_features，157 维）；
奖励=奖赏差塑形（档案 J=奖赏差）+胜负终结项；熵正则防坍缩。
"""
import glob, json, os, random, sys, time
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
    _G["eval_agent"] = make_eval_agent()
    _G["play"] = play_local_match
    _G["v5"] = _base(_G["deck"])
    _G["rng"] = random.Random(os.getpid())

def _softmax_sample(scores, rng, temperature=1.0):
    s = np.asarray(scores, dtype=np.float64) / temperature
    s = s - s.max()
    p = np.exp(s)
    p = p / p.sum()
    return int(rng.choices(range(len(p)), weights=p)[0]), p

def make_policy_agent(model, record, temperature=1.0, greedy=False, seat_name="p"):
    rng = random.Random(os.getpid() * 7 + sum(map(ord, seat_name)) % 10000)
    def agent(obs, config=None):
        sel = (obs or {}).get("select")
        if sel is None:
            return list(_G["deck"])
        opts = sel.get("option") or []
        mc = int(sel.get("maxCount") or 0)
        mn = int(sel.get("minCount") or 0)
        if not opts or mc <= 0:
            return []
        feats = _G["build"](obs)
        X = np.stack(feats)
        H = np.tanh(X @ model.W1.T + model.b1)
        scores = (H @ model.W2.T + model.b2).ravel()
        # 采样 k 个（不放回 Gumbel-top-k）；k 规则：mn==mc 时取满，否则 max(mn, min(1,mc))
        k = mc if mn == mc else max(mn, min(1, mc))
        k = max(1, min(k, len(opts)))
        cur = (obs.get("current") or {})
        my_i = cur.get("yourIndex", 0) or 0
        players = cur.get("players") or []
        my = players[my_i] if len(players) > my_i else {}
        my_prize = len(my.get("prize") or [])
        if greedy:
            order = sorted(range(len(opts)), key=lambda i: -scores[i])
            chosen = order[:k]
            pvec = np.zeros(len(opts))
            for i in chosen:
                pvec[i] = 1.0 / max(1, len(chosen))
        else:
            # Gumbel top-k
            g = np.array([-np.log(max(-np.log(max(rng.random(), 1e-12)), 1e-12)) for _ in scores])  # 真 Gumbel：-log(-log U)
            noisy = np.asarray(scores) / max(temperature, 1e-6) - g
            chosen = sorted(range(len(opts)), key=lambda i: -noisy[i])[:k]
            pvec = np.zeros(len(opts))
            single = np.exp(np.asarray(scores) - scores.max())
            single = single / single.sum()
            for i in chosen:
                pvec[i] = single[i]
        if record is not None:
            record.append({
                "feats": feats,
                "chosen": list(chosen),
                "pvec": pvec.tolist(),
                "seat": my_i,
                "prize": my_prize,
            })
        return chosen
    return agent

def run_games(args):
    """worker：打 n 局（self 或 anchor），返回轨迹片段"""
    model_w, n_games, mode, seed0, temperature = args
    MLP = _G["MLP"]
    model = MLP(h=96, seed=0, d=model_w["d"])
    model.W1 = np.array(model_w["W1"]); model.b1 = np.array(model_w["b1"])
    model.W2 = np.array(model_w["W2"]); model.b2 = np.array(model_w["b2"])
    play = _G["play"]
    deck = _G["deck"]
    out = []
    for g in range(n_games):
        rec_a, rec_b = [], []
        ag_a = make_policy_agent(model, rec_a, temperature, seat_name=f"a{os.getpid()}{g}")
        if mode == "self":
            ag_b = make_policy_agent(model, rec_b, temperature, seat_name=f"b{os.getpid()}{g}")
        else:
            ag_b = _G[mode] if mode in ("v5", "eval_agent") else _G["v5"]
        try:
            r = play(ag_a, ag_b, deck, deck, seed=seed0 + g, config={"bo": 3})
        except Exception:
            continue
        rewards = r["rewards"]
        if rewards[0] is None or rewards[1] is None:
            continue
        # 奖赏差塑形 + 终结
        for rec, seat, opp_seat in ((rec_a, 0, 1), (rec_b, 1, 0)):
            if mode != "self" and rec is rec_b:
                continue  # 只学己方策略（对手固定时不给对手攒轨迹）
            n = len(rec)
            if n == 0:
                continue
            prev = rec[0]["prize"]
            shaped = [0.0] * n
            for t in range(1, n):
                shaped[t] += (prev - rec[t]["prize"]) / 6.0
                prev = rec[t]["prize"]
            terminal = 1.0 if rewards[seat] > 0 else (-1.0 if rewards[seat] < 0 else 0.0)
            shaped[-1] += terminal
            G = 0.0
            gam = 0.98
            returns = [0.0] * n
            for t in range(n - 1, -1, -1):
                G = shaped[t] + gam * G
                returns[t] = G
            out.append((rec, returns))
    return out

def update(model, traj, lr, entropy_beta, rng):
    """REINFORCE：A=z-score(returns)，∇logπ·A + β∇H"""
    tuples = []
    for rec, returns in traj:
        rets = np.asarray(returns, dtype=np.float64)
        for t, step in enumerate(rec):
            tuples.append((step["feats"], step["chosen"], step["pvec"], rets[t]))
    if len(tuples) < 10:
        return 0.0
    rets_all = np.array([t[3] for t in tuples])
    mu, sd = rets_all.mean(), rets_all.std() + 1e-8
    params = ["W1", "b1", "W2", "b2"]
    grads = {k: np.zeros_like(getattr(model, k)) for k in params}
    ll_sum = 0.0
    for feats, chosen, pvec, ret in tuples:
        A = (ret - mu) / sd
        X = np.stack(feats)
        H = np.tanh(X @ model.W1.T + model.b1)
        s = (H @ model.W2.T + model.b2).ravel()
        s = s - s.max()
        p = np.exp(s); p = p / p.sum()
        dH_term = entropy_beta * (1.0 / len(p) - p)  # 均匀吸引项（每次决策一次，勿随 k 重复）
        for c in chosen:
            dL = A * _onehot_grad(p, c)  # ∇logπ(a)·A
            dL = dL + dH_term
            grads["W2"] += (dL @ H).reshape(1, -1)
            grads["b2"] += dL.sum()
            dH = np.outer(dL, model.W2.ravel()) * (1 - H ** 2)
            grads["W1"] += dH.T @ X
            grads["b1"] += dH.sum(0)
            ll_sum += np.log(max(p[c], 1e-12))
    n = max(1, len(tuples))
    for k in params:
        grads[k] /= n
        setattr(model, k, getattr(model, k) + lr * grads[k])
    return ll_sum / n

def _onehot_grad(p, idx):
    g = -p.copy()
    g[idx] += 1.0
    return g  # = ∇ log p_idx wrt logits

def eval_greedy(model_w, opponents, games=16, seed0=900000):
    MLP = _G["MLP"]
    model = MLP(h=96, seed=0, d=model_w["d"])
    model.W1 = np.array(model_w["W1"]); model.b1 = np.array(model_w["b1"])
    model.W2 = np.array(model_w["W2"]); model.b2 = np.array(model_w["b2"])
    play = _G["play"]; deck = _G["deck"]
    res = {}
    for name, y in opponents.items():
        won = 0
        for i in range(games):
            ag = make_policy_agent(model, None, greedy=True, seat_name=f"ev{os.getpid()}{i}")
            swap = i % 2 == 1
            a, b = (y, ag) if swap else (ag, y)
            r = play(a, b, deck, deck, seed=seed0 + i, config={"bo": 3})
            mine = r["rewards"][1] if swap else r["rewards"][0]
            won += (mine or -1) > 0
        res[name] = won / games
    return res

def distill_games(args):
    """专家（eval_agent）打局，记录 (提示特征集, 专家选择) 供 BC 热启动"""
    n_games, seed0 = args
    rows = []
    expert = _G["eval_agent"]
    deck = _G["deck"]
    rec_holder = {}

    def recorder(obs, config=None):
        choice = expert(obs, config)
        sel = (obs or {}).get("select")
        if sel and isinstance(choice, list) and len(choice) == 1:
            feats = _G["build"](obs)
            rows.append((feats, choice[0], "d"))
        return choice

    for g in range(n_games):
        try:
            _G["play"](recorder, expert, deck, deck, seed=seed0 + g, config={"bo": 3})
        except Exception:
            continue
    return rows


def main():
    _init_worker()
    t0 = time.time()
    NPROC = 12
    pool = Pool(NPROC, initializer=_init_worker)
    MLP = _G["MLP"]
    # BC 热启动：专家 eval_agent 在线蒸馏（msdsm BC 段）
    d = 157  # bc_policy_v4 机制特征维度
    model = MLP(h=96, seed=11, d=d)
    drows = [r for chunk in pool.map(distill_games, [(12, 500000 + k * 100) for k in range(NPROC)]) for r in chunk]
    if len(drows) > 200:
        model.train(drows, epochs=12, lr=0.02)
        print(f"[sp] BC 蒸馏完成 rows={len(drows)}", flush=True)
    else:
        print(f"[sp] 蒸馏样本不足 {len(drows)}，随机热启动", flush=True)
    export_w = lambda m: {"d": d, "W1": m.W1.tolist(), "b1": m.b1.tolist(), "W2": m.W2.tolist(), "b2": m.b2.tolist()}
    ev0 = eval_greedy(export_w(model), {"v5": _G["v5"], "eval_agent": _G["eval_agent"]}, games=16, seed0=424242)
    print(f"[sp] 蒸馏起点 eval={ev0}（应接近 v9 水平 vs v5≈0.6）", flush=True)
    print(f"[sp] self-play start procs={NPROC}", flush=True)
    best = {"fit": -1, "w": export_w(model)}
    GAMES_PER_ITER, ITERS = 240, 60
    for it in range(1, ITERS + 1):
        # 自产对局：60% self + 25% v5 + 15% eval_agent（专家陪练保底）
        batch_args = []
        n_self = GAMES_PER_ITER // 2
        n_v5 = GAMES_PER_ITER // 4
        n_exp = GAMES_PER_ITER - n_self - n_v5
        base_seed = 1000000 + it * 10000
        batch_args.append((export_w(model), n_self, "self", base_seed, 1.0))
        batch_args.append((export_w(model), n_v5, "v5", base_seed + 1000, 1.0))
        batch_args.append((export_w(model), n_exp, "eval_agent", base_seed + 2000, 1.0))
        chunks = pool.map(run_games, batch_args)
        traj = [x for ch in chunks for x in ch]
        ll = update(model, traj, lr=0.004, entropy_beta=0.01, rng=random.Random(it))  # 稳锚版：步长 1/3
        # BC 锚定——**衰减锚**（防局部最优锁死老师）：
        # 前 1/3 训练强锚（学手艺），中 1/3 渐弱，后 1/3 微锚（放手探索超越老师）
        if drows:
            import random as _r
            anchor_lr = 0.03 * max(0.0, 1.0 - it / (ITERS * 0.7)) + 0.005  # 稳锚版：锚力加倍
            model.train(_r.sample(drows, min(3000, len(drows))), epochs=2, lr=anchor_lr)
        if it % 5 == 0 or it == 1:
            ev = eval_greedy(export_w(model), {"v5": _G["v5"], "eval_agent": _G["eval_agent"]}, games=12, seed0=800000 + it)
            score = ev["v5"] + ev["eval_agent"]
            mark = ""
            if score > best["fit"] or it == 1:
                best = {"fit": score, "w": export_w(model)}
                mark = " *BEST*"
                json.dump(best["w"], open("weights/selfplay_best.json", "w"))
                # 自我蒸馏阶梯：学生超越老师 → 反哺锚定池（老师随版本进化）
                if score > 1.15:  # 双锚合计 >1.15 ≈ 稳超专家
                    drows = []  # 老师退役：锚定关闭，纯自强
                    print(f"[sp] it{it}: 学生超越专家，锚定关闭（自我蒸馏阶梯）", flush=True)
            print(f"[sp] it{it}: traj={len(traj)} ll={ll:.2f} eval={ev}{mark} ({time.time()-t0:.0f}s)", flush=True)
        json.dump(export_w(model), open("weights/selfplay_latest.json", "w"))
    ev = eval_greedy(best["w"], {"v5": _G["v5"], "eval_agent": _G["eval_agent"], "self": None} if False else {"v5": _G["v5"], "eval_agent": _G["eval_agent"]}, games=24, seed0=777000)
    fin = {"eval": ev, "best_fit": best["fit"], "iters": ITERS, "games_total": ITERS * GAMES_PER_ITER * 2, "elapsed_s": round(time.time() - t0)}
    json.dump(fin, open("sp_results.json", "w"), indent=1)
    print(json.dumps(fin), flush=True)

if __name__ == "__main__":
    main()
