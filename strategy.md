---
generated_at: 2026-10-05
direction: 黑客松与数据竞赛
profile_ref: config/profile.yaml
kb_snapshot: f529c17c
---

# 攻略：compete-strategy 方法论实战测试选赛

任务口径（grill-notes 2026-10-05）：完整实战·验证优先；严格完美条件（引擎源码+公开回放）；找到就开·并行；诉求=方法论验证+奖金/名次。

## 一、赛事情报摘要

**kaggle-pokemon-tcg-ai-battle-challenge-playground**（新建条目，2026-10-05，13 项预核零修正）：Kaggle Playground·Simulation，2026-09-29 开赛（开赛仅 6 天，冷启动窗口仍在），最终提交 **2027-01-08**、BT 终局评估至 01-22；奖励=Kaggle 周边（1-5 名，无现金、Playground 无奖牌——待核平台口径）；当前 172 队；日 5 提交、仅最新 2 件活跃、μ0=600。**引擎源码可得铁证**：`cabt`（Card Battle，BO3，动作=合法选项索引）已入 kaggle-environments 官方仓库；**回放三通道**（自己提交的 episode/他队 Leaderboard 回放/**官方每日顶部评分对局导出**，BC/RL/IL 官方鼓励）；对局评测禁联网；Winner License=None 不强制开源。AI 政策：本赛即 AI 智能体赛（apply）。

**gsk-pyxis-simulation**（新建条目，upcoming，2026-10-05）：GSK Pyxis Portfolio Challenge，引擎 `pyxis` 已入官方 wheel（README/AGENTS.md/QUICKSTART.md 全公开），gsk.ai 可对战内置 AI。**gsk.ai 已公布**：entry 2027-01-04、终交 2027-01-11、奖金池 **$50k**（15k/12k/9k/8k/6k）+论文共同作者邀请；赛制=两家药企研发组合对抗（100 步、£5B、隐藏 PTRS+噪声读数、共享市场 1/n^α 进入惩罚、BD 竞标、净现金流定胜负）——与 kagriculture **同构**（双人经济仿真+隐藏信息+随机事件）。⚠ Kaggle 赛站延期未上线（公告开赛 09-29，10-05 仍 404，双通道复核）。

**非 Kaggle 广搜**（2026-10-05 分片结论，不建条）：Battlecode 2027=窗口内最优（2026 届>$20k、引擎开源、Sprint 赛道开放），但 2027 届未官宣、引擎仓库预计 11-12 月落地、赛期 2027 年 1 月 IAP；CodeCup 2027（Tumbleweed）即刻可报、决赛 2027-01-23、全对局公开，但裁判仅规格不开源、无奖金；Battlesnake=开源引擎常年天梯（沙盒级）；SSCAIT 停摆、riddles.io/.ai 双死、AIcrowd 无 PvP、AIIDE 出窗、Terminal/CodinGame 报名窗已关或未开。

## 二、赛道对比矩阵（六维；每格一句证据，标来源条目）

| 赛事 | 时间窗 | 技术契合 | 通吃度 | 画像匹配 | 竞争密度 | 合规风险 |
|---|---|---|---|---|---|---|
| PTCG Playground | ★ 立即可战至 2027-01-08，entry 开放中（条目 meta） | ★ 引擎+回放+PvP 天梯全齐，compete-strategy 十步可完整走通（cabt 铁证+回放三通道） | 高：判决池/对拍/语料管线与 GSK pyxis 同框架（kaggle-environments） | 高：python 全栈即可，CPU 为主，禁联网=纯本地智能体 | 中：172 队（Playground），但含 featured 赛 6807 队尾流老将 | 低：apply（本赛即 AI 赛），rules 已核 |
| GSK pyxis（未上线） | 中：entry 2027-01-04/终交 01-11，但 Kaggle 站 404 延期（条目待办） | ★ 同构经济仿真，方法论迁移最顺；引擎今即可预研 | 高（同上框架） | 高（同上；求解器段数学建模强项可发挥） | 未知（未上线；featured 规模参考 kagriculture 10246 队） | 低：gsk.ai 无 AI 限制条款（待开赛核验） |
| Battlecode 2027 | 弱：2027-01 IAP，现无报名通道（广搜分片） | 高：引擎开源+scrimmage PvP | 中：Java 引擎异框架 | 中：Java 画像可写但非熟手列 | 高（MIT 全球学生赛） | 低（学生赛传统开放） |
| CodeCup 2027 | 中：可即刻提交，决赛 2027-01-23（广搜分片） | 中：裁判仅规格不开源——严格条件 (a) 不满足（grill 决策②排除主推） | 低：抽象棋 1v1，资产管线异构 | 高 | 低（社区赛） | 低 |

## 三、大显身手信号

**无 90 天内 KB-2 新卡直接命中**（如实告知：KB-2 时序/agents 卡群与本任务方法论无重叠，禁止硬凑）。实际差异化点=**非 KB-2 的自有资产**：K-14 compete-strategy 技能 v18（三轮评审收敛）+ kagriculture 战役沉淀的判决机/对拍/复刻提示词方法论（JOURNAL 在档）——本战役正是它的首次实战检验，差异化来源即测试对象本身。

## 四、一鱼多吃路线

1. **PTCG Playground（主，立即）→ GSK pyxis（正赛，待上线）**：同 kaggle-environments 框架，判决池/对拍/语料开采/迭代台账基建复用率 ~90%；GSK 预研包（引擎六问+参数表+判决池 v0 vs 内置 AI）本战役内交付，上线即切入——改造量：低。
2. **→ Battlecode 2027（2027-01）**：十步方法论跨引擎迁移（Java），决策面立方体/净账纪律等语言无关层直接复用；引擎仓库 11-12 月落地后评估另立——改造量：中。
3. **→ CodeCup 2027（可选轻量）**：确定性 1v1 抽象棋，作"无语料退路/搜索派"分支的低成本补充验证场——改造量：低。

## 五、合规与风险

- **模式判定：apply**。依据：PTCG 条目 ai_policy——本赛即"Build an AI Training Agent"的智能体对战赛（rules 为 skills-based competition 口径，AI 开发即赛事本意）；对局评测禁联网已转化为技术约束（纯本地智能体）；自训模型归参赛者、无强制开源。
- 风险清单：
  1. **GSK 上线延期**（公告 09-29 已过仍 404）→ 缓解：预研包不依赖上线；每日探活（CLI/页面），上线即核验四页并触发正赛决策。
  2. **Playground 无奖金与"奖金/名次"诉求部分错位** → 缓解：名次诉求由天梯+BT 终局兑现；奖金诉求明确转由 GSK（$50k）承担；呈报明示此分工。
  3. **天梯老将尾流**（featured 6807 队强队可能转战 Playground）→ 缓解：方法论一等目标是走通十步而非夺魁；对手池聚类恰好以其为强锚素材。
  4. **三战役并行时间冲突**（安航云盾材料 10 月中旬、STITP 中期 12 月）→ 缓解：线上赛节奏自控，日 5 提交上限天然限流；GSK 终交 01-11 与 STITP 中期错峰 3 周。
  5. 卡牌游戏类目陌生（隐藏信息+运气成分）→ 这正是测试价值：与 kagriculture 经济仿真构成方法论泛化性的一对极对照（skill 引擎六问文档中宝可梦即反例分支）。

## 六、推荐结论

**推荐第一名：PTCG Playground 立即立项**（战役 ptcg-playground-2026）。理由：它是当前全球范围内唯一"今天就能提交打天梯"的严格完美条件对抗赛（引擎源码+回放三通道+PvP+3 个月窗口），开赛仅 6 天冷启动路径可直接实测；且游戏类与 kagriculture 异构（隐藏信息卡牌 vs 完美信息经济仿真），对 compete-strategy 泛化性是硬核检验——方法论验证（一等目标）最大化。**备选：GSK pyxis 预研→上线即切入**（$50k 奖金+同构迁移最顺，但未上线不可战，作为本战役内置里程碑 m4 承接，不另立主推）。诚实兜底说明：若用户坚持"必须有奖金的完美条件赛"，当前窗口内不存在——GSK 是唯一候选且需等待上线。
