"""T3 规格书渲染：资产名/来源/生成器/验收数字/血统表（R8 P1）"""
from __future__ import annotations


def emit_asset_spec(asset_table, meta, out_path):
    """渲染 T3 规格书 Markdown。meta 必含：asset_name/source/n_gen/acceptance(list)。

    血统表=每 state 格一行（局面/最优动作签名/样本量/占比）。元数据缺验收数字抛异常。
    """
    for key in ("asset_name", "source", "n_gen", "acceptance"):
        if key not in meta:
            raise ValueError(f"meta 缺 {key}（T3 规格书硬字段）")
    lines = [f"# T3 资产规格书：{meta['asset_name']}", "",
             f"- 来源：{meta['source']}", f"- 生成器：{meta['n_gen']}（可复跑）",
             "- 验收数字："] + [f"  - {a}" for a in meta["acceptance"]] + ["",
             "## 常量血统表", "", "| 局面(turn桶,hand,prize) | 最优动作签名(type 集) | 样本量 n | 占比 |", "|---|---|---|---|"]
    for k, cell in sorted(asset_table.items(), key=lambda kv: str(kv[0])):
        (sig, n) = max(cell.items(), key=lambda kv: kv[1])
        total = sum(cell.values())
        lines.append(f"| {k} | {sig} | {n} | {round(n / total, 3)} |")
    out = "\n".join(lines) + "\n"
    import os
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    return out_path
