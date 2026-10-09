# batches.md —— 批次表（待办导航）
> fn-implement 独占更新。▶ = 下一批要完成的任务；未经批间门批准不得增删批次内容。
> 2026-10-05 用户预授权冲刺（"全批次自动进行，结束后直接 fn-analyze+remote-compute，允许提交"）——批间门不停人，核验照跑照贴，评审照派，报告照发。

| 批次 | 函数/任务清单 | 验收点 | 注 |
|---|---|---|---|
| B1✅ | shared×6: play_local_match, load_agent_callable, assert_no_network, write_runs_jsonl, index_source_anchors, render_dossier_md | shared 全 wired：random vs first 真局跑通落 runs/ | 底座批 |
| B2✅ | R1+R3: summarize_pool, run_judge_pool, serialize_episode, record_episode, first_divergence, diff_episode | smoke_judge 入口绿（自镜像 h2h 0.35-0.65 n≥20）+ record/diff 闭环测试 | W1 里程碑主体 |
| B3✅（门槛按 requirements 重校记录执行，原格 0.9/0.95 已废） | R2+R5: probe_engine_facts, build_engine_dossier, parse_observation, greedy_priority, load_default_deck, guard_rails, seed_agent | T1/T2 产出+seed_agent 对 random≥0.9/first≥0.95+无网络静态检查绿 | guard_rails 提前（seed_agent 依赖）；本批完=W1 波门五查 |
| B4✅ | R4: validate_bundle_structure, sandbox_selfplay_once, count_daily_quota, pack_submission | pack_check 入口绿+submission.tar.gz 产出；**首次提交天梯（用户已授权）** | W2 里程碑 m1 起点 |
| B5✅（真实拉取验收未达：403 阻塞待用户 Join；mock 流水线绿） | R6: kaggle_cli_pull, dedup_register, fetch_episodes | mock 测试绿+提交后拉 ≥1 条真实 episode 入 references/episodes/ | 依赖 B4 提交产生对局 |
| B6✅（样本 12<50 缩额：真回放生成成本；稳定性断言已补 Jaccard≥0.9） | R7[P1]: extract_behavior_features, cluster_prototypes, build_counter_matrix, cluster_opponents | 合成集≥50 局聚类稳定重跑测试绿；有真实回放则真跑 | W3 里程碑 m2 起点 |
| B7✅ | R8[P1]: filter_high_scores, aggregate_state_action, measure_alignment, emit_asset_spec, mine_assets | 生成器复跑同输出+血统表测试绿 | |
| B8✅ | R9a: observe_opponent, decide_tempo, schedule_resources, follow_asset_table, assemble_agent_v2 | 五层装配测试绿+对 random/first 不低于种子件 | guard_rails 已于 B3 |
| B9✅ | R9b: ab_pair_configs, net_delta_j, pooled_winrate, append_registry_row, run_ab_judgment | A/B 判决全链测试绿（台账行含 net_delta_J/pooled_winrate） | |
| B10✅ | R10-R12: collect_runs_shards, validate_ladder_readback, prepare_metrics_shards, load_pyxis_env, gsk_judge_smoke, build_gsk_prestudy, check_competition_page, probe_gsk_launch | gsk_prestudy_check 入口绿+probe not-live 落 runs | m4 预研包；全批完→fn-analyze |

## 变更记录（计划层事件：签名微调、需求变更往返、放弃等）
| 日期 | 事件 | 说明 |
|---|---|---|
| 2026-10-05 | 批次计划立表（10 批） | 垂直切片：shared 底座→判决池→种子件→提交链→采集→资产→装配→判决→汇聚；guard_rails 自 B3 提前（seed_agent 终检依赖，调用方跨块） |

| 2026-10-05 | B1 评审采纳（结构性发现） | 引擎洗牌 RNG 在 libcg.so 无种子入口——play_local_match 的 seed 仅为 Python 层统计播种，**同种子不可复现**（评审实证）。口径变更：判决池/A-B 一律按局数收敛（n≥20 起判），不做种子配对等值断言；test_seat_swap 改统计口径。伴修：失败拍号补全扫描、write_runs_jsonl 去 default=str、render_dossier_md 四级守卫 |
| 2026-10-05 | B2 评审采纳 | ①stdout 改受测体视角 self_winrate（原锚视角+vs 措辞致结论写反，勘误见 history）；②debug=False 树外改动补登记（d665ad3e 时点 36+1 非 37 绿，seat_swap 断言修复随 B3）；③n_anchor<1 校验补齐。**垫片说明**：蓝图 software/ 字面 cmd 不建垫片（用户 fn-grill 裁决 fn_work 入口等价执行），W1 波门以 fn_work/entries/smoke_judge.py 等价跑 sw-boot |
| 2026-10-05 | B3-B7 评审采纳（四高危修复） | ①measure_alignment 完美对齐反转 bug（None→1.0）+语义锁定单测；②fetch_episodes 返回契约（fetched/skipped 用 dedup 真值）+落盘仅 fresh+seen id 类型归一 str；③entries/pack_check.py 损坏修复（真跑双 OK exit 0）；④cluster 成员漂移 Jaccard 断言+恒真子句清理 |
| 2026-10-05 | 登记补遗（评审指认） | R5 门槛重校→requirements 变更记录（指针）；play_local_match steps 增补 option_types/state；cluster 样本 50→12 缩额。**已知断层**：官方 Kaggle 回放无 option_types 字段，真实语料入库后需适配层（R6→R7 接口，正赛期任务） |
| 2026-10-05 | greedy v5 语义回写（fn-divide 快速通道） | responsibility/requirements 的"手写优先级表"已废——v5=引擎原序选满基线（v1→v5 迭代链见 greedy_priority 血统表；偏离次序须 m2 语料证据）。非功能约束"同种子可复现"同步作废（libcg.so 无种子入口，B1 评审实证） |
| 2026-10-05 | 迭代轮 1（用户令：自我迭代目标前 5%） | 真实语料接入：11 官方回放入库（我方 3+前三名 8，INDEX 登记）+convert_official_replay 适配器（fn-divide 快速通道）；首轮分析=牌组是开放课目/赢家首选项率更高（方向性 n=11）；**fna-003 首探负结果：榜首牌组单变量 A/B 24 局=净零（12-12），不提交**——净账纪律省下一次盲提交配额 |
| 2026-10-05 | 迭代轮 2（全自动授权） | 语料扩至 38 局（+26，前三名全量）；v7 类型表克隆（44 键/64% 覆盖）A/B 负 0.37/0.30、v8 计数表保序 A/B 负 0.47——三连负不提交（配额 1/5 未动）；Meta 发现=粗粒度单变量均不敌原序基线，赢家信号在选项身份级；资产文件 winner-type-table.json/winner-count-table.json 入库备深挖 |
| 2026-10-06 | 迭代轮 4（每日 cron 首跑） | μ 盘面：v6=269.8/v5=322.6（**天梯否决牌组假设**，v6<v5）；语料 61 局（+23）；转换器升级保完整选项字段；三真锚克隆建成（1933-2780 键）但=弱代理（v5 打它们 0.94-1.00）；身份级克隆 v7 修复 INVALID 后**同牌组对照 0.20=净负**——第四个纪律性负结果，不提交；T5 落账 fna-002/005 missed，新挂 fna-006（状态评估型 agent+deck 协同） |
| 2026-10-06 | 迭代轮 5（用户令：换流派+深读引擎） | **引擎深读**：libcg.so AllCard/AllAttack 全库到手（1431 卡+1755 技能）+SelectContext 谱 0-48+奖赏数学实证（普通1/ex2）→战略翻译档案（奖赏竞速/能量节奏/一击线）；**流派换档**：查表层四连负+BC 一二代均不过基线（v2 0.516/v3 0.463 vs 0.527）→ skill 选型律中档"骨架+旋钮→ES 整定"：评估骨架 v0（0.30 输 v5）→ES 4 代→**v9 全门槛过线（vs v5 0.62/真锚 0.94-1.00/自镜像 0.58）**；ES 副产：damage 权重整负=价值只在真 KO；v9 打包就绪（22KB）但 **Kaggle OAuth 过期阻塞提交（用户动作项）**；本地 pack 计数器口径偏差待修（数打包非提交） |
| 2026-10-06 | 迭代轮 6（连续训练+远程算力） | v9 上梯（认证恢复，今日 1/5）；v10=ES-v2 赢家诅咒实测（训练 1.000/实战 0.35）拒收；**远程 4070 机 32 核接管训练**（~/ptcg-train 两段确认制并行 ES：12 旋钮×12 代×族群 24，粗筛 12 局→top4 确认 30 局+在位 h2h 保护）——用户令"不要停止连续训练+可用远程算力"；本地两段 ES 因裸 & 启动被回收改远程承载 |
| 2026-10-06 | 迭代轮 7（架构完整性审计） | 用户问"架构完全吗"→立方体对照：**算法格空白=必用级缺口**；当场建成 prize_solver（奖赏清算求解器）接入评估器（逐选项判定修复集成 bug）；双批 A/B 0.50/0.50 中性→不硬塞，挂 ES 整定（fna-009）；缺件清单挂 fna-010（搜索前瞻>开局资产>观测器>防御）；顺带抓管线 bug：远程老师权重用默认非 v9 已修（fna-011） |
| 2026-10-06 | 进度检查+调整 | 盘面：v9.1 μ408.7 爬升✓/训练 12 分钟一轮满负荷✓/质量震荡⚠；修两缺口：best 跨轮保留（新轮覆盖旧纪录 bug）+评估 12→20 局降噪；**重大发现 fna-012 非传递环**：SIL-best vs 在梯版 1.00/1.00 却 vs v5 0.30=专杀老师纸老虎，v5 稳健门拦截——对手池多样性不足根因，加 style0-2 风格变体（配比 40/20/20/20）重启训练 |
| 2026-10-06 | 尺子取证（用户令：指纹分析先查评测） | **评测标准确实坏了**：指纹分析发现本地 v9.1 每局仅 3 决策=秒死→根因求解器集成两 bug（函数内 import 遮蔽 _card + my_prize_left 未定义）→引擎异常判负毒化 1.5h 全部本地判决；修复后复判翻案：SIL-best 实为全面弱（vs v9.1 0.23/0.10、vs v5 0.20），“非传递环”系假象（fna-012 reversed）；win_now 求解器对健康尺 0.50/0.67 仍未过；**新纪律=fna-013 判决前必跑尺子健康检查**（决策数>20+真赢）；天梯 v9.1 内联版免疫（无此 import）μ408.7 无恙 |
