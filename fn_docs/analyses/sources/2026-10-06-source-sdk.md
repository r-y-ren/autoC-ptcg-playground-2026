# cabt 引擎 Python SDK 源码契约与枚举表（docstring 为权威语义）

- 抓取日期: 2026-10-06（源码本地读取，非网络抓取）
- 来源（两份对照）:
  - 对手工程版: `references/opponents/pokemon-tcg-ai-battle-agent/cg/{api.py,utils.py,game.py,sim.py}`
  - wheel 安装版: `fn_work/.venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cg/{api.py,utils.py,game.py,sim.py}` + 环境层 `.../envs/cabt/cabt.py`、`cabt.json`
- 两版关系: `api.py`、`utils.py` **逐字节相同**；`game.py`、`sim.py` 有差异（见 §0.3）。以下契约以两版共同内容为准，差异处显式标注。
- 全局前向兼容警告（源码原文注释）: "new elements may be appended to the Enum during the competition"、"new attributes may be appended to each class during the competition"——枚举可能追加新值、数据类可能追加新字段，解析必须防御性（按值分派时留 default 分支；`to_dataclass` 会静默丢弃未知 key）。

---

## 0. 文件布局与版本差异

### 0.1 模块职责

| 文件 | 职责 |
|---|---|
| `sim.py` | ctypes 加载原生引擎（`cg.dll`/`libcg.so`），声明各 FFI 签名；定义 `StartData`/`SerialData` 结构体与进程级单例 `Battle` |
| `game.py` | **对局层**（整场真实对战）: `battle_start/battle_finish/battle_select/visualize_data` |
| `api.py` | **搜索层**（引擎内前瞻/推演）: 全部枚举、观测数据类、`all_card_data/all_attack/to_observation_class/search_begin/search_step/search_end/search_release` |
| `utils.py` | `to_dataclass`（dict→dataclass 递归转换）、`json_to_dataclass`（bytes→dataclass） |
| `cabt.py` | kaggle_environments 环境层: interpreter/renderer/bo3 组织/内置 agent |
| `cabt.json` | 环境规格: 超时、bo 配置、reward、action 形态 |

### 0.2 ctypes 结构体（sim.py）

| 结构体 | 字段 | 类型 | 语义 |
|---|---|---|---|
| `StartData` | `battlePtr` | `c_void_p` | 对局指针；None/0 表示开战失败（牌表非法） |
| | `errorPlayer` | `c_int` | 出错玩家索引；>=0 表示该玩家牌表非法 |
| | `errorType` | `c_int` | 错误类型码（**Python 层无任何文档**，取值不可考） |
| `SerialData` | `json` | `c_char_p` | 观测 JSON 字符串 |
| | `data` | `POINTER(c_ubyte)` | 附带二进制 blob（`search_begin_input` 的来源） |
| | `count` | `c_int` | blob 字节长度 |
| | `selectPlayer` | `c_int` | 当前要选择的玩家索引 |

进程级单例 `Battle`: `battle_ptr` / `obs`（wheel 版追加 `decks` / `result=[0,0,0]` / `vis=[]` / `last_step=0`，cabt.py 依赖这些字段）。

### 0.3 两版差异（wheel vs 对手工程）

| 项 | 对手工程版 | wheel 版 |
|---|---|---|
| `game.battle_start` 签名 | `(deck0, deck1)` | `(deck0, deck1, reverse_player=False)`，docstring: "When True, the second player can choose whether to go first or second."；为 True 走 `lib.BattleStartReverse(arg)`（wheel 新增 FFI 入口，restype/argtypes 与 BattleStart 相同） |
| `sim.py` 平台选择 | `os.name=='nt'`→cg.dll，否则 libcg.so | `platform.system()`: Windows→cg.dll / Darwin→libcg.dylib / arm64→libcg-arm64.so / 否则 libcg.so |
| `sim.py` FFI 声明 | 含 `AgentStart/SearchBegin/SearchStep/SearchEnd/SearchRelease/AllCard/AllAttack` 的 restype/argtypes | **缺这些声明**（仅声明 BattleStart/BattleStartReverse/BattleFinish/GetBattleData/Select/VisualizeData）。api.py 相同却会调用这些入口——wheel 下 ctypes 默认 restype=c_int，指针会被截断，属**装载缺陷**（见 §6） |
| `Battle` 类字段 | 2 个 | 6 个（+decks/result/vis/last_step） |

---

## 1. 枚举逐值表（值 → 英文名 → 中文语义）

### 1.1 EnergyType（12 值，0–11）能量属性

| 值 | 英文名 | 中文语义 |
|---|---|---|
| 0 | COLORLESS | 无色 |
| 1 | GRASS | 草 |
| 2 | FIRE | 火 |
| 3 | WATER | 水 |
| 4 | LIGHTNING | 雷 |
| 5 | PSYCHIC | 超能 |
| 6 | FIGHTING | 格斗 |
| 7 | DARKNESS | 恶 |
| 8 | METAL | 钢 |
| 9 | DRAGON | 龙 |
| 10 | RAINBOW | 彩虹（Every Types，全属性） |
| 11 | TEAM_ROCKET | 火箭队（PSYCHIC and DARKNESS，超+恶双属性） |

### 1.2 CardType（7 值，0–6）卡牌类别

| 值 | 英文名 | 中文语义 |
|---|---|---|
| 0 | POKEMON | 宝可梦卡 |
| 1 | ITEM | 道具卡（Item） |
| 2 | TOOL | 宝可梦道具卡（Pokémon Tool） |
| 3 | SUPPORTER | 支援者卡 |
| 4 | STADIUM | 竞技场卡 |
| 5 | BASIC_ENERGY | 基本能量卡 |
| 6 | SPECIAL_ENERGY | 特殊能量卡 |

### 1.3 AreaType（12 值，1–12，注意从 1 起）区域类型

| 值 | 英文名 | 中文语义 |
|---|---|---|
| 1 | DECK | 牌库 |
| 2 | HAND | 手牌 |
| 3 | DISCARD | 弃牌区（Discard Pile） |
| 4 | ACTIVE | 战斗场（Active Spot） |
| 5 | BENCH | 备战区 |
| 6 | PRIZE | 奖赏卡区 |
| 7 | STADIUM | 场地卡区 |
| 8 | ENERGY | （宝可梦身上的）附加能量卡区 |
| 9 | TOOL | （宝可梦身上的）附加道具卡区 |
| 10 | PRE_EVOLUTION | 进化前形态（场上宝可梦的退化下层卡） |
| 11 | PLAYER | 玩家（源码无注释；按命名指"玩家本身"，用于非卡牌目标的效果） |
| 12 | LOOKING | 正在查看的牌（The card you are looking） |

### 1.4 SelectType（11 值，0–10）选择类型（决定合法 OptionType 集合）

| 值 | 英文名 | 中文语义 | 允许的 OptionType（源注释） |
|---|---|---|---|
| 0 | MAIN | 回合主操作 | PLAY, ATTACH, EVOLVE, ABILITY, DISCARD, RETREAT, ATTACK, END |
| 1 | CARD | 选卡牌 | CARD |
| 2 | ATTACHED_CARD | 选附加卡 | TOOL_CARD, ENERGY_CARD |
| 3 | CARD_OR_ATTACHED_CARD | 选卡或附加卡 | CARD, TOOL_CARD, ENERGY_CARD |
| 4 | ENERGY | 选能量（能量单位） | ENERGY |
| 5 | SKILL | 选技能发动顺序 | SKILL |
| 6 | ATTACK | 选招式 | ATTACK |
| 7 | EVOLVE | 选进化（源+目标） | EVOLVE |
| 8 | COUNT | 选数量 | NUMBER |
| 9 | YES_NO | 是/否 | YES, NO |
| 10 | SPECIAL_CONDITION | 选特殊状态 | SPECIAL_CONDITION |

### 1.5 SelectContext（49 值，0–48）选择情境（"在选什么"）

| 值 | 英文名 | 中文语义（源注释译） | 形态 |
|---|---|---|---|
| 0 | MAIN | 主选择（回合主操作选择） | Main |
| 1 | SETUP_ACTIVE_POKEMON | Set Up 阶段选择放入战斗场的宝可梦 | Card |
| 2 | SETUP_BENCH_POKEMON | Set Up 阶段选择放入备战区的宝可梦 | Card |
| 3 | SWITCH | 选择与战斗场互换的宝可梦 | Card |
| 4 | TO_ACTIVE | 选择放入战斗场的宝可梦 | Card |
| 5 | TO_BENCH | 选择放入备战区的宝可梦 | Card |
| 6 | TO_FIELD | 选择放进场上的宝可梦 | Card |
| 7 | TO_HAND | 选择加入手牌的卡 | Card |
| 8 | DISCARD | 选择要弃掉的卡 | Card |
| 9 | TO_DECK | 选择放回牌库的卡 | Card |
| 10 | TO_DECK_BOTTOM | 选择放回牌库底的卡 | Card |
| 11 | TO_PRIZE | 选择加入奖赏的卡 | Card |
| 12 | NOT_MOVE | 选择留在原地的卡 | Card |
| 13 | DAMAGE_COUNTER | 选择放置伤害指示物的宝可梦 | Card |
| 14 | DAMAGE_COUNTER_ANY | 按自选数量放置伤害指示物的宝可梦 | Card |
| 15 | DAMAGE | 选择造成伤害的宝可梦 | Card |
| 16 | REMOVE_DAMAGE_COUNTER | 选择移除伤害指示物的宝可梦 | Card |
| 17 | HEAL | 选择治疗的宝可梦 | Card |
| 18 | EVOLVES_FROM | 选择进化的下层（进化源） | Card |
| 19 | EVOLVES_TO | 选择进化成的目标 | Card |
| 20 | DEVOLVE | 选择退化的宝可梦 | Card |
| 21 | ATTACH_FROM | 选择被附加卡的宝可梦 | Card |
| 22 | ATTACH_TO | 选择要贴到宝可梦身上的卡 | Card |
| 23 | DETACH_FROM | 选择移除附加卡来源的宝可梦 | Card |
| 24 | LOOK | 选择要查看的卡 | Card |
| 25 | EFFECT_TARGET | 选择效果作用目标卡 | Card |
| 26 | DISCARD_ENERGY_CARD | 选择要弃掉的能量卡 | AttachedCard |
| 27 | DISCARD_TOOL_CARD | 选择要丢弃的宝可梦道具 | AttachedCard |
| 28 | SWITCH_ENERGY_CARD | 选择被替换的能量卡 | AttachedCard |
| 29 | DISCARD_CARD_OR_ATTACHED_CARD | 选择要弃掉的卡或附加卡 | CardOrAttachedCard |
| 30 | DISCARD_ENERGY | 选择要弃掉的能量（单位） | Energy |
| 31 | TO_HAND_ENERGY | 选择回手的能量 | Energy |
| 32 | TO_DECK_ENERGY | 选择回牌库的能量 | Energy |
| 33 | SWITCH_ENERGY | 选择要替换的能量 | Energy |
| 34 | SKILL_ORDER | 选择效果发动顺序 | Skill |
| 35 | ATTACK | 选择要使用的招式 | Attack |
| 36 | DISABLE_ATTACK | 选择要禁用的招式 | Attack |
| 37 | EVOLVE | 选择进化源与进化目标（成对） | Evolve |
| 38 | DRAW_COUNT | 选择抽卡张数 | Count |
| 39 | DAMAGE_COUNTER_COUNT | 选择放置伤害指示物数量 | Count |
| 40 | REMOVE_DAMAGE_COUNTER_COUNT | 选择移除伤害指示物数量 | Count |
| 41 | IS_FIRST | 是否要先手？（"Would you like to go first?"） | YesNo |
| 42 | MULLIGAN | 是否重新抽牌？ | YesNo |
| 43 | ACTIVATE | 是否发动效果？ | YesNo |
| 44 | FIRST_EFFECT | 是否选择先发动的效果？ | YesNo |
| 45 | MORE_DEVOLVE | 是否继续退化？ | YesNo |
| 46 | COIN_HEAD | 是否选正面？ | YesNo |
| 47 | AFFECT_SPECIAL_CONDITION | 选择要陷入的特殊状态 | SpecialCondition |
| 48 | RECOVER_SPECIAL_CONDITION | 选择要恢复的特殊状态 | SpecialCondition |

（源码注释: 竞赛期间可能追加新元素。）

### 1.6 OptionType（17 值，0–16）选项类型（决定 Option 哪些字段有效）

| 值 | 英文名 | 中文语义 | 有效字段（源注释） |
|---|---|---|---|
| 0 | NUMBER | 数字选择 | number(int): Count |
| 1 | YES | 选"是" | — |
| 2 | NO | 选"否" | — |
| 3 | CARD | 选卡牌 | area(AreaType)+index(int)+playerIndex(int) |
| 4 | TOOL_CARD | 选宝可梦道具卡 | area+index+playerIndex（均指被附着宝可梦）+toolIndex(int) |
| 5 | ENERGY_CARD | 选能量卡 | area+index+playerIndex（均指被附着宝可梦）+energyIndex(int) |
| 6 | ENERGY | 选能量（单位） | area+index+playerIndex（被附着宝可梦）+energyIndex+count(int: 该能量对应多少单位) |
| 7 | PLAY | 从手牌出牌 | index(int): 手牌内下标 |
| 8 | ATTACH | 把卡贴到宝可梦 | area+index（被贴的卡）+inPlayArea(AreaType)+inPlayIndex(int)（场上宝可梦） |
| 9 | EVOLVE | 选择进化 | area+index（进化卡）+inPlayArea+inPlayIndex（场上宝可梦） |
| 10 | ABILITY | 使用特性 | area+index |
| 11 | DISCARD | 弃掉场上的卡 | area+index |
| 12 | RETREAT | 战斗宝可梦撤退 | — |
| 13 | ATTACK | 选招式 | attackId(int) |
| 14 | END | 回合结束 | — |
| 15 | SKILL | 选择卡牌技能顺序 | cardId(int: 为 0 表示处理特殊状态)+serial(int) |
| 16 | SPECIAL_CONDITION | 选特殊状态 | specialConditionType(SpecialConditionType) |

### 1.7 LogType（24 值，0–23）事件类型（各值字段见 §4）

SHUFFLE=0, HAS_BASIC_POKEMON=1, TURN_START=2, TURN_END=3, DRAW=4, DRAW_REVERSE=5, MOVE_CARD=6, MOVE_CARD_REVERSE=7, SWITCH=8, CHANGE=9, PLAY=10, ATTACH=11, EVOLVE=12, DEVOLVE=13, MOVE_ATTACHED=14, ATTACK=15, HP_CHANGE=16, POISONED=17, BURNED=18, ASLEEP=19, PARALYZED=20, CONFUSED=21, COIN=22, RESULT=23。

### 1.8 SpecialConditionType（5 值，0–4）特殊状态

| 值 | 英文名 | 中文语义 |
|---|---|---|
| 0 | POISON | 中毒 |
| 1 | BURN | 灼伤 |
| 2 | SLEEP | 睡眠 |
| 3 | PARALYZE | 麻痹 |
| 4 | CONFUSE | 混乱 |

---

## 2. 数据类字段表

### 2.1 Card（场上/区域内一张已知卡）

| 字段 | 类型 | 语义 |
|---|---|---|
| id | int | CardData ID |
| serial | int | 对局内每张卡唯一序列号 |
| playerIndex | int | 归属玩家 |

### 2.2 Pokemon（场上宝可梦）

| 字段 | 类型 | 语义 |
|---|---|---|
| id | int | CardData ID |
| serial | int | 对局内唯一序列号 |
| hp | int | 当前 HP |
| maxHp | int | 当前最大 HP |
| appearThisTurn | bool | 本回合刚进场 |
| energies | list[EnergyType] | 能量数组（按单位） |
| energyCards | list[Card] | 附加能量卡数组 |
| tools | list[Card] | 附加宝可梦道具数组 |
| preEvolution | list[Card] | 进化前卡链数组 |

### 2.3 PlayerState（单方玩家状态）

| 字段 | 类型 | 语义 |
|---|---|---|
| active | list[Pokemon \| None] | 战斗宝可梦（背面向为 None）；长度 0 或 1 |
| bench | list[Pokemon] | 备战宝可梦 |
| benchMax | int | 备战区上限 |
| deckCount | int | 牌库剩余张数 |
| discard | list[Card] | 弃牌区 |
| prize | list[Card \| None] | 奖赏卡（背面向为 None）；首元素=奖赏底，末元素=奖赏顶 |
| handCount | int | 手牌张数 |
| hand | list[Card] \| None | 手牌数组；**对手恒为 None** |
| poisoned/burned/asleep/paralyzed/confused | bool | 战斗宝可梦对应特殊状态 |

### 2.4 State（对局全局状态，即 Observation.current）

| 字段 | 类型 | 语义 |
|---|---|---|
| turn | int | 回合计数: 1=先手第 1 回合, 2=后手第 1 回合, 3=先手第 2 回合…; 0=先手首回合前 |
| turnActionCount | int | 本回合已执行动作数 |
| yourIndex | int | 当前做选择的玩家索引（0/1） |
| firstPlayer | int | 先手玩家索引；未定时 -1 |
| supporterPlayed | bool | 本回合已用过支援者 |
| stadiumPlayed | bool | 本回合已用过竞技场 |
| energyAttached | bool | 本回合手动贴能量已用 |
| retreated | bool | 本回合已撤退 |
| result | int | 胜方索引；-1=未结束（0/1=胜者，2=平局——由 LogType.RESULT 的 result 语义推得） |
| stadium | list[Card] | 场地卡（长度 0 或 1） |
| looking | list[Card \| None] \| None | 正在查看的卡（背面向为 None）；未在看则 None |
| players | list[PlayerState] | 双方状态，固定 2 元素 |

### 2.5 Option（一个可选项）

| 字段 | 类型 | 默认 | 语义 |
|---|---|---|---|
| type | OptionType | 必填 | 决定其余哪些字段有效（见 §1.6） |
| number | int \| None | None | Count 用 |
| area | AreaType \| None | None | 卡所在区域 |
| index | int \| None | None | 区域内下标 |
| playerIndex | int \| None | None | 卡归属玩家 |
| toolIndex | int \| None | None | 道具内下标 |
| energyIndex | int \| None | None | 能量卡内下标 |
| count | int \| None | None | 能量单位数 |
| inPlayArea | AreaType \| None | None | 场上目标宝可梦区域 |
| inPlayIndex | int \| None | None | 场上目标下标 |
| attackId | int \| None | None | 招式 ID |
| cardId | int \| None | None | 卡 ID |
| serial | int \| None | None | 卡序列号 |
| specialConditionType | SpecialConditionType \| None | None | 特殊状态类型 |

### 2.6 SelectData（一次选择请求）

| 字段 | 类型 | 语义 |
|---|---|---|
| type | SelectType | 选择类型 |
| context | SelectContext | 在选什么 |
| minCount | int | 最少选几个（可为 0） |
| maxCount | int | 最多选几个（不超过 len(option)） |
| remainDamageCounter | int | 还可放置的伤害指示物数 |
| remainEnergyCost | int | type=Energy 时剩余所需能量数 |
| option | list[Option] | 可选项数组 |
| deck | list[Card] \| None | 仅当从牌库选卡时非 None（牌库可见卡数组） |
| contextCard | Card \| None | 本次选择相关的卡；仅 context=Activate（ACTIVATE）时下发，否则 null |
| effect | Card \| None | 当前正在结算效果的卡 |

### 2.7 Log（事件；全字段可空，按 type 分派，见 §4）

字段全集: `type: LogType`（必填）, `playerIndex, hasBasicPokemon, cardId, serial, fromArea, toArea, cardIdActive, serialActive, cardIdBench, serialBench, cardIdBefore, serialBefore, cardIdAfter, serialAfter, cardIdTarget, serialTarget, attackId, value, putDamageCounter, isRecover, head, result, reason`（均 `X | None = None`）。

### 2.8 Observation（agent 收到的观测）

| 字段 | 类型 | 语义 |
|---|---|---|
| select | SelectData \| None | 选择信息；**初始交牌表时为 None** |
| logs | list[Log] | 自上次选择以来发生的事件 |
| current | State \| None | 当前状态；初始交牌表时为 None |
| search_begin_input | str \| None = None | 传给 search_begin 的输入（引擎附带 blob 的 ASCII 解码） |

### 2.9 SearchState / ApiResult

| 类 | 字段 | 类型 | 语义 |
|---|---|---|---|
| SearchState | observation | Observation | 新观测（其 search_begin_input 恒为 None） |
| | searchId | int | 搜索状态 ID |
| ApiResult | state | SearchState \| None | 搜索状态 |
| | error | int | 非 0 即错误码 |

### 2.10 Skill / CardData / Attack（卡数据库）

Skill: `name: str`（技能名）, `text: str`（说明）。源注释: "Abilities and effects at the time of card play."

CardData:

| 字段 | 类型 | 语义 |
|---|---|---|
| cardId | int | 卡 ID |
| name | str | 卡名 |
| cardType | CardType | 卡类别 |
| retreatCost | int | 撤退能量花费 |
| hp | int | HP |
| weakness | EnergyType \| None | 弱点 |
| resistance | EnergyType \| None | 抵抗 |
| energyType | EnergyType | 宝可梦属性或基本能量属性 |
| basic / stage1 / stage2 | bool | 基础/一阶/二阶进化 |
| ex | bool | Pokémon ex（含 Mega ex）；被击倒对手拿 2 奖（Mega ex 除外） |
| megaEx | bool | Mega Evolution ex；被击倒对手拿 3 奖 |
| tera | bool | Tera 宝可梦；在备战区不受招式伤害 |
| aceSpec | bool | ACE SPEC；牌组中此类卡至多 1 张 |
| evolvesFrom | str \| None | 进化源卡名，未进化为 None |
| skills | list[Skill] | 持有技能 |
| attacks | list[int] | 可用招式 ID 列表 |

Attack: `attackId: int`, `name: str`, `text: str`, `damage: int`, `energies: list[EnergyType]`（所需能量）。

### 2.11 utils.to_dataclass 转换语义（影响解析行为）

- dict→dataclass 递归；`None`→`None`；**字典中不在字段表里的 key 静默丢弃**（故 cabt.py 注入的 `win/draw/round` 被 to_observation_class 忽略）。
- list 字段: 元素类型经 `__args__` 逐层解包（支持 `list[Pokemon | None]` 等）；元素非 dataclass（如 `list[EnergyType]`）则原样保留 int。
- 缺 key 的必填字段会在 `cls(**d)` 处 TypeError（因此引擎必须下发全字段）。

---

## 3. 函数签名与契约

### 3.1 api.py（搜索层）

| 函数 | 签名 | 契约/参数约束 | 错误语义 |
|---|---|---|---|
| `all_card_data` | `() -> list[CardData]` | 无参；`lib.AllCard()` JSON→dataclass。返回全部卡 | 无 Python 层检查 |
| `all_attack` | `() -> list[Attack]` | 无参；`lib.AllAttack()` JSON→dataclass。返回全部招式 | 同上 |
| `to_observation_class` | `(obs: dict) -> Observation` | dict→Observation 递归；未知 key 丢弃 | 缺必填字段→TypeError |
| `search_begin` | `(agent_observation: Observation, your_deck: list[int], your_prize: list[int], opponent_deck: list[int], opponent_prize: list[int], opponent_hand: list[int], opponent_active: list[int], manual_coin: bool = False) -> SearchState` | 见下方展开 | 见下方展开 |
| `search_step` | `(search_id: int, select: list[int]) -> SearchState` | `select` 是 **option 数组下标**（不是 OptionType） | 见下方展开 |
| `search_end` | `() -> None` | 结束搜索；搜索内存供下次搜索复用 | — |
| `search_release` | `(search_id: int) -> None` | 删除指定 ID 状态，内存可复用 | — |

`search_begin` 参数约束（docstring 为权威）:

- `agent_observation`: **必须把传给 agent 函数的 observation 原样传入**（引擎校验 `search_begin_input` blob）；`search_begin_input is None` → `ValueError("Not agent observation.")`。
- `your_deck`: 预测自己牌库卡 ID；docstring 要求"与牌库张数相同"，代码实检为 `len < deckCount` 才报错（即 ≥ 即可，见 §6 差异 5）；若 `Observation.select.deck != None`（正在从牌库选卡）则忽略并强制置空。
- `your_prize`: 预测自己奖赏卡 ID；`len < len(prize)` → ValueError。
- `opponent_deck`: 预测对手牌库 ID；`len < deckCount` → ValueError；docstring: setup 时至少含 1 张基础宝可梦。
- `opponent_prize` / `opponent_hand`: 同上，分别对照对手 prize 数组长度 / handCount。
- `opponent_active`: 仅当对手战斗场有**背面向**宝可梦（`active[0] is None`）时必须给出（且必须是宝可梦卡 ID），否则强制清空。
- `manual_coin=True`: 可自行选择硬币正反。
- 引擎错误码 → 异常: `1` Invalid Card ID→ValueError; `2` "Active card must be the ID of a Pokémon card."→ValueError; `30` "agent_ptr broken."→ValueError; 其他→`RuntimeError()`。
- 全局惰性单例 `agent_ptr = lib.AgentStart()`（每进程一次）。

`search_step` 错误码 → 异常（均 ValueError，除注明）:

| 码 | 语义 |
|---|---|
| 1 | 不存在指定 search_id |
| 2 | 该状态已被释放（Released item） |
| 3 | 对局已结束不能继续选择 |
| 4 | 违反 `minCount <= len(select) <= maxCount` |
| 5 | 存在越界元素（须 `0 <= e < len(option)`） |
| 6 | select 元素重复 |
| 30 | agent_ptr broken |
| 其他 | `RuntimeError()` |

### 3.2 game.py（对局层）

| 函数 | 签名 | 契约 | 错误语义 |
|---|---|---|---|
| `battle_start` | `(deck0: list[int], deck1: list[int]) -> tuple[dict, StartData]`（wheel 版多 `reverse_player=False`） | deck0/deck1=先/后手玩家牌表卡 ID 列表；两副都**必须恰 60 张**；拼接后送 `lib.BattleStart`（wheel: `reverse_player=True` 时 `BattleStartReverse`，"第二玩家可选择先/后手"）。成功返回 `(首观测 dict, StartData)` | `len != 60` → `ValueError("The deck must contain 60 cards.")`；引擎侧牌表非法 → `battlePtr` 为 None/0，返回 `(None, start_data)`，经 `start_data.errorPlayer/errorType` 指认（errorType 取值无文档） |
| `battle_finish` | `() -> None` | 结束对局并释放内存 | — |
| `battle_select` | `(select_list: list[int]) -> dict` | 提交当前选择（option 下标数组）；返回下一观测 | 非 list[int] → `ValueError("select_list is not list[int]")`；引擎 `Select` 返回 30 → `ValueError("battle_ptr broken.")`；其余非 0 → `IndexError()`（无更细文档） |
| `visualize_data` | `() -> str` | 返回可视化器用 JSON 字符串（帧数组） | — |

`_get_battle_data`（观测构造核心）: `obs = json.loads(lib.GetBattleData(battle_ptr).json)`，再把 `SerialData.data[0:count]` 按 ASCII 解码为 `obs["search_begin_input"]`。即 **search_begin_input 是引擎随每次观测下发的二进制 blob，必须原样交回 search_begin**。

### 3.3 FFI 入口一览（sim.py）

`GameInitialize()`（import 时执行一次）、`BattleStart(int*) -> StartData`、`BattleStartReverse(int*) -> StartData`（wheel）、`BattleFinish(void*)`、`GetBattleData(void*) -> SerialData`、`Select(void*, int*, int) -> int`、`VisualizeData(void*) -> char*`、`AgentStart() -> void*`、`SearchBegin(void*, char*, int, int*×6, int) -> char*`、`SearchStep(void*, int64, int*, int) -> char*`、`SearchEnd(void*)`、`SearchRelease(void*, int64)`、`AllCard() -> char*`、`AllAttack() -> char*`。

---

## 4. Log 事件结构表（LogType → 可选字段，回放解析字典）

公共字段: `type`（必填）、`playerIndex`（除 RESULT 外均有）。

| LogType | 值 | 语义 | 可选字段（docstring 语义） |
|---|---|---|---|
| SHUFFLE | 0 | 洗牌库 | playerIndex |
| HAS_BASIC_POKEMON | 1 | 是否有基础宝可梦 | hasBasicPokemon(bool): false=没有基础宝可梦 |
| TURN_START | 2 | 回合开始 | playerIndex |
| TURN_END | 3 | 回合结束 | playerIndex |
| DRAW | 4 | 从牌库抽卡（己方视角） | cardId, serial（抽到的卡） |
| DRAW_REVERSE | 5 | 对手抽卡（信息隐藏） | 仅 playerIndex |
| MOVE_CARD | 6 | 卡移动（明） | cardId, serial, fromArea(AreaType), toArea(AreaType) |
| MOVE_CARD_REVERSE | 7 | 卡暗置移动 | fromArea, toArea（无 cardId/serial） |
| SWITCH | 8 | 战斗/备战互换 | cardIdActive/serialActive（注释: 移入备战区的宝可梦）, cardIdBench/serialBench（注释: 移入战斗区的宝可梦）——字段名与注释相反，以注释为准 |
| CHANGE | 9 | 宝可梦替换 | cardIdBefore/serialBefore（变化前）, cardIdAfter/serialAfter（变化后） |
| PLAY | 10 | 从手牌使用卡 | cardId, serial |
| ATTACH | 11 | 给宝可梦贴卡 | cardId/serial（被贴的卡）, cardIdTarget/serialTarget（宝可梦） |
| EVOLVE | 12 | 进化 | cardId/serial（进化卡）, cardIdTarget/serialTarget（宝可梦） |
| DEVOLVE | 13 | 退化 | cardId/serial（退化卡）, cardIdTarget/serialTarget（宝可梦） |
| MOVE_ATTACHED | 14 | 移动附加卡 | cardId/serial（附加卡）, cardIdBefore/serialBefore（原宿主）, cardIdAfter/serialAfter（新宿主） |
| ATTACK | 15 | 使用招式 | cardId/serial（出招宝可梦）, attackId(int) |
| HP_CHANGE | 16 | HP 变化 | cardId/serial, value(int: 变化量), putDamageCounter(bool: 是否"放置伤害指示物"效果所致) |
| POISONED | 17 | 中毒/解除 | isRecover(bool: true=已解除), cardId, serial |
| BURNED | 18 | 灼伤/解除 | 同上 |
| ASLEEP | 19 | 睡眠/解除 | 同上 |
| PARALYZED | 20 | 麻痹/解除 | 同上 |
| CONFUSED | 21 | 混乱/解除 | 同上 |
| COIN | 22 | 硬币结果 | head(bool: true=正面) |
| RESULT | 23 | 对局结果 | result(int: 0=玩家 0 胜, 1=玩家 1 胜, 2=平), reason(int: 1=奖赏卡归零获胜, 2=回合开始牌库 0 张(爆牌)败, 3=战斗场无宝可梦败, 4=卡效果直接决定) |

---

## 5. cabt.py 环境层契约（kaggle_environments "cabt" 环境）

### 5.1 环境规格（cabt.json）

| 项 | 值 | 语义 |
|---|---|---|
| agents | [2] | 2 名玩家 |
| episodeSteps | 10000000 | 实际无上限 |
| actTimeout | 0 | 单步超时关闭 |
| runTimeout | 2000 | 整场运行上限 2000s |
| configuration.bo | integer, default 3, min 1 | "Best of" 局数（1=BO1, 3=BO3） |
| reward | enum [-1,0,1], default 0 | 败-1/平0/胜1 |
| observation.remainingOverageTime | 600 | 每 agent 总超时预算 600s |
| action | array | "List of option index."（option 下标数组；交牌表时=卡 ID 数组） |
| status 默认 | INACTIVE, INACTIVE | — |

### 5.2 obs 构造（agent 视角）

- agent 函数签名: `agent(obs: dict) -> list[int]`；返回值直接作为 action。
- `obs` = kaggle_environments 层 observation（含 `remainingOverageTime`）+ 环境注入的 4 键: `select` / `logs` / `current` / `search_begin_input`（来自 `_get_battle_data`）。
- **仅当前行动方**（`current.yourIndex`）的 obs 被更新，对方状态置 INACTIVE 且 obs 不动。
- `current` 里被追加 3+2 个非 SDK 字段（to_observation_class 会丢弃，直接读 dict 可见）: `players[0].win`、`players[1].win`、`draw`、`round`（= 已赛场数+1）。
- 回合交接: `state[index].status="ACTIVE"`，`state[1-index].status="INACTIVE"`。
- 交牌表阶段: `obs["select"] is None` 且 `obs["current"] is None`（SDK docstring 同述），此时 action = 自己的牌表（卡 ID 数组）。

### 5.3 deck 校验规则

| 规则 | 强制点 | 说明 |
|---|---|---|
| 恰 60 张 | Python 层双重强制 | `game.battle_start` 两副都须 60 否则 ValueError；cabt.py 对 `len(action)!=60` 判 `INVALID` 并写 `env.steps[0][0]["error"]="Player {i}'s deck does not have 60 cards."` |
| 4 张上限 | **Python 层不查** | 仅引擎侧 `BattleStart` 校验，失败经 `StartData.errorPlayer>=0` 判 `INVALID`（"Player {i}'s deck error."）。errorType 取值无源码文档 |
| ACE SPEC ≤ 1 | Python 层不查 | 仅 `CardData.aceSpec` docstring 声明规则；引擎侧强制 |
| 至少 1 基础宝可梦 | 仅 docstring 提及 | `search_begin` 的 opponent_deck 注释: setup 时至少 1 张基础宝可梦；实体强制在引擎 |

### 5.4 超时与错误判定

| 阶段 | 判定 | 处置 |
|---|---|---|
| 交牌表 | agent status 为 TIMEOUT/ERROR | 记 error，跳过其校验 |
| 交牌表 | `len(deck)!=60` 或 `errorPlayer>=0` | 该玩家 `INVALID`；其余 `ACTIVE→DONE`；**不显式给 reward**（交 KE 核心裁决），不写 env.result |
| 对局中 | 当前行动方 TIMEOUT/ERROR | 同下: 该方 reward=-1，对方 DONE reward=+1，`finish()` 收束（visualize+battle_finish） |
| 对局中 | `battle_select` 抛任意异常（含 IndexError） | 该方 `INVALID`，reward=-1，对方 reward=+1，立即 `finish()` |
| 超时机制 | KE `agent.py`: `duration - actTimeout > remainingOverageTime` → TIMEOUT | actTimeout=0 + 预算 600s/agent；runTimeout 2000s 全场 |

### 5.5 BO3 组织（bo 配置驱动）

1. 每局结束（`current.result >= 0`）: `Battle.result[result] += 1`（result=2 计入平局格）。
2. `count = w0+w1+draw`，`remain = bo - count`。
3. 提前结束条件: `w0 > w1+remain` → 玩家 0 胜；`w1 > w0+remain` → 玩家 1 胜；`remain<=0` 且无人达标 → 平（result=2）。终局两方 `DONE`，reward +1/-1 或 0/0，`env.result = Battle.result`（[w0,w1,draw]）。
4. 未分胜负: `round_finish`（收集可视化帧 + `battle_finish`）→ `Battle.last_step = len(env.steps)-1` → `battle_start(Battle.decks[0], Battle.decks[1], reverse_player = count % 2 != 0)` 开新局（第 2 局起 reverse_player=True，"第二玩家可选先/后手"，对应 SelectContext.IS_FIRST）。
5. 可视化帧: `visualize_data()` JSON 帧数组，逐帧注 `obs`（去掉 search_begin_input 的观测副本）与 `action=[a0,a1]`，并给每帧 `current.players[j].remainingTime = remainingOverageTime`；累计进 `Battle.vis`，最终写 `env.steps[0][0]["visualize"]`。

### 5.6 agent 装载语义（kaggle_environments/agent.py）

- 内置 agent 按名解析: `{"random": random_agent, "first": first_agent}`；`random` 取 `random.sample(range(len(option)), maxCount)`，`first` 取 `range(maxCount)`；两者在 `obs["select"] is None` 时返回硬编码 60 张牌表（33 张基本能量 id=3 + 27 张宝可梦/训练家卡，各卡 ≤4 张）。
- 外部 agent（文件路径或源码串）经 `get_last_callable`: `compile(raw, path|"<string>", "exec")` + `exec(code_object, env={})`，**执行环境不含 `__file__`**（env 是裸 dict，仅收集模块级定义）；从文件装载时其目录被临时压入 `sys.path`（同目录 import 可用），随后弹出。**取命名空间中"最后一个可调用对象"作为 agent 函数**。故 agent 代码不能依赖 `__file__` 定位资源；需用 CWD 相对路径或经 sys.path 的同目录 import。
- action 契约: 返回 `list[int]`（option 下标；交牌表时为 60 张卡 ID）。

---

## 6. 异常与限界

1. **两版 sim.py 不一致（wheel 缺 FFI 声明）**: wheel `cg/sim.py` 没有 `AgentStart/SearchBegin/SearchStep/SearchEnd/SearchRelease/AllCard/AllAttack` 的 restype/argtypes 声明，而两版 api.py 完全相同且会调用它们。ctypes 未声明时 restype 默认 `c_int`，64 位指针会被截断——wheel 直接调 `search_begin`/`all_card_data` 存在崩溃/截断风险；对手工程版的 sim.py 声明齐全。使用搜索层前应自行补声明或以对手工程版 sim.py 为准。
2. **wheel 版 game.py 多 `reverse_player` 参数与 `BattleStartReverse` FFI**，对手工程版没有；cabt.py 依赖 wheel 形态（含 `Battle.decks/result/vis/last_step` 字段），对手工程版的 sim/game 无法直接驱动 cabt.py。
3. **`StartData.errorType` 无文档**: 引擎侧牌表校验（推测含 4 张上限、ACE SPEC、卡 ID 合法性）只回传错误码，Python 源码不解释取值，4 张上限无法在 Python 层证实。
4. **docstring 与代码不完全一致**: `search_begin` 各预测数组 docstring 说"必须与实际张数相同"，代码只检查 `len < N`（偏多不会报错）；`battle_select` 非 30 错误统一 `IndexError()` 无语义细分。
5. **cabt.py 小缺陷**: 交牌表阶段错误消息 `f"Player {i}'s deck error."` 用了过期循环变量 `i`（恒为 1），错误归属应以 `start_data.errorPlayer` 为准；交牌表失败分支不显式设 reward、不写 env.result。
6. **枚举/类前向追加**: SelectContext/LogType 等明确注释"竞赛期间可能追加"，`to_dataclass` 静默丢未知 key、IntEnum 构造未知值会抛错——回放解析需按 int 值分派并留 default 分支。
7. **搜索层与对局层是两套独立句柄**: `agent_ptr`（搜索, `AgentStart` 惰性单例）与 `Battle.battle_ptr`（对局）互不通用；错误码 30 在两侧都表示"指针损坏"。
8. **docstring 缺失处**: AreaType.PLAYER 无注释（语义按命名推断）；`battle_select` 的 select_list 参数 docstring 为空（"select_list:"）；RESULT 的 reason=1 "0 Prize cards" 指奖赏卡取尽获胜，细节未展开。
