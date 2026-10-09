"""远程并行 ES 训练：两段确认制（防赢家诅咒）+在位保护+对局级并行（32 核）"""
import json, os, random, sys, time
from multiprocessing import Pool

sys.path.insert(0, "src")

_G = {}

def _base(deck):
    def a(obs, config=None):
        if obs.get("select") is None:
            return list(deck)
        sel = obs["select"]
        return list(range(min(sel.get("maxCount") or 0, len(sel.get("option") or []))))
    return a

def _opt_id(o):
    return (o.get("type"), o.get("area"), o.get("index"), o.get("playerIndex"), o.get("attackId")) if isinstance(o, dict) else None

def _init_worker():
    from kaggle_environments.envs.cabt import cabt
    from learn.eval_agent import make_agent
    from shared.play_local_match import play_local_match
    _G["deck"] = list(cabt.deck)
    _G["make_agent"] = make_agent
    _G["play"] = play_local_match
    _G["v5"] = _base(_G["deck"])
    clones = json.load(open("submission/real-anchor-clones.json"))
    def clone(team):
        c = clones[team]; table, deck = c["table"], c["deck"]
        def agent(obs, config=None):
            if obs.get("select") is None:
                return list(deck)
            sel = obs["select"]
            opts = sel.get("option") or []
            mc = int(sel.get("maxCount") or 0); mn = int(sel.get("minCount") or 0)
            if not opts or mc <= 0: return []
            ids = [_opt_id(o) for o in opts]
            key = str((sel.get("context"), tuple(sorted(map(str, ids)))))
            chosen = table.get(key)
            if chosen is not None:
                out = []
                for i, oid in enumerate(ids):
                    if str(oid) in chosen and i not in out: out.append(i)
                if out:
                    out = out[:mc]
                    for i in range(len(opts)):
                        if len(out) >= mn or len(out) >= mc: break
                        if i not in out: out.append(i)
                    return out
            return list(range(min(mc, len(opts))))
        return agent, list(deck)
    a1, d1 = clone("OceanMix"); a2, d2 = clone("Darren Sheehan")
    _G["anchors"] = [("v5", _G["v5"], _G["deck"]), ("ocean", a1, d1), ("sheehan", a2, d2)]

def eval_candidate(args):
    w, games, seed0 = args
    agent = _G["make_agent"](weights=w)
    deck = _G["deck"]; play = _G["play"]
    tot = 0.0
    for name, y, yd in _G["anchors"]:
        won = 0
        for i in range(games):
            swap = i % 2 == 1
            a, b, da, db = (y, agent, yd, deck) if swap else (agent, y, deck, yd)
            r = play(a, b, da, db, seed=seed0 + i, config={"bo": 3})
            mine = r["rewards"][1] if swap else r["rewards"][0]
            won += (mine or -1) > 0
        tot += won / games
    return tot / len(_G["anchors"])

def head_to_head(args):
    """w_new vs w_ref direct matchup"""
    w_new, w_ref, games, seed0 = args
    deck = _G["deck"]; play = _G["play"]
    new_a = _G["make_agent"](weights=w_new)
    ref_a = _G["make_agent"](weights=w_ref)
    won = 0
    for i in range(games):
        swap = i % 2 == 1
        a, b = (ref_a, new_a) if swap else (new_a, ref_a)
        r = play(a, b, deck, deck, seed=seed0 + i, config={"bo": 3})
        mine = r["rewards"][1] if swap else r["rewards"][0]
        won += (mine or -1) > 0
    return won / games

KEYS = ["oneshot", "damage", "covered", "attach_progress", "evolve", "play",
        "retreat_penalty", "retreat_escape", "weakness_progress", "ko_desperation",
        "ex_retreat_boost", "fatigue_push"]

def main():
    t0 = time.time()
    _init_worker()  # 主进程也要锚组（gen0/终判直调 eval_candidate）
    NPROC = min(24, os.cpu_count() or 8)
    pool = Pool(NPROC, initializer=_init_worker)
    print(f"[es] procs={NPROC}", flush=True)
    best_w = json.load(open("weights/eval_es_v1.json"))
    for k in KEYS:
        best_w.setdefault(k, 0.0)
    best_w["end"] = 0.0
    best_f = eval_candidate((best_w, 30, 700000))
    print(f"[es] gen0 incumbent(v9) confirm fitness={best_f:.3f}", flush=True)
    rng = random.Random(int(time.time()))
    GENS, POP = 12, 24
    for gen in range(1, GENS + 1):
        cands = []
        for _ in range(POP):
            w = dict(best_w)
            for k in rng.sample(KEYS, rng.randint(1, 3)):
                w[k] = w[k] + rng.gauss(0, abs(w[k]) * 0.35 + 0.25)
            cands.append(w)
        coarse = pool.map(eval_candidate, [(w, 12, 800000 + gen * 1000 + j) for j, w in enumerate(cands)])
        top_idx = sorted(range(POP), key=lambda j: -coarse[j])[:4]
        confirms = pool.map(eval_candidate, [(cands[j], 30, 900000 + gen * 100 + t) for t, j in enumerate(top_idx)])
        # In-place protection: top1 also needs to win head-to-head against incumbent
        h2h = pool.apply(head_to_head, ((cands[top_idx[0]], best_w, 20, 990000 + gen),))
        ci = confirms[0]
        if ci > best_f + 0.005 and h2h > 0.50:
            best_f, best_w = ci, cands[top_idx[0]]
            print(f"[es] gen{gen}: UPGRADE f={best_f:.3f} h2h={h2h:.2f} coarse_top={[round(coarse[j],3) for j in top_idx]}", flush=True)
        else:
            print(f"[es] gen{gen}: hold f={best_f:.3f} (cand {ci:.3f}/h2h {h2h:.2f})", flush=True)
        json.dump(best_w, open("weights/eval_es_v4.json", "w"))
    # Final judgment
    print("[es] finals...", flush=True)
    v9w = json.load(open("weights/eval_es_v1.json"))
    fin = {}
    for name, y, yd in _G["anchors"]:
        pass
    finals = pool.map(head_to_head, [
        (best_w, v9w, 30, 600000),  # vs v9
    ])
    fin["vs_v9"] = finals[0]
    # Judge each anchor separately
    fin["fit_anchors_mean"] = eval_candidate((best_w, 30, 610000))  # 三锚均值（勿称 vs_v5）
    fin["self_mirror"] = head_to_head((best_w, best_w, 16, 620000))
    fin["confirm_fitness"] = best_f
    fin["best_w"] = {k: round(v, 3) for k, v in best_w.items()}
    fin["elapsed_s"] = round(time.time() - t0)
    json.dump(fin, open("results_v4.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(fin, ensure_ascii=False), flush=True)
    pool.close(); pool.join()

if __name__ == "__main__":
    main()
