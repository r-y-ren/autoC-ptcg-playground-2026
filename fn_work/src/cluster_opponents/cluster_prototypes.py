"""指纹集聚类（K 由简化轮廓定）→原型画像卡（R7 P1）"""
from __future__ import annotations

import random

from src.cluster_opponents.extract_behavior_features import vec_of


def _dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def _kmeans(vecs, k, seed=7, iters=20):
    rng = random.Random(seed)
    cent = rng.sample(vecs, k)
    for _ in range(iters):
        assign = [min(range(k), key=lambda j: _dist(v, cent[j])) for v in vecs]
        newc = []
        for j in range(k):
            members = [vecs[i] for i in range(len(vecs)) if assign[i] == j]
            newc.append([sum(col) / len(members) for col in zip(*members)] if members else cent[j])
        if newc == cent:
            break
        cent = newc
    return [min(range(k), key=lambda j: _dist(v, cent[j])) for v in vecs], cent


def _silhouette(vecs, assign, cent):
    k = len(cent)
    if k < 2:
        return -1
    total = 0.0
    for i, v in enumerate(vecs):
        own = [vecs[j] for j in range(len(vecs)) if assign[j] == assign[i] and j != i]
        a = sum(_dist(v, w) for w in own) / len(own) if own else 0.0
        b = min(
            sum(_dist(v, w) for w in [vecs[j] for j in range(len(vecs)) if assign[j] == c])
            / max(1, sum(1 for j in range(len(vecs)) if assign[j] == c))
            for c in range(k) if c != assign[i]
        )
        total += (b - a) / max(a, b) if max(a, b) else 0
    return total / len(vecs)


def cluster_prototypes(fingerprints):
    """[{id, vec, feat}] → 原型卡列表 [{proto_id, members, centroid, profile}]。

    K∈[2,5] 按简化轮廓选；样本<4 或全同 → 单原型。空输入抛异常。
    """
    if not fingerprints:
        raise ValueError("指纹集为空")
    vecs = [f["vec"] for f in fingerprints]
    if len(set(map(tuple, vecs))) < 4 or len(vecs) < 4:
        return [{"proto_id": 0, "members": [f["id"] for f in fingerprints],
                 "centroid": vecs[0] if vecs else [],
                 "profile": "单原型（样本不足或全同）"}]
    best = None
    for k in (2, 3, 4, 5):
        if k >= len(vecs):
            break
        assign, cent = _kmeans(vecs, k)
        s = _silhouette(vecs, assign, cent)
        if best is None or s > best[0]:
            best = (s, assign, cent, k)
    _s, assign, cent, k = best
    protos = []
    for j in range(k):
        members = [fingerprints[i]["id"] for i in range(len(fingerprints)) if assign[i] == j]
        feats = [fingerprints[i]["feat"] for i in range(len(fingerprints)) if assign[i] == j]
        if not members:
            continue
        avg = {key: round(sum(f.get(key, 0) for f in feats) / len(feats), 3)
               for key in feats[0]}
        profile = (f"开局首选项率 {avg.get('firstness')}｜攻击倾向 {avg.get('attack_rate')}｜"
                   f"附着 {avg.get('attach_rate')}｜进化 {avg.get('evolve_rate')}｜"
                   f"出牌 {avg.get('play_rate')}｜pass {avg.get('pass_rate')}")
        protos.append({"proto_id": j, "members": members, "centroid": cent[j], "profile": profile})
    return protos
