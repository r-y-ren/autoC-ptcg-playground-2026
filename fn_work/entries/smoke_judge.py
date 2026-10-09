"""R1 判决池冒烟入口（蓝图 sw-boot 等价）：默认配置跑批并打印摘要"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from kaggle_environments.envs.cabt import cabt

from src.run_judge_pool.run_judge_pool import run_judge_pool

if __name__ == "__main__":
    # 冒烟受测体 = 引擎 first_agent（种子件就绪后换 seed_agent）
    run_judge_pool({"agent": cabt.first_agent, "n_mirror": 20, "n_anchor": 10, "bo": 3})
