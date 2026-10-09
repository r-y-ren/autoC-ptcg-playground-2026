# T1 世界参数表（引擎六问）

| 六问 | 答案（带源码行号/实验证据） | 决定了什么 |
|---|---|---|
| 钱/分怎么算出来的？ | 100 步后净现金流（NCF）高者胜；破产即负（pyxis README；gsk.ai 官方公告 2026-10-05 实抓） | J=NCF 差；终局清算段可离线求解 |
| 对手在哪个函数里影响我？ | 共享适应症市场（收入 1/n^α 进入惩罚）+同批 BD 资产竞标+对手管线噪声情报 | 对手建模必选（市场耦合） |
| 失败怎么表达？ | ke 标准语义（agent 异常→ERROR 判负）；破产=引擎终局条件 | 防御层：现金护栏+动作掩码遵从 |
| 时间结构是什么？ | 100 行动步（开局前市场空转 500 步，时钟归零） | 按步规划；长视界资产化 |
| 谁能看见什么？ | PTRS 隐藏（1 次免费噪声读数+可购）；对手管线仅噪声情报 | 观测器=PTRS 估计（唯一深隐藏面） |
| rng 在哪几行被调用？ | 试验结果随机（PTRS 真值滚动）+资产到达均值回归过程 | 方差预算管试验段 |

## 源码锚点

- `^def ` → 第 38 行：`def _to_jsonable(value):`
- `^def ` → 第 53 行：`def _build_pyxis_env():`
- `^def ` → 第 87 行：`def _ta_index(therapeutic_area):`
- `^def ` → 第 104 行：`def _asset_key(asset):`
- `^def ` → 第 109 行：`def _ptrs_readings_config():`
- `ptrs` → 第 113 行：`    cfg = config.ptrs_readings`
- `^def ` → 第 117 行：`def _ptrs_readings(trial, cfg):`
- `ptrs` → 第 123 行：`    precision-weighted count, the one ``offset_ptrs_count`` normalises for`
- `ptrs` → 第 129 行：`    return cfg.effective_readings(trial.ptrs_total_precision)`
- `^def ` → 第 132 行：`def _ended_reason(gs):`
- `bankrupt` → 第 136 行：`    ``"bankrupt"``; a short key lets the viewer phrase it.`
- `^def ` → 第 149 行：`def _render_snapshot(game, known):`
- `cash` → 第 166 行：`    on: next step's trial bill (what triggers bankruptcy, invisible in the cash`
- `ptrs` → 第 174 行：`    readings_cfg = _ptrs_readings_config()`
- `revenue` → 第 189 行：`                    round(float(asset.max_revenue)),`
- `ptrs` → 第 202 行：`                    round(float(trial.ptrs), 3) if trial else 0,`
- `ptrs` → 第 205 行：`                    round(_ptrs_readings(trial, readings_cfg), 2),`
- `revenue` → 第 206 行：`                    # Every drug launches at a floor sized by its revenue, so the`
- `cash` → 第 224 行：`            "cash": round(float(gs.cash)),`
- `bankrupt` → 第 227 行：`            "bankrupt": bool(gs.bankrupt),`
- `cash` → 第 236 行：`            # acts; cash under this is bankruptcy. Investment levels and R&D`
- `cash` → 第 241 行：`            # Realised cash flow of the step just played, all sources.`
- `revenue` → 第 242 行：`            "revenue": round(float(gs.realised_revenues[-1])) if gs.realised_revenues else 0,`
- `revenue` → 第 260 行：`                "maxRevenue": round(float(a.max_revenue)),`
- `ptrs` → 第 263 行：`                "ptrs": round(float(a.trial.ptrs), 3) if a.trial else 0,`
- `^def ` → 第 298 行：`def _write_observations(state, pyenv, observations, known_assets):`
- `cash` → 第 307 行：`            obs.cash = float(gs.cash)`
- `bankrupt` → 第 309 行：`            obs.bankrupt = bool(gs.bankrupt)`
- `^def ` → 第 315 行：`def _outcomes(pyenv, cum):`
- `^def ` → 第 339 行：`def _finish(state, outcomes):`
- `^def ` → 第 346 行：`def _coerce_for_space(space, action):`
- `^def ` → 第 369 行：`def _masked_head_illegal(mask, values):`
- `^def ` → 第 395 行：`def _normalize_action(pyenv, aid, action):`
- `^def ` → 第 437 行：`def _forfeit(state, env, loser_seats):`
- `^def ` → 第 449 行：`def interpreter(state, env):`
- `^def ` → 第 510 行：`def renderer(state, env):`
- `cash` → 第 515 行：`            f"{aid}: cash={obs.cash:,.0f} enpv={obs.enpv:,.0f} "`
- `bankrupt` → 第 516 行：`            f"bankrupt={obs.bankrupt} status={state[i].status} reward={state[i].reward}"`
- `^def ` → 第 521 行：`def html_renderer(env, mode):`
- `^def ` → 第 530 行：`def _make_baseline(spec_name):`
- `rng|random` → 第 555 行：`    "random": _make_baseline("random"),`
