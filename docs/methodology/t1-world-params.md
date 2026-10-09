# T1 世界参数表（引擎六问）

| 六问 | 答案（带源码行号/实验证据） | 决定了什么 |
|---|---|---|
| 钱/分怎么算出来的？ | 胜负=单局 result（C 层判定：奖赏卡取尽/对手无宝可梦/对手无牌），BO3 按 Battle.result 多数定胜（cabt.py:179-211）；无金钱变量，J=BO 系列胜负 | J=终局 BO 胜负；净账=奖赏进度差-资源损失 |
| 对手在哪个函数里影响我？ | 双方共享同一 Battle 状态（C 层单实例），yourIndex 交替 ACTIVE（cabt.py:218-225）；对手动作直接改变我方收到的 select 选项集 | 对手建模必选（耦合在共享状态里） |
| 失败怎么表达？ | 非法动作=battle_select 抛错→当场 INVALID→整场判负 -1/+1（cabt.py:164-168）；deck≠60 卡=INVALID（141-149）；超时/异常同判——无静默失败 | 防御层刚需：guard_rails 终检+61 卡字面量 bug 即例证 |
| 时间结构是什么？ | BO3 分轮（bo 默认 3，cabt.json；轮间换先手 battle_start(reverse=count%2)，cabt.py:215）；回合内 turnActionCount/能量一次/支援一次；remainingOverageTime=600 | 按轮+按回合双周期规划；调度层管回合内资源 |
| 谁能看见什么？ | PlayerState.hand 仅自己可见；对手只有 handCount/deckCount/discard 计数；场面 active/bench/prize 公开 | 观测器窄而深：估对手手牌构成（唯一隐藏面） |
| rng 在哪几行被调用？ | Python 层零 rng（random 仅 random_agent 用，cabt.py:4/73-76）；洗牌/掷币在 libcg.so C 层，**同种子不可复现**（probe 实证） | 方差预算覆盖全局；判决池按局数收敛 n≥20；A/B 用双席折叠而非种子配对 |

## 源码锚点

- `import random` → 第 4 行：`import random`
- `^deck = \[` → 第 9 行：`deck = [`
- `def random_agent` → 第 73 行：`def random_agent(obs: dict) -> list[int]:`
- `select.*=.*None` → 第 74 行：`    if obs["select"] == None:`
- `def first_agent` → 第 79 行：`def first_agent(obs: dict) -> list[int]:`
- `select.*=.*None` → 第 80 行：`    if obs["select"] == None:`
- `remainingOverageTime` → 第 108 行：`                vis[i]["current"]["players"][j]["remainingTime"] = steps[i][j]["observation"]["remainingOverageTime"]`
- `def interpreter` → 第 118 行：`def interpreter(state, env):`
- `select.*=.*None` → 第 128 行：`            o["select"] = None`
- `status.*ERROR` → 第 138 行：`            if state[i].status == "TIMEOUT" or state[i].status == "ERROR":`
- `status.*INVALID` → 第 142 行：`                state[i].status = "INVALID"`
- `battle_start\(` → 第 146 行：`            _, start_data = battle_start(state[0].action, state[1].action)`
- `status.*INVALID` → 第 148 行：`                state[start_data.errorPlayer].status = "INVALID"`
- `yourIndex` → 第 160 行：`        select_player = Battle.obs["current"]["yourIndex"]`
- `status.*ERROR` → 第 161 行：`        if state[select_player].status == "TIMEOUT" or state[select_player].status == "ERROR":`
- `battle_select\(` → 第 165 行：`                battle_select(state[select_player].action)`
- `status.*INVALID` → 第 167 行：`                state[select_player].status = "INVALID"`
- `\.reward = -1` → 第 171 行：`            state[select_player].reward = -1`
- `\.reward = 1` → 第 173 行：`            state[1 - select_player].reward = 1`
- `result\[` → 第 181 行：`            Battle.result[0] += 1`
- `result\[` → 第 183 行：`            Battle.result[1] += 1`
- `result\[` → 第 185 行：`            Battle.result[2] += 1`
- `result\[` → 第 187 行：`        count = Battle.result[0] + Battle.result[1] + Battle.result[2]`
- `result\[` → 第 190 行：`        if Battle.result[0] > Battle.result[1] + remain:`
- `result\[` → 第 192 行：`        elif Battle.result[1] > Battle.result[0] + remain:`
- `\.reward = 1` → 第 202 行：`                state[0].reward = 1`
- `\.reward = -1` → 第 203 行：`                state[1].reward = -1`
- `\.reward = -1` → 第 205 行：`                state[0].reward = -1`
- `\.reward = 1` → 第 206 行：`                state[1].reward = 1`
- `battle_start\(` → 第 215 行：`            battle_start(Battle.decks[0], Battle.decks[1], count % 2 != 0)`
- `yourIndex` → 第 218 行：`    index = s["yourIndex"]`
- `result\[` → 第 226 行：`    s["players"][0]["win"] = Battle.result[0]`
- `result\[` → 第 227 行：`    s["players"][1]["win"] = Battle.result[1]`
- `result\[` → 第 228 行：`    s["draw"] = Battle.result[2]`
- `result\[` → 第 229 行：`    s["round"] = Battle.result[0] + Battle.result[1] + Battle.result[2] + 1`

## 受控实验证据（probe_engine_facts 实跑）

### 失败怎么表达？（q3）
- 观测：越界索引提交后 statuses=['INVALID', 'DONE'] rewards=[None, 1]
- 结论：非法动作=battle_select 抛错→该席 INVALID→当场判负（-1/+1），非静默跳过（cabt.py:164-168）

### 谁能看见什么？观测构造（q5）
- 观测：deck 提交拍 select=None 出现=False；select 阶段含 option/maxCount/minCount；current.players 仅己方含 hand 明细
- 结论：信息结构=初始牌组提交阶段无 select；对局中双方公开场面（active/bench/deckCount/prize 计数），手牌仅自己可见（PlayerState.hand）

### rng 在哪几行被调用？同种子可复现吗？（q6）
- 观测：同种子 7 两局逐拍 steps 完全一致=False（rewards [1, -1] vs [1, -1]）
- 结论：Python 层无 rng 调用（cabt.py 仅 import random 供 random_agent 用）；同种子不可复现=C 层 rng 无种子入口，方差预算覆盖全局，判决池须按局数收敛而非固定种子

