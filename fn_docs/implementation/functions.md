# functions.md —— 函数级实现清单（唯一状态真值）
> fn-implement 独占更新。**代码是真值，本表只是导航。**
> **改任何状态前必须先跑核验命令、在对话中贴出输出，绿了才许改。**

| 函数 | 批次 | 状态(日期) | 核验命令+摘要 | commit |
|---|---|---|---|---|
| play_local_match | B1 | wired 10-05 | pytest tests/shared → 16 passed（含真局/席位对换/bo1）；b1-smoke 真局落 runs | d76114cc |
| load_agent_callable | B1 | tested | pytest -k load_agent → 4 passed | d76114cc |
| assert_no_network | B1 | tested | pytest -k assert_no_network → 4 passed | d76114cc |
| write_runs_jsonl | B1 | tested | pytest -k write_runs → passed（reload 环境变量隔离） | d76114cc |
| index_source_anchors | B1 | tested | pytest -k index_source → 2 passed | d76114cc |
| render_dossier_md | B1 | tested | pytest -k render_dossier → 2 passed（六问+四级断言） | d76114cc |
| summarize_pool | B2 | tested | 上游覆盖: test_run_judge_pool | — |
| run_judge_pool | B2 | wired 10-05 | pytest -k run_judge_pool + entries/smoke_judge 实跑 40 局（自镜像 h2h 0.6∈[0.35,0.65]） | 见B2 commit |
| serialize_episode | B2 | tested | 上游覆盖: test_record_episode | — |
| record_episode | B2 | wired 10-05 | pytest -k record_episode（真局落盘回读+失败标记） | 见B2 commit |
| first_divergence | B2 | tested | 上游覆盖: test_diff_episode（纯函数 4 例） | — |
| diff_episode | B2 | wired 10-05 | pytest -k diff_episode（自对拍一致+篡改定位+破损行号） | 见B2 commit |
| probe_engine_facts | B3 | tested | 上游覆盖: test_build_engine_dossier（三实验实证：非法判负/同种子不可复现/None 观测） | 见B3 commit |
| build_engine_dossier | B3 | wired 10-05 | pytest + 真跑：docs/methodology/t1+t2 产出（六问行号+受控实验证据节） | 见B3 commit |
| parse_observation | B3 | tested | 上游覆盖: test_seed_agent（None/缺段/满段） | 见B3 commit |
| greedy_priority | B3 | tested | test_seed_agent v5 语义+血统表含 v1-v5 迭代链 | 见B3 commit |
| load_default_deck | B3 | tested | deck.csv 60 行纯数字（引擎源直读） | 见B3 commit |
| guard_rails | B3 | tested | 上游覆盖: test_seed_agent（越界/去重/minCount 补足/兜底） | 见B3 commit |
| seed_agent | B3 | wired 10-05 | 锚定标门槛 v2：vs random 0.82/vs first 0.52（60 局）通过；**61 卡字面量 bug 被测试逮住修复**（[3]*34→33） | 见B3 commit |
| validate_bundle_structure | B4 | tested | 上游覆盖: test_pack_submission（好/嵌套包） | 见B4/B5 commit |
| sandbox_selfplay_once | B4 | tested | 真包解包装载自对弈 OK | 见B4/B5 commit |
| count_daily_quota | B4 | tested | 5 限/记账/破损容错 | 见B4/B5 commit |
| pack_submission | B4 | wired 10-05 | entries 等价+真打包双 OK（配额 1/5）；提交 403=账号未接规则（用户动作项） | 见B4/B5 commit |
| convert_official_replay | B5+ | wired 10-05 | 真实语料 11 局转换实跑（fna-001 适配层） | 见迭代 commit |
| kaggle_cli_pull | B5 | tested | 上游覆盖: test_fetch_episodes（mock） | 见B4/B5 commit |
| dedup_register | B5 | tested | 去重+INDEX 登记行 | 见B4/B5 commit |
| fetch_episodes | B5 | wired 10-05 | mock 流水线绿（失败隔离+seen 持久化）；真实拉取待规则接受 | 见B4/B5 commit |
| extract_behavior_features | B6 | tested | 上游覆盖: test_cluster_opponents（first/random 双席真回放） | 见B6/B7 commit |
| cluster_prototypes | B6 | tested | 上游覆盖（K∈2-5 简化轮廓，稳定性±1 断言） | 见B6/B7 commit |
| build_counter_matrix | B6 | tested | 上游覆盖（CSV 产出断言） | 见B6/B7 commit |
| cluster_opponents | B6 | wired 10-05 | 12 局 first-vs-random 真回放聚出 ≥2 原型+稳定重跑+矩阵/原型卡产出 | 见B6/B7 commit |
| filter_high_scores | B7 | tested | 决出局+分位+快胜排序断言 | 见B6/B7 commit |
| aggregate_state_action | B7 | tested | 状态键-动作签名计数断言 | 见B6/B7 commit |
| measure_alignment | B7 | tested | 上游覆盖: test_mine_assets 端到端 | 见B6/B7 commit |
| emit_asset_spec | B7 | tested | T3 硬字段/血统表/可复跑断言 | 见B6/B7 commit |
| mine_assets | B7 | wired 10-05 | 8 局真回放端到端：规格书可复跑同输出+方向性标注正确 | 见B6/B7 commit |
| observe_opponent | B8 | tested | 上游覆盖: test_assemble_agent_v2 | 见B8-B10 commit |
| decide_tempo | B8 | tested | 上游覆盖（抢攻修正单规则） | 见B8-B10 commit |
| schedule_resources | B8 | tested | 上游覆盖（记录性计划） | 见B8-B10 commit |
| follow_asset_table | B8 | tested | 资产命中/缺格/损坏回退三断言 | 见B8-B10 commit |
| assemble_agent_v2 | B8 | wired 10-05 | 永不抛错+deck 相+60 局门槛（vs random≥0.70 过） | 见B8-B10 commit |
| ab_pair_configs | B9 | tested | 折叠数与下限异常断言 | 见B8-B10 commit |
| net_delta_j | B9 | tested | 均值/CI/折数断言 | 见B8-B10 commit |
| pooled_winrate | B9 | tested | maximin 稳健口径断言 | 见B8-B10 commit |
| append_registry_row | B9 | tested | T5 字段校验+只追加 | 见B8-B10 commit |
| run_ab_judgment | B9 | wired 10-05 | 全链 12 折真跑：双读数+verdict+registry 行；folds<12 拒绝 | 见B8-B10 commit |
| collect_runs_shards | B10 | tested | 末行快照+source 行号 | 见B8-B10 commit |
| validate_ladder_readback | B10 | tested | 三要素+合理域+ISO 日期 | 见B8-B10 commit |
| prepare_metrics_shards | B10 | wired 10-05 | 端到端分片目录产出（对接全局 merge_metrics） | 见B8-B10 commit |
| load_pyxis_env | B10 | tested | 版本锁 1.33.0 断言 | 见B8-B10 commit |
| gsk_judge_smoke | B10 | tested | do-nothing 地板 6/6 平局=噪声地板起点 | 见B8-B10 commit |
| build_gsk_prestudy | B10 | wired 10-05 | 入口真跑：env 锁定+T1/T2（1/n^α/PTRS/500 步回链）+冒烟 | 见B8-B10 commit |
| check_competition_page | B10 | tested | 上游覆盖（双通道证据） | 见B8-B10 commit |
| probe_gsk_launch | B10 | wired 10-05 | 真跑 not-live（cli=False, http=404）落 runs | 见B8-B10 commit |
