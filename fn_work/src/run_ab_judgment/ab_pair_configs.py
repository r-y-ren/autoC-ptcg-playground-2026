"""同种子双席折叠对局组配置生成（R9）"""
from __future__ import annotations


def ab_pair_configs(n_seeds, pool_members):
    """生成 A/B 双席折叠配置：每种子两局（A 席 0/B 席 1 与对调），成员=判决池锚。

    种子数<6 抛异常（折叠意义下限）。返回 [{seed, a_seat, b_seat, member}]。
    注意：引擎熵不可种子化（B1 评审实证）——"同种子"仅作 Python 层统计播种标记，
    判决按局数收敛（每成员 ≥2×n_seeds 局）。
    """
    if n_seeds < 6:
        raise ValueError(f"种子数不足折叠下限: {n_seeds} < 6")
    configs = []
    for s in range(n_seeds):
        for member in pool_members:
            configs.append({"seed": 10000 + s, "a_seat": 0, "b_seat": 1, "member": member})
            configs.append({"seed": 10000 + s, "a_seat": 1, "b_seat": 0, "member": member})
    return configs
