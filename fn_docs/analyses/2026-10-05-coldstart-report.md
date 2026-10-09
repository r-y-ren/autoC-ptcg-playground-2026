# fn-analyze 报告：PTCG 冷启动首日复盘（全量线）

- 快照：results/2026-10-05-ladder-and-runs.md + 本文件（天梯首分 COMPLETE μ=600 已入 metrics_shards/ladder-readback.json）
- 机械轴：桩 0 / doc-lint 0 错 0 警 / 58 tests 绿（fn-check 双查过）——数据可信前置成立

## 上次快照 vs 本次（首份=基线）

| 读数 | 基线（今日首测） | 来源 |
|---|---|---|
| 天梯 μ | 600.0（初始，验证局过） | CLI submissions 回读 |
| 自镜像 h2h | 0.6（20 局 bo3，decided 20/20） | judge-pool runs |
| 种子件 vs random/first | 0.82 / 0.52（60 局 bo1 席位对开） | B3 实测 |
| greedy 迭代链 | v1 0.17→v2 0.38→v3 0.07→v4 0.80→v5 0.82 | B3 血统表 |
| 资产对齐率（训练集口径 v1） | 0.0717（4 局方向性） | mine-assets runs |
| GSK 地板 | do-nothing 6/6 平局 | gsk-prestudy runs |
| GSK 赛站 | not-live（cli=False, http=404） | gsk-probe runs |

## 三轴分析要点

1. **结果轴**：v3 崩溃（0.07）与 v1（0.17）证明引擎选项次序编码目标语义——重排=选错目标；此为引擎六问 q3/q5 的实战级补充证据。
2. **职责关联轴**：对齐率 0.07 嫌疑人=aggregate_state_action 状态键过粗（turn//10 桶+hand+prize）+ 样本 4 局方向性——但证据弱（n=4、训练集口径），不足以定罪，真实语料复算后再判。
3. **证据强度轴**：对手池原型卡当前只反映 first/random 两个自产风格——**对手池尚未见过任何真实天梯对手**（语料阻塞已解除：首提 COMPLETE，episodes API 可用）。

## 改进提案（registry fna-001..004，全部 pending）

- **P1[高] 真实语料激活**（fna-001）：拉天梯回放→适配层转内部格式（官方 JSON 无 option_types，需补全适配器=结构性，回 fn-divide）→真实对手聚类+资产复算。预期信号：≥20 真实局入库+真实原型卡。
- **P2[中] 语境定标**（fna-002）：YES/NO 与多选提示按真实语料统计定标（观察性→受控单变量→A/B 判决）。预期信号：net_delta_J>0。
- **P3[激进] deck 空间第一杠杆**（fna-003）：60 卡组合空间零探索——主题牌组（快攻/全进化线）对默认组判决池 A/B。牌组是比动作序更大的可控面。
- **P4[中] GSK 预研深化**（fna-004）：PTRS 贝叶斯观测器+终局求解器原型+内置 AI 人工实测；探活持续。

## 效果闭环

fn-score 工作台：4 提案全部 pending（首份 registry 无历史提案可打分）；各提案 scored_in 已指定数据源，达成后 --set 落分。
