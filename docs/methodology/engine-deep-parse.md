# cabt 引擎与规则深解档案（2026-10-06，六问法深读+实证）

来源：kaggle-environments 1.33.0 cabt（cabt.py 252 行 + libcg.so 绑定层）+ API 文档
（matsuoinstitute.github.io/cabt api.html/game.html/sim.html）+ 引擎内置数据库
（libcg.so `AllCard()` 520KB/`AllAttack()` 232KB，已落 references/engine/）+ 61 局官方回放实测。

## 一、胜利条件（RESULT 日志 reason 枚举）

| reason | 含义 | 战略翻译 |
|---|---|---|
| 1 | 0 prize cards（一方拿完奖赏） | **主胜利路径=奖赏竞速** |
| 2 | no deck（牌库抽空） | 疲劳线：长局防守方风险 |
| 3 | no Active Pokémon（无可用主动位） | 清场线：把对手场打穿 |
| 4 | card effect | 卡效果直接胜利（罕见） |

## 二、奖赏数学（61 局实测跳变分布）

KO 对手宝可梦→我方领奖：**普通 1 张、ex 2 张**（实测 68×1 + 34×2 + 多重 KO 3-6 张）。
赢=领完 6 张 → **等价杀伤需求：3 只 ex 或 6 只普通（混合线性加权）**。这是全游戏的目标函数骨架：
> J = Σ(KO 的对手宝可梦奖赏值) − Σ(我方宝可梦被 KO 的奖赏值) = 奖赏差，终局判胜即 J≥6。

## 三、卡牌模型（AllCard 1431 张）

| cardType | 张数 | 语义（名称实证） |
|---|---|---|
| 0 | 1196 | 宝可梦（HP 30-380；basic/stage1/stage2 进化链；**ex/megaEx/tera/aceSpec 标记**；weakness/resistance；retreatCost；attacks=[attackId]） |
| 1 | 83 | 道具 Item（Rare Candy/Enhanced Hammer…） |
| 2 | 29 | 工具 Tool（Lucky Helmet/Maximum Belt…，附着宝可梦） |
| 3 | 69 | 支援者 Supporter（Boss's Orders…，每回合限 1） |
| 4 | 29 | 竞技场 Stadium（双方共享，每回合限 1） |
| 5 | 8 | 基本能量（每回合手动附着限 1） |
| 6 | 17 | 特殊能量 |

技能库 AllAttack 1755 条：damage 均值 53/最大 350，energy 需求（0=无色），
**text 字段含完整效果文本**（效果四件套可解析：抽牌/伤害指示物/换位/找牌）。

## 四、选择场景谱（SelectContext 0-48，api.html 全表）

按 61 局实测频率排序（win/lose 计数）：

| ctx | 场景 | win/lose | 读法 |
|---|---|---|---|
| 0 | MAIN 主菜单（PLAY/ATTACH/EVOLVE/ABILITY/RETREAT/ATTACK/END） | 5821/5328 | **决策质量主战场**（每回合的编排） |
| 7 | TO_HAND 找牌上手 | 1802/1527 | 检索类效果 |
| 14 | DAMAGE_COUNTER_ANY 自由放伤 | 552/504 | 效果伤害分配 |
| 8 | DISCARD 弃牌选择 | 475/371 | 效果代价 |
| 21/22 | ATTACH_FROM/TO 附着 | 414-428/358-370 | 能量/工具附着目标 |
| 3 | SWITCH 换位 | 405/333 | |
| 4 | TO_ACTIVE 被打倒后补位 | **209/330** | **输家显著更多=被动换单更多（被 KO 频率信号）** |
| 1/2 | 开局 SETUP | 146/146 | |
| 37/38/40/41/42/43/44 | EVOLVE/DRAW_COUNT/数量选择/IS_FIRST/MULLIGAN/ACTIVATE/… | 低频 | |

## 五、回合结构（State 字段实证）

每回合一次性限制：**能量附着 1 次、支援者 1 次、撤退 1 次、竞技场 1 次**；
turnActionCount 计本回合行动数；MAIN 选项集=[PLAY, ATTACH, EVOLVE, ABILITY, DISCARD, RETREAT, ATTACK, END]。
firstPlayer=-1 待定→IS_FIRST(41) 选择；开局 SETUP_ACTIVE(1)→SETUP_BENCH(2)→MULLIGAN(42)。

## 六、信息结构（观测面精确化）

完全可见：双方场面（active/bench 含 HP/能量/工具/进化链/特殊状态）、双方弃牌、
奖赏计数、deckCount。**唯一隐藏：对手手牌内容**（仅计数）——比初判更宽的可见面，
查表/语义评估的可靠度高，但对手手牌推理仍留观测器位。

## 七、对玩法的战略翻译（本档案的核心产出）

1. **奖赏竞速是主轴**：所有决策用"奖赏差期望"做通货。KO ex（2 奖）价值=普通怪双倍；
   防线选位要按"被 KO 的奖赏损失"定价（ex 站前=高风险高回报）。
2. **能量节奏=输出节奏**：每回合 1 次手动附着 → 攻击启动时间由能量线决定；
   技能需求（energies）决定哪只能最快开火。**"能量到位数"是攻击可行性的硬门槛**。
3. **伤害阈值逻辑**：damage vs 对手 active HP 决定几回合 KO（含 weakness ×2 类倍率）；
   **一击线（one-shot）比期望伤害重要**——能一击=先手方优势最大化。
4. **retreat 经济**：撤退费（retreatCost 能量单位）+每回合 1 次撤退限制 →
   保主动位=保输出节奏；被迫 TO_ACTIVE（ctx=4）=节奏损失（输家信号实证）。
5. **进化时点**：evolvesFrom 链+appearThisTurn 限制 → 第几回合进化决定 HP 与伤害跃迁；
   Rare Candy（道具）跳级=时间套利。
6. **疲劳线**：deckCount 是防守方的隐性时钟——长局里每抽一张=离 reason 2 近一步。

## 八、与此前打法的对照（为什么四连负）

- v5/v6/v7/v8 全部在"可见提示→动作"层打转，**没有一版知道卡是干什么的**（BC v2 前特征=ID 数字桶）。
- 赢家优势实际在：MAIN 菜单的编排质量（能量给谁/何时进化/何时开火/何时撤退）
  ——这是**状态评估问题**（奖赏差期望），不是提示模式匹配问题。
- 本档案给出评估函数的全部原料：HP/伤害/能量需求/奖赏值/weakness。
