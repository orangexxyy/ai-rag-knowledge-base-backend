import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.agent_tools as agent_tools
import app.main
from app.agent_planner import parse_strict_tool_call, plan_tool_call
from app.agent_tools import (
    execute_get_index_info,
    execute_rebuild_index,
    execute_search_knowledge_base,
    fake_plan_tool_call,
    validate_dangerous_tool_authorization,
    validate_tool_arguments,
    validate_tool_name,
)


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


def test_rebuild_authorized_but_executor_still_guarded():
    result = validate_dangerous_tool_authorization(
        tool_name="rebuild_index",
        arguments={"confirm": True},
        allow_rebuild_index=True,
    )
    assert result["valid"] is True
    assert result["status"] == "authorized"

    executor_result = execute_rebuild_index({"confirm": True}, SimpleNamespace())
    assert executor_result["status"] == "not_implemented_for_safety"
    assert executor_result["rebuild_executed"] is False


def test_search_knowledge_base_uses_read_only_rag_tool_chain():
    original_get_embedding = agent_tools.get_embedding
    original_hybrid_search = agent_tools.hybrid_search
    original_rerank_dashscope = agent_tools.rerank_chunks_by_dashscope
    original_rerank_llm = agent_tools.rerank_chunks_by_llm
    original_run_rag_chain = agent_tools.run_rag_chain

    def fake_get_embedding(text):
        assert text == "事假怎么申请？"
        return [0.1, 0.2, 0.3]

    def fake_hybrid_search(**kwargs):
        assert kwargs["query"] == "事假怎么申请？"
        return [
            {
                "chunk_id": "leave-policy-001",
                "source": "hr_policy.txt",
                "metadata": {"source_file": "hr_policy.txt"},
                "text": "事假申请需要在系统中提交请假申请，并等待直属主管审批。",
                "faiss_score": 0.91,
                "bm25_score": 3.2,
                "rrf_score": 0.5,
            }
        ]

    def fake_rerank(query, chunks, top_k):
        assert query == "事假怎么申请？"
        selected = chunks[:top_k]
        selected[0]["rerank_score"] = 0.99
        selected[0]["reranker_provider"] = "test"
        return selected

    def fake_run_rag_chain(question, reference_text):
        assert question == "事假怎么申请？"
        assert "事假申请" in reference_text
        return "事假需要先在系统中提交请假申请，并等待主管审批。"

    # 这里替换外部依赖，验证 agent tool 的编排逻辑，不触发真实 embedding / reranker / LLM API。
    agent_tools.get_embedding = fake_get_embedding
    agent_tools.hybrid_search = fake_hybrid_search
    agent_tools.rerank_chunks_by_dashscope = fake_rerank
    agent_tools.rerank_chunks_by_llm = fake_rerank
    agent_tools.run_rag_chain = fake_run_rag_chain

    try:
        app_state = SimpleNamespace(
            bm25_index=object(),
            faiss_index=object(),
            chunk_records=[{"text": "placeholder"}],
        )
        result = execute_search_knowledge_base(
            {"question": "事假怎么申请？"},
            app_state,
        )
    finally:
        agent_tools.get_embedding = original_get_embedding
        agent_tools.hybrid_search = original_hybrid_search
        agent_tools.rerank_chunks_by_dashscope = original_rerank_dashscope
        agent_tools.rerank_chunks_by_llm = original_rerank_llm
        agent_tools.run_rag_chain = original_run_rag_chain

    assert result["success"] is True
    assert result["retriever_status"] == "matched"
    assert result["answer"]
    assert "事假申请" in result["reference_preview"]
    assert result["used_chunk_count"] == 1


def test_unknown_tool_rejected():
    result = validate_tool_name({"tool_name": "run_shell", "arguments": {}})
    assert result["valid"] is False
    assert result["error_code"] == "unknown_tool"


def test_invalid_arguments_rejected():
    result = validate_tool_arguments("rebuild_index", {"confirm": "yes"})
    assert result["valid"] is False
    assert result["error_code"] == "invalid_argument_type"


def test_fake_planner_provider_still_available():
    result = plan_tool_call("index status", provider="fake")
    assert result["success"] is True
    assert result["provider"] == "fake"
    assert result["tool_call"]["tool_name"] == "get_index_info"


def test_strict_json_tool_call_parse_success():
    result = parse_strict_tool_call(
        '{"tool_name": "get_index_info", "arguments": {}}'
    )
    assert result == {"tool_name": "get_index_info", "arguments": {}}


def test_strict_json_rejects_natural_language_prefix():
    try:
        parse_strict_tool_call(
            'I will call a tool.\n{"tool_name": "get_index_info", "arguments": {}}'
        )
    except ValueError as exc:
        assert "valid JSON" in str(exc)
    else:
        raise AssertionError("natural language mixed with JSON should be rejected")


def test_strict_json_rejects_extra_keys():
    try:
        parse_strict_tool_call(
            '{"tool_name": "get_index_info", "arguments": {}, "reason": "check"}'
        )
    except ValueError as exc:
        assert "only" in str(exc)
    else:
        raise AssertionError("extra planner keys should be rejected")


def test_ask_langchain_route_still_registered():
    route_paths = {route.path for route in app.main.app.routes}
    assert "/ask_langchain" in route_paths
    assert "/agent_demo" in route_paths


if __name__ == "__main__":
    # 这些测试只验证 agent demo 的安全边界和只读 RAG tool 编排，不启动 FastAPI。
    test_get_index_info_read_only()
    test_rebuild_blocked_without_request_authorization()
    test_rebuild_authorized_but_executor_still_guarded()
    test_search_knowledge_base_uses_read_only_rag_tool_chain()
    test_unknown_tool_rejected()
    test_invalid_arguments_rejected()
    test_fake_planner_provider_still_available()
    test_strict_json_tool_call_parse_success()
    test_strict_json_rejects_natural_language_prefix()
    test_strict_json_rejects_extra_keys()
    test_ask_langchain_route_still_registered()
    print("agent_demo phase-three tests passed")
