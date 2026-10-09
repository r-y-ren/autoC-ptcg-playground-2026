# 需求文档：PTCG Playground 方法论实战（compete-strategy v18 首战）

## 根本目的

以 Kaggle PTCG AI Battle Challenge Playground（终交 2027-01-08）为实战场，首次完整执行 compete-strategy 十步方法论（含冷启动降级路径），一等目标=验证方法论可执行并产出复盘改进提案；二等目标=天梯名次。附带交付 GSK pyxis 预研包（$50k 奖金赛先手件，终交 2027-01-11）。成功形态：种子件→资产装配件上天梯在榜、判决池双读数迭代运转、复盘报告回灌技能。

## 环境与技术栈决策

| 项 | 决策 |
|---|---|
| 语言/框架/运行时 | Python 3.14.7（系统，兼容 kaggle-environments≥3.11）；战役内独立 venv `fn_work/.venv`（D14 圈禁：战役文件只落战役根；kagriculture 先例） |
| 核心依赖 | kaggle-environments==1.33.0（含 cabt 引擎 252 行 + pyxis 引擎）、pytest、kaggle CLI（已装 2.2.4 已鉴权） |
| 错误处理风格 | 异常（pytest 生态一致）；判决池跑批对单局失败隔离计数、不中断整批 |
| 日志方式 | 结构化 JSON 行落 `fn_work/runs/`（gitignore；kagriculture 先例：运行结果全留作 AI 纠错） |
| 结构与入口 | **一切置于 `fn_work/`**（fn-ladder 固定结构，用户 2026-10-05 裁决"结构以 fn-ladder 为主"）；蓝图验收 cmd 为 `software/` 字面路径处，波门以 fn_work 入口**等价执行**，蓝图字面路径留待下次 /attack 顺手对齐（不改语义只改路径） |

## 术语表

| 术语 | 精确定义 |
|---|---|
| episode | 一整局对局的记录文件（JSON），含双方逐拍动作；官方回放与本地对拍产物同构 |
| 拍（step） | 引擎一次向双方要动作的回合点；对拍以拍为单位对齐 |
| 判决池 | 本地评测台：固定的一组对局配置（自镜像+强锚+弱锚），输出胜率/分差读数 |
| 自镜像 | 同一份智能体坐双方席位对打；胜率应≈0.5，偏离量=实现偏差，收敛后=噪声地板 |
| 强锚/弱锚 | 判决池中的参照对手：强锚=当前最强可用件（初期=random_agent 之上的种子件，后期=上版正式件）；弱锚=first_agent/random_agent（引擎自带，cabt.py:73/79） |
| 净账 ΔJ | 改动验收读数 = Δ我方得分 − Δ对手得分 − 自伤（不以"目标参数动了"计） |
| 池内稳健胜率 | 对判决池全部原型对手的稳健口径胜率（非平均胜率，防非传递） |
| 逐拍对齐率 | 复刻件/资产与真实回放逐拍动作一致的比例（资产保真指标） |
| 原型卡 | 对手池聚类产物：一类行为指纹相近的对手（画像+被克制关系） |
| 资产 | 承载决策的数据件（查表/磁带/求解器），带生成器+血统表+两个验收数字（T3 规格书） |
| 血统表 | 每个进决策层的数字一行：值/来源/样本量/置信 |
| 天梯 μ | Kaggle 官方 skill rating（Gaussian μ/σ，初始 600），唯一对外名次数字（官方回读） |
| deck | 60 张卡的牌组清单（deck.csv：60 行纯数字卡 ID，无表头） |

## 需求条目

### R1 本地判决池 v0 [P0]（m0）
- 内容：`make("cabt")` 本地对战封装——自镜像局 N 局、对锚局（first_agent/random_agent）；输出胜率/分差/自镜像校准值；单局失败隔离计数。输入=配置（局数/双方 agent/deck）；输出=JSON 结果行（落 runs/）+stdout 摘要；错误=局失败计入 failed 计数不中断。
- 验收方式：命令 `python workspace/ptcg-playground-2026/software/judge/smoke_judge.py`（入口垫片）→ 退出码 0，stdout 含 `self-mirror h2h`（值域 0.35–0.65，局数≥20）与各锚点胜率行。

### R2 引擎六问产物（T1/T2）[P0]（m0）
- 内容：世界参数表 T1（六问各一节：cabt 计分/对手交互点/失败语义/时间结构/信息结构/随机源——每条结论带 cabt.py 行号）+受控坐标表 T2（可控/可影响/可观测不可推/不可控随机四级）。产物为 Markdown 表格文件，落 `docs/methodology/`。
- 验收方式：可观察判据——评审人（用户/子代理）核对：六问各≥1 行且每行含 `cabt.py:行号` 引用；T2 覆盖四级各≥1 行。

### R3 episode 记录器与对拍器 [P0]（m0）
- 内容：本地局落 episode JSON（与官方回放同构：逐拍双方动作+终局）；对拍器输入两份 episode，输出首个分叉拍号+双方动作。错误=格式不符时报明确行号。
- 验收方式：pytest——本地自对弈产 episode→自对拍分叉拍=None（全程一致）；人为篡改一拍→分叉拍=篡改位。

### R4 提交打包器 [P0]（m1）
- 内容：main.py+deck.csv → submission.tar.gz（顶层不嵌套）；结构校验+打包后本地自对弈一局（装载路径模拟 `/kaggle_simulations/agent/`）。
- 验收方式：命令 `python workspace/ptcg-playground-2026/software/pack_check.py` → 退出码 0，输出含 `tar structure OK` 与 `local self-play OK`。

### R5 种子件智能体 [P0]（m1）
- 内容："最傻但完整"参赛件：obs{logs,current,select}→引擎原序选满（v5 语义，2026-10-05 实测迭代后回写：手写优先级表 v1-v3 证伪，first 基线 0.82 胜 random；见 greedy_priority.py 血统表）；默认牌组 60 卡=引擎 cabt.py:9-70 自带组逐行拷贝。纯本地推理（禁联网）。
- 验收方式：pytest——对 random_agent 胜率 ≥0.9（n≥50）；对 first_agent 胜率 ≥0.95；obs 各字段缺失/None 时不崩（防御层雏形）。天梯首提=人工项（man-ladder）。

### R6 回放采集器 [P0]（m1）
- 内容：kaggle CLI 拉己方提交 episode+他队 leaderboard 回放 → `references/episodes/`（INDEX.md 登记来源与日期）；去重（episodeId）。
- 验收方式：命令行拉取 ≥1 条真实 episode 存盘成功+INDEX 登记（人工核一眼来源行）。

### R7 对手池聚类器 [P1]（m2）
- 内容：episode 集合→行为指纹（开局一致度/出牌节奏/资源结构）→原型卡+对抗矩阵。输入=episode 目录；输出=原型卡 Markdown+矩阵 CSV。
- 验收方式：可观察判据——对 ≥50 局聚出的原型跨局稳定（同版本重跑原型数±1、成员漂移<10%）。

### R8 资产开采器 [P1]（m2）
- 内容：高分回放→局面-动作分布统计→候选查表资产（T3 规格书：生成器+血统表+逐拍对齐率）。
- 验收方式：生成器可复跑（同输入同输出）；对齐率数字产出且血统表每数字带样本量。

### R9 正式件五层装配与 A/B 判决 [P0]（m2）
- 内容：观测/控制器/调度/清单/防御（净账护栏：自伤上限/非法动作自检/破产线类比=奖赏卡不落空）五层 agent v2；单变量 A/B 跑判决池出双读数（净账 ΔJ+池内稳健胜率），T5 台账行（JSON registry）。
- 验收方式：pytest——A/B 判决流程对固定两版 agent 产出含 `net_delta_J` 与 `pooled_winrate` 的台账行；判负版自动标记 rollback 建议。

### R10 metrics 汇总器 [P0]（m3 前置）
- 内容：各分片 runs/ 读数+天梯 μ 官方回读值 → 战役顶层 metrics.json（唯一数字源，铁律 4）。键：ladder_mu/ladder_mu_date/pooled_winrate/net_delta_J_lastN/alignment_rate/prototype_count。
- 验收方式：命令跑通+metrics.json 含上述全部键且每个数字带来源字段。

### R11 GSK 预研包 [P0]（m4）
- 内容：pyxis 环境装载+引擎六问 T1/T2（pyxis.py/README 行号引用）+本地判决池 v0（自镜像+内置 AI 对手若可编程接入；不可编程则记录 gsk.ai/play 人工实测 N 局结果）。
- 验收方式：命令 `python workspace/ptcg-playground-2026/software/gsk_prestudy_check.py` → 退出码 0，输出含 pyxis 自镜像局结果与 T1/T2 文件存在性。

### R12 GSK 上线探活器 [P1]（m4）
- 内容：每日探测 gsk-simulation 赛站（CLI 查询+页面 404 检查），上线即输出核验清单提示。
- 验收方式：跑一次输出当前状态行（`not-live`）+退出码 0；探活结果入 runs/。

## 非功能约束

| 约束 | 判据 |
|---|---|
| 对局评测禁联网 | agent 代码无网络 import/调用（grep 静态检查进 R5 pytest） |
| 每日提交配额 ≤5 | 提交流程内置当日计数（本地记录），超限拒绝打包 |
| 无 GPU 依赖 | 全流程 CPU 可跑（查表/规则为主；RTX 4070 仅预留） |
| 本地引擎=线上同构 | kaggle-environments 固定版本 1.33.0（requirements 锁定，升级须过对拍） |
| 判决池可复现 | ~~同种子同结果~~（作废：libcg.so 洗牌无种子入口，B1 评审实证）→ 同配置按局数收敛（n≥20），episode 记录器锚定动作序列供对拍 |

## 外部依赖

| 依赖 | 用途与边界 |
|---|---|
| kaggle-environments==1.33.0 | cabt（PTCG 引擎，252 行）+pyxis（GSK 引擎）；本地对战唯一裁判 |
| kaggle CLI 2.2.4（已鉴权） | 提交/榜单/episode 回放拉取；不用于抓规则外数据 |
| cabt API 文档（matsuoinstitute.github.io/cabt） | 接口语义参考（obs 三段/选项索引动作/deck 60 行） |
| Kaggle 数据页卡表（EN/JA PDF） | 默认牌组卡 ID 来源 |
| typst | m3 复盘报告编译 |
| 官方每日顶部对局导出（论坛） | 高分语料一手来源；未落地前以 leaderboard 回放替代（条目待办） |

**结果数据源**（fn-analyze 消费）：episode 回放=CLI 拉取落 `references/episodes/<episodeId>.json`+INDEX 登记；天梯读数=官方 leaderboard 页回读（μ 手抄入 metrics 带日期）；本地跑批=JSON 行落 `fn_work/runs/`。

## 范围外

（承蓝图 out_of_scope，不因实现顺手扩张）
- GSK pyxis 正赛（上线后另立战役或经用户确认扩蓝图）
- 奖金冲刺叙事（Playground 无现金；奖金诉求由 GSK 正赛承接）
- Battlecode 2027 / CodeCup 2027 参赛（仅情报跟踪）
- 对局期联网的智能体形态；多账号/评分操纵（禁令）
- 修改蓝图验收项语义（路径垫片对齐除外，见环境表末行）

## 变更记录

| 日期 | 变更 | 原因 |
|---|---|---|
| 2026-10-05 | 初版 12 条 R（R1-R12） | fn-grill 首轮草稿（前沿四问按已确认蓝图+D14 规则+kagriculture 先例推导） |
| 2026-10-05 | 撤回 software/ 入口垫片方案 | 用户裁决"结构以 fn-ladder 为主，严格按步走"——一切置于 fn_work/，蓝图 cmd 等价执行 |
| 2026-10-05 | **R5 验收门槛锚定标重校（待用户批准）** | 原"vs random≥0.9/vs first≥0.95"为 fn-grill 初值——实测发现 first 锚=强基线（引擎原序选满，自身≈0.85 胜 random），种子件（最傻但完整）定义上与 first 同水位，0.95 门槛必然失败=假完成陷阱。重校：vs random≥0.70（破损侦测线，v1=0.17/v3=0.07 均会被拦）+ vs first 平手带 [0.30,0.70]；差异化门槛移交 m2 资产层（语料定标后 A/B 判决）。依据=compete-strategy"验收数字自定标 vs 初值"纪律 |
| 2026-10-05 | grill 第一轮用户四问全按推荐落定 | ①环境=战役内 venv（Python 3.14.7+ke==1.33.0 锁版+异常+JSON 日志）；②粒度=全战役一棵函数树；③回放归宿=references/episodes/+INDEX；④蓝图 cmd 出入=fn_work 入口等价执行——必问八条至此全覆盖，前沿清空 |
