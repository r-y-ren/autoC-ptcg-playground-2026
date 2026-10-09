"""R4 提交包自检入口（蓝图 sw-pack 等价）"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.pack_submission.pack_submission import pack_submission

if __name__ == "__main__":
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src = os.environ.get("SUBMISSION_DIR", os.path.join(base, "submission"))
    out = os.environ.get("SUBMISSION_TAR", os.path.join(base, "submission", "submission.tar.gz"))
    r = pack_submission(src, out)
    sys.exit(0 if r["ok"] else 1)
