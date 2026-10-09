# 责任文档：PTCG Playground 方法论实战（compete-strategy v18 首战）

> 由 fn-divide 产出与独占更新；fn-implement 只读。进度与状态见 implementation.md。
> 职责字段是**重写规约**：凭职责详述 + 签名意图（输入/输出），必须能完美复现该函数功能。
> ⚠ 实现期发现结构性变化（函数增/删/拆/并/职责或调用关系变化）时，必须回到 fn-divide 改本文档。

## 结构概览（纯结构，不带职责）

- run_judge_pool ← R1
  - summarize_pool
- build_engine_dossier ← R2
  - probe_engine_facts
- record_episode ← R3
  - serialize_episode
- diff_episode ← R3
  - first_divergence
- pack_submission ← R4
  - validate_bundle_structure
  - sandbox_selfplay_once
  - count_daily_quota
- seed_agent ← R5
  - parse_observation
  - greedy_priority
  - load_default_deck
- fetch_episodes ← R6
  - kaggle_cli_pull
  - convert_official_replay
  - dedup_register
- cluster_opponents ← R7
  - extract_behavior_features
  - cluster_prototypes
  - build_counter_matrix
- mine_assets ← R8
  - filter_high_scores
  - aggregate_state_action
  - measure_alignment
  - emit_asset_spec
- assemble_agent_v2 ← R9
  - observe_opponent
  - decide_tempo
  - schedule_resources
  - follow_asset_table
  - guard_rails
- run_ab_judgment ← R9
  - ab_pair_configs
  - net_delta_j
  - pooled_winrate
  - append_registry_row
- prepare_metrics_shards ← R10
  - collect_runs_shards
  - validate_ladder_readback
- build_gsk_prestudy ← R11
  - load_pyxis_env
  - gsk_judge_smoke
- probe_gsk_launch ← R12
  - check_competition_page
- shared/
  - play_local_match
  - load_agent_callable
  - assert_no_network
  - write_runs_jsonl
  - index_source_anchors
  - render_dossier_md

## 需求覆盖矩阵（P1 在 R 号后标注）

| 需求 | 顶层函数 |
|---|---|
| R1 | run_judge_pool |
| R2 | build_engine_dossier |
| R3 | record_episode |
| R3 | diff_episode |
| R4 | pack_submission |
| R5 | seed_agent |
| R6 | fetch_episodes |
| R7 [P1] | cluster_opponents |
| R8 [P1] | mine_assets |
| R9 | assemble_agent_v2 |
| R9 | run_ab_judgment |
| R10 | prepare_metrics_shards |
| R11 | build_gsk_prestudy |
| R12 | probe_gsk_launch |

## 共享函数（shared/：多顶层共用；矩阵挂全部受益需求）

- **play_local_match**（调用方：run_judge_pool, record_episode, run_ab_judgment, sandbox_selfplay_once）受益：R1/R3/R4/R9
  - 职责：执行一局本地 cabt 对战——给定双方 agent 可调用对象（或装载路径）、双方 deck、随机种子，调 `kaggle_environments.make("cabt")` 跑完，返回结构化局结果（胜方/分差/逐拍动作序列/终局状态）。逐拍动作序列按拍号对齐双方。单局异常（agent 抛错/超时）不向上抛，转为该局失败记录（含失败拍号与原因）。
  - 签名意图：输入: (agent_a, agent_b, deck_a, deck_b, seed) / 输出: MatchResult（含 steps 列表与 outcome；失败局 outcome="failed"+原因）/ 错误: 引擎初始化失败（deck 非法/配置错）抛异常
  - tested 策略：自有单测
  - 核验命令：测试: test_play_local_match
- **load_agent_callable**（调用方：play_local_match, pack_submission）受益：R1/R3/R4/R9/R5
  - 职责：从文件路径装载 agent 函数——模拟 Kaggle 线上装载语义（子目录装载/`/kaggle_simulations/agent/` 等价），返回可调用对象。装载失败报出精确原因（文件缺失/函数名不存在/import 报错原文）。
  - 签名意图：输入: (路径, 函数名="agent") / 输出: callable / 错误: 装载失败抛异常含原因
  - tested 策略：自有单测
  - 核验命令：测试: test_load_agent_callable
- **assert_no_network**（调用方：seed_agent, assemble_agent_v2）受益：R5/R9
  - 职责：静态自检——扫描给定 agent 源码目录 import 树，断言无 socket/http/requests/urllib 等网络模块（赛规禁联网）。命中即返回违规清单。
  - 签名意图：输入: (源码目录) / 输出: 违规模块列表（空=通过）/ 错误: 目录不存在抛异常
  - tested 策略：自有单测
  - 核验命令：测试: test_assert_no_network
- **write_runs_jsonl**（调用方：run_judge_pool, record_episode, run_ab_judgment, prepare_metrics_shards, probe_gsk_launch）受益：R1/R3/R9/R10/R12
  - 职责：把一行结构化结果 JSON 追加落 `fn_work/runs/<类别>-<日期>.jsonl`（自动建目录、原子追加、行含时间戳与来源标记）。
  - 签名意图：输入: (类别, dict) / 输出: 行文件路径 / 错误: 序列化失败抛异常
  - tested 策略：自有单测
  - 核验命令：测试: test_write_runs_jsonl
- **index_source_anchors**（调用方：build_engine_dossier, build_gsk_prestudy）受益：R2/R11
  - 职责：读引擎源码文件，按符号名/正则定位关键锚点（计分函数/交互点/失败语义/时间结构/观测构造/rng 调用），输出"符号→行号→源码行"索引表。
  - 签名意图：输入: (源码路径, 符号模式列表) / 输出: [{symbol, line, source_line}] / 错误: 文件不存在抛异常
  - tested 策略：自有单测
  - 核验命令：测试: test_index_source_anchors
- **render_dossier_md**（调用方：build_engine_dossier, build_gsk_prestudy）受益：R2/R11
  - 职责：把六问答案与锚点索引装配成 T1 世界参数表与 T2 受控坐标表的 Markdown 骨架（六问各一节、每结论行带 `文件:行号` 引用占位、T2 四级各含示例行）。只装配结构，结论文本由调用方提供。
  - 签名意图：输入: (六问答案 dict, 锚点索引, 输出路径) / 输出: 写盘的 T1/T2 文件路径对 / 错误: 模板字段缺失抛异常
  - tested 策略：自有单测
  - 核验命令：测试: test_render_dossier_md

## 功能块 run_judge_pool ← R1

本功能口实现本地判决池 v0（compete-strategy 第 1 步一等产出物）：对局组=自镜像（同一 agent 双席）+弱锚（first_agent）+随机锚（random_agent，cabt.py:73/79 自带），跑批输出胜率与自镜像校准值；单局失败隔离计数。验收=程序入口冒烟（蓝图 cmd `software/judge/smoke_judge.py` 以 fn_work 入口等价执行）：退出码 0、stdout 含 `self-mirror h2h`（值域 0.35–0.65，局数≥20）与各锚点胜率行。

- **run_judge_pool** [L0|新增]
  - 职责：编排判决池跑批——按配置（局数/池成员/deck/种子区间）逐配置调 play_local_match，汇总各成员胜局/失败局，调 summarize_pool 出读数并 write_runs_jsonl 落 runs/。stdout 打印摘要（自镜像 h2h 行+各锚胜率行）。失败局计入 failed 计数不中断整批。
  - 签名意图：输入: (config: 局数/成员表/deck 路径/seed 起) / 输出: PoolReport dict + stdout 摘要 / 错误: 配置非法（局数<1/成员空）抛异常
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_run_judge_pool（断言自镜像局数≥20、校准值打印、锚点胜率行存在）
  - **summarize_pool** [L1|新增]
    - 职责：把逐局结果聚合成读数——各成员胜率/平率/失败率、自镜像 h2h、平均分差与方差；输出可直接 JSON 化的 dict。
    - 签名意图：输入: [MatchResult] / 输出: {member→stats, self_mirror_h2h, n} / 错误: 空列表抛异常
    - 调用方：run_judge_pool
    - tested 策略：上游覆盖: run_judge_pool
    - 核验命令：上游覆盖: run_judge_pool

## 功能块 build_engine_dossier ← R2

本功能口产出引擎六问档案：T1 世界参数表与 T2 受控坐标表（cabt 引擎 252 行），每条结论带源码行号；答案不只读源码，还用 probe_engine_facts 的受控实验证实（非法动作行为/None 观测/随机源位置）。产物落 `docs/methodology/`（PTCG 两表）。

- **build_engine_dossier** [L0|新增]
  - 职责：编排六问档案生成——index_source_anchors 扫 cabt.py 出锚点表；probe_engine_facts 跑受控实验补证；人工/调用方提供六问结论；render_dossier_md 装配 T1/T2 写盘。T2 四级（可控/可影响/可观测不可推/不可控随机）各≥1 行，每行带 `cabt.py:行号`。
  - 签名意图：输入: (源码路径, 六问结论 dict, 输出目录) / 输出: (t1_path, t2_path) / 错误: 结论缺问抛异常
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_build_engine_dossier（六问各≥1 行、行号引用存在、T2 四级覆盖）
  - **probe_engine_facts** [L1|新增]
    - 职责：跑小受控实验验证六问答案——①非法动作索引提交后引擎行为（静默跳过 or 报错）②obs 三段为 None 的阶段（初始选卡）③同种子重放确定性（分叉点=随机源全集）。每实验输出"问题→观测→结论行（带复现命令）"。
    - 签名意图：输入: () / 输出: [{question, observation, conclusion, reproduce_cmd}] / 错误: 引擎不可用抛异常
    - 调用方：build_engine_dossier
    - tested 策略：上游覆盖: build_engine_dossier
    - 核验命令：上游覆盖: build_engine_dossier

## 功能块 record_episode ← R3（记录器）

本功能口把本地局落成与官方回放同构的 episode JSON。

- **record_episode** [L0|新增]
  - 职责：跑一局并序列化落盘——play_local_match 得 MatchResult，serialize_episode 转官方同构 JSON（逐拍双方动作+终局+配置），落 `fn_work/episodes/`（本地对拍基准局；天梯回放归 R6 的 references/episodes/）。
  - 签名意图：输入: (agent_a, agent_b, deck_a, deck_b, seed, 输出路径) / 输出: episode 文件路径 / 错误: 局失败（含失败拍）落失败标记不半写
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_record_episode
  - **serialize_episode** [L1|新增]
    - 职责：MatchResult→episode JSON 结构（metadata/配置/逐拍 steps[{step, action_a, action_b}]/outcome）；字段与官方回放命名对齐。
    - 签名意图：输入: MatchResult / 输出: dict（可 json.dump）/ 错误: steps 缺失抛异常
    - 调用方：record_episode
    - tested 策略：上游覆盖: record_episode
    - 核验命令：上游覆盖: record_episode

## 功能块 diff_episode ← R3（对拍器）

本功能口是复刻/调试的唯一可靠手段（compete-strategy 对拍纪律）：找两份 episode 的首个分叉拍。

- **diff_episode** [L0|新增]
  - 职责：装载两份 episode 并逐拍对比，输出首个分叉（拍号/A 的动作/B 的动作）；全程一致则分叉=None。格式不符报明确行号。
  - 签名意图：输入: (episode_a 路径, episode_b 路径) / 输出: {diverged: bool, step, action_a, action_b} 或 {diverged: false} / 错误: JSON 破损抛异常含行号
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_diff_episode（自对拍=一致；篡改一拍→分叉拍=篡改位）
  - **first_divergence** [L1|新增]
    - 职责：纯函数——两个 steps 序列逐拍对比，返回首个不等拍号（含长度不等处理：短者先尽=分叉在末拍后）。
    - 签名意图：输入: (steps_a, steps_b) / 输出: 拍号或 None / 错误: 序列空抛异常
    - 调用方：diff_episode, measure_alignment
    - tested 策略：上游覆盖: diff_episode
    - 核验命令：上游覆盖: diff_episode

## 功能块 pack_submission ← R4

本功能口产 Kaggle 提交包并自检：tar.gz（顶层 main.py+deck.csv，不嵌套）+结构校验+沙箱等价装载自对弈一局+每日配额记账（≤5）。

- **pack_submission** [L0|新增]
  - 职责：编排打包自检——count_daily_quota 先查当日余量（超限拒绝）；打包 main.py+deck.csv（及资产文件）为 submission.tar.gz；validate_bundle_structure 校验结构；sandbox_selfplay_once 模拟线上装载路径自对弈一局；stdout 输出 `tar structure OK` 与 `local self-play OK`。
  - 签名意图：输入: (源目录, 输出 tar 路径) / 输出: tar 路径 + 检查结论 / 错误: 结构非法或配额尽→非零退出码+原因
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_pack_submission（蓝图 cmd `software/pack_check.py` 以 fn_work 入口等价执行，退出码 0+两行 OK）
  - **validate_bundle_structure** [L1|新增]
    - 职责：解开 tar.gz 校验：顶层 main.py 存在、deck.csv 存在且 60 行纯数字、无嵌套目录包裹；违规项列清单。
    - 签名意图：输入: (tar 路径) / 输出: (ok: bool, 违规清单) / 错误: 文件不存在抛异常
    - 调用方：pack_submission
    - tested 策略：上游覆盖: pack_submission
    - 核验命令：上游覆盖: pack_submission
  - **sandbox_selfplay_once** [L1|新增]
    - 职责：把 tar 解到临时目录模拟 `/kaggle_simulations/agent/` 装载语义（load_agent_callable），自对弈一局（默认 deck 双方），断言 agent 全程不抛错不超时。
    - 签名意图：输入: (tar 路径) / 输出: (ok, 局结果摘要) / 错误: 装载失败抛异常含原因
    - 调用方：pack_submission
    - tested 策略：上游覆盖: pack_submission
    - 核验命令：上游覆盖: pack_submission
  - **count_daily_quota** [L1|新增]
    - 职责：读本地提交记账（runs/ 中当日打包记录），返回 (已用, 剩余)；剩余 0 时 pack_submission 拒绝。
    - 签名意图：输入: (日期, 默认今日) / 输出: (used, remaining) / 错误: 记账文件破损按 0 用量处理并告警
    - 调用方：pack_submission
    - tested 策略：上游覆盖: pack_submission
    - 核验命令：上游覆盖: pack_submission

## 功能块 seed_agent ← R5

本功能口是"最傻但完整"参赛件（蓝图 m1 原文）：贪心选项+默认牌组，纯本地推理，obs 缺失字段防御。

- **seed_agent** [L0|新增]
  - 职责：参赛主函数——parse_observation 解析 obs{logs, current, select}（任一段缺失/None 时走防御兜底：select 缺失→返回合法空选/首选项），greedy_priority 从合法 option 列表按手写优先级（进化>打点>抽牌>收尾，常量带血统标注）选 1..maxCount 个索引。无任何网络/文件副作用。
  - 签名意图：输入: obs dict（+可选 config） / 输出: list[int]（选项索引，长度≤maxCount）/ 错误: 永不抛错（防御层雏形：兜底返回）
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_seed_agent（对 random_agent 胜率≥0.9 n≥50；对 first_agent ≥0.95；None obs 各段不崩；assert_no_network 通过）
  - **parse_observation** [L1|新增]
    - 职责：obs 规范化——三段（logs/current/select）缺失补 None 标记；select 内 option 列表与 maxCount 提取；返回统一内部结构。
    - 签名意图：输入: obs dict / 输出: {logs, current, options, max_count, missing:[字段名]} / 错误: 不抛（缺什么标什么）
    - 调用方：seed_agent, assemble_agent_v2
    - tested 策略：上游覆盖: seed_agent
    - 核验命令：上游覆盖: seed_agent
  - **greedy_priority** [L1|新增]
    - 职责：（v5 语义，2026-10-05 fn-divide 快速通道回写）引擎原序选满 maxCount=first 语义基线；v1 手写优先级表经实测证伪（选项次序编码目标语义，重排=选错目标；迭代链见 greedy_priority.py 血统表）——偏离原序的决策必须待 m2 语料证据
    - 签名意图：输入: (options 列表, max_count) / 输出: list[int] 索引 / 错误: options 空返回 []
    - 调用方：seed_agent
    - tested 策略：上游覆盖: seed_agent
    - 核验命令：上游覆盖: seed_agent
  - **load_default_deck** [L1|新增]
    - 职责：产默认 60 卡 deck.csv——从引擎 `all_card_data()`（或数据页卡表）取官方示例牌组写 60 行纯数字文件。
    - 签名意图：输入: (输出路径) / 输出: deck 路径 / 错误: 卡数≠60 抛异常
    - 调用方：程序入口
    - tested 策略：上游覆盖: pack_submission
    - 核验命令：上游覆盖: pack_submission

## 功能块 fetch_episodes ← R6

本功能口把天梯回放（己方提交 episode+他队 leaderboard 回放）拉入 `references/episodes/` 并登记来源（D14 外部资料归宿）。

- **fetch_episodes** [L0|新增]
  - 职责：编排采集——kaggle_cli_pull 按 episodeId/榜单范围拉 JSON；dedup_register 去重（episodeId 集合存 runs/）并追加 references/episodes/INDEX.md 来源行（来源 URL+日期）。
  - 签名意图：输入: (episodeIds 或榜单范围) / 输出: (新入库数, 跳过重复数) + INDEX 行 / 错误: CLI 失败重试 1 次后报错不中断其余
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_fetch_episodes（mock CLI 拉取≥1 条→存盘+INDEX 登记行存在）
  - **kaggle_cli_pull** [L1|新增]
    - 职责：封装 kaggle CLI 调用（子进程）拉指定 episode JSON/榜单列表，带限速（same_host 间隔）与失败重试 1 次。
    - 签名意图：输入: (目标描述) / 输出: [episode dict] / 错误: 重试后仍失败抛异常含 CLI stderr
    - 调用方：fetch_episodes
    - tested 策略：上游覆盖: fetch_episodes
    - 核验命令：上游覆盖: fetch_episodes
  - **convert_official_replay** [L1|新增]
    - 职责：（2026-10-05 fn-divide 快速通道新增，fna-001 落地）官方 replay JSON→内部 episode 同构格式（含 option_types/state 提取与双方 deck），供 B6/B7 管线直接消费
    - 签名意图：输入: (官方 replay 路径, 输出路径?) / 输出: 内部 episode 路径 / 错误: JSON 破损抛异常
    - 调用方：程序入口
    - tested 策略：上游覆盖: 真实语料转换实跑（11 局）
    - 核验命令：上游覆盖: references/episodes/conv/*.conv.json 产出
  - **dedup_register** [L1|新增]
    - 职责：episodeId 去重（对照历史集合）+INDEX.md 追加来源行（URL+抓取日期+局数）。
    - 签名意图：输入: (episodes, index 路径) / 输出: (新入库, 重复跳过) / 错误: INDEX 不可写抛异常
    - 调用方：fetch_episodes
    - tested 策略：上游覆盖: fetch_episodes
    - 核验命令：上游覆盖: fetch_episodes

## 功能块 cluster_opponents ← R7 [P1]

本功能口产对手池：episode→行为指纹→原型卡+对抗矩阵（compete-strategy 第 2 步）。

- **cluster_opponents** [L0|新增]
  - 职责：编排聚类——对 references/episodes/ 全集 extract_behavior_features 出指纹向量，cluster_prototypes 聚类成原型卡（画像 Markdown），build_counter_matrix 按对局胜负统计原型间克制关系出矩阵 CSV。同版本重跑原型数±1、成员漂移<10%。
  - 签名意图：输入: (episode 目录, 输出目录) / 输出: (原型卡路径集, matrix.csv 路径, 原型数) / 错误: 样本<10 抛异常（不足聚类）
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_cluster_opponents（≥50 局合成集→原型稳定重跑）
  - **extract_behavior_features** [L1|新增]
    - 职责：单 episode→指纹向量（开局 N 拍一致度/出牌节奏统计/资源结构占比），数值归一。
    - 签名意图：输入: episode dict / 输出: 向量 dict / 错误: 字段缺失跳过该局计 warn
    - 调用方：cluster_opponents
    - tested 策略：上游覆盖: cluster_opponents
    - 核验命令：上游覆盖: cluster_opponents
  - **cluster_prototypes** [L1|新增]
    - 职责：指纹集→聚类（K 由轮廓系数定）→每原型画像卡（典型开局/节奏/结构+成员数）。
    - 签名意图：输入: [指纹] / 输出: [原型卡 dict] / 错误: 全空输入抛异常
    - 调用方：cluster_opponents
    - tested 策略：上游覆盖: cluster_opponents
    - 核验命令：上游覆盖: cluster_opponents
  - **build_counter_matrix** [L1|新增]
    - 职责：按原型对原型对局胜率统计出克制矩阵（含对局数），写 CSV。
    - 签名意图：输入: (原型归属 map, episodes) / 输出: matrix.csv 路径 / 错误: 无跨原型对局输出空矩阵+告警
    - 调用方：cluster_opponents
    - tested 策略：上游覆盖: cluster_opponents
    - 核验命令：上游覆盖: cluster_opponents

## 功能块 mine_assets ← R8 [P1]

本功能口产查表资产（T3 规格书+血统表+逐拍对齐率；compete-strategy 第 6 步统计分支）。

- **mine_assets** [L0|新增]
  - 职责：编排资产开采——filter_high_scores 筛高分局；aggregate_state_action 统计局面-动作分布产候选查表；measure_alignment 对官方回放逐拍对齐率；emit_asset_spec 出 T3 规格书（生成器可复跑+每数字带样本量血统）。
  - 签名意图：输入: (episode 目录, 高分线, 输出目录) / 输出: (资产文件, 规格书, 对齐率) / 错误: 高分局<30 降级"方向性"标注继续产出
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_mine_assets（同输入重跑同输出；血统表每数字带 n）
  - **filter_high_scores** [L1|新增]
    - 职责：按终局分/胜方筛选高分 episode 子集，输出带入选原因（分位）。
    - 签名意图：输入: (episodes, 分位线) / 输出: [episode] / 错误: 空集返回空
    - 调用方：mine_assets
    - tested 策略：上游覆盖: mine_assets
    - 核验命令：上游覆盖: mine_assets
  - **aggregate_state_action** [L1|新增]
    - 职责：局面特征（场上宝可梦/手牌数/奖赏进度桶）×动作 分布统计→候选表（含每格样本量）。
    - 签名意图：输入: [episode] / 输出: 候选资产表 dict（每格带 n）/ 错误: 特征提取失败局跳过计数
    - 调用方：mine_assets
    - tested 策略：上游覆盖: mine_assets
    - 核验命令：上游覆盖: mine_assets
  - **measure_alignment** [L1|新增]
    - 职责：逐拍对齐率——对每局官方回放，用资产表驱动复刻决策，first_divergence 找分叉，对齐率=分叉拍/总拍；汇总分布。
    - 签名意图：输入: (资产表, [episode]) / 输出: {per_episode 对齐率, mean} / 错误: 单局失败跳过计数
    - 调用方：mine_assets
    - tested 策略：上游覆盖: mine_assets
    - 核验命令：上游覆盖: mine_assets
  - **emit_asset_spec** [L1|新增]
    - 职责：T3 规格书渲染——资产名/来源与样本/生成器命令/两个验收数字/待定标项；血统表每数字一行。
    - 签名意图：输入: (资产表, 统计元数据) / 输出: spec.md 路径 / 错误: 元数据缺验收数字抛异常
    - 调用方：mine_assets
    - tested 策略：上游覆盖: mine_assets
    - 核验命令：上游覆盖: mine_assets

## 功能块 assemble_agent_v2 ← R9（五层装配）

本功能口把资产装进五层结构（compete-strategy 第 7 步）：观测器（对手信息推断）/控制器（进攻-撤退-换位杠杆）/调度层（能量与进化时机=资源利用率）/清单层（执行资产查表）/防御层（净账护栏：非法动作自检、奖赏卡不落空、异常兜底）。

- **assemble_agent_v2** [L0|新增]
  - 职责：正式参赛主函数——parse_observation 规范化后依次过五层：observe_opponent 更新对手推断→follow_asset_table 查设定点→schedule_resources 定资源分配→decide_tempo 定战术动作→guard_rails 终检（动作合法性/自伤上限/兜底），输出最终选项索引。任一层内部异常由 guard_rails 兜底为合法首选项。
  - 签名意图：输入: obs dict（+资产文件路径常量） / 输出: list[int] / 错误: 永不抛错（防御层保证）
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_assemble_agent_v2（五层各自单测+全链对 random/first 胜率不低于种子件）
  - **observe_opponent** [L1|新增]
    - 职责：观测器——从公开信息（对手手牌数/牌库数/弃牌区/奖赏进度）推断对手类型（接原型卡库匹配），输出对手画像置信更新。
    - 签名意图：输入: (规范化 obs, 原型库) / 输出: {proto_id, confidence, 资源估计} / 错误: 原型库空返回 unknown 画像
    - 调用方：assemble_agent_v2
    - tested 策略：上游覆盖: assemble_agent_v2
    - 核验命令：上游覆盖: assemble_agent_v2
  - **decide_tempo** [L1|新增]
    - 职责：控制器——按对手画像与局面定战术倾向（抢攻/续航/换位）打分修正候选动作序。
    - 签名意图：输入: (规范化 obs, 对手画像, 候选动作) / 输出: 修正后候选序 / 错误: 不抛
    - 调用方：assemble_agent_v2
    - tested 策略：上游覆盖: assemble_agent_v2
    - 核验命令：上游覆盖: assemble_agent_v2
  - **schedule_resources** [L1|新增]
    - 职责：调度层——能量附着/进化时机/撤退成本的资源利用率决策（可计算段走查表，不在线求解）。
    - 签名意图：输入: (规范化 obs, 资产表) / 输出: 资源动作计划 / 错误: 不抛
    - 调用方：assemble_agent_v2
    - tested 策略：上游覆盖: assemble_agent_v2
    - 核验命令：上游覆盖: assemble_agent_v2
  - **follow_asset_table** [L1|新增]
    - 职责：清单层——按局面特征查资产表取设定点动作序（缺失格回退种子件贪心）。
    - 签名意图：输入: (规范化 obs, 资产表) / 输出: 动作序或 None / 错误: 表损坏返回 None 触发回退
    - 调用方：assemble_agent_v2
    - tested 策略：上游覆盖: assemble_agent_v2
    - 核验命令：上游覆盖: assemble_agent_v2
  - **guard_rails** [L1|新增]
    - 职责：防御层终检——动作索引合法性（不越 option 界）、数量≤maxCount、"我真执行了吗"自检标志、自伤上限（弃牌/损失阈值）；违规回退合法首选项。
    - 签名意图：输入: (候选动作, options, max_count, 局面) / 输出: 合法动作 list[int] / 错误: 不抛
    - 调用方：assemble_agent_v2, seed_agent
    - tested 策略：上游覆盖: assemble_agent_v2
    - 核验命令：上游覆盖: assemble_agent_v2

## 功能块 run_ab_judgment ← R9（A/B 判决）

本功能口是闭环迭代的心脏（compete-strategy 第 8 步）：单变量 A/B，双读数（净账 ΔJ+池内稳健胜率），T5 台账行。

- **run_ab_judgment** [L0|新增]
  - 职责：编排 A/B——ab_pair_configs 生成同种子双席对局组（A/B 各坐两席，fold=局数一半）；play_local_match 跑批；net_delta_j 与 pooled_winrate 出双读数；append_registry_row 落 T5 台账（pending→achieved/missed/reversed 由人判后 --set）。判负输出回滚建议。
  - 签名意图：输入: (agent_a, agent_b, pool 配置, fold 数≥12) / 输出: {net_delta_j, pooled_winrate_a, pooled_winrate_b, verdict_suggest} / 错误: fold<12 抛异常（尺子纪律）
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_run_ab_judgment（固定两版 agent→台账行含 net_delta_J 与 pooled_winrate；判负版标记 rollback）
  - **ab_pair_configs** [L1|新增]
    - 职责：生成对局组配置——同种子集 A/B 双席折叠（每种子两局，交换席位），deck 与池成员对齐判决池。
    - 签名意图：输入: (种子数, 池成员) / 输出: [MatchConfig] / 错误: 种子数<6 抛异常
    - 调用方：run_ab_judgment
    - tested 策略：上游覆盖: run_ab_judgment
    - 核验命令：上游覆盖: run_ab_judgment
  - **net_delta_j** [L1|新增]
    - 职责：净账计算——ΔA 得分 − ΔB 得分 − A 自伤项（弃牌/损失折算），按 fold 汇总均值与置信区间。
    - 签名意图：输入: [对局结果] / 输出: {mean, ci} / 错误: 空输入抛异常
    - 调用方：run_ab_judgment
    - tested 策略：上游覆盖: run_ab_judgment
    - 核验命令：上游覆盖: run_ab_judgment
  - **pooled_winrate** [L1|新增]
    - 职责：池内稳健胜率——对池内每原型对手分别胜率后取稳健口径（最差原型加权），非简单平均。
    - 签名意图：输入: (按原型分组对局结果) / 输出: {per_proto, robust} / 错误: 某原型 0 局该原型标 unknown 不计
    - 调用方：run_ab_judgment
    - tested 策略：上游覆盖: run_ab_judgment
    - 核验命令：上游覆盖: run_ab_judgment
  - **append_registry_row** [L1|新增]
    - 职责：T5 台账行追加（JSON registry：id/日期/现象/目标/预期信号/状态/判定出处），只追加不改历史。
    - 签名意图：输入: (registry 路径, 行 dict) / 输出: 行 id / 错误: 字段缺失抛异常
    - 调用方：run_ab_judgment
    - tested 策略：上游覆盖: run_ab_judgment
    - 核验命令：上游覆盖: run_ab_judgment

## 功能块 prepare_metrics_shards ← R10

本功能口把本地读数与官方回读汇聚成分片，对接全局 `scripts/verify/merge_metrics.py`（顶层 metrics.json 唯一写入者，不自建合并）。

- **prepare_metrics_shards** [L0|新增]
  - 职责：编排分片——collect_runs_shards 归集 runs/ 各类别读数出分片 JSON（键：pooled_winrate/net_delta_J_lastN/alignment_rate/prototype_count）；validate_ladder_readback 校验人工回读录入模板（ladder_mu/ladder_mu_date 必填带来源）；输出全局 merge_metrics 可消费的分片目录。
  - 签名意图：输入: (runs 目录, 回读录入文件) / 输出: 分片目录路径 / 错误: 回读缺日期/来源抛异常
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_prepare_metrics_shards（分片含全部键+每数字带 source 字段）
  - **collect_runs_shards** [L1|新增]
    - 职责：runs/*.jsonl 按类别聚合成指标分片（取最新 N 与分布），每指标带 source（来源 runs 文件+行号）。
    - 签名意图：输入: runs 目录 / 输出: [分片 dict] / 错误: 目录空返回空+告警
    - 调用方：prepare_metrics_shards
    - tested 策略：上游覆盖: prepare_metrics_shards
    - 核验命令：上游覆盖: prepare_metrics_shards
  - **validate_ladder_readback** [L1|新增]
    - 职责：校验天梯回读录入（μ 值/日期/官方页 URL 三要素齐全，值域合理），通过即转分片格式。
    - 签名意图：输入: 录入 dict / 输出: 分片 dict / 错误: 三要素缺一抛异常
    - 调用方：prepare_metrics_shards
    - tested 策略：上游覆盖: prepare_metrics_shards
    - 核验命令：上游覆盖: prepare_metrics_shards

## 功能块 build_gsk_prestudy ← R11

本功能口产 GSK 预研包：pyxis 装载+六问档案（pyxis.py 引用）+判决池 v0 冒烟（自镜像+内置 AI 若可编程接入；不可编程则跑自镜像并留人工实测记录模板）。

- **build_gsk_prestudy** [L0|新增]
  - 职责：编排预研——load_pyxis_env 装载与版本对拍；index_source_anchors+render_dossier_md 产 pyxis T1/T2（六问结论另附：定价=进入次序惩罚 1/n^α 等已核事实）；gsk_judge_smoke 自镜像跑批出噪声地板。蓝图 cmd `software/gsk_prestudy_check.py` 以 fn_work 入口等价执行。
  - 签名意图：输入: (输出目录) / 输出: (t1, t2, 冒烟读数) / 错误: pyxis 装载失败抛异常含原因
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_build_gsk_prestudy（T1/T2 存在+自镜像局跑通）
  - **load_pyxis_env** [L1|新增]
    - 职责：`make("pyxis")` 装载+与官方 wheel 版本一致性断言（锁 1.33.0），输出环境能力描述（观测/动作接口形态）。
    - 签名意图：输入: () / 输出: env 描述 dict / 错误: 版本不符或装载失败抛异常
    - 调用方：build_gsk_prestudy
    - tested 策略：上游覆盖: build_gsk_prestudy
    - 核验命令：上游覆盖: build_gsk_prestudy
  - **gsk_judge_smoke** [L1|新增]
    - 职责：pyxis 自镜像局 N≥20 出 h2h 校准；内置 AI 对手若引擎侧可编程接入则加锚点局，否则在产物中留人工实测模板（gsk.ai/play N 局手记）。
    - 签名意图：输入: (局数) / 输出: {self_mirror_h2h, builtin_ai: 自动或"manual-template"} / 错误: 局失败隔离计数
    - 调用方：build_gsk_prestudy
    - tested 策略：上游覆盖: build_gsk_prestudy
    - 核验命令：上游覆盖: build_gsk_prestudy

## 功能块 probe_gsk_launch ← R12

本功能口每日探活 GSK 赛站，上线即提示四页核验。

- **probe_gsk_launch** [L0|新增]
  - 职责：编排探活——check_competition_page 双通道探测（kaggle CLI competitions list 查询+赛站 HTTP 状态），结果 write_runs_jsonl 落 runs/；上线（任一通道见 gsk-simulation）时 stdout 打核验清单提示（rules/timeline/prizes/evaluation 四页）。
  - 签名意图：输入: () / 输出: {status: "not-live"|"live", evidence} + runs 行 / 错误: 网络失败重试 1 次后落 "unknown" 不抛
  - 调用方：程序入口
  - tested 策略：自有单测
  - 核验命令：测试: test_probe_gsk_launch（mock 双通道→not-live 输出+退出码 0）
  - **check_competition_page** [L1|新增]
    - 职责：单次双通道探测——CLI 查询 gsk/pyxis 关键词+赛站 HTTP 状态码，返回证据（命令/状态码/时间）。
    - 签名意图：输入: () / 输出: {cli: …, http: …, ts} / 错误: 不抛（失败信息入证据）
    - 调用方：probe_gsk_launch
    - tested 策略：上游覆盖: probe_gsk_launch
    - 核验命令：上游覆盖: probe_gsk_launch
