"""编排 GSK 预研：pyxis 装载+T1/T2+自镜像冒烟（R11）"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kaggle_environments.envs.pyxis.pyxis as pyxis_mod

from src.build_gsk_prestudy.gsk_judge_smoke import gsk_judge_smoke
from src.build_gsk_prestudy.load_pyxis_env import load_pyxis_env
from src.shared.index_source_anchors import index_source_anchors
from src.shared.render_dossier_md import render_dossier_md
from src.shared.write_runs_jsonl import write_runs_jsonl

PYXIS_PATTERNS = [r"^def ", r"rng|random", r"cash", r"ptrs", r"revenue", r"bankrupt", r"class "]


def build_gsk_prestudy(out_dir="docs/methodology/gsk"):
    """GSK 预研包：环境装载（版本锁断言）+pyxis 六问 T1/T2（README 事实回链）+自镜像冒烟。

    返回 {env, t1, t2, smoke}；pyxis 装载失败抛异常含原因。
    """
    env_info = load_pyxis_env()
    smoke = gsk_judge_smoke(n_games=6)  # 预研冒烟 6 局（正式判决池扩到 20+）

    anchors = index_source_anchors(os.path.abspath(pyxis_mod.__file__), PYXIS_PATTERNS)
    conclusions = {
        "q1_money": {"answer": "100 步后净现金流（NCF）高者胜；破产即负（pyxis README；gsk.ai 官方公告 2026-10-05 实抓）", "decision": "J=NCF 差；终局清算段可离线求解"},
        "q2_opponent": {"answer": "共享适应症市场（收入 1/n^α 进入惩罚）+同批 BD 资产竞标+对手管线噪声情报", "decision": "对手建模必选（市场耦合）"},
        "q3_failure": {"answer": "ke 标准语义（agent 异常→ERROR 判负）；破产=引擎终局条件", "decision": "防御层：现金护栏+动作掩码遵从"},
        "q4_time": {"answer": "100 行动步（开局前市场空转 500 步，时钟归零）", "decision": "按步规划；长视界资产化"},
        "q5_info": {"answer": "PTRS 隐藏（1 次免费噪声读数+可购）；对手管线仅噪声情报", "decision": "观测器=PTRS 估计（唯一深隐藏面）"},
        "q6_rng": {"answer": "试验结果随机（PTRS 真值滚动）+资产到达均值回归过程", "decision": "方差预算管试验段"},
        "coords": [
            {"coord": "试验推进/BD 出价/上市", "level": "可控", "note": "动作通道"},
            {"coord": "市场份额/价格", "level": "可影响", "note": "双方共推（1/n^α）"},
            {"coord": "资产真值 PTRS", "level": "可观测不可推", "note": "噪声读数可购（观测器对象）"},
            {"coord": "试验成败/资产到达", "level": "不可控随机", "note": "方差预算"},
        ],
    }
    t1, t2 = render_dossier_md(conclusions, anchors, out_dir)
    result = {"env": env_info, "t1": t1, "t2": t2, "smoke": smoke}
    write_runs_jsonl("gsk-prestudy", {"env": env_info, "smoke": smoke})
    print(f"gsk prestudy: env v{env_info['version']} OK | smoke h2h={smoke['self_mirror_h2h']} "
          f"(draws={smoke['draws']}/{smoke['n_games']}) | T1/T2 → {t1}")
    return result
