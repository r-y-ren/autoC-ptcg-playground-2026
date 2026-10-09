# libcg.so 反汇编：PTCG 对战引擎（cabt）游戏规则取证

- **对象**：`fn_work/.venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cg/libcg.so`
  （ELF64 x86-64，1.4 MB，**未剥离符号**，BuildID `b10b4a893921a4edb54b65bb15f6b98a37776888`）
- **方法**：`nm`（全符号表，635 项，含内部函数）+ `objdump -d -M intel`（203,664 行）+ `strings -t x`
- **取证日**：2026-10-06
- **已知前置**（不重做）：`CalcDamage` = 弱点 ×2 → 抗性 −30 → 下限 0，属系取攻击方 `energyType`
- **证据记法**：`addr` = 虚拟地址（= 文件偏移，.text 载入于 0x4880/.rodata 于 0xe1000，二者重合）；
  `S(x)` = .rodata 字符串地址 x

---

## 0. 结构布局（后续所有证据的锚点）

反汇编的地址计算可直接反推内存布局。约定：`P(i) = State + i*0x258`（引擎的"伪基址"），
`PlayerState[i] = State + 0x260 + i*0x258`，`Card[k] = State + 0x718 + k*0xA0`（Card 块 160 字节）。

### State（对局级）
| 偏移 | 类型 | 含义 | 证据 |
|---|---|---|---|
| +0x00 | ptr | 随机/配置上下文（含 MT19937） | `SelectCoinSingle` 0x2422d `mov r13,[rdi]` |
| +0x08 | int | **turn 回合计数** | `TurnStart` 0x6811b `mov ebx,[r12+0x8]` / 0x68125 写回 +1 |
| +0x0c | int | 回合内动作计数（TurnStart 清零） | 0x68112 `mov DWORD PTR [r12+0xc],0x0` |
| +0x14 | int | 递归/循环保险计数，上限 0x2710=10000 | `ConfuseProc` 0x81913/0x81919 |
| +0x18 | byte | 阶段号（1=回合内 / 2 / 3=Checkup） | `TurnStart` 0x68143；`PokemonCheckupEnd` 0x82267 |
| +0x19 | byte | **结果：1=玩家0胜 / 2=玩家1胜 / 3=平** | `finishCheck` 0x11105 `lea edx,[rdx+rdx*1+0x1]` |
| +0x1a | byte | **原因 1..4** | `TurnStart` 0x6846d `mov BYTE PTR [r12+0x1a],0x2` |
| +0x28 | int8 | **firstPlayer 先手方** | `Current` 0x4c302 + key `S(0xe2970)="firstPlayer"` |
| +0x2d | byte | 本步是否产生日志 | 多处 `mov BYTE PTR [...+0x2d],0x1` |
| +0x2e | byte | 需要补位/弃牌选择 | `KOProc2` 0x58012；`PokemonCheckupEnd` 0x8231b |
| +0x32 | byte | **每回合一次性位段**（见 §2） | `Current` 0x4c318/0x4c450/0x4c57f/0x4c6b6 |
| +0x3c | int | **上次掷硬币的正面向上数** | `SelectCoinSingle` 0x242c4 `add DWORD PTR [rbp+0x3c],1` |
| +0x40 | byte | 当前行动方 | `PokemonCheckupEnd` 0x824c4 `movzx edx,BYTE PTR [rbp+0x40]` |
| +0x42/0x43 | byte | SelectType / SelectContext | `State::setSelect` 0x11174 |
| +0x46 | byte | 当前应选择的玩家（yourIndex） | `Search::start` λ 0x38ae1 |
| +0xf8 | int | 当前攻击 attackId | `ConfuseProc` 0x81924 |
| +0x100 | int | **攻击伤害加成累加器（"W&R 之前"类）** | `AttackDamage` 0x7eec6 |
| +0x108 | CardRef | 当前攻击宝可梦 | `ConfuseProc` 0x818c5 |
| +0x19 / +0x1a | — | 见上 | |

### PlayerState（0x258 步长，字段相对 `&players[i]`）
| 偏移 | 类型 | 含义 | 证据 |
|---|---|---|---|
| +0x000 | FixedList<char,CardRef,1> | 战斗场 active（+0=count，+1=CardRef） | `EffectPoison` 0x3c76d |
| +0x002 | FixedList<char,CardRef,8> | 后备 bench（+0=count） | `finishCheck` 0x11053 `cmp BYTE PTR [rdi+0x262],0x0` |
| +0x00c | int | **剩余奖赏张数** | `finishCheck` 0x1102f `mov r9d,[rdi+0x26c]` |
| +0x094 | int | **牌库剩余张数** | `TurnStart` 0x6845e `mov eax,[rdx+0x2f4]` |
| +0x232 | byte | 位标志（0x40=中毒禁撤退，0x10=…） | `MainSelect` 0x674af |
| +0x238 | int8 | **中毒伤害指示物数（0=未中毒）** | `EffectPoison` 0x3c904 写；0x56ee5 读 |
| +0x239 | int8 | **0=无 / 1=睡眠 / 2=麻痹 / 3=混乱**（三者互斥单槽） | `EffectSleep` 0x3cb51 `cmp ...,0x1`；`ParalyzeProc` 0x386ea `cmp ...,0x2`；`EffectConfuse` 0x3ce51 `mov ...,0x3` |
| +0x23a | int8 | **灼伤标志 0/1** | `EffectBurn` 0x3ca29 `mov BYTE PTR [...+0x49a],0x1` |
| +0x250 | int16 | 中毒伤害修正 | `AfterMoveTriggerStack` 0x56efc |
| +0x252 | int16 | 灼伤伤害修正 | `BurnProc` 0x5625b |
| +0x254 | int8 | 中毒伤害附加修正（条件触发） | 0x57087 |
| +0x255 | nibble | **后备区上限**（0 → 默认 5） | `PokemonCheckupEnd` 0x824ee `and eax,0xf` / `cmove eax,5` |

### Card（160 B）/ CardMaster
| 偏移 | 含义 | 证据 |
|---|---|---|
| Card+0x00 | cardId(int) | `Map_base::at(&Card)` 以首 dword 为键 |
| Card+0x10 | 当前 HP | `AddDamage` 0x55a99 |
| Card+0x44 | 持有者 playerIndex(int8) | `EffectPoison` 0x3c851 |
| Card+0x78 | 最大 HP 修正(int16) | `KOProc` 0x5835f |
| Card+0x99 | 位：0x40=防特殊状态，0x08=…，符号位=… | `EffectPoison` 0x3c803；`EffectSleep` 0x3cb16 |
| Card+0x9a / +0x9b | 位：0x1/0x2；0x1=不能撤退 0x2=不能攻击 | `EffectSleep` 0x3cb47；`MainSelect` 0x668b2 |
| Master+0x05 | **pokemonType**（JSON 键 `S(0xe2129)`） | `ApiAllCard` 0x320ec |
| Master+0x06 | **evolutionType**（basic/stage1/stage2） | `ApiAllCard` 0x327ea / 0x32829 `cmp r13b,0x3` |
| Master+0x07 | retreatCost(int8)（键 `S(0xe2143)`） | `ApiAllCard` 0x321fb |
| Master+0x08 / +0x18 | HP | `AddDamage` 0x55aa8；`KOProc` 0x58355 |

**pokemonType 枚举实证**（`AllCard()` 交叉验证，1431 张卡）：
`0`=非宝可梦、`1`=普通宝可梦、**`2`=Antique 化石道具卡**（7 张：Antique Root/Cover/Plume/Jaw/Sail/Skull/Armor Fossil，`cardType=ITEM`、`hp=60`、`basic=true`）、`3`=ex、`4`=Mega Evolution ex。
`evolutionType`：`0`=非宝可梦、`1`=Basic、`2`=Stage1、`3`=Stage2。

---

## 1. 状态条件（Special Conditions）五种

**Checkup 触发链**（`AfterMoveTriggerStack` 0x56d80 起，实为宝可梦检查分派器）：
先按玩家序扫中毒 → 推入 `ParalyzeProc` → `SleepProc(p)`/`SleepProc(1-p)` → `BurnProc(1-p)`/`BurnProc(p)`。
**混乱不进 Checkup**（持续到被解除/交换）。

### 1.1 中毒 Poisoned
- **何时掉血**：宝可梦检查（Checkup）阶段，对每个 `active` 非空且 `poisonValue>0` 的宝可梦结算一次。
  0x56dcf–0x56dff 判定 → 0x56ec0 结算。
- **掉多少**：`damage = poisonValue * 10 + *(int16)(player+0x250)`，条件分支再 `+ *(int8)(player+0x254)`
  —— 0x56ee5 `movsx eax,BYTE PTR [r12+0x498]` / 0x56ef9 `lea ecx,[rax+rax*4]` /
  0x56efc `movsx eax,WORD PTR [r12+0x4b0]` / 0x56f05 `lea ecx,[rax+rcx*2]`（×5 再 ×2 = ×10）。
  **默认 `poisonValue=1` → 10 伤害**；`EffectPoison(player,value)` 可设 2 → 20。
  经 `AddDamage(...,damage, r8=0, r9=target, push 0,0, NULL)` 落地（0x57056–0x5706e），`putDamageCounter` 标志为 0 = 记为伤害而非放置指示物。
- **何时解除**：**不会自动解除**（Checkup 无 PoisonProc）。只能被效果清除（`ClearSpecialCondition` 0x38cf0、
  `ClearSleepParalyzeConfuse` 0x379c0）或换下场/离场时清槽（多处 `mov DWORD PTR [...+0x498],0x0`）。
- **对行动的限制**：无。但存在"中毒禁撤退"效果位：`MainSelect` 0x674af `test BYTE PTR [rbx+0x492],0x40`
  → 若置位且 `poisonValue>0` 且 `Card+0x99 bit 0x8` 未置 → 不给 RETREAT 选项（0x674c1–0x674d6）。
- **施加门槛**（`EffectPoison` 0x3c730）：`active` 非空、`isPreventEffect(Card)` 为假、
  `Card+0x99 bit0x40`=0、`CardMaster+0x5 != 2`（Antique 化石免疫）、且 `poisonValue != newValue`（同值不重复施加，0x3c828）。

### 1.2 灼伤 Burned
- **掉多少**：`damage = 20 + *(int16)(player+0x252)` —— `BurnProc` 0x5625b `movsx ecx,WORD PTR [rbp+0x4b2]`
  / 0x56265 `add ecx,0x14`。默认 **20 伤害**。
- **掉血时机 + 解除**：Checkup 内 `BurnProc(player)`（0x561e0）：先 `AddDamage` 掉血，
  再推 `AfterBurnProc` + `AfterSelectCoin` + `SelectCoinSingle` → **掷一枚硬币**；
  `AfterBurnProc`（0x38960）判 `State+0x3c > 0`（有正面）→ `player+0x23a = 0` 并记 `LogType.BURNED(0x12)` 的 `isRecover=1`。
  **即：掉 20 → 掷币，正面则解除灼伤。**
- **对行动**：无限制。
- **施加门槛**（`EffectBurn` 0x3c940）：同 Poison 的四道门槛 + `player+0x23a == 0`（已灼伤不重复，0x3c9f8）。

### 1.3 睡眠 Asleep
- **何时解除**：Checkup 内 `SleepProc(player)`（0x18200）→ 掷硬币；`AfterSleepProc`（0x38810）
  判 `State+0x3c > 0` → `player+0x239 = 0` 并记 `LogType.ASLEEP(0x13)` `isRecover=1`。
  **正面才醒。**
- **对行动的限制**：**不能攻击、不能撤退** ——
  - `MainSelect` 0x66885 `movzx eax,BYTE PTR [r14+rax*1+0x499]` / `sub eax,1` / `cmp al,1` / `jbe 670ae`
    → **槽值 ∈ {1,2}（睡眠/麻痹）不生成 ATTACK 选项**。
  - `MainSelect` 0x6744d 同一模式 `jbe 674d6` → **不生成 RETREAT 选项**。
  - **混乱（槽值 3）不拦截**（`sub eax,1` 后 `al=2` > 1）。
- **施加门槛**（`EffectSleep` 0x3ca60）：同上四道 + `player+0x239 != 1`（已睡眠不重复，0x3cb51）。

### 1.4 麻痹 Paralyzed
- **何时解除**：Checkup 内 `ParalyzeProc`（0x386a0）：若 `player+0x239 == 2` → 清 0 并记
  `LogType.PARALYZED(0x14)` `isRecover=1`。**无需掷币，Between turns 自动解除。**
- **对行动的限制**：同睡眠（不能攻击、不能撤退）。
- **施加**：`EffectParalyze`（0x3d21f 起）门槛同上 + `player+0x239 != 2`（0x3d237）。
  另有硬币触发形态 `Chain::postEffectParalyzeIfCoinHead`（0x…）。

### 1.5 混乱 Confused
- **何时解除**：不在 Checkup 中解除。由 `ClearSleepParalyzeConfuse`（0x379c0）/`ClearSpecialCondition`（0x38cf0）
  或换下场清除。**攻击失败不会解除混乱。**
- **攻击失败判定**（`ConfuseProc` 0x818b0）：
  - `State+0x3c > 0`（掷币有正面）→ 攻击照常进行（跳 `AfterAttack` 0x7f200）。
  - 否则（反面）→ **攻击失败，且自己受 30 伤害**：0x818c5 取 `State+0x108`（攻击方）→
    0x818e2 `mov ecx,0x1e` → `AddDamage(...,30, 0, self, 0,0,NULL)` → 之后直接 `AfterAttack`（不再结算攻击伤害/效果）。
  - 递归保险：`State+0x14` 计数，`> 0x2710` 直接走 `AfterAttack`（0x81919）。
- **对行动的限制**：不拦截攻击/撤退（见上）。
- **施加**：`EffectConfuse`（0x3cd4e 起）门槛同上 + `player+0x239 != 3`（0x3cd67）。

**小结表**

| 条件 | Checkup 掉血 | 解除 | 攻击 | 撤退 |
|---|---|---|---|---|
| Poison | `value×10 + mod`（默认 10） | 不自动 | 无限制 | 无限制* |
| Burn | `20 + mod` 后掷币 | 掷币正面 | 无限制 | 无限制 |
| Sleep | 无 | Checkup 掷币正面 | **禁止** | **禁止** |
| Paralyze | 无 | Checkup 自动 | **禁止** | **禁止** |
| Confuse | 无 | 效果/换位 | 允许（掷币，反面→失败+自伤 30） | 允许 |

\* 仅当场上存在"中毒不能撤退"效果位（`PlayerState+0x232 bit0x40`）时禁止。

---

## 2. 回合结构与每回合一次性限制

### 2.1 一次性限制：`State+0x32` 位段
| 位 | 字段（JSON） | 置位地址 | MainSelect 门禁地址 |
|---|---|---|---|
| 0x01 | `supporterPlayed` | 0x815bc `or BYTE PTR [rbp+0x32],0x1` | 0x66c8b `test ...,0x1` |
| 0x02 | `stadiumPlayed` | 0x81500 `or ...,0x2` | 0x66b9f `test ...,0x2` |
| 0x04 | `energyAttached` | 0x6e698 `or ...,0x4` | 0x66ab0 `test ...,0x4` |
| 0x08 | `retreated` | 0x80fcb `or ...,0x8` | 0x67388 `test ...,0x8` |
| 0x10 | （第 5 位，效果用） | 0x75699 `or ...,0x10` | 0x662d4 `test ...,0x10` |

**清零点**：`TurnEnd2` 0x6cdf0 `mov BYTE PTR [rbp+0x32],0x0`（回合结束整体复位）。
→ **能量附着/支援者/竞技场/撤退各 1 次/回合**，由位段 + 选项生成门禁双重保证（`MainSelect` 0x662a0 起构建 `PLAY/ATTACH/RETREAT/END` 选项时逐位判）。

### 2.2 先手首回合能否攻击
`MainSelect` 0x669bb–0x669dd：
```
cmp  DWORD PTR [r13+0x8],0x1     ; turn
jg   669dd                        ; turn > 1 → 允许
test BYTE PTR [rax+0xe],0x8       ; Attack+0xe bit3
jne  669dd                        ; 该招式带"首回合可用"标志 → 允许
cmp  BYTE PTR [rcx+0x7b2],0x0
jns  66930                        ; 否则跳过（不生成 ATTACK 选项）
```
→ **turn==1（先手第一回合）默认禁止攻击**，除非招式带 `Attack+0xe bit 0x8` 标志。
后手首回合是 turn==2，不受限。与 `api.py` 注释 `turn: 1 = 先手第一回合` 自洽。

### 2.3 撤退费用与门禁
`MainSelect` 0x673fc–0x674d6（费用=可用能量数比较）：
```
6741c: xor eax,eax
6741e: cmp BYTE PTR [rcx+0x5],0x2      ; pokemonType == Antique Fossil?
67422: je  67429                        ; 是 → 费用 0
67424: test esi,esi
67426: cmovns eax,esi                  ; 否则取 max(修正和,0)
6742b: cdqe
6742c: cmp rax,rbx                     ; rbx = 可用能量数
6742e: jg  674d6                        ; 费用>能量 → 不给 RETREAT
```
门禁顺序（0x67440–0x674d1）：bench 为空 → 不给；睡眠/麻痹 → 不给；`Card+0x20 bit0x1` → 不给；
`Card+0x9b bit0x1` → 不给；`CardMaster.pokemonType==2`（Antique 化石）→ **不给**；中毒+禁撤退位 → 不给。
**费用函数**：`State::retreatCost(Card const&)` 0x75e0（含效果修正累加，0x6740c–0x67419 三项相加）。

### 2.4 强制补位（TO_ACTIVE）
`KOProc2` 0x57fc7–0x58067：
```
edx  = ((turn+1) ^ firstPlayer) & 1        ; 当前检查方
r13d = 1 - edx
if (players[edx].active 为空) { State+0x2e=1; push SelectActivePokemon(edx) }      ; 0x58052
if (players[r13].active 为空) { State+0x2e=1; push SelectActivePokemon(r13d) }     ; 0x58003→0x58012
```
→ **KO 后双方各自检查：战斗场空则强制从后备补位**（`SelectActivePokemon` 0x17610，SelectContext `TO_ACTIVE=4`）。
无后备可补时由 `finishCheck`/`TurnStart` 的"无宝可梦在场"判负（reason 3）。

### 2.5 回合流程骨架
`TurnStart`（0x67fe0）：胜负面扫描 → `turn++`（0x68125）→ 清动作计数（0x68112）→ `State+0x18=1`
→ 清回合内效果队列 → **牌库为 0 判负**（0x68450–0x6847a）→ 推 `MainSelect`（0x684c6）。
`TurnEnd`（0x65e20）/`TurnEnd2`（0x6cdb0）：清 `State+0x32`（0x6cdf0）→ 推 `PokemonCheckup`（0x6d2ac）。
`PokemonCheckup`（0x67ca0）→ 推 `PokemonCheckupEnd`（0x82220）→ 推 `TurnStart`。
**后备上限**：`PokemonCheckupEnd` 0x824c4–0x825d9 比较 `bench.count` 与 `benchMax`（`PlayerState+0x255` 低 4 位，0→5），
超限则推 `SelectBenchMaxTrash`（0x17150）强制弃到上限。

---

## 3. 奖赏领取：KO 张数分支

`KOProc3` 0x6ebd9–0x6ec80（核心三行）：
```
call CardMaster::at(cardId)                ; 0x6ebd9
mov  edx,0x2                               ; 0x6ebde
movzx eax,BYTE PTR [rax+0x5]               ; 0x6ebe3  pokemonType
cmp  al,0x3                                ; 0x6ebe7  == ex
je   6ebf6                                 ;          → edx = 2
xor  edx,edx
cmp  al,0x4                                ; 0x6ebed  == Mega ex
sete dl                                    ; 0x6ebef
lea  edx,[rdx+rdx*1+0x1]                   ; 0x6ebf2  → edx = 3 (Mega) 否则 1
```
**结论：普通 1 张 / pokemonType==3（ex）2 张 / pokemonType==4（Mega Evolution ex）3 张。**
随后 `ecx = edx + Card+0x69(int8 修正)`（0x6ec02–0x6ec09），并按 `Card+0x6b bit0x20`、`Card+0x6a`、
`Card+0x6c bit5`、`Card+0x6c bit4` 做加减（0x6ec12–0x6ec7d）——即"少拿 1 张/多拿 1 张"类效果（如 Legacy Energy 的
`S(0xe17006)` "that player takes 1 fewer Prize card"）挂在 Card 上的修正字段/标志位。
`ecx <= 0` 或 `Card+0x6c bit0` 置位等情形跳过领奖（0x6ec80 `test ecx,ecx; js` / 0x6eca0 `je`）。
领奖方 = `1 - Card+0x44`（对手，0x6ec94 `mov eax,0x1; sub eax,r15d`），推 `SelectPrize(state, winner, count, flag)`（0x183a0）。
`SelectPrize` 内：`flag != 0` 时先推 `CoinPrize`（0x16ee0）掷币决定张数，再 `SelectedPrizeTarget`（0x6b400）择张。
开局发奖由 `DeckToPrize(state, player, n)`（0xb3f0）完成，调用点 `AfterSetupActivePokemon` 0x50c13/0x50c4a。

---

## 4. 胜负判定：reason 1-4 的检查顺序

`State::finishCheck`（0x10fe0）——每玩家累计 `score[i]`：
```
1102f: if (players[sel].prizeCount == 0)        { score[sel] = 1;  reason = 1 }   ; 0 奖赏
11047: if (players[sel].active==0 && bench==0)  { score[1-sel] += 1; reason = 3 } ; 无宝可梦在场
11065: 对另一玩家重复上述两条
1109f: cmp score[0], score[1]
        score[0] <  score[1] → [0x19]=2（玩家1胜）
        score[0] >  score[1] → [0x19]=1（玩家0胜）
        score[0] == score[1] → [0x19]=3（平）
```
返回 0 = 未分胜负（0x110ee `xor r8d,r8d`）。

**reason 枚举与产生点**：
| reason | 语义 | 产生点 | 结果字节 |
|---|---|---|---|
| 1 | 0 张奖赏 | `finishCheck` 0x11042 / `PokemonCheckup` 0x67ddc | 胜者=奖赏拿完方 |
| 2 | 回合开始时牌库 0 张 | `TurnStart` 0x6845e–0x68475：`[P(cur)+0x94]==0` → `[0x1a]=2`，`[0x19]= 2-cur` | 输家=当回合方 |
| 3 | 战斗场无宝可梦 | `finishCheck` 0x11060 / `PokemonCheckup` 0x67d55 | 胜者=对方 |
| 4 | 卡牌效果直接定胜负 | `EffectInstatnt` 0x756b2–0x75705：`[0x1a]=4`，`[0x19]` 由效果目标玩家算出（P=0→1，P=1→2，P=2→3 平） | — |

**检查顺序**：①先奖赏（reason 1）→ ②后无宝可梦（reason 3），二者同帧触发时 reason 取后写的 3；
score 相等 → 平局（`[0x19]=3`）。`TurnStart` 在回合开始额外先跑同一张扫描（0x68037–0x680c7），
再单独判 reason 2。`PokemonCheckup`（0x67ddc–0x67f70）在 Checkup 里也跑一次并把结果写进 `[0x19]/[0x1a]`。
**`[0x19]` 编码 1/2/3 = 玩家0胜/玩家1胜/平**；日志 `RESULT` 的 `result` 字段为 0/1/2（= `[0x19]-1`，见 `S(0xe1ff5)="reason"` / `S(0xe1fee)="result"`）。

---

## 5. 硬币 / 随机数

### 5.1 硬币
`SelectCoinSingle(State, player)`（0x24210）三种模式，取自 `*(State+0x0)` 的随机上下文：
1. `ctx+0x231 != 0` → **manual_coin**（0x24251 `jne 24380`）：**完全不消耗 RNG**，改为向玩家发选择
   （0x243de `mov esi,0x2` + `State::addOption` 0x243e3，SelectContext `COIN_HEAD=46`，.rodata `S(0xe12a6)="CoinHead"`），
   回调 `SelectedCoinSingle`（0x24b40）：玩家选 YES → `State+0x3c += 1`（0x24bcf–0x24bd5），即自选正/反面。
   `manual_coin` 的写入点在 `Search::start` 0x50675–0x5067d（`movzx edx,[rbp+0x0]; mov rax,[r12]; mov BYTE PTR [rax+0x231],dl`）。
2. `ctx+0x233 != 0` → **真随机**（0x24257 `jne 24308`）：`std::random_device("default")`（0x24317 起构造
   `"default"` 串 + `random_device::_M_init` + `_M_getval`），非确定性。
3. 否则 → **MT19937**：0x24265 `mov rax,[r13+0x15b8]`（MT 索引）/ 0x24278 `mov rbx,[r13+rax*8+0x238]`（状态数组），
   标准 tempering 常数 `0x9d2c5680`（0x2429e）/ `0xefc60000`（0x242ad）/ 移位 11/7/15/18 —— 即 `std::mt19937`。

**结果编码**：`State+0x3c` = **正面次数（heads count）**，两条独立证据：
- MT 路径：0x242bf `and ebx,0x1` / 0x242c2 `jne` / 0x242c4 `add DWORD PTR [rbp+0x3c],1`
  → **随机位 == 0 才 `+1`**，故 **位值 0 = 正面(heads)**，1 = 反面。
- 手选路径：`SelectedCoinSingle` 0x24bcf `cmp r13b,0x1`（选中的 OptionType）/ 0x24bd3 `jne` /
  0x24bd5 `add DWORD PTR [rbx+0x3c],1` → **选"YES(正面)"才 `+1`**。

引擎把 `State+0x3c > 0` 用作"正面"分支条件（`AfterSleepProc` 0x38830 `test eax,eax; jg` → 醒；
`AfterBurnProc` 0x38983 `jg` → 解除灼伤；`ConfuseProc` 0x818c3 `jg` → 攻击成功）。
掷币记 `LogType.COIN(0x16)`（0x2442c `mov BYTE PTR [rsp+0xf],0x16`），args = `[playerIndex, bit]`，
`head` 字段（`S(0xe1fe2)="head"`）在 MT 路径存的是**原始随机位**（0x24463 `mov ...,ebx`），
与上面"0=正面"的编码**极性相反**——建议消费端以 `State+0x3c` 语义为准，`head` 字段当作 raw bit（见 §9 限界）。

**派生掷币形态**（供卡面效果用）：`SelectCoin`(0x173c0, 多枚)、`SelectCoinUntilTail`(0x27550)、
`SelectCoinSingle`(0x24210)、`AfterSelectCoin`(0x58b50)、`AfterSelectCoin2`(0x16d60)、
`CoinPrize`(0x16ee0 奖赏张数掷币)、`CoinLuckyBonus`(0x16c10)、`AttackCoinProc/2`(0x…/0x80b80)、
`AttackDamageCoin`(0x17a90)、`AttackNoDamageCoin`(0x714e0)、`SelectCoinUntilTail` 系列。

### 5.2 洗牌 RNG 与种子入口
`ShuffleDeck(State, player, bool)`（0x244f0）：
- `ctx+0x233 != 0` → `std::shuffle(..., std::random_device)`（0x245f0 分支，非确定）
- 否则 → `std::shuffle(..., std::mt19937&)`，引擎体在 `ctx+0x238`，索引 `ctx+0x15b8`（0x24561–0x24573）。
- 洗牌记 `LogType.SHUFFLE(0x00)`（0x2458e–0x245b9）。

**种子入口：无**。`ApiAgentStart`（0x13740）在 0x137d4 `mov QWORD PTR [r12+0x238], 0x1571`
以 **固定常数 5489（0x1571，`std::mt19937` 的默认种子）** 初始化状态数组
（0x137e0–0x13807 标准 `x[i] = 0x6c078965*(x[i-1]^(x[i-1]>>30)) + i`，624 词），
0x13855 `mov QWORD PTR [r12+0x15b8], 0x270`（索引置 624 触发再生成）。
导出面 `GameInitialize / BattleStart / BattleStartReverse / SearchBegin` 的参数表中**均无 seed**
（见 `sim.py` 的 `argtypes`），故**每次对局的洗牌/硬币序列完全确定可复现**，除非开启 `ctx+0x233` 真随机位。

---

## 6. 伤害修饰：W&R 前 / 后两类

流水线（三处 `CalcDamage` 调用点一致）：
`AttackDamage`(0x7ee20) / `AfterAttackDamageCoin`(0x6ff10) / `EffectAttackDamage`(0x724b0)
→ `CalcDamage`(0x9c10) → `AddDamage`(0x55a40)。

1. **W&R 之前的修饰类**（卡面 "…(before applying Weakness and Resistance)"，`S(0xe2225)`、`S(0xe27128)`）
   → 累加进 **`State+0x100`**（`EffectInstatnt` 0x76d31/0x76d6f、0x76f62/0x76fad 等多处 `add DWORD PTR [r15+0x100], …`），
   在 `AttackDamage` 0x7eec6 `mov r12d,[rbp+0x100]` / 0x7eed1 `add r12d,[rbx+0x8]`（+ `Attack.damage`）后
   **送入 `CalcDamage`**。
2. **`CalcDamage` 内**：弱点 ×2 → 抗性 −30 → 下限 0（已破解，不重做）。
3. **W&R 之后的修饰类**（"…takes 30 less damage from attacks (after applying Weakness and Resistance)"，
   `S(0xe27185)`、`S(0xe27246)`）→ 在 `CalcDamage` 返回之后、`AddDamage` 之前/之内应用。
   已确证的结构事实：`CalcDamage` 返回值 `eax` 直接作为 `AddDamage` 的 `ecx`（0x70025→0x70084、0x72572→0x725d3、
   0x7ef24→0x7ef50 尾调 `AttackDamage2`），中间无第二次 W&R 运算；`AddDamage` 内读 `Card+0x78`(int16) 与
   `CardMaster+0x08` 做 HP 相关比较（0x55a99–0x55ab8），并有 `CardMaster+0x5==4`（Mega ex）+ 伤害 ≥ 0xf0 的特判（0x55cb0–0x55cbc）。
   **未定论**：承载"after W&R"减伤的具体字段未一一对上（候选 `Card+0x1c`(int16，仅 `AttackDamage` 0x7eeef/0x7f014 读，
   非零走旁路)、`State+0x104`（0x70df9/0x715b7 写，0x7923b 读，0x80e24 清））。
   另有能量卡位掩码判定（`OR` 全部附着能量字的位 0x40，0x56f08–0x5704a）与 `PlayerState+0x254` 附加修正的分支。

**顺序结论**：`攻击基础值 + Σ(before-W&R 修饰)` → `×弱点2` → `−抗性30` → `max(0,…)` → `Σ(after-W&R 修饰)` → 落 HP。

---

## 7. SearchBegin / SearchStep 状态机

### 7.1 导出签名（`sim.py`/`api.py` 交叉）
`SearchBegin(agent_ptr, sbi, sbi_len, your_deck[], your_prize[], opp_deck[], opp_prize[], opp_hand[], opp_active[], manual_coin)`
→ `ApiResult{state: SearchState{observation, searchId}, error:int}`；
`SearchStep(agent_ptr, search_id, select[], len)`；`SearchEnd(agent_ptr)`；`SearchRelease(agent_ptr, id)`。

### 7.2 状态机与并发
- `Search::alloc(const State&)`（0x22b90）：从状态池取一块复制出新节点；`Search::start(config, state)`（0x4ffc0）建根。
- `searchId` 是**状态向量下标**：`SearchStep` 0xd1f1–0xd1f8 `cmp r13, rax; jge → error 1`（越界即"无此 search_id"）。
  `SearchRelease` 回收（对应 error 2 "Released item"）。
- **并发上限**：未发现显式条数上限常量；`agent_ptr` 是单例（`ApiAgentStart` 0x13740 一次性分配，`api.py` 用全局缓存），
  **同一进程内多个 `agent_ptr` 会互相踩随机上下文/状态池**（与 fna-016 记录的"抢原生 libcg 缓冲"现象一致）。
- `Search::start` 的 λ（0x38ab0、0x3e890）负责把预测牌表灌入 `FixedList`，`manual_coin` 在 0x50675–0x5067d
  `movzx edx,BYTE PTR [rbp+0x0]; mov rax,[r12]; mov BYTE PTR [rax+0x231],dl` 写入随机上下文
  → **`manual_coin` 就是 `ctx+0x231` 位**（见 §5.1）。

### 7.3 错误码枚举
**SearchStep**（0xc770）：
| 码 | 条件 | 证据 |
|---|---|---|
| 0 | 成功 | 0xc78b `mov [rsp+0x10],eax`（初始） |
| **1** | search_id 不存在（下标越界） | 0xd240 `mov DWORD PTR [rsp+0x10],0x1` |
| **2** | 已释放的条目 | 由 `Search::alloc`/池校验返回（api.py 文案"Released item."） |
| **3** | 对局已结束 | 0xd21a `mov DWORD PTR [rsp+0x10],0x3`，条件 0xd20f `cmp BYTE PTR [r13+0x19],0x0; je` |
| **4** | `len(select)` 越界 min/max | `State::checkPlayerSelect` 0x3bbbb / 0x3bd50 / 0x3bdc9 `mov eax,0x4` |
| **5** | 选项下标越界 | `checkPlayerSelect` 0x3bd19 `mov eax,0x5` |
| **6** | 选项重复 | `checkPlayerSelect` 0x3bcbf `mov eax,0x6` |
| **30** | `agent_ptr` 损坏（`[agent+0x6f98] != 2`） | 0xc785 读 / 0xc78f `cmp eax,0x2` / 0xc798 `mov ...,0x1e` |

**SearchBegin**（0xd680）：
| 码 | 条件 | 证据 |
|---|---|---|
| **1** | 无效 cardId | api.py 文案；由 `Search::start` 的灌表 λ 抛出 |
| **2** | active 必须是宝可梦卡 ID | api.py 文案 |
| **99** | **No Basic Pokemon**（起手无基础宝可梦） | 抛出点 `SetupActivePokemon` 0x43ee8–0x43f02，字符串 `S(0xe27f8)="No Basic Pokemon."` |
| **30** | `agent_ptr` 损坏 | 0xd6c8 `cmp DWORD PTR [rdi+0x6f98],0x2` / 0xd6d5 `mov ...,0x1e` |

### 7.4 "buffer full. capacity: N"
字符串 `S(0xe1b5e) = "buffer full. capacity:"`，被 `FixedListBase::checkFull` 系列抛出
（引用点 0x8e7c/0x8efc/0xaa03/0xb8d9…）。容量由模板参数决定：
- `FixedListBase<int,int,7>`（0x8eb0）→ **capacity 7 = 单条 Log 的 int 参数槽上限**（`Log.args` 最多 7 个 int）；
- `FixedListBase<int,CardRef,61>`（0x8eb0 同族）→ 61 = 牌表容量（60 张 + 余量）；
- `FixedListBase<char,CardRef,8>` → 后备区 8；`<char,CardRef,1>` → 战斗场 1；
- `FixedListBase<AreaType,2>` / `<AreaType,4>` → AreaRef 列表 2/4。
**故 fna-016 记录的 `buffer full capacity:7` = Log 参数槽溢出**（单条日志塞了 >7 个 int 参数），
不是"搜索并发缓冲 7"。相关：`State::pushCardRef unexpected area`（`S(0xe1c84)`）、
`negative index`（`S(0xe1ce0)`）、`invalid index`（`S(0xe1026)`/`S(0xe1cf0)`）、
`invalid select`（`S(0xe1034)`）、`invalid target type`（`S(0xe25d7)`）。

---

## 8. 其他取证（顺带）

- **Antique 化石（pokemonType==2）**：`EffectPoison/Burn/Sleep/…` 一律 `cmp BYTE PTR [master+0x5],0x2; je 跳过`
  （0x3c81e/0x3c9ee/0x3cb2e/0x3cd4e/0x3cefe/0x3d21f/0x3d323/0x3d423/0x3d4aa）→ **免疫全部特殊状态**；
  `MainSelect` 0x674a9 `je 674d6` → **不能撤退**；`retreatCost` 路径 0x6741e `je` → 费用记 0。
- **先手/检查方推导**：`((turn+1) ^ firstPlayer) & 1`（`ParalyzeProc` 0x386b0–0x386d2、`KOProc2` 0x57fc7–0x57fdc）。
- **后备上限**：`PlayerState+0x255` 低 4 位，0 → 5（`PokemonCheckupEnd` 0x824ee）。
- **日志类型枚举**与 `api.py` 的 `LogType` 一致（`S(0xe1e94)` 起："Shuffle/HasBasicPokemon/TurnStart/TurnEnd/
  DrawReverse/MoveCard/…/Poisoned(0x11)/Burned(0x12)/Asleep(0x13)/Paralyzed(0x14)/Confused/Result(0x17)"）。
  `Log.args` 为 `FixedList<int,7>`，`LogJson` 0x2f940。
- **SelectType / SelectContext / OptionType 三套枚举**字符串分别在 `S(0xe10d5)`、`S(0xe1a1f)`，
  与 `api.py` 完全对应（`Main/SetupActivePokemon/…/IsFirst(33)/Mulligan(34)/CoinHead(38)/…`）。
- **胜负字段**：`State+0x19` 1/2/3 = 玩家0胜/玩家1胜/平；`State+0x1a` = reason 1..4。
- **`Search::start` 里的 `error` JSON 键**：`S(0xe10cf)="error"`，`ApiResult` 键序 `state`/`error`（`S(0xe10b4)`）。

---

## 9. 置信声明

| 结论 | 置信 |
|---|---|
| 中毒 `value×10+mod`、灼伤 `20+mod`、睡眠/麻痹/混乱的解除与行动限制 | **高**（常数与位运算直接可读，且与官方规则文本一致） |
| 混淆掷反面→自伤 30 + 攻击失败 | **高**（`mov ecx,0x1e` + `AddDamage` 直读） |
| 每回合一次性位段（0x32）与门禁地址 | **高** |
| 先手首回合禁攻击（`turn<=1` + `Attack+0xe bit3` 豁免） | **高** |
| 奖赏 1/2/3 分支 | **高**（`cmp al,0x3/0x4` + `lea edx,[rdx+rdx+1]`） |
| reason 1-4 与 `[0x19]` 编码 | **高** |
| MT19937 固定种子 5489、无种子入口、manual_coin=`ctx+0x231` | **高** |
| `State+0x3c`=正面数（MT 位 0=正面 / 选 YES=正面） | **高** |
| `Log.COIN.head` 字段极性与 `State+0x3c` 相反（存 raw bit） | **中**（反汇编直读，疑为日志极性不一致，建议运行时对拍一次） |
| error 码 1/3/4/5/6/30 | **高**；error 2/99 为代码+文案互证（99 的抛出点已定位） |
| "buffer full capacity:7" = Log 参数槽 | **中高**（`FixedListBase<int,int,7>::checkFull` 直读） |
| W&R 前修饰 = `State+0x100` | **高** |
| W&R 后修饰的具体承载字段 | **低-中**（流水线顺序确定，字段未定） |
| 并发上限 | **未找到显式常量**（仅观察到单 `agent_ptr` 单例语义） |
