# PTCG 自动化复工包(2026-10-06 停摆时存档)

> 用户令"停止迭代,之后再开始"时存档。复工=新会话里 CronCreate(15min,minute interval)贴下述 prompt 原文即可。
> 停摆时现场:远程训练已 kill(30 进程→0,monitor.sh 仍在写心跳);天梯在榜 v9.1(μ375.5,队伍最高)+search v0.2(μ276.6,实验负结果留档);今日配额已用 1/5。

## 复工前必读(状态增量)

- fna-028/029:规则折叠 fold=rules 为代码默认(对在梯 0.700/老师 0.833 本地新高,v5 修复后四线均值 0.633);
- **天梯判决:search v0.2 μ276.6 < v9.1 μ375.5——本地锚池不代表战场**(指纹取证=搜索层生产确认活着,非静默降级);
- 未做的归因:①v9.2 贪心+META 牌组隔离诊断(1 配额,判"牌组坑 vs 策略坑")②真对手入池(94 局头部回放行为克隆,治本);
- 深度轴/权重轴已榨干(fna-027/028),对手模型补丁已证伪弃用(fna-026/027)。

## 自动化 prompt 原文(复工贴用)

PTCG 战役自动迭代(15min 快巡拍 + 2h 重活块状态门控)。**最高授权(用户 2026-10-06):允许自动修改自我大范围迭代,唯一目标=尽快 μ≥974,禁止拖延**——证据门放宽:单读数即可行动(尺子健康检查与 ≥30 局判提交两门保留),架构级改动不再停等人(改完记档即可),过线即交(日≤3,Kaggle 日上限 5)。

背景先读:memory/ptcg-playground-2026-campaign.md;workspace/ptcg-playground-2026/docs/methodology/layer-change-protocol.md;docs/methodology/search-lookahead-design.md;fn_docs/analyses/registry.jsonl。

【快巡块——每拍都做】(战役根 /mnt/data/Code/autoC/workspace/ptcg-playground-2026,venv=fn_work/.venv/bin/python,ssh wsl,kill 与 launch 分两次 ssh):
1. 三灯健康:ssh wsl 'cat ~/ptcg-train/status.txt'——进程数 0=按需拉起训练(先确认训练线是否仍要跑);日志新鲜度>300s=查因;CPU 负载<8=查任务粒度。
2. 收割触发:出现未判新 best(mtime 新于 `ls -t fn_work/runs/judge-pool-*.jsonl` 最新文件最新行 ts;判决文件按日期滚动,glob 全部)→scp 回 fn_work/weights/sil_best_new.json 立即严判。
3. 严判:`cd fn_work && .venv/bin/python entries/strict_judge.py <weights> <标签>`——内含 fna-013 尺子健康检查(FAIL 即中止先修装载),四线 30 局双席,出口 breakthrough_gate。
4. 强制判:距最新 judge-pool-*.jsonl 行 ts ≥50min 无新 best 也判当前版 sil_latest.json。
5. 判决分流:gate=true→进提交队列,重活块执行(过线即交,日≤3);未达→registry 记演进史。
6. 主线工作:每拍推进当前最高优先单变量(复工时先读 registry 尾部定优先级)。
7. 查 μ(严判后顺手):kaggle 回读≥974 → 删本自动化报告结束;鉴权失败=记录跳过(用户动作项:CLI 重登),勿刷屏。

【重活块——状态门控约 2h 一次】`ls --full-time fn_work/runs/heavy-stamp.txt` mtime>120min 才执行,收尾 `date > fn_work/runs/heavy-stamp.txt`:
a. cd /mnt/data/Code/autoC && git pull --rebase && python scripts/guard/contract_check.py。
b. 提交:队列有货且日<3 且未交同款→内联重建(exec 预验)→pack 自检→kaggle submit;鉴权挂=跳过记档。**注意:外发提交按最新纪律仍需用户明批(fna-029 后先例)**。
c. 语料增量顺手拉(鉴权挂=跳过);T5 落账;负结果照登。
d. JOURNAL.md 追加一行(勿覆盖)、commit+push;GSK 探活(CLI 挂看 HTTP)——live 停下报告用户。

纪律:数字只收实测(判决读数<30 局不作数);D14 圈禁;venv 必须 fn_work/.venv/bin/python;bash 绝对路径/带 cd 前缀;能做就做,不等不拖;**外发提交(比赛)与删除/覆盖既有成果须用户明批**。
