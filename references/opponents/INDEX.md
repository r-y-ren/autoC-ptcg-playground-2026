# opponents/ 开源对手登记(2026-10-05 git clone --depth 1)

> 用途:陪练对手池扩充(打法多样性)。内部训练/评测使用;对外分发前须剥离引擎二进制并向作者确认许可。

| 目录 | 来源 URL | 抓取日期 | 许可 | 内容 | 进程内可用性 |
|---|---|---|---|---|---|
| topdeck/ | https://github.com/samyakrajbayar/Topdeck---PTCG-AI-Battle-Challenge-Strategy | 2026-10-05 | MIT(README 有"rights reserved"混杂表述) | ISMCTS+6 轴启发式评分 agent(main.py+deck_logic.py) | **可用**(1 局烟测 141 步 DONE)——已入 SIL 对手组合 |
| ptcg-abc/ | https://github.com/wmh/ptcg-abc | 2026-10-05 | 无(商用前须问作者) | 20+ ladder agent 变体(alakazam/bellibolt/…)+cabt_ab 对评测工具 | 不可用(自搜索与对局引擎抢原生 libcg 缓冲,`buffer full. capacity:7` 崩溃)——仅子进程外挂路线 |
| pokemon-tcg-ai-battle-agent/ | https://github.com/ronniepiku/pokemon-tcg-ai-battle-agent | 2026-10-05 | Apache-2.0 | 启发式+可选 MCTS agent(bot/ 包),自带 cg 绑定(缺 Linux libcg.so,已软链 wheel 版借用) | 不可用(同上原生缓冲冲突)——仅子进程外挂路线 |

## 装载备注

- `shared.load_agent_callable(path)` 可直接装 topdeck;多模块包(pokemon-tcg-ai-battle-agent 的 `bot/`、ptcg-abc 的 `agents/_base`)须先把仓库根加 `sys.path`。
- ptcg-abc/pokemon-tcg-ai-battle-agent 都 import `cg.api`(旧 API 面,api.html 同源)而 wheel 自带的 `cg` 包无 `api.py`;`cg.api` 只能用 pokemon-tcg-ai-battle-agent/cg/api.py,其 Linux `libcg.so` 缺失→已软链至 wheel 的 libcg.so。
- 进程内冲突根因:同一 libcg 全局缓冲被"进行中的对局"与"agent 自带搜索实例"同时占用(capacity 7)。子进程隔离可解,判决池外挂时按"每 agent 一进程"设计。
