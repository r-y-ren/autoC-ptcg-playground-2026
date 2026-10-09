# history.md —— 历史表（已完成批次队列，只追加不删改）
> fn-implement 独占更新。每批次完成后尾部追加留痕。

| 完成日期 | 批次 | 任务/函数清单（含操作与来源说明） | 验收摘要 |
|---|---|---|---|
| 10-05 | B1 | shared×6: play_local_match/load_agent_callable/assert_no_network/write_runs_jsonl/index_source_anchors/render_dossier_md | 16 tests 绿+真局冒烟（first 2-0 random）落 runs；d76114cc |
| 10-05 | B2 | R1+R3×6: summarize_pool/run_judge_pool/serialize_episode/record_episode/first_divergence/diff_episode | 全套 37 绿；smoke_judge 入口实跑 40 局：自镜像 h2h 0.6 合格；**发现**：random 锚对 first 锚 9-1（锚点强度序反直觉，判决池首战即产出真读数）；修 play_local_match debug=False（agent 异常归引擎判 ERROR 不穿透；**B2 评审指认：此为计划外树外改动，入表补登记，且在 d665ad3e 时点引入 seat_swap 回归 1 例——36+1 而非 37 绿，断言修复随 B3 提交**）；修 summarize 测试断言笔误 |
| 10-05 | B3 | R2+R5×7: probe_engine_facts/build_engine_dossier/parse_observation/greedy_priority/load_default_deck/guard_rails/seed_agent | 42 tests 全绿；T1/T2 真跑产出（docs/methodology/）；种子件 greedy v1→v5 迭代链（0.17→0.38→0.07→0.80→0.82，教训=引擎选项次序即强基线）；**61 卡 deck 字面量 bug 测试逮住**；R5 门槛锚定标重校（requirements 变更记录，待用户批准） |
| 10-05 | B4+B5 | R4×4+R6×3 | 45 tests 绿；submission.tar.gz 真打包（结构+沙箱自对弈双 OK，配额记账生效）；首提 403（账号未接赛事规则→用户动作项）；采集链 mock 流水线绿（去重/INDEX/失败隔离） |
| 10-05 | B6+B7 | R7×4+R8×5（P1） | 49 tests 绿；对手池：12 局 first-vs-random 真回放聚出多原型+克制矩阵；资产开采：T3 规格书可复跑（同输入同输出）+方向性样本标注；play_local_match steps 增补 option_types/state 字段（B6/B7 前置，向后兼容） |
| 10-05 | B8-B10 | R9×10+R10×3+R11×3+R12×2 | 全套 58 tests 绿；五层装配+AB 判决 12 折全链真跑；metrics 分片对接全局 merge_metrics；GSK 预研包真跑（版本锁+T1/T2+do-nothing 地板）+探活 not-live 双证；B3-B7 评审四高危修复收口（对齐率反转/fetch 契约/pack 入口/漂移断言）——53/53 函数全 wired，桩 0 |
