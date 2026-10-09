"""H1-H3 轨迹取证:6 个配对分歧局(rules 负/greedy 胜),双方 action 序列+折叠预测对照。
H1=v5 实际首序 vs 两种折叠在同一 select 的预测(错报率,按回合首行动分层);
H2=受测体攻击频率/时机(rules vs greedy 同种子对照);H3=撤退次数对照;
附 rollout 内 rules fold 代打分布(被模拟对手实际被折叠成什么行动)。
用法: .venv/bin/python tmp/v5reg_trace.py
"""
import sys, os, json, copy
ROOT = "/mnt/data/Code/autoC/workspace/ptcg-playground-2026/fn_work"
for p in (ROOT, ROOT + "/src"): sys.path.insert(0, p)
os.chdir(ROOT)

import learn.search_lookahead as SL
from learn.search_lookahead import make_search_agent, _pick, _pick_greedy
from src.shared.play_local_match import play_local_match

META = [96,96,96,96,92,92,93,93,150,150,917,917,709,709,710,710,1071,1071,140,920,1227,1227,1227,1227,1231,1231,1182,1182,1184,1213,1121,1121,1121,1121,1094,1094,1094,1094,1080,1261,1261,1261,1261,1152,1152,1097,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
TN = {0:"NUMBER",1:"YES",2:"NO",3:"CARD",4:"TOOL",5:"ENERGY_CARD",6:"ENERGY",7:"PLAY",8:"ATTACH",
      9:"EVOLVE",10:"ABILITY",11:"DISCARD",12:"RETREAT",13:"ATTACK",14:"END",15:"SKILL",16:"SPCOND"}

# rollout 内 rules fold 代打日志(区分代打对象:我方中间决策 vs 对手回合)
FOLD_LOG = []
_orig_fold = SL._pick_rules_fold
def _fold_probe(sel, obs, my_i):
    r = _orig_fold(sel, obs, my_i)
    cur = (obs or {}).get("current") or {}
    yi = cur.get("yourIndex", 0) or 0
    FOLD_LOG.append({"actor_me": bool(yi == my_i),
                     "opts": [TN.get(o.get("type")) for o in (sel.get("option") or [])],
                     "picked": [TN.get((sel.get("option") or [{}])[j].get("type")) for j in r[:3]]})
    return r
SL._pick_rules_fold = _fold_probe

SEEDS = [(3, 31003), (5, 31005), (12, 31012), (16, 31016), (18, 31018), (20, 31020)]

def t_of(o):
    return TN.get(o.get("type")) if isinstance(o, dict) else None

def run_one(fold, i, seed):
    FOLD_LOG.clear()
    v5_rows, my_rows = [], []
    my_idx_seen = set()

    def v5(obs, config=None):
        sel = (obs or {}).get("select")
        if sel is None: return list(META)
        if sel.get("context") == 0:
            cur = (obs or {}).get("current") or {}
            yi = cur.get("yourIndex", 0) or 0
            opts = sel.get("option") or []
            actual = _pick(sel)
            pred_r = _pick_greedy  # noqa 占位避免闭包误用
            pg = _pick_greedy(sel, yi)
            pr = SL._pick_rules_fold(sel, obs, yi)
            v5_rows.append({
                "turn": cur.get("turn"),
                "opts": [t_of(o) for o in opts],
                "actual": [t_of(opts[j]) for j in actual if j < len(opts)],
                "greedy_pred": [t_of(opts[j]) for j in pg if j < len(opts)],
                "rules_pred": [t_of(opts[j]) for j in pr if j < len(opts)],
            })
        return _pick(sel)

    agent = make_search_agent(META, fold=fold)
    def mine(obs, config=None):
        sel = (obs or {}).get("select")
        if sel is None: return list(META)
        if sel.get("context") == 0:
            cur = (obs or {}).get("current") or {}
            yi = cur.get("yourIndex", 0) or 0
            my_idx_seen.add(yi)
            opts = sel.get("option") or []
            act = agent(obs, config)
            my_rows.append({"turn": cur.get("turn"),
                            "opts": [t_of(o) for o in opts],
                            "picked": [t_of(opts[j]) for j in act if j < len(opts)]})
            return act
        return agent(obs, config)

    swap = i % 2 == 1
    a, b = (v5, mine) if swap else (mine, v5)
    r = play_local_match(a, b, META, META, seed=seed, config={"bo": 3})
    my = r["rewards"][1] if swap else r["rewards"][0]
    opp = r["rewards"][0] if swap else r["rewards"][1]
    res = "W" if my > opp else ("L" if my < opp else "D")

    # 回合切分(我方):ATTACK/END 截断;统计攻击回合占比/撤退/贴能-攻击次序
    turns, cur_t = [], []
    for row in my_rows:
        cur_t.append(row)
        if row["picked"] and row["picked"][0] in ("ATTACK", "END"):
            turns.append(cur_t); cur_t = []
    if cur_t: turns.append(cur_t)
    atk_turns = sum(1 for t in turns if any(x["picked"][0] == "ATTACK" for x in t if x["picked"]))
    retreats = sum(1 for t in turns for x in t if x["picked"] and x["picked"][0] == "RETREAT")
    turn_open_attach_atk = sum(1 for t in turns if t and t[0]["picked"] and t[0]["picked"][0] == "ATTACK")

    # v5 回合切分同款(口径一致)
    v_turns, v_cur = [], []
    for row in v5_rows:
        v_cur.append(row)
        if row["actual"] and row["actual"][0] in ("ATTACK", "END"):
            v_turns.append(v_cur); v_cur = []
    if v_cur: v_turns.append(v_cur)
    v_atk = sum(1 for t in v_turns if any(x["actual"][0] == "ATTACK" for x in t if x["actual"]))

    # H1 错报率:v5 每个 MAIN select 上 rules/greedy 预测首行动类型与实际不同的比率
    def mis(rows, key):
        n = m = 0
        for row in rows:
            if not row["actual"]: continue
            n += 1
            pred = row[key]
            if not pred or pred[0] != row["actual"][0]:
                m += 1
        return {"n": n, "mismatch": m, "rate": round(m / n, 3) if n else None}
    # 仅统计"回合首个 select"(资源未动,预测差异最大处)
    opens = [t[0] for t in v_turns if t]
    fold_calls = len(FOLD_LOG)
    fold_opp = [x for x in FOLD_LOG if not x["actor_me"]]
    fold_opp_pick = {}
    for x in fold_opp:
        for p in x["picked"][:1]:
            fold_opp_pick[p] = fold_opp_pick.get(p, 0) + 1
    return {"seed": seed, "i": i, "swap": swap, "res": res, "steps": r.get("n_steps"),
            "my": {"n_main": len(my_rows), "n_turns": len(turns), "atk_turns": atk_turns,
                   "atk_rate": round(atk_turns / len(turns), 3) if turns else None,
                   "open_with_attack": turn_open_attach_atk, "retreats": retreats},
            "v5": {"n_main": len(v5_rows), "n_turns": len(v_turns), "atk_turns": v_atk,
                   "h1_all": mis(v5_rows, "rules_pred"), "h1_open": mis(opens, "rules_pred"),
                   "h1_all_greedy": mis(v5_rows, "greedy_pred"),
                   "h1_open_greedy": mis([t[0] for t in v_turns if t], "greedy_pred")},
            "fold_sim_opp_picks": fold_opp_pick, "fold_sim_opp_calls": len(fold_opp),
            "fold_sim_me_calls": fold_calls - len(fold_opp),
            "_v5_rows": v5_rows, "_my_rows": my_rows}

out = {"rules": [], "greedy": []}
for fold in ("rules", "greedy"):
    for i, seed in SEEDS:
        row = run_one(fold, i, seed)
        out[fold].append(row)
        print(fold, json.dumps({k: v for k, v in row.items() if not k.startswith("_")},
                               ensure_ascii=False), flush=True)

def agg(fold):
    rows = out[fold]
    atk = [r["my"]["atk_rate"] for r in rows if r["my"]["atk_rate"] is not None]
    ret = sum(r["my"]["retreats"] for r in rows)
    nt = sum(r["my"]["n_turns"] for r in rows)
    h1o = [r["v5"]["h1_open"] for r in rows if r["v5"]["h1_open"]["rate"] is not None]
    h1a = [r["v5"]["h1_all"] for r in rows if r["v5"]["h1_all"]["rate"] is not None]
    h1og = [r["v5"]["h1_open_greedy"] for r in rows if r["v5"]["h1_open_greedy"]["rate"] is not None]
    return {"res": [r["res"] for r in rows],
            "mean_atk_rate": round(sum(atk) / len(atk), 3) if atk else None,
            "retreats_total": ret, "turns_total": nt,
            "h1_open_mismatch": round(sum(x["mismatch"] for x in h1o) / max(1, sum(x["n"] for x in h1o)), 3),
            "h1_all_mismatch": round(sum(x["mismatch"] for x in h1a) / max(1, sum(x["n"] for x in h1a)), 3),
            "h1_open_mismatch_greedy": round(sum(x["mismatch"] for x in h1og) / max(1, sum(x["n"] for x in h1og)), 3),
            "fold_sim_opp_calls": sum(r["fold_sim_opp_calls"] for r in rows),
            "fold_sim_me_calls": sum(r["fold_sim_me_calls"] for r in rows)}

summary = {"rules": agg("rules"), "greedy": agg("greedy")}
print("AGG", json.dumps(summary, ensure_ascii=False), flush=True)
out["summary"] = summary
with open(ROOT + "/tmp/v5reg_trace.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
