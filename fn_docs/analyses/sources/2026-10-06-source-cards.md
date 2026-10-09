# cabt 引擎卡牌数据库：统计与效果文本分类学

- 数据源（本次实抓/入库文件，2026-10-05 入库）：
  - `/mnt/data/Code/autoC/workspace/ptcg-playground-2026/references/engine/cabt-cards.json`（1431 卡）
  - `/mnt/data/Code/autoC/workspace/ptcg-playground-2026/references/engine/cabt-attacks.json`（1755 技能）
- 统计日期：2026-10-06；方法：python3 一次性统计脚本（json 载入→Counter/分位/正则词表），无抽样、全量口径。
- 枚举映射判据（由数据自身锚定）：`cardType` 0-6 = Pokémon/Item/Tool/Supporter/Stadium/BasicEnergy/SpecialEnergy（按卡名单义确认）；`energyType/weakness/resistance` 同一取值域 0-9 = {C}/{G}/{R}/{W}/{L}/{P}/{F}/{D}/{M}/{N}Dragon，10/11 为两张特殊能量的单例码（由 Basic {X} Energy 卡名锚定）。
- 分类学口径：效果文本关键词正则**多标签**归类（一条技能可命中多类）；"仅其他"=十类全不命中。

---

## 1. 卡型分布与字段完备性

| cardType | 卡型 | 张数 | 占比 |
|---|---|---|---|
| 0 | Pokémon | 1196 | 83.6% |
| 1 | Item | 83 | 5.8% |
| 2 | Tool | 29 | 2.0% |
| 3 | Supporter | 69 | 4.8% |
| 4 | Stadium | 29 | 2.0% |
| 5 | Basic Energy | 8 | 0.6% |
| 6 | Special Energy | 17 | 1.2% |
| — | 合计 | 1431 | 100% |

字段完备性（各字段非空张数；全库 20 字段每卡皆存在，差异在取值）：

| 字段 | Poké(1196) | Item(83) | Tool(29) | Supp(69) | Stad(29) | BasicE(8) | SpecE(17) | 归属结论 |
|---|---|---|---|---|---|---|---|---|
| hp | 1196 | 7 | 0 | 0 | 0 | 0 | 0 | 宝可梦专有；7 张化石 Item 携带 hp=60 |
| pokemonType | 1196 | 7 | 0 | 0 | 0 | 0 | 0 | 同上（化石携带 =2） |
| evolutionType | 1196 | 7 | 0 | 0 | 0 | 0 | 0 | 同上（化石携带 =1=basic） |
| basic/stage1/stage2 | 672/393/131 | 7/0/0 | 0 | 0 | 0 | 0 | 0 | 宝可梦专有（化石 7 张 basic） |
| evolvesFrom | 524 | 0 | 0 | 0 | 0 | 0 | 0 | **仅宝可梦** |
| weakness / resistance | 1157 / 263 | 0 | 0 | 0 | 0 | 0 | 0 | **仅宝可梦** |
| retreatCost | 1158 | 0 | 0 | 0 | 0 | 0 | 0 | **仅宝可梦**（38 张 =0） |
| ex / megaEx / tera | 129/38/32 | 0 | 0 | 0 | 0 | 0 | 0 | **仅宝可梦** |
| energyType | 1081 | 0 | 0 | 0 | 0 | 8 | 10 | 双语义：宝可梦=自身属系；能量卡=供能属系 |
| attacks | 1196 | 0 | **1** | 0 | 0 | 0 | 0 | 近乎宝可梦专有；例外 Tool「Core Memory [1556]」 |
| skills | 244 | 83 | 29 | 69 | 29 | 0 | 17 | 除基本能量外全卡型都有（特性/卡牌效果文本） |
| aceSpec | 0 | 18 | 6 | 0 | 2 | 0 | 3 | 仅训练家与特殊能量 |

结论：**只有宝可梦有的字段**=evolvesFrom、weakness、resistance、retreatCost、ex、megaEx、tera、stage1、stage2；hp/pokemonType/evolutionType/basic 被 7 张化石 Item 越界携带；energyType/attacks/skills 为跨卡型字段（语义随卡型变）。

## 2. 宝可梦统计

### 2.1 HP 分布（n=1196）

| min | p10 | p25 | p50 | p75 | p90 | p95 | max | mean |
|---|---|---|---|---|---|---|---|---|
| 30 | 60 | 70 | 100 | 140 | 230 | 280 | 380 | 122.4 |

HP 区间直方：30-60:144 ｜ 70-90:381 ｜ 100-120:263 ｜ 130-160:205 ｜ 170-200:52 ｜ 210-250:48 ｜ 260-300:50 ｜ 310-380:53。按进化级：basic 均值 97.1（max 310）→ stage1 137.2（max 380）→ stage2 207.4（max 380）。7 张化石 Item 固定 hp=60。

### 2.2 进化链

| 项 | 读数 |
|---|---|
| basic / stage1 / stage2 | 672 / 393 / 131 |
| evolvesFrom 存在 | 524（=stage1+stage2 全量）；flags 与 evolutionType 零错位 |
| 父名可在宝可梦中解析 | 517；**7 条指向化石 Item 名**（Lileep←Antique Root Fossil 等）→ 在宝可梦索引中悬空 |
| 父名多卡歧义命中 | 238 条（父名对多张卡，如 Eevee×3、Bronzor×5） |
| 链深一致 | 509/517（不一致 8 条全为化石线父级悬空） |
| 最大链深 | 3（basic→stage1→stage2，无更高） |

### 2.3 标记（ex/megaEx/tera/aceSpec）

| 标记 | 张数 | 交集结构 |
|---|---|---|
| ex | 129 | 97 纯 ex + 32 ex∩tera |
| megaEx | 38 | 与 ex **不相交**（卡名含 "ex" 但 ex 标志=False，如 Mega Venusaur ex） |
| tera | 32 | 全部 ⊆ ex |
| aceSpec | 29 | 与三者皆不相交：Item 18 + Tool 6 + Stadium 2 + SpecialEnergy 3 |
| 四标皆无 | 1235 | — |

标记与 HP：ex 均值 255.4（160-380）；tera 均值 257.2（160-330）；megaEx 均值 321.8（250-380，全库最高档）。

### 2.4 Weakness / Resistance 值域

弱点分布（1196；编码值即被弱点属性）：{R}Fire 244、{F}Fighting 211、{L}Lightning 183、{G}Grass 159、{D}Darkness 113、{W}Water 112、{M}Metal 91、{P}Psychic 44、**无弱点 39（全部 {N}Dragon）**。**没有任何卡以 {C}/{N} 为弱点值**。

弱点主轴（属系→被弱属性，卡数）：

| 自属系 | 被弱于 | 卡数 | 备注 |
|---|---|---|---|
| {G} | {R} | 168 | 主轴；另 2 张弱 {L} |
| {R} | {W} | 112 | 另 4 张弱 {L} |
| {W} | {L} | 112 | 另 46 张弱 {M} |
| {L} | {F} | 81 | 另 5 张自弱 {L} |
| {P} | {D} | 113 | 另 45 弱 {M}、4 弱 {L} |
| {F} | {G} | 88 | 另 44 弱 {P} |
| {D} | {G} | 71 | 另 48 弱 {F}、18 弱 {L} |
| {M} | {R} | 76 | 另 5 弱 {L} |
| {C} | {F} | 82 | 另 33 弱 {L} |
| {N} | — | 0 | 39 张全无弱点 |

抗性分布：**仅两个值**——{F}Fighting 187、{G}Grass 76、无抗性 933。抗 {G}=Metal 全体 76 张；抗 {F} 集中在 Psychic 117，另 Colorless 33、Darkness 18、Metal 5、Lightning 5、Fire 4、Water 3、Grass 2。其余 8 个属性值从未出现在抗性栏。

### 2.5 retreatCost

| 值 | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| 张数 | 38 | 589 | 363 | 163 | 43 |

均值 1.65，中位 1；随进化级递增：basic 1.43 → stage1 1.84 → stage2 2.19。0 撤退代表：Shaymin、Dunsparce、Budew、Tapu Koko ex、Cinderace ex 等。

## 3. 能量卡（8 基本 + 17 特殊）

基本能量 8 张：Basic {G}/{R}/{W}/{L}/{P}/{F}/{D}/{M} Energy，energyType 各 1-8，无 skills 文本（"供 1 个本系能量"为引擎内隐规则）。

特殊能量 17 张逐卡分类（供能规则 / 附加效果；17 张全部 = 显式供能句 + 至少一条附加效果）：

| 卡名 | 供能规则 | 附加效果类 |
|---|---|---|
| Boomerang Energy | 恒定 {C}×1 | 弃牌回收（被自己攻击弃→攻击后再贴回） |
| Neo Upper Energy | {C}×1；贴 Stage2 时→全属性×2 | 供能增强（条件变身） |
| Mist Energy | 恒定 {C}×1 | 防护（挡对手攻击的全部效果） |
| Legacy Energy | 全属性×1 | 减奖（被击倒时对手少拿 1 奖，整局一次） |
| Enriching Energy | 恒定 {C}×1 | 抽牌（从手贴出时抽 4） |
| Spiky Energy | 恒定 {C}×1 | 反伤（active 被打→放 2 指示物于攻击方） |
| Team Rocket's Energy | 任意×2；仅限 Team Rocket's 宝可梦，违贴即弃 | 限定佩戴 |
| Prism Energy | {C}×1；贴 Basic 时→全属性×1 | 供能增强（条件变身） |
| Ignition Energy | {C}×1；进化型供能提升；回合结束自动弃 | 时限/自动弃 |
| Grow Grass Energy | 恒定 {G}×1 | HP +20 |
| Telepath Psychic Energy | 恒定 {P}×1 | 铺场（贴出时搜 2 Basic {P} 上 bench） |
| Rock Fighting Energy | 恒定 {F}×1 | 防护（挡效果） |
| Nitro {R} Energy | 恒定 {R}×1 | 回收（被自己攻击弃→回手） |
| Bubbly {W} Energy | 恒定 {W}×1 | 免异常（解+免疫 Special Condition） |
| Magnetic {M} Energy | 恒定 {M}×1 | 减撤退（0 retreat） |
| Voltaic {L} Energy | 恒定 {L}×1 | 增伤 +20（W/R 计算前） |
| Shadowy {D} Energy | 恒定 {D}×1 | 防护（bench 上免受伤） |

供能规则三型：恒定单色 8 张（Grow/Telepath/Rock/Nitro/Bubbly/Magnetic/Voltaic/Shadowy）、恒定无色 5 张（Boomerang/Mist/Enriching/Spiky/Ignition）、条件全属性/双倍 3 张（Neo Upper/Prism/Legacy）+ 限定 2 倍 1 张（Team Rocket's）。附加效果主题：防护 3、供能增强 3、回收/时限 3、增益（抽牌/HP/增伤/免异常/减撤退/铺场/减奖/反伤）各 1。

## 4. 技能统计（cabt-attacks.json，1755 条）

### 4.1 伤害

| 项 | 读数 |
|---|---|
| 0 伤效果技 | 429（24.4%，**全部带效果文本**） |
| 带文本技能 | 1161（其中 732 条有伤+文本，429 条 0 伤纯效果） |
| 无文本纯数值技 | 594（全部有伤） |
| max | 350（Geobuster） |
| mean 全量 / 仅正伤 | 52.9 / 70.0 |
| p50 / p90 / p95 | 30 / 140 / 180 |

区间直方：0:429 ｜ 1-30:558 ｜ 31-60:263 ｜ 61-90:134 ｜ 91-120:130 ｜ 121-160:135 ｜ 161-200:47 ｜ 201+:59。

### 4.2 费用结构

| cost 长度 | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| 技能数 | 5 | 770 | 504 | 401 | 66 | 9 |

均长 1.87；总能量符号 3290，其中无色 {C} 1575 = **47.9%**；1042/1755（59.4%）技能含 ≥1 无色。0 费技能 5 条（Delightful Kiss、Itchy Pollen、Zapping Draw、Chiming Commotion、Pow-Pow Punching）。宝可梦攻击位：638 张 1 技、558 张 2 技。技能名 1118 个 distinct（Tackle×17、Ram×16、Bite×16 为复用名，(name,cost,dmg) 三元组 distinct 1645）。

### 4.3 效果文本关键词分类学（n=1161 带文本，多标签）

| 类 | 命中数 | 占比 | 代表技能名 |
|---|---|---|---|
| 能量操作 | 271 | 23.3% | Leaflet Blessings、Pick and Stick、Peak Acceleration、Volt Cyclone |
| 弃牌 | 198 | 17.1% | Slow Crunch、Ground Burn、Pick and Stick、Recovery Net |
| 硬币 | 157 | 13.5% | Comet Punch、Quick Attack、Ball Roll、Mysterious Beam |
| 找牌 | 118 | 10.2% | Nab 'n' Dash、Flock、Find a Friend、Ascension |
| 异常状态 | 118 | 10.2% | Hot Magma、Numbing Water、Super Poison Breath、Fake Out |
| 伤害指示物 | 77 | 6.6% | Super Sandstorm、Re-Brew、Permeating Chill、Hex Hurl |
| 换位 | 71 | 6.1% | Push Down、Reverse Thrust、Drum Beating、Sob |
| 治疗 | 40 | 3.4% | Leaflet Blessings、Matcha Splash、Aurora Gain、Hold Still |
| 抽牌 | 39 | 3.4% | Allure、Return、Stock Up on Feathers、Add On |
| 保护 | 27 | 2.3% | Dig、Crown Opal、Harden、Undulate |
| 仅"其他" | 309 | 26.6% | Wicked Impact、Avenging Edge、Blood Moon、Primordial Beatdown |

标签数分布：0 标 309、1 标 605、2 标 230、3 标 17。"其他"残差 309 条再切片：伤害加成（"does N more damage"）74、攻击自缚文本（"can't use again…"）95、下回合持续效果 59、自伤/反作用 45、减伤/承伤修正 26、杂项 10——即残差主体是**伤害修正与自缚**，而非新机制。

### 4.4 按属系的技能伤害均值（按技能所属宝可梦属系）

| 属系 | 技数 | 均伤(全) | 均伤(>0) | max |
|---|---|---|---|---|
| {N} Dragon | 66 | 73.6 | 103.4 | 330 |
| {M} Metal | 120 | 65.5 | 80.2 | 260 |
| {F} Fighting | 196 | 61.2 | 73.1 | 270 |
| {R} Fire | 167 | 61.1 | 77.3 | 320 |
| {L} Lightning | 129 | 60.8 | 79.2 | 300 |
| {W} Water | 232 | 53.3 | 67.2 | 280 |
| {D} Darkness | 205 | 50.2 | 66.0 | 240 |
| {C} Colorless | 168 | 45.5 | 65.9 | 280 |
| {G} Grass | 235 | 43.2 | 58.1 | 240 |
| {P} Psychic | 236 | 39.3 | 60.3 | 230 |

Dragon 均伤断层第一（HP 上限也最高、无弱点），Psychic 均伤垫底但技能数最多——高效果密度/低直伤的属系画像。

## 5. 训练家卡

| 类 | 张数 | aceSpec | 代表卡名 |
|---|---|---|---|
| Item | 83 | 18 | Roto-Stick、Rare Candy、Enhanced Hammer、Hyper Aroma、Love Ball |
| Tool | 29 | 6 | Team Rocket's Hypnotizer、Lucky Helmet、Rescue Board、Maximum Belt、Heavy Baton |
| Supporter | 69 | 0 | Billy & O'Nare、Boss's Orders、Perrin、Eri、Morty's Conviction |
| Stadium | 29 | 2 | Community Center、Perilous Jungle、Full Metal Lab、Jamming Tower、Grand Tree |

skills 文本主题（卡级多标签命中，同一词表）：

| 主题 | Item | Tool | Supporter | Stadium | 各类例证 |
|---|---|---|---|---|---|
| 弃牌 | 32 | 6 | 17 | 6 | Item: Hole-Digging Shovel、Enhanced Hammer；Stadium: Neutralization Zone |
| 找牌 | 29 | 1 | 25 | 4 | Item: Roto-Stick、Love Ball；Supp: Perrin、Eri |
| 能量操作 | 28 | 29 | 17 | 4 | Item: Reboot Pod；Supp: Colress's Tenacity |
| 换位 | 15 | 4 | 7 | 2 | Item: Prime Catcher；Supp: Boss's Orders、Kieran |
| 异常状态 | 12 | 2 | 3 | 3 | Item: Dangerous Laser；Stadium: Perilous Jungle |
| 治疗 | 7 | 0 | 6 | 1 | Item: Poké Vital A、Super Potion；Supp: Bianca's Devotion |
| 硬币 | 5 | 1 | 2 | 0 | Item: Crushing Hammer、Pokémon Catcher |
| 抽牌 | 4 | 1 | 20 | 3 | Supp: Billy & O'Nare、Carmine；Stadium: Mystery Garden |
| 伤害指示物 | 4 | 3 | 0 | 3 | Tool: Deluxe Bomb、Punk Helmet |
| 保护 | 3 | 0 | 1 | 2 | Stadium: Neutralization Zone、Battle Cage |
| 十类全不中 | 5 | 0 | 5 | 9 | Item: Rare Candy；Supp: Judge；Stadium: Full Metal Lab |

主题画像：Item=搜/弃/能量的工具箱；Tool=清一色"贴附后"持续修正（29/29 命中能量操作词——贴附语义）；Supporter=抽牌与找牌主场（一回合一次的强检索/抽滤）；Stadium=场地持续规则与状态场。

宝可梦特性（skills 244 条，一卡一特性）：能量操作 75、仅其他 58、找牌 33、弃牌 36、换位 27、伤害指示物 25、保护 24、状态 14、硬币 12、治疗 9、抽牌 17——特性偏"资源调度+防护"，抽牌反而少（抽牌权在 Supporter/Item）。

## 6. 规则性文本线索（规则书对照锚点；全库 1639 条文本=1161 技能+478 卡效果）

| 锚点 | 出现文本数 | 占比 | 语境切片 |
|---|---|---|---|
| Active | 371 | 22.6% | 目标指定（Defending/Active Pokémon） |
| your hand | 228 | 13.9% | 手牌来源/弃手条件 |
| shuffle | 219 | 13.4% | 搜寻后洗牌收尾（固定模板） |
| your deck | 214 | 13.1% | 搜寻/洗牌模板 |
| coin flip | 177 | 10.8% | if heads/tails 条件 109、for-each 计数 55、杂 13 |
| **Resistance** | 161 | 9.8% | Bench 括注 64、计算时点 79、免 W/R 13、改弱点 2 |
| **Weakness** | 158 | 9.6% | 同上（两词几乎同文出现） |
| Bench | 94 | 5.7% | 换位/铺场/Bench 伤 |
| knock(ed) out | 78 | 4.8% | 击倒判定（含延迟击倒） |
| discard pile | 65 | 4.0% | 弃牌区回收 |
| heal | 63 | 3.8% | 治疗量/全治 |
| damage counter | 113 | 6.9% | 指示物放置/计数 |
| **Prize card** | 38 | 2.3% | "for each Prize card taken" 放大 10、剩余奖判定（Victory Symbol 仅剩 1 奖可赢、Fickle Spitting 需恰 3/4 奖）、直接拿奖（Onyx） |
| evolve | 50 | 3.1% | 搜进化卡/禁进化 |
| ex/Mega/Tera 记号 | 72 | 4.4% | {ex}/{V} 定向增伤与指定 |
| attach | 81 | 4.9% | 能量加速模板 |
| Special Condition | 23 | 1.4% | 全异常统称（Burned/Poisoned/Asleep/Paralyzed/Confused 分列更多） |
| Tool / Stadium | 21 / 20 | 1.3% / 1.2% | 卡类定向（弃/搜/条件增伤） |
| VSTAR/GX/V | 15 | 0.9% | {V}/{ex} 记号混用（引擎文本仍含 {V} 时代卡记号） |
| ACE SPEC | 1 | 0.1% | ACE Nullifier：禁手牌打出 {ACE SPEC} |

Weakness/Resistance 语境三型（规则书核对优先级）：① 括注模板"(Don't apply Weakness and Resistance for Benched Pokémon.)"64 处——Bench 伤不计 W/R 是引擎文本高频显式规则；② 时点标注"(after/before applying Weakness and Resistance)"79 处——增减伤与 W/R 的先后序必须可判；③ "isn't affected by Weakness or Resistance"13 处——免 W/R 特例；④ "has no Weakness"2 处——弱点可被效果改写。

## 7. 异常与限界

1. **化石跨界**：7 张 Antique Fossil 为 Item 却携带 hp/pokemonType/evolutionType/basic（hp=60）；7 条 evolvesFrom（Lileep 等）指向这些 Item 名，在宝可梦索引中悬空 → 按名解析进化链必断。
2. **名字非唯一**：1431 卡仅 1196 个 distinct 名（Bronzor×5、Applin/Charcadet/Deoxys×4）；238 条 evolvesFrom 链按名解析有歧义；同名不同卡（如两张 Beldum 分属 {M} 与 {P}、弱点/抗性不同）→ **任何按名的统计或查询都必须改用 cardId**。
3. **megaEx 与 ex 标志不相交**：38 张 "Mega … ex" 卡 ex=False；卡名文本与标志位语义需以标志位为准。
4. **W/R 无倍率字段**：weakness/resistance 只存属性码（x2 / -30 量值不在数据里）；抗性值域仅 {G}/{F} 两值，其余 8 属性从未被抗。
5. **damage 是裸整数**："Flip 4 coins. 30 damage for each heads"（Comet Punch）记 0，"+N more damage" 技记基数 → 伤害字段对可变伤害系统性低估，预测模型须以文本为条件。
6. **分类学是关键词多标签**：230 条命中 2 类、17 条 3 类，类间不互斥；"其他" 309 为残差（主体=伤害修正/自缚）；"能量操作"含 attach/energy 泛词会略偏高。
7. **单例编码值**：energyType 10/11（Legacy / Team Rocket's Energy）为非标属系码；Core Memory（Tool）持 attackId 1556 是 attacks 字段唯一非宝可梦载体。
8. 本统计只覆盖两份 JSON 的字段与文本；引擎实际裁定逻辑（倍率、时点）不在此数据内，规则书对照只能以 §6 锚点为线索、不能以字段反推规则细节。
