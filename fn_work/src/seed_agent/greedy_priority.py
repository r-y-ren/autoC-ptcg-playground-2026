"""按手写优先级表（带血统标注）对 options 打分取前 maxCount（R5）"""
from __future__ import annotations

# 血统表：v5 定格（2026-10-05 实测迭代链完整留档：
#   v1 type 重排选满→vs random 0.17｜v2 双模→0.38｜v3 攻击浮前→0.07（崩溃：选项次序编码
#   目标语义，重排=选错目标）｜v4 first 语义+弃牌 pass→0.80（pass 反而掉分：可选弃牌多为
#   有益换牌）｜v5 纯 first 语义→≈first 同水位）。
# 结论（m0 级方法论发现）：**引擎选项默认次序即强基线**（first 锚 0.90 胜 random）；
# 种子件=最傻但完整=该基线+我们的解析/防御管线。偏离次序的决策必须等 m2 语料证据
# （compete-strategy 叙事纪律：决策内容不拍脑袋，语料定标）。
# type 枚举（官方 api.html OptionType）：0 数选/1 YES/2 NO/3 选卡/4 工具卡/5 能量卡/
# 6 能量/7 手牌出牌/8 附着/9 进化/10 特性/11 弃牌/12 撤退/13 攻击/14 结束/15 技能/16 异常状态


def greedy_priority(options, max_count, min_count=0):
    """v5：引擎原序选满 maxCount（first 语义基线）。

    options 空或 max_count<=0 返回 []；min_count 保留参数位供 m2 资产层接管。
    """
    if not options or max_count <= 0:
        return []
    return list(range(min(max_count, len(options))))
