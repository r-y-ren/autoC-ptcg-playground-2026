"""R11 GSK 预检入口（蓝图 sw-gsk 等价）"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.build_gsk_prestudy.build_gsk_prestudy import build_gsk_prestudy

if __name__ == "__main__":
    out = os.environ.get("GSK_OUT", os.path.join(os.path.dirname(__file__), "..", "docs", "methodology", "gsk"))
    build_gsk_prestudy(out_dir=out)
