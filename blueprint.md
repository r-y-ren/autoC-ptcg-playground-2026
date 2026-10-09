---
campaign:
  competition_id: kaggle-pokemon-tcg-ai-battle-challenge-playground
  name: PTCG Playground 方法论实战（compete-strategy v18 首战 + GSK pyxis 先手预研）
  theme: Kaggle Simulation · Playground · 对抗智能体（宝可梦 TCG bo3 天梯）

scope:
  deliverables:
    - 参赛智能体（种子件→资产装配件，天梯在榜、μ 稳定、终局 BT 存活至 2027-01-22 评估窗）
    - 判决池基建（本地 cabt 判决机 v0→全量：自镜像噪声地板+强锚+弱锚；first-divergence 对拍管线）
    - 方法论验证复盘报告（十步逐项执行记录+卡点+模板缺口，回灌 compete-strategy 技能迭代提案）
    - GSK pyxis 预研包（引擎六问世界参数表 T1+受控坐标表 T2+本地判决池 v0 对战内置 AI 手感实测；开赛即切入的先手件）
    - 对手池情报资产（官方每日顶部对局导出+他队回放聚类：原型画像卡+对抗矩阵）
    - metrics.json 实测数字体系（天梯 μ 官方回读/池内稳健胜率/净账 ΔJ/逐拍对齐率，全血统可溯源）
  out_of_scope:
    - GSK pyxis 正赛（Kaggle 站上线后另立战役或经用户确认扩展本蓝图；本战役只交付预研包）
    - 奖金冲刺叙事（Playground 无现金奖；奖金诉求由 GSK 正赛承接）
    - Battlecode 2027 / CodeCup 2027 参赛（仅情报跟踪，见 strategy 第四节）
    - 任何对局期联网的智能体形态（赛规禁联网，纯本地推理）
    - 违反 Kaggle 规则的多账号/评分操纵（铁律：不生成违反目标赛事规则的提交策略）

tech_stack:
  - name: kaggle_environments（cabt 引擎：Card Battle，BO3，合法选项索引动作空间）
    kb_tech_ids: []
    rationale: >-
      引擎源码随赛方发布（官方 wheel 铁证），KB-2 暂无对应卡——锚=KB-1 条目
      kaggle-pokemon-tcg-ai-battle-challenge-playground（API 文档 matsuoinstitute.github.io/cabt）；
      补录技术卡留慢循环。选型依据：本地可复现全部对局语义=判决池与对拍的前置条件。
    reuse_cost: 低
  - name: compete-strategy 十步方法论（K-14 技能 v18，含判决池 v0/冷启动降级/T1-T5 模板）
    kb_tech_ids: []
    rationale: >-
      本战役的测试对象与主方法（工作流资产非 KB-2 卡）：合规门→J+判决池 v0→引擎六问→
      转移函数→资产化→五层装配→净账闭环→监控。产出=十步执行记录，缺步即报告的负结果。
    reuse_cost: 低
  - name: 回放语料开采管线（episode 下载/聚类/原型卡生成——kagriculture 战役模式复刻）
    kb_tech_ids: []
    rationale: >-
      复用 kaggriculture 战役沉淀的判决机/对拍/复刻提示词方法论（JOURNAL 在档；
      archive 待归档）。官方每日顶部对局导出=一手语料杠杆（条目 meta 核实）。
    reuse_cost: 中

interface_contracts:
  - between: [software, document]
    contract_file: workspace/ptcg-playground-2026/references/metrics_contract.md
  - between: [software, software]
    contract_file: workspace/ptcg-playground-2026/references/judge_pool_contract.md

milestones:
  - id: m0-engine
    task: 冷启动步 0/1/4——合规台账；目标函数 J+选优尺声明；本地 cabt 跑通+引擎六问（T1 世界参数表/T2 受控坐标表）；判决池 v0 可跑（自镜像 h2h≈0.5 校准+一强锚一弱锚）；GSK pyxis 同步开工（pyxis 环境装载）
    owner_role: software
    depends_on: []
  - id: m1-vertical
    task: 竖切——种子件（最傻但完整）tar.gz 打包+提交上天梯；episode 回放采集管线跑通；对手池初聚类（原型卡 v1）；迭代台账（T5）建档
    owner_role: software
    depends_on: [m0-engine]
  - id: m2-loop
    task: 闭环——资产开采（官方每日导出+他队回放统计→查表/磁带资产，T3 规格书+常量血统表）；五层回路装配（观测器/控制器/调度/清单/防御净账护栏）；单变量 A/B 迭代运转（净账 ΔJ+池内稳健胜率双读数）
    owner_role: software
    depends_on: [m1-vertical]
  - id: m3-polish
    task: 监控与再适应（对手池漂移分段统计）+方法论验证复盘报告成稿（typst，数字全部回填 metrics.json 实测）+compete-strategy 技能回灌提案
    owner_role: document
    depends_on: [m2-loop]
  - id: m4-gsk
    task: GSK pyxis 预研包——引擎六问 T1/T2+本地判决池 v0 对战内置 AI（gsk.ai/play 实测）+上线探活规程（CLI/页面每日检查）；Kaggle 站上线即触发 KB 条目四页核验与正赛另立决策呈报
    owner_role: software
    depends_on: [m0-engine]

acceptance:
  checklist:
    - {id: sw-boot, category: software, item: 判决池 v0 一键冒烟（自镜像局跑通+h2h 校准值打印）, method: 自动,
       cmd: "python workspace/ptcg-playground-2026/software/judge/smoke_judge.py"}
    - {id: sw-test, category: software, item: 测试套件全过, method: 自动,
       cmd: "python -m pytest workspace/ptcg-playground-2026/software/tests -q"}
    - {id: sw-pack, category: software, item: 提交包结构校验+本地自对弈一局（tar.gz 顶层 main.py+deck.csv）, method: 自动,
       cmd: "python workspace/ptcg-playground-2026/software/pack_check.py"}
    - {id: sw-gsk, category: software, item: GSK 预研包含世界参数表+pyxis 判决池冒烟, method: 自动,
       cmd: "python workspace/ptcg-playground-2026/software/gsk_prestudy_check.py"}
    - {id: doc-compile, category: document, item: 方法论复盘报告编译通过（typst）, method: 自动,
       cmd: "typst compile workspace/ptcg-playground-2026/docs/methodology_report.typ"}
    - {id: man-ladder, category: manual, item: Kaggle 天梯首次提交成功且 episode 回放可下载（人工站内操作+URL 存档）, method: 人工}
    - {id: man-metrics, category: manual, item: 天梯 μ 数字官方回读记录进 metrics.json（数字纪律：只收站内实测值）, method: 人工}
    - {id: man-gsk-live, category: manual, item: GSK 上线核验（KB 条目 rules/timeline/prizes/evaluation 四页回填，双源确认）, method: 人工}

compliance:
  ai_policy_reviewed: true
  mode: apply
  policy_basis: >-
    赛事本体即 AI 智能体对战（"Build an AI Training Agent to play the Pokémon Trading Card
    Game"，skills-based competition 口径）；对局评测禁联网（条目 meta，2026-10-05 实抓）；
    自训模型/权重归参赛者（rules §3.18），Winner License=None 无强制开源。
  notes: GSK pyxis 预研仅消费公开引擎文档与内置 AI 对手，无参赛行为，合规随正赛另核。
workflow:
  auto_chain: false
---

# 正文（人读）

## 选型依据摘要

推荐与备选的完整论证见 `strategy.md`（六节+证据强度）。核心：PTCG Playground 是当前唯一可立即参战的严格完美条件对抗赛（引擎 cabt 入官方 wheel+回放三通道+PvP 天梯+3 个月窗口），且与 kagriculture 构成方法论泛化性的异构对照（隐藏信息卡牌 vs 完美信息经济仿真）。

## 里程碑展开

- **m0-engine（冷启动步 0/1/4）**：本里程碑直接产出 compete-strategy 冷启动降级路径的实测记录——判决池 v0 定义=自镜像+一强锚+一弱锚（强锚候选=featured 赛尾流老将件或内置策略，弱锚=随机/贪心种子）。
- **m1-vertical（竖切=走路骨架）**：种子件原则"最傻但完整"（skill 冷启动第 3 条），目标是全链路跑通而非强度；当日 5 次提交配额即天然迭代节奏。
- **m2-loop（闭环主体）**：资产承载决策（T3），文档只承载基建——直接检验叙事纪律红线；净账护栏防"赢了参数输了钱"式翻车。
- **m3-polish**：复盘报告的负结果与卡点同等一等公民（测试目标=发现 skill 缺口而非证明其完美）。
- **m4-gsk（并行）**：GSK 引擎今即可预研（公开 wheel+内置 AI），上线延期不阻塞；终交 2027-01-11 与 STITP 中期错峰。

## 验收数字体系（metrics.json 键清单）

天梯 μ（官方回读）| 池内稳健胜率（判决池多原型口径）| 净账 ΔJ（单变量 A/B 台账）| 逐拍对齐率（资产保真）| 对手池原型数与覆盖度。一切对外数字只出自 metrics.json（铁律 4）。

## 风险与缓解

见 strategy.md 第五节五项（GSK 延期探活/奖金诉求分工/老将尾流/三战役并行限流/类目陌生即测试价值）。
