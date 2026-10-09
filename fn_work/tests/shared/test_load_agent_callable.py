import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.shared.load_agent_callable import load_agent_callable


def test_load_from_file():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "myagent.py")
        with open(p, "w") as f:
            f.write("def agent(obs):\n    return []\n")
        fn = load_agent_callable(p, "agent")
        assert callable(fn)
        assert fn({}) == []


def test_load_from_directory_kaggle_semantics():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "main.py"), "w") as f:
            f.write("def agent(obs):\n    return [0]\n")
        fn = load_agent_callable(d)  # 目录→main.py
        assert fn({}) == [0]


def test_missing_file_raises_with_reason():
    try:
        load_agent_callable("/nonexistent/agent.py")
        assert False, "should raise"
    except FileNotFoundError as e:
        assert "不存在" in str(e)


def test_missing_function_raises():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "noagent.py")
        with open(p, "w") as f:
            f.write("x = 1\n")
        try:
            load_agent_callable(p, "agent")
            assert False, "should raise"
        except AttributeError as e:
            assert "agent" in str(e)
