"""编排对手池：指纹→聚类原型卡→克制矩阵（R7 P1）"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.cluster_opponents.build_counter_matrix import build_counter_matrix
from src.cluster_opponents.cluster_prototypes import cluster_prototypes
from src.cluster_opponents.extract_behavior_features import extract_behavior_features, vec_of
from src.shared.write_runs_jsonl import write_runs_jsonl


def cluster_opponents(episode_dir, out_dir):
    """episode 目录→原型卡 Markdown+克制矩阵 CSV。

    样本<10 抛异常；产出原型数与稳定性读数落 runs/。返回 {prototypes, matrix, n_episodes}。
    """
    eps = []
    for fname in sorted(os.listdir(episode_dir)):
        if not fname.endswith(".json"):
            continue
        ep = json.load(open(os.path.join(episode_dir, fname), encoding="utf-8"))
        ep.setdefault("id", fname[:-5])
        eps.append(ep)
    if len(eps) < 10:
        raise ValueError(f"样本不足聚类: {len(eps)} < 10")

    fingerprints = []
    assignment = {}
    for ep in eps:
        feats = extract_behavior_features(ep)
        if not feats:
            continue
        assignment[ep["id"]] = {}
        for seat, feat in feats.items():
            fid = f"{ep['id']}#s{seat}"
            fingerprints.append({"id": fid, "vec": vec_of(feat), "feat": feat})
            assignment[ep["id"]][seat] = fid  # 先挂指纹 id，矩阵前再换 proto

    protos = cluster_prototypes(fingerprints)
    proto_of = {}
    for p in protos:
        for m in p["members"]:
            proto_of[m] = p["proto_id"]
    final_assign = {eid: {s: proto_of.get(f) for s, f in seats.items()} for eid, seats in assignment.items()}

    os.makedirs(out_dir, exist_ok=True)
    md = os.path.join(out_dir, "prototype-cards.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("# 对手原型卡（cluster_opponents 产出）\n\n")
        for p in protos:
            f.write(f"## 原型 P{p['proto_id']}（成员 {len(p['members'])}）\n\n{p['profile']}\n\n成员：{', '.join(map(str, p['members'][:20]))}\n\n")
    matrix = build_counter_matrix(final_assign, eps, os.path.join(out_dir, "counter-matrix.csv"))

    result = {"n_prototypes": len(protos), "n_episodes": len(eps), "prototype_ids": [p["proto_id"] for p in protos]}
    write_runs_jsonl("cluster-opponents", result)
    return {"prototypes": protos, "matrix": matrix, "n_episodes": len(eps), "cards_md": md, "n_prototypes": len(protos)}
