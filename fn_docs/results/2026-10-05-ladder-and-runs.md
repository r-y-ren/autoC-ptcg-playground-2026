# 结果快照 2026-10-05（fn-analyze 数据源拉取）

## 天梯提交状态
     ref  fileName           date                        description                                                                status                    publicScore  privateScore  
--------  -----------------  --------------------------  -------------------------------------------------------------------------  ------------------------  -----------  ------------  
56831987  submission.tar.gz  2026-10-04 19:10:58.477000  seed v5: engine-order baseline + guardrails (compete-strategy cold-start)  SubmissionStatus.PENDING                             

## episode 列表（首提后）
usage: kaggle competitions episodes [-h] [-v | --format OUTPUT_FORMAT] [-q]
                                    submission_id
kaggle competitions episodes: error: argument submission_id: invalid int value: 'the-pokemon-company-ptcg-ai-battle-challenge-playground'

## 本地 runs 汇总
--- fn_work/runs/ab-judgment-2026-10-05.jsonl
{"ts": "2026-10-05T02:54:08", "category": "ab-judgment", "net_delta_J": {"A": {"mean": -0.3333, "ci95": 1.1654, "n_folds": 12}, "B": {"mean": -1.0, "ci95": 1.0236, "n_folds": 12}}, "pooled_winrate": {"A": {"per_proto": {"random": 0.4167}, "robust": 0.4167}, "B": {"per_proto": {"random": 0.25}, "robust": 0.25}}, "verdict_suggest": "keep-A", "config": {"folds": 12, "members": ["random"], "bo": 1}}
--- fn_work/runs/b1-smoke-2026-10-05.jsonl
{"ts": "2026-10-05T02:32:47", "category": "b1-smoke", "seed": 1, "rewards": [1, -1], "n_steps": 71, "wins": [2, 0, 0]}
--- fn_work/runs/cluster-opponents-2026-10-05.jsonl
{"ts": "2026-10-05T03:10:21", "category": "cluster-opponents", "n_prototypes": 2, "n_episodes": 12, "prototype_ids": [0, 1]}
{"ts": "2026-10-05T03:10:21", "category": "cluster-opponents", "n_prototypes": 2, "n_episodes": 12, "prototype_ids": [0, 1]}
--- fn_work/runs/gsk-prestudy-2026-10-05.jsonl
{"ts": "2026-10-05T03:05:59", "category": "gsk-prestudy", "env": {"version": "1.33.0", "agents": [2], "episodeSteps_default": 1000, "runTimeout_default": 1200}, "smoke": {"self_mirror_h2h": null, "decided": 0, "draws": 6, "failed": 0, "n_games": 6, "builtin_ai": "manual-template"}}
{"ts": "2026-10-05T03:10:20", "category": "gsk-prestudy", "env": {"version": "1.33.0", "agents": [2], "episodeSteps_default": 1000, "runTimeout_default": 1200}, "smoke": {"self_mirror_h2h": null, "decided": 0, "draws": 6, "failed": 0, "n_games": 6, "builtin_ai": "manual-template"}}
--- fn_work/runs/gsk-probe-2026-10-05.jsonl
{"ts": "2026-10-05T02:59:14", "category": "gsk-probe", "status": "not-live", "evidence": {"ts": "2026-10-05T02:59:11", "cli": {"found": false, "stdout_head": "No competitions found\n"}, "http": {"status": 404}}}
--- fn_work/runs/judge-pool-2026-10-05.jsonl
{"ts": "2026-10-05T02:34:37", "category": "judge-pool", "members": {"self": {"win": 32, "loss": 28, "draw": 0, "failed": 0, "n": 60, "winrate": 0.5333}, "first": {"win": 7, "loss": 3, "draw": 0, "failed": 0, "n": 10, "winrate": 0.7}, "random": {"win": 1, "loss": 9, "draw": 0, "failed": 0, "n": 10, "winrate": 0.1}}, "self_mirror_h2h": 0.6, "self_mirror_decided": 20, "n": 40, "reward_mean": 0.0, "reward_stdev": 1.0, "config": {"n_mirror": 20, "n_anchor": 10, "bo": 3, "anchors": ["first", "random"]}}
--- fn_work/runs/metrics-shards-2026-10-05.jsonl
{"ts": "2026-10-05T02:56:55", "category": "metrics-shards", "n_shards": 2, "out_dir": "/tmp/pytest-of-renyxin/pytest-148/test_prepare_end_to_end0/shards"}
--- fn_work/runs/mine-assets-2026-10-05.jsonl
{"ts": "2026-10-05T03:08:41", "category": "mine-assets", "n_kept": 4, "n_total": 8, "alignment_mean": 0.0717, "directional": true, "spec": "/tmp/pytest-of-renyxin/pytest-154/test_mine_assets_end_to_end0/out/state-action-table-q50.md"}
{"ts": "2026-10-05T03:08:41", "category": "mine-assets", "n_kept": 4, "n_total": 8, "alignment_mean": 0.0717, "directional": true, "spec": "/tmp/pytest-of-renyxin/pytest-154/test_mine_assets_end_to_end0/out2/state-action-table-q50.md"}
--- fn_work/runs/pack-quota-2026-10-05.jsonl
{"ts": "2026-10-05T02:47:31", "category": "pack-quota", "tar": "submission.tar.gz", "ok": true, "issues": [], "force": false}
{"ts": "2026-10-05T03:04:26", "category": "pack-quota", "tar": "submission.tar.gz", "ok": true, "issues": [], "force": false}
