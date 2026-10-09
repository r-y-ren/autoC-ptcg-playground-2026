"""纯函数：两个 steps 序列首个不等拍号，含长度不等处理（R3）"""
from __future__ import annotations


def first_divergence(steps_a, steps_b):
    """逐元素相等比较，返回首个不等位置索引；全等返回 None。

    长度不等：若前 min(len) 个全等，分叉=短者末位之后（返回 min(len)）。
    任一序列为空抛异常。
    """
    if not steps_a or not steps_b:
        raise ValueError("steps 序列为空")
    n = min(len(steps_a), len(steps_b))
    for i in range(n):
        if steps_a[i] != steps_b[i]:
            return i
    if len(steps_a) != len(steps_b):
        return n
    return None
