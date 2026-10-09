"""行为克隆（BC）打分策略：真实强者的 obs→选择 映射做函数逼近（fna-006 学习派第一件）

流派定位：compete-strategy 选型律升档——查表层四连负后，语料统计开采升级为
函数逼近（平滑隐藏状态噪声）。键不再是精确查表，而是特征打分。
"""
from __future__ import annotations

import glob
import json

import numpy as np

TYPE_N, AREA_N = 17, 13
G_N = 18
O_N = TYPE_N + AREA_N + 3
D_N = G_N + O_N + 1  # + is_pass


def featurize_global(cur):
    my_i = cur.get("yourIndex", 0) if isinstance(cur, dict) else 0
    players = (cur or {}).get("players") or []
    my = players[my_i] if len(players) > my_i else {}
    opp = players[1 - my_i] if len(players) > 1 - my_i else {}

    def cnt(v):
        return len([x for x in (v or []) if x])

    cur = cur or {}
    return [
        min(cur.get("turn") or 0, 400) / 400.0,
        (my.get("handCount") or 0) / 10.0, (opp.get("handCount") or 0) / 10.0,
        (my.get("deckCount") or 0) / 60.0, (opp.get("deckCount") or 0) / 60.0,
        cnt(my.get("bench")) / 5.0, cnt(opp.get("bench")) / 5.0,
        cnt(my.get("prize")) / 6.0, cnt(opp.get("prize")) / 6.0,
        min(len(my.get("discard") or []), 30) / 30.0,
        min(len(opp.get("discard") or []), 30) / 30.0,
        1.0 if my.get("active") else 0.0, 1.0 if opp.get("active") else 0.0,
        1.0 if cur.get("supporterPlayed") else 0.0,
        1.0 if cur.get("energyAttached") else 0.0,
        1.0 if cur.get("retreated") else 0.0,
        min(cur.get("turnActionCount") or 0, 10) / 10.0,
        1.0 if cur.get("firstPlayer") == my_i else 0.0,
    ]


def featurize_option(o, pos, n_opts):
    t = np.zeros(TYPE_N)
    a = np.zeros(AREA_N)
    idx = pi = 0.0
    if isinstance(o, dict):
        tt = o.get("type")
        if isinstance(tt, int) and 0 <= tt < TYPE_N:
            t[tt] = 1.0
        ar = o.get("area")
        if isinstance(ar, int) and 1 <= ar <= 12:
            a[ar - 1] = 1.0
        else:
            a[12] = 1.0
        idx = (o.get("index") or 0) / 60.0
        pi = (o.get("playerIndex") or 0) / 2.0
    else:
        a[12] = 1.0
    order = pos / (n_opts - 1) if n_opts > 1 else 0.0
    return np.concatenate([t, a, [idx, pi, order]])


def extract_pairs(raw_glob="references/episodes/episode-*-replay.json", winners_only=True):
    """从官方原始回放抽 (X_prompt, label) 序列。单选提示（maxCount==1）+ minCount==0 时附 PASS 伪选项。

    返回 [(feats list of np.array, label_idx, episode_id)]——按 episode 分组便于留出切分。
    """
    by_ep = []
    for p in sorted(glob.glob(raw_glob)):
        d = json.load(open(p))
        eid = p.split("episode-")[-1].split("-")[0]
        winners = set()
        for pair in d.get("steps", []):
            for j in (0, 1):
                r = pair[j].get("reward")
                if r is not None and r > 0:
                    winners.add(j)
        rows = []
        for pair in d.get("steps", []):
            for j in (0, 1):
                st = pair[j]
                if st.get("status") != "ACTIVE":
                    continue
                obs = st.get("observation") or {}
                sel = obs.get("select")
                act = st.get("action")
                if not sel or not isinstance(act, list) or len(act) != 1 or sel.get("maxCount") != 1:
                    continue
                if winners_only and j not in winners:
                    continue
                g = featurize_global(obs.get("current") or {})
                opts = sel.get("option") or []
                n = len(opts)
                feats = [np.concatenate([g, featurize_option(o, i, n), [0.0]]) for i, o in enumerate(opts)]
                label = act[0]
                if not (0 <= label < n):
                    continue
                if int(sel.get("minCount") or 0) == 0:
                    feats.append(np.concatenate([g, np.zeros(O_N), [1.0]]))  # PASS 伪选项
                rows.append((feats, label, eid))
        if rows:
            by_ep.append((eid, rows))
    return by_ep


class MLP:
    """d 维特征 → h 隐 → 标量打分"""
    """D_N 维特征 → 64 隐 → 标量打分。选项间 softmax。纯 numpy。"""

    def __init__(self, h=64, seed=0, d=None):
        rng = np.random.default_rng(seed)
        self.W1 = rng.normal(0, 0.15, (h, d if d else D_N))
        self.b1 = np.zeros(h)
        self.W2 = rng.normal(0, 0.15, (1, h))
        self.b2 = np.zeros(1)
        self.params = ["W1", "b1", "W2", "b2"]

    def scores(self, feats):
        X = np.stack(feats)  # (n, D)
        H = np.tanh(X @ self.W1.T + self.b1)
        return (H @ self.W2.T + self.b2).ravel()  # (n,)

    def train(self, data, epochs=25, lr=0.02, seed=0):
        rng = np.random.default_rng(seed)
        m = {k: getattr(self, k) for k in self.params}
        v = {k: np.zeros_like(vv) for k, vv in m.items()}
        mm = {k: np.zeros_like(vv) for k, vv in m.items()}
        t = 0
        for ep in range(epochs):
            total = correct = 0
            order = rng.permutation(len(data))
            for bi in order:
                feats, label, _eid = data[bi]
                X = np.stack(feats)
                H = np.tanh(X @ self.W1.T + self.b1)
                s = (H @ self.W2.T + self.b2).ravel()
                s = s - s.max()
                p = np.exp(s)
                p = p / p.sum()
                correct += int(np.argmax(p) == label)
                total += 1
                dL = p.copy()
                dL[label] -= 1.0
                gW2 = dL @ H  # (h,)
                gb2 = dL.sum()
                dH = np.outer(dL, self.W2.ravel()) * (1 - H ** 2)  # (n,h)
                gW1 = dH.T @ X  # (h,D)
                gb1 = dH.sum(axis=0)
                grads = {"W1": gW1, "b1": gb1, "W2": gW2.reshape(1, -1), "b2": np.array([gb2])}
                t += 1
                for k in self.params:
                    mm[k] = 0.9 * mm[k] + 0.1 * grads[k]
                    v[k] = 0.999 * v[k] + 0.001 * grads[k] ** 2
                    mh = mm[k] / (1 - 0.9 ** t)
                    vh = v[k] / (1 - 0.999 ** t)
                    m[k] -= lr * mh / (np.sqrt(vh) + 1e-8)
            if (ep + 1) % 5 == 0:
                print(f"  epoch {ep+1}: train_acc={correct/total:.3f}")
        for k in self.params:
            setattr(self, k, m[k])

    def eval_acc(self, data):
        hit = 0
        for feats, label, _eid in data:
            if int(np.argmax(self.scores(feats))) == label:
                hit += 1
        return hit / max(1, len(data))

    def export(self):
        return {k: getattr(self, k).round(4).tolist() for k in self.params}
