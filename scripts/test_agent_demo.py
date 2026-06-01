import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agent_tools import (
    execute_get_index_info,
    fake_plan_tool_call,
    validate_dangerous_tool_authorization,
    validate_tool_arguments,
    validate_tool_name,
)
import app.main  # noqa: F401


def test_get_index_info_read_only():
    result = execute_get_index_info({}, SimpleNamespace(chunk_records=[]))
    assert "index_exists" in result
    assert "chunk_count" in result
    assert "rebuild_required" in result
    assert "knowledge_dir" in result


def test_rebuild_blocked_without_request_authorization():
    tool_call = fake_plan_tool_call("请重建知识库索引")
    assert tool_call["tool_name"] == "rebuild_index"
    assert tool_call["arguments"]["confirm"] is True

    result = validate_dangerous_tool_authorization(
        tool_name="rebuild_index",
        arguments=tool_call["arguments"],
        allow_rebuild_index=False,
    )
    assert result["valid"] is False
    assert result["status"] == "blocked"


def test_rebuild_authorized_but_executor_still_guarded_in_phase_one():
    result = validate_dangerous_tool_authorization(
        tool_name="rebuild_index",
        arguments={"confirm": True},
        allow_rebuild_index=True,
    )
    assert result["valid"] is True
    assert result["status"] == "authorized"


def test_unknown_tool_rejected():
    result = validate_tool_name({"tool_name": "run_shell", "arguments": {}})
    assert result["valid"] is False
    assert result["error_code"] == "unknown_tool"


def test_invalid_arguments_rejected():
    result = validate_tool_arguments("rebuild_index", {"confirm": "yes"})
    assert result["valid"] is False
    assert result["error_code"] == "invalid_argument_type"


if __name__ == "__main__":
    # 这些测试只验证 agent demo 的安全边界，不启动 FastAPI，也不执行真实重建。
    test_get_index_info_read_only()
    test_rebuild_blocked_without_request_authorization()
    test_rebuild_authorized_but_executor_still_guarded_in_phase_one()
    test_unknown_tool_rejected()
    test_invalid_arguments_rejected()
    print("agent_demo phase-one tests passed")
