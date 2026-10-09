# 搜索前瞻 v0 设计与实测(fna-022/fna-010,2026-10-06)

> 用户裁决(五拍振荡二选一)选 B=转搜索前瞻。本文固化引擎搜索 API 的契约事实、
> 三个致命坑、v0 架构与首测读数。模块:`fn_work/src/learn/cg_search.py`(原语)+
> `fn_work/src/learn/search_lookahead.py`(rollout 选优)。

## 一、引擎搜索 API 契约(libcg 1.33.0 实测)

- 符号齐备:`AgentStart/SearchBegin/SearchStep/SearchEnd/SearchRelease` 全部导出;
  wheel 的 sim.py 只绑了对局六函数——搜索绑定必须自建(权威签名参考
  references/opponents/pokemon-tcg-ai-battle-agent/cg/sim.py)。
- **`search_begin_input`(sbi)= 引擎签发的状态句柄**(观测自带,≈81 字符 ascii);无句柄的
  观测不可搜索(报 "Not agent observation")。
- 隐藏信息预测列表**长度须 ≥ 真实余量**(prize/handCount/deckCount);开局预测牌堆须含
  至少一只基础怪(error=99)。
- **敌我回合判定=`current.yourIndex`**(搜索态里随换手翻转 0↔1)——只凭 context==0 断
  "轮到我方"必错(会把对手 MAIN 当成自己的停点,rollout 全废)。
- 串行纪律:一次一个搜索态,用完 `search_release`;整局结束 `search_end`。

## 二、三个致命坑(全部踩过,学费在案)

1. **单副本铁律**:对局引擎与搜索必须共用同一份 libcg 实例——两份副本(第三方 api.py 经
   软链加载另一路径)= `buffer full. capacity:7` 或 segfault。解法:绑定直接复用 wheel 的
   `cg.sim.lib`,勿混用第三方 api.py 的绑定层。
2. **返回值是 `c_char_p` 不是结构体**:SearchBegin/SearchStep restype=char*(JSON 串);
   按结构体解=按垃圾指针读字段=segfault。SearchStep/End/Release 全部要带 agent_ptr,
   searchId 是 int64。
3. 【2026-10-06 勘误·原表述反了】**`prize` 列表=剩余奖赏堆**(发奖 6→随领取递减归 0 即胜,ctx=41 开局前未发故为 0——原"已拿走"结论系开局前探针误判);价值函数须用**已拿=6−剩余**——符号搞反会
   倒向 END(弃权)。

## 三、v0 架构(rollout 行动选优)

- 只在我方决策点(ctx==0 且 yourIndex==我)对**单选**分支;候选逐个:
  `search_begin`→走这步→贪心折叠(能攻击就攻击,否则前排)至"我方再决策/终局/步数帽 12";
- 叶子价值(我方视角)=10×奖赏差 + 2×主动位血差 + 3×一击威胁差 + 0.5×疲劳差,
  终局 ±1000(megaEx 奖赏 3 的数学已同步进老师/求解器/部署件);
- 隐藏信息 v0=基础怪+能量填充(数量对齐);单决策预算 1.2s,异常/超预算回退贪心;
- 参考文献:ronniepiku/bot/search.py(Apache-2.0,贪心折叠 MDP+PUCT,本 v0 取其折叠思想)。

## 四、首测读数(2026-10-06,本地 play_local_match,各 6 局 bo3)

| 对手 | v0 搜索 | 备注 |
|---|---|---|
| random | **6W-0L** | 修复敌我判定前 0-4(修一处即翻盘) |
| v5 首序基线 | 1W-5L | 尚未越过——v0.1 的靶子 |

性能:单次 12 步 rollout **≈1ms**(预算极宽裕,可加深加宽)。

## 五、v0.1 清单(按预期收益排序)

1. 叶子评估加厚:能量附着进度/手牌数/效果技关键词(v4 特征组可复用);
2. 搜索加深:折到"我方下一个 MAIN"再走一步自己的再决策(2 轮深);
3. 对手模型:填充牌换成 meta 牌组(Schott 牌组在语料,88 局可提取)+其贪心策略;
4. 集成:并入 eval_agent/部署件为选项层(打包时把 cg/ 一并入 tar——比赛环境游戏在
   服务端跑,agent 自带引擎副本做搜索是榜首通行做法,无冲突);
5. 验收:strict_judge 四线 30 局双席 A/B(vs 无搜索版)。
