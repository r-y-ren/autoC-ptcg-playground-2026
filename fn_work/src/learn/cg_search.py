"""引擎搜索 API 自绑封装(fna-022/fna-010 搜索前瞻的原语层)。

wheel libcg 1.33.0 导出 SearchBegin/SearchStep/SearchEnd/SearchRelease/AgentStart
但 wheel 的 sim.py 未绑定;第三方 cg/api.py 的绑定与本版签名不配(混用即原生 segfault)。
本模块直接复用 wheel 的 lib/SerialData,按 api.html 契约声明签名——单副本单绑定。

契约要点(api.html+api.py 调用形态):
- 观测必须携带 search_begin_input(引擎签发的状态句柄),否则"非 agent 观测"不可搜索;
- 预测列表长度须 ≥ 真实余量(prize/handCount/deckCount),不足即拒;
- search_begin 一步、search_step 推进一个选择;search_end 全清,search_release 放单个。
"""
from __future__ import annotations

import ctypes
import json

from kaggle_environments.envs.cabt.cg.sim import SerialData, lib

_INT = ctypes.c_int
_ARR = ctypes.POINTER(_INT)

lib.AgentStart.restype = ctypes.c_void_p
lib.AgentStart.argtypes = []
lib.SearchBegin.restype = ctypes.c_char_p
lib.SearchBegin.argtypes = [ctypes.c_void_p, ctypes.c_char_p, _INT,
                            _ARR, _ARR, _ARR, _ARR, _ARR, _ARR, _INT]
lib.SearchStep.restype = ctypes.c_char_p
lib.SearchStep.argtypes = [ctypes.c_void_p, ctypes.c_int64, _ARR, _INT]
lib.SearchEnd.restype = None
lib.SearchEnd.argtypes = [ctypes.c_void_p]
lib.SearchRelease.restype = None
lib.SearchRelease.argtypes = [ctypes.c_void_p, ctypes.c_int64]

_agent_ptr = None


def _arr(xs):
    xs = list(xs or [])
    return (_INT * len(xs))(*xs)


def _decode(raw) -> dict:
    if raw is None:
        raise RuntimeError("search 返回空")
    return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)


def _agent():
    global _agent_ptr
    if _agent_ptr is None:
        _agent_ptr = lib.AgentStart()
    return _agent_ptr


def search_begin(obs: dict, your_deck, your_prize, opponent_deck, opponent_prize,
                 opponent_hand, opponent_active, manual_coin: bool = False) -> dict:
    """开搜索:返回 {"observation": {...}, "searchId": int}"""
    sbi = obs.get("search_begin_input") if isinstance(obs, dict) else None
    if not sbi:
        raise ValueError("Not agent observation.(观测缺 search_begin_input)")
    cur = obs.get("current") or {}
    my_i = cur.get("yourIndex", 0) or 0
    players = cur.get("players") or []
    my = players[my_i] if len(players) > my_i else {}
    opp = players[1 - my_i] if len(players) > 1 - my_i else {}
    if len(your_prize) < len(my.get("prize") or []):
        raise ValueError("your_prize 张数不足")
    if len(opponent_deck) < (opp.get("deckCount") or 0):
        raise ValueError("opponent_deck 张数不足")
    if len(opponent_prize) < len(opp.get("prize") or []):
        raise ValueError("opponent_prize 张数不足")
    if len(opponent_hand) < (opp.get("handCount") or 0):
        raise ValueError("opponent_hand 张数不足")
    bs = lib.SearchBegin(_agent(), sbi.encode("ascii"), len(sbi),
                         _arr(your_deck), _arr(your_prize), _arr(opponent_deck),
                         _arr(opponent_prize), _arr(opponent_hand),
                         _arr(opponent_active), int(bool(manual_coin)))
    out = _decode(bs)
    if out.get("error"):
        raise RuntimeError(f"SearchBegin error={out['error']}")
    return out["state"]


def search_step(search_id: int, select: list[int]) -> dict:
    bs = lib.SearchStep(_agent(), int(search_id), _arr(select), len(select))
    out = _decode(bs)
    if out.get("error"):
        raise RuntimeError(f"SearchStep error={out['error']}")
    return out["state"]


def search_end() -> None:
    lib.SearchEnd(_agent())


def search_release(search_id: int) -> None:
    lib.SearchRelease(_agent(), int(search_id))
