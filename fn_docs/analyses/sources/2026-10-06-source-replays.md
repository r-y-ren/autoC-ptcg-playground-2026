# 93 局官方回放游戏规则实证挖掘（引擎行为一手证据）

- 抓取/挖掘日期：2026-10-06
- 数据来源：`references/episodes/episode-*-replay.json`（kaggle-environments 1.33.0 cabt 官方回放，**93 个**；目录另有 1 个 `episode-118265080-agent-0-logs.json` 为 agent 日志非回放，是"94 个 json"错觉的来源）
- 卡牌/技能库：`references/engine/cabt-cards.json`（1431 张）、`cabt-attacks.json`（1755 条）
- 挖掘脚本：`fn_work/tmp/replay_mine/`（mine_all / analyze / diag2-6 / final1-3），全部纯离线解析，无模型参与
- 对照基准：`docs/methodology/engine-deep-parse.md`（61 局档案，2026-10-06）；61 局子集由 `references/episodes/conv/*.conv.json`（61 个）精确圈定

## 0. 数据口径与解码基础（先立尺）

| 事实 | 读数 | 依据 |
|---|---|---|
| 93 个回放 = **93 场 bo3 对局** | 共 **222 个 game**（57 场 2-0 → 2 game；36 场 2-1 → 3 game） | `configuration.bo=3`；每 game 一条 `Result` 日志，93 文件合计 222 条 |
| 胜负判定信号 | `visualize` 流内 `Result` 日志 `{reason, result}`（result=胜方 playerIndex） | 222/222 game 均有 Result，无中断局 |
| 命名日志流 | `steps[0][0].visualize`：每步 1 帧，含 `logs`(命名)/`select`(命名 context)/`selected`/`action`/`current`(全量含卡名) | 事件词表：TurnStart/TurnEnd/Draw/Play/Attach/Evolve/Switch/Attack/HpChange/MoveCard/Shuffle/Coin/HasBasicPokemon/Result |
| **帧语义（关键）** | `viz[i].selected` = 对 `viz[i-1].select` 的应答；`viz[i].logs` = 该应答的结算；`viz[i].select` = 结算后新的待选 | 逐帧推演验证（Drakloak 链/Phantom Dive 6 指示物案例）；错位配对会产生"一回合多次攻击"等假象 |
| 观测流与 viz 对齐 | `viz[i].action == steps[i+1][j].action`（viz 领先 1 步）；观测侧 `select.context` 为数值枚举，viz 侧为名称 | 动作逐拍相等检验 |
| MoveCard 区位编码 | 1=deck 2=hand 3=discard 4=active 5=bench 6=prize 8=能量附着位 9=工具位 10=进化链下层 12=翻看区 14=丢失区 | 与状态量（handCount/prize/…）逐帧对账 |
| 决策归属 | 一帧的 `selected` 恰等于某一方 `action` → 该方为决策方 | 93 局全量 0 例外；kaggle `status==ACTIVE` 口径与之差 10.6%（见 §5 限界） |

## 1. 胜负结构

### 1.1 胜负 reason 分布（222 game）

| reason | 含义（61 局档案枚举） | 次数 | 占比 | 胜方=先手 | 胜方=后手 |
|---|---|---|---|---|---|
| 1 | 奖赏拿完 | 179 | 80.6% | 90 | 89 |
| 2 | 牌库空 | 2 | 0.9% | 0 | 2 |
| 3 | 无主动位（清场） | 41 | 18.5% | 19 | 22 |
| 4 | 卡效果直接胜利 | 0 | 0 | — | — |

- game 胜方：player0 111 / player1 111（完全均衡）。
- **先手 game 胜率 109/222 = 49.1%**（无先手优势）；首个 TurnStart 的 playerIndex==firstPlayer **222/222**（回合序确认）。
- 与 61 局档案对照：reason 枚举 1/2/3/4 一致；主路径=奖赏竞速（80.6%）与档案"主胜利路径=奖赏竞速"吻合，但**清场线（reason 3）占 18.5%**，远高于"罕见"直觉，应作为独立防线定价。

### 1.2 步数/回合分布

| 指标 | min | p25 | median | mean | p75 | max |
|---|---|---|---|---|---|---|
| 每 game 帧数（≈步数） | 21 | 123 | 152 | 145.6 | 180 | 248 |
| 每 game 回合数 | 2 | — | 11 | 11.2 | — | 26 |
| 每 episode 步数 | 65 | — | 341 | — | — | 645 |

全 corpus 合计 2496 个回合（TurnStart/TurnEnd 配对）。

## 2. 回合结构实证（每回合限 1 验证）

动作层=消耗的 Main 选项 pick（select[i-1]×selected[i] 正确配对）；事件层=命名日志。**"限 1"在动作层全数成立，事件层可被卡效果突破**：

| 项目 | 动作层每回合分布 | 事件层每回合分布 | 判定 |
|---|---|---|---|
| 能量附着（手动 ATTACH 动作，按卡型识别为能量） | **{1: 1975}**（2496 回合中 1975 回合用满 1 次，0 违例） | 能量 Attach 事件 {0:321, 1:1321, 2:361, 3:256, 4:210, 5:21, 6:4, 7:2} | **手动限 1 成立**；效果附着（能量加速）不受限，全 corpus 3794 次能量附着中约 1819 次为效果来源，单回合最高 7 次 |
| 工具附着 | {1: 149, 2: 1} | 工具 Attach {1: 149, 2: 1} | 无每回合限（观测上限 2） |
| 支援者 | — | Play(cardType 3) **{0: 809, 1: 1687}** | **限 1 成立**（2496 回合 0 违例，无效果豁免案例） |
| 竞技场 | — | {0: 2220, 1: 276} | **限 1 成立** |
| 撤退 | 手动 RETREAT 动作 **{1: 455}** | Switch 事件 {0:1544, 1:830, 2:116, 3:6} | **手动限 1 成立**（455 回合各恰 1 次）；效果换位不受限（约 675 次，单回合最高 3 次） |
| 攻击 | Attack 动作 **{1: 1763}** | Attack 事件 {1: 1763} | 每回合恰 1（攻击即回合结束），0 违例 |
| 进化 | {1:545, 2:310, 3:99, 4:41, 5:6} | Evolve 事件同形 | 无每回合限 |
| 道具 | — | item Play 最高 9/回合 | 无限 |

每回合行动数（引擎 `turnActionCount`，2496 回合）：分布 0–38，峰值 8（140 回合），中位 12，>20 的回合 459 个（18.4%）；事件数/回合（上表事件求和）分布 0–18，中位 5。**回合内编排空间远大于"四件套"**——大头是道具/能力/进化与效果链。

**先手首回合攻击：0/222**（先手首回合一例未出现攻击动作，规则成立）。后手首回合（turn idx1）攻击 92 次（规则允许）。

## 3. 奖赏实证

- 领奖以"帧内领取张数"计：**{1 张: 722 簇, 2 张: 354 簇, 3 张: 95 簇}**（1171 簇 / 1715 张；单帧最多 3 张，多 KO 簇合计可达 6 张）。
- KO 事件（顶层宝可梦离场入弃牌，按在场 serial 剔除进化链下层卡）：**1176 次 = normal 688 / ex 366 / megaEx 122**。
- **簇级验证（1110 个 KO/领取簇）：1049 簇（94.5%）严格满足 Σ奖赏值==领取张数**；61 个不一致簇**全部是"少领"**（59 个为该局最后簇=拿完即胜的终局截断；2 个 residual 为 normal KO 0 领取，未解释），**"多领"违例 0**。
- 奖赏值映射（干净单 KO 配对）：**normal→1**（629/649）、**ex→2**（307/353）、**megaEx→3**（86/118）；偏离项全部可由多 KO 簇内归属歧义 + 终局截断解释（例：Dragapult ex+Dreepy 同帧双 KO → 领 3 张=2+1 ✓；Meowth ex+Fezandipiti ex+Munkidori 三 KO → 领 5 张=2+2+1 ✓）。
- **结论：1/2/3 张规则为严格上界（normal/ex/megaEx），本 corpus 零反例**；等价杀伤需求维持 6 只普通 / 3 只 ex / 2 只 megaEx 的奖赏竞速骨架。
- 与 61 局档案对照：档案"普通 1、ex 2"+多 KO 3-6 张读数吻合；**新增修正：megaEx=3 张**（61 局档案未单列）。

## 4. 状态条件（5 种异常状态）

| 状态 | 施加次数 | 受影响 player-turn | 掉血模式 |
|---|---|---|---|
| confused 混乱 | 26（p0 11 / p1 15） | 52 | 自伤观测（攻击结算中对己方 HpChange 73 例，含文本反弹/混乱类） |
| poisoned 中毒 | **0** | 0 | 无样本 |
| burned 烧伤 | **0** | 0 | 无样本 |
| asleep 睡眠 | **0** | 0 | 无样本 |
| paralyzed 麻痹 | **0** | 0 | 无样本 |

- **93 局 222 game 里只出现过混乱**；毒/烧每回合伤害实测值**无样本缺口**（引擎字段存在且混乱标志可用，非字段失效）。
- 高频的 HpChange(−10, putDamageCounter=True) 1543 次**不是毒伤**：是"放置伤害指示物"效果（1 指示物=10 HP），例如 Dragapult ex "Phantom Dive"（200 伤+对手备战区任意分配 6 指示物）逐决策帧落 6×(−10)；另有 (−30) 84 次、(−20) 16 次同类。回合边界（TurnEnd/TurnStart 帧）出现的 −10 簇同样是效果结算，无中毒标志伴随。
- 非攻击 HpChange(putDamageCounter=False)：−30×18 及 −70/−100/−130/−140/−150/−210/−280/−300/−330/−350 各若干，为效果直伤。

## 5. 选择场景谱（SelectContext，win/lose 侧分开）

口径与 61 局档案完全同法：conv 式逐步记录（`active`=kaggle status-ACTIVE 侧），win/lose=该决策所属方是否为**对局（match）**胜者。93 局全量 32193 决策拍；61 子集 21124；新增 32 局 11069。

| ctx | 场景（名称映射） | 93 win | 93 lose | 93 share% | 61 share% | 新32 share% | win率 93 | win率 61 |
|---|---|---|---|---|---|---|---|---|
| 0 | Main 主菜单 | 8931 | 8244 | 53.35 | 52.86 | 54.28 | 0.520 | 0.521 |
| 7 | ToHand 找牌上手 | 2822 | 2363 | 16.11 | 15.94 | 16.42 | 0.544 | 0.544 |
| 14 | DamageCounterAny 自由放伤 | 750 | 737 | 4.62 | 5.02 | 3.86 | 0.504 | 0.521 |
| 22 | AttachTo 附着目标 | 776 | 641 | 4.40 | 3.73 | 5.69 | 0.548 | 0.544 |
| 8 | Discard 弃牌选择 | 690 | 580 | 3.94 | 4.00 | 3.83 | 0.543 | 0.561 |
| 21 | AttachFrom 附着来源 | 569 | 547 | 3.47 | 3.71 | 3.00 | 0.510 | 0.528 |
| 3 | Switch 换位 | 591 | 491 | 3.36 | 3.49 | 3.11 | 0.546 | 0.549 |
| 4 | ToActive 被 KO 补位 | 332 | 501 | 2.59 | 2.55 | 2.66 | **0.399** | **0.388** |
| 30 | DiscardEnergy 弃能量 | 325 | 317 | 1.99 | 1.95 | 2.08 | 0.506 | 0.519 |
| 1 | SetupActivePokemon | 222 | 222 | 1.38 | 1.38 | 1.37 | 0.500 | 0.500 |
| 43 | Activate 能力发动 | 167 | 152 | 0.99 | 1.00 | 0.97 | 0.524 | 0.528 |
| 5 | ToBench | 114 | 139 | 0.79 | 0.84 | 0.69 | 0.451 | 0.446 |
| 41 | IsFirst | 110 | 112 | 0.69 | 0.69 | 0.69 | 0.495 | 0.493 |
| 2 | SetupBenchPokemon | 116 | 100 | 0.67 | 0.67 | 0.68 | 0.537 | 0.546 |
| 13/16/40 | DamageCounter / RemoveDamageCounter(Count) | 47/47/46 | 53/50/49 | ≈0.3×3 | ≈0.4×3 | ≈0.1×3 | ≈0.48 | ≈0.48 |
| 38 | DrawCount | 60 | 38 | 0.30 | 0.33 | 0.26 | 0.612 | 0.652 |
| 17/15/9/37/34/26/19/44/42/27/33/28/18 | Heal/Damage/ToDeck/Evolve/SkillOrder/DiscardEnergyCard/EvolvesTo/FirstEffect/Mulligan/…低频 | 各 ≤32 | | ≤0.15 | | | | |

**稳定性判定**：Top-8 场景份额 61 子集 vs 新 32 局逐项差 ≤0.7pp（ctx 14 除外 1.2pp），win 率逐项差 ≤0.03；**ctx 4（ToActive）输家偏斜 0.39/0.40 双样本稳定**——"被动换单=被 KO 频率信号"在 93 局上复现。谱系稳定，可用于评测特征。

**数值 ctx→名称映射**（消耗决策同帧配对取众数）：0=Main, 1=SetupActivePokemon, 2=SetupBenchPokemon, 3=Switch, 4=ToActive, 5=ToBench, 7=ToHand, 8=Discard, 9=ToDeck, 13=DamageCounter, 14=DamageCounterAny, 15=Damage, 16=RemoveDamageCounter(Count), 17=Heal, 19=EvolvesTo, 21=AttachFrom, 22=AttachTo, 26=DiscardEnergyCard, 27=DiscardToolCard, 30=DiscardEnergy, 33=SwitchEnergy, 34=SkillOrder, 37=Evolve/Activate, 38=DrawCount, 40=RemoveDamageCounter(Count), 41=IsFirst, 42=Mulligan, 43=Activate, 44=FirstEffect（低频项含配对噪声，标注为候选）。

## 6. 伤害实证（base×倍率对照）

- 攻击→HpChange 同帧配对 1737 对；**纯数值攻击（base>0 且 text 空）63 对**。
- 公式 `exp = (base + bonus) ×(弱点半 ? 2 : 1) − (抗性 ? 30 : 0)`（先加成后弱点）：

| 检验 | 样本 | 吻合 | 吻合率 | 备注 |
|---|---|---|---|---|
| 纯数值攻击全量 | 63 | 59 | **93.7%** | 4 例残差全部是 +30 平坦加成（见下） |
| 30 例抽查（含 W 7 例） | 30 | 26 | **86.7%** | 不符 4 例即 +30 加成案例 |
| 弱点 ×2（纯数值 W 命中） | 7 | 5 + 2 例一致(含加成) | 结构确认 | 例：Super Psy Bolt 30→60 vs Mega Lucario ex ✓ |
| 抗性 −30（纯数值 R 命中） | **0** | — | **缺口** | 纯数值攻击无抗性命中样本 |
| 抗性 −30（效果攻击 R 命中） | 81 | 32 精确 fit base−30 | 39.5% | 例：Aura Jab 130→100=130−30 ✓；不符 49 例均为伤害缩放类文本（Syrup Storm/Myriad Leaf Shower），printed base 无意义 |
| W+R 双命中 | 0 | — | **缺口** | 乘算顺序（先 W 后 R 或反序）无法由本 corpus 判定 |

- **4 例残差全解**：Corkscrew Punch 10→40、10→80(W)、Power Gem 50→160(W)、10→40——恰为 `(base+30)×W`，对应场上道具 **Premium Power Pro**（"本回合己方 {F} 攻击 +30，弱点/抗性结算前"）逐例在同回合打出。**公式结构成立，加成层在弱点乘算之前，与卡文本一致**。
- 30 例抽查表（原样，eid/攻击/base/攻方类型/守方/weak/res/期望/实测/吻合）：

```
117968378 Super Psy Bolt 30 W(5) Mega Lucario ex exp60 act60 OK      118033388 Corkscrew Punch 10 Beldum(r=1) exp10 act10 OK
117968378 Super Psy Bolt 30 W(5) Mega Lucario ex exp60 act60 OK      118407783 Jet Headbutt 70 Teal Mask Ogerpon ex exp70 act70 OK
117968378 Super Psy Bolt 30 W(5) Mega Lucario ex exp60 act60 OK      117458047 Corkscrew Punch 10 Dreepy exp10 act40 NG(+30)
117981541 Corkscrew Punch 10 W(6) Meowth ex exp20 act20 OK           118474143 Jet Headbutt 70 Meganium exp70 act70 OK
118036247 Corkscrew Punch 10 W(6) Fezandipiti ex exp20 act20 OK      117452360 Dragon Headbutt 70 Dreepy exp70 act70 OK
118355047 Corkscrew Punch 10 W(6) Meowth ex exp20 act80 NG(+30后×2)  118400621 Jet Headbutt 70 Dipplin exp70 act70 OK
118406355 Power Gem 50 W(6) Dunsparce exp100 act160 NG(+30后×2)      117899384 Corkscrew Punch 10 Hydrapple ex exp10 act40 NG(+30)
117688606 Super Psy Bolt 30 Hydrapple ex exp30 act30 OK              117681447 Solar Beam 140 Teal Mask Ogerpon ex exp140 act140 OK
117459490 Dragon Headbutt 70 Crustle exp70 act70 OK                  117899384 Solar Beam 140 Hariyama exp140 act140 OK
117459490 Dragon Headbutt 70 Crustle exp70 act70 OK                  117460945 Jet Headbutt 70 Solrock exp70 act70 OK
118406360 Jet Headbutt 70 Beldum(r=1) exp70 act70 OK                 118030454 Jet Headbutt 70 Teal Mask Ogerpon ex exp70 act70 OK
117944683 Jet Headbutt 70 Lunatone exp70 act70 OK                    118044787 Beat 10 Riolu exp10 act10 OK
117980082 Dig Claws 10 Dragapult ex exp10 act10 OK                   118407783 Jet Headbutt 70 Fezandipiti ex exp70 act70 OK
118023280 Solar Beam 140 Mega Lucario ex exp140 act140 OK            118366658 Power Gem 50 Budew exp50 act50 OK
```
（W=弱点命中，r=抗性字段在场但类型不命中）

## 7. 决策量（每局每方）

口径=每 game 每方**被引擎消耗的选择决策数**（含铺场/检索细选；93 局共 31827 决策）。

| n | min | p10 | median | mean | p90 | max |
|---|---|---|---|---|---|---|
| 444（222 game×2 方） | 3 | 30.5 | **73** | 71.7 | 104 | 148 |

| 区间 | <10 | 10-19 | 20-29 | 30-42 | 43-60 | >60 |
|---|---|---|---|---|---|---|
| (player,game) 数 | 12 | 16 | 15 | 21 | 65 | **315** |
| 占比 | 2.7% | 3.6% | 3.4% | 4.7% | 14.6% | 71.0% |

- **"正常 30-42"基线不成立**：健康对局单方决策中位数 73（43–148 才是主体，>60 占 71%）；30-42 带仅 4.7%。30-42 更接近"短局健康下限"而非正常值。
- **秒死签名实证**：单方 <10 决策的 12 个 game **全部是 reason 3（无主动位）速败**，2–5 回合内被清场（例：117681447 g0，败方 4 决策，Applin 40HP 前场 2-3 回合被击穿后无宝可梦可补位）。即**官方语料里 <10 决策=清场速败的真实签名，不是 agent 崩溃**；本 corpus 无 agent 故障局（222/222 以 Result 终局），崩溃签名无法在此标定——评测健康检查仍应沿用 fna-013（决策数>20+真赢一局），但要意识到 20 以下也可能是真实速败。

## 8. 与 61 局档案逐条对照

| 61 局档案条目 | 93 局实证 | 判定 |
|---|---|---|
| 一、reason 枚举 1/2/3/4 | 1/2/3 全出现（179/2/41），4=0 | 复现并补频率 |
| 二、奖赏数学：普通 1 / ex 2 / 多 KO 3-6 | 严格 1/2/3（含 **megaEx=3**），簇级 94.5% 精确、0 多领反例 | 修正+强化 |
| 三、卡牌模型 | ex 129 / megaEx 38；奖赏值与 ex/megaEx 标志严格挂钩 | 复现 |
| 四、SelectContext 谱 | Top-8 份额差 ≤0.7pp；ctx4 输家偏斜 0.39/0.40 稳定 | **稳定** |
| 五、每回合附着 1/支援者 1/撤退 1/竞技场 1 | **动作层全部严格限 1（0 违例）**；事件层能量附着可达 7/回合、换位 3/回合（效果豁免） | 精确化 |
| 五、先手首回合禁攻 | 0/222 违例 | 复现 |
| 六、信息结构 | 未复核（本任务未挖） | — |

## 9. 限界与缺口（引用时必读）

1. **样本不是天梯抽样**：93 局为特定 agent 群（Schott/バーベナ/Darren/OceanMix/JerryChen/自家种子等）的公开局+team-submissions 局，meta 集中（Dragapult ex/Munkidori/Lunatone-Makuhita 等），**不代表全卡池分布**。
2. **毒/烧/睡/麻 0 样本**：每回合伤害实测值无读数；卡池里存在此类卡但未被使用。需要受控探针（libcg.so 直驱）补测。
3. **抗性 −30 纯数值 0 样本、W+R 双命中 0 样本**：乘算顺序与纯数值 R 案例需受控探针（`fn_work/tmp/dmgprobe/resist.py` 已有引擎直驱验证 −30 的先例，属独立证据）。
4. **归属残差**：奖赏簇 61/1110 不一致（59=终局截断、2 未解释）；SelectContext 数值↔名称低频项有配对噪声；`convert_official_replay.py` 的 `active=status` 口径与动作级真值差 10.6%（3405/32193），建议适配层改用"action==selected"归属。
5. **win/lose 拆分以 match 胜者为口径**（与 61 局档案同法）；若按单 game 胜者拆分数字会有小出入。
6. 本挖掘只做"引擎行为实证"，未与规则书（`references/rules/meg_rulebook_en`）逐条 diff；卡文本效果（如 Premium Power Pro 的 +30 时点）以 DB `skills.text` 为准。

## 10. 建议

1. 评测特征加"每回合手动限 1 四件套已用/未用"位（能量/支援者/撤退/竞技场 flag），并单列"效果附着预算"（单回合能量附着事件可达 7，属正常）。
2. 奖赏差目标函数按 **1/2/3**（normal/ex/megaEx）计价；终局截断（拿完即胜）应进胜负模拟的边界处理。
3. reason 3（清场线）占 18.5%：给"场上宝可梦存量/补位储备"独立风险项，避免只算奖赏差。
4. fna-013 尺子健康检查加注：单方决策 <10 在真实对局=清场速败签名；判崩溃需叠加"Result reason/INACTIVE 轨迹"证据。
5. 毒/烧/睡/麻与 R−30、W+R 顺序：走 libcg.so 受控探针补数（dmgprobe 已有脚手架）。
